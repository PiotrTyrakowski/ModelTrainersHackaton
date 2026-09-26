"""Preserve PDF pages and propose question boundaries for explicit review.

This is text extraction and layout preservation, not OCR or a semantic parser.
All imported question candidates remain needs_review and are blocked from solver
export until someone verifies the segmentation, visual sources, type and points.
"""

from collections import Counter
from dataclasses import asdict
from pathlib import Path
import re
import shutil
import subprocess
from .models import Task, SourceRecord, SourceRef, PageSpan, AnswerKey
from .dataset import Dataset, write_json, write_jsonl, sha256_file
from .imports import new_output

HEADER = re.compile(
    r"^[ \t]*Zadanie[ \t]+(\d+(?:\.\d+)?)\.?[ \t]*(?:\([ \t]*0[ \t]*[–−-][ \t]*(\d+)[ \t]*\))?[^\S\n]*",
    re.M,
)


def segment_pages(pages, exam_id):
    """Return candidate tasks and exact spans into the unmodified page texts."""
    offsets = []
    parts = []
    pos = 0
    for i, text in enumerate(pages, 1):
        offsets.append((i, pos, pos + len(text)))
        parts.append(text)
        pos += len(text) + 3
    full = "\n\f\n".join(parts)
    headers = list(HEADER.finditer(full))
    counts = Counter(m[1] for m in headers)
    groups = {}
    for i, m in enumerate(headers):
        groups.setdefault(m[1].split(".")[0], []).append((i, m))

    def spans(a, b):
        return tuple(
            PageSpan(page, max(a, start) - start, min(b, end) - start)
            for page, start, end in offsets
            if max(a, start) < min(b, end)
        )

    tasks = []
    occurrences = Counter()
    for index, m in enumerate(headers):
        original = m[1]
        group = groups[original.split(".")[0]]
        children = [h for _, h in group if "." in h[1]]
        if "." not in original and children:
            continue  # shared sources belong to the subitems
        end = headers[index + 1].start() if index + 1 < len(headers) else len(full)
        task_spans = spans(m.start(), end)
        shared = ""
        shared_spans = ()
        roots = [h for _, h in group if "." not in h[1] and h.start() < m.start()]
        notes = [
            "Automatic PDF segmentation is unreviewed.",
            "Page furniture, answer lines and source text are preserved; prompt/source separation needs review.",
        ]
        if children:
            if len(roots) == 1:
                root = roots[0]
                first_child = min(h.start() for h in children)
                shared = full[root.start() : first_child].strip()
                shared_spans = spans(root.start(), first_child)
            else:
                notes.append("Missing or ambiguous parent-task source block.")
        if counts[original] > 1:
            notes.append(
                "Duplicate task heading; inspect all occurrences before merging."
            )
        points = int(m[2]) if m[2] else None
        if points is None:
            notes.append("Point value was not recognised in the heading.")
        occurrences[original] += 1
        tid = (
            original if counts[original] == 1 else f"{original}~{occurrences[original]}"
        )
        all_spans = tuple(
            sorted(set(shared_spans + task_spans), key=lambda s: (s.page, s.start))
        )
        page_numbers = tuple(sorted({s.page for s in all_spans}))
        tasks.append(
            Task(
                tid,
                exam_id,
                full[m.start() : end].strip(),
                "unknown",
                shared,
                (),
                (SourceRef("exam-pdf", page_numbers, all_spans, item_id=original),),
                points,
                {},
                "needs_review",
                tuple(notes),
                original,
            )
        )
    return tasks


def import_pdf(
    pdf_path,
    output,
    exam_id,
    source_uri=None,
    render=True,
    dpi=110,
    pdftoppm="pdftoppm",
):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Install tasks-data[pdf] to extract PDF text") from error
    if not 50 <= dpi <= 300:
        raise ValueError("Use a rendering resolution between50and300DPI")
    pdf_path = Path(pdf_path).resolve()
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    if sum("Zasady oceniania" in t for t in pages) >= 3:
        raise ValueError(
            "This looks like a marking scheme; do not import grading text as questions"
        )
    tasks = segment_pages(pages, exam_id)
    root = new_output(output)
    (root / "raw").mkdir()
    shutil.copy2(pdf_path, root / "raw/exam.pdf")
    write_jsonl(
        root / "raw/pages.jsonl",
        [
            {
                "page": i + 1,
                "text": text,
                "text_extracted": bool(text.strip()),
                "character_count": len(text),
            }
            for i, text in enumerate(pages)
        ],
    )
    (root / "raw/exam.txt").write_text("\f".join(pages), encoding="utf-8")
    sources = [
        SourceRecord(
            "exam-pdf",
            exam_id,
            "exam_pdf",
            source_uri or pdf_path.as_uri(),
            sha256_file(pdf_path),
            "raw/exam.pdf",
            metadata={
                "pdf_pages": len(pages),
                "page_numbering": "PDF file page index,1-based; may differ from printed page numbers",
                "extracted_pages_source_id": "page-texts",
            },
        ),
        SourceRecord(
            "page-texts",
            f"{exam_id}, extracted page texts",
            "reference",
            (source_uri or pdf_path.as_uri()) + "#extracted-text",
            sha256_file(root / "raw/pages.jsonl"),
            "raw/pages.jsonl",
        ),
        SourceRecord(
            "plain-text",
            f"{exam_id}, joined raw text",
            "reference",
            (source_uri or pdf_path.as_uri()) + "#plain-text",
            sha256_file(root / "raw/exam.txt"),
            "raw/exam.txt",
        ),
    ]
    requested = sorted(
        {page for task in tasks for ref in task.source_refs for page in ref.pages}
    )
    images = {}
    if render and requested:
        binary = shutil.which(pdftoppm)
        if binary is None:
            raise RuntimeError(
                "pdftoppm is required for page images; install Poppler or explicitly use --no-render (drafts only)"
            )
        (root / "pages").mkdir()
        for page in requested:
            prefix = root / "pages" / f"page-{page:03d}"
            subprocess.run(
                [
                    binary,
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-singlefile",
                    "-r",
                    str(dpi),
                    "-png",
                    str(root / "raw/exam.pdf"),
                    str(prefix),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            local = f"pages/page-{page:03d}.png"
            images[page] = local
            sources.append(
                SourceRecord(
                    f"page:{page}",
                    f"{exam_id}, PDF page{page}",
                    "image",
                    sources[0].uri + f"#page={page}",
                    sha256_file(root / local),
                    local,
                    metadata={
                        "derived_from": "exam-pdf",
                        "page": page,
                        "renderer": "pdftoppm",
                        "dpi": dpi,
                    },
                )
            )
    from dataclasses import replace

    tasks = [
        replace(
            t,
            image_paths=tuple(
                images[p] for ref in t.source_refs for p in ref.pages if p in images
            ),
            review_notes=t.review_notes
            + (
                ()
                if render
                else (
                    "Page PNGs were not rendered; visual content remains in raw/exam.pdf.",
                )
            ),
        )
        for t in tasks
    ]
    metadata = {
        "importer": "pdf-candidates-v1",
        "pdf_pages": len(pages),
        "pages_with_text": sum(bool(t.strip()) for t in pages),
        "candidate_tasks": len(tasks),
        "rendered_pages": len(images),
        "render_dpi": dpi if render else None,
        "segmentation_status": "needs_human_review",
        "ocr_used": False,
        "grading_status": "manual placeholders; no answer key inferred",
        "warnings": (
            []
            if tasks
            else [
                "No task markers detected; scanned documents or unsupported layouts require review/OCR."
            ]
        ),
    }
    dataset = Dataset(
        exam_id,
        tasks,
        sources,
        [AnswerKey(t.id, max_points=t.max_points) for t in tasks],
        metadata,
        root,
    )
    dataset.save()
    write_json(
        root / "review-queue.json",
        [
            {
                "id": t.id,
                "original_id": t.original_id,
                "pages": [p for ref in t.source_refs for p in ref.pages],
                "notes": list(t.review_notes),
            }
            for t in tasks
        ],
    )
    return dataset
