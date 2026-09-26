# Eight additional history exam/marking pairs

Downloaded **8 further CKE history papers and their marking guides: 16 PDFs,
539 PDF pages**. Files are under `data/raw/exams/history-more-papers-v1/`, with
each exam in `input/exam.pdf` and its separate guide in `grading/marking.pdf`.
All raw files remain local and ignored by Git. The public
[manifest](history-more-papers-v1.manifest.json) records URLs, hashes, physical
page counts and acquisition status.

| Archive session | Formula | Cover maximum | Status |
|---|---|---:|---|
| June 2026 | 2023 | 60 | Reserved evaluation candidate; cover/file checks only |
| June 2025 | 2023 | 60 | Downloaded; unreviewed |
| June 2024 | 2023 | 60 | Downloaded; unreviewed |
| June 2023 | 2023 | 60 | Downloaded; unreviewed |
| May 2022 | 2015 | 50 | Downloaded; unreviewed |
| May 2021 | 2015 | 50 | Downloaded; unreviewed |
| June 2020 archive entry | 2015 | 50 | Printed cover says 18 May 2020; date discrepancy retained for review |
| May 2019 | 2015 | 50 | Downloaded; unreviewed |

These supplement the previously held 2023 development paper and May 2024–2026
files. Older 50-point papers must not be compared as raw totals with the newer
60-point papers. Their question structure and essay rubrics also need separate
review before scoring.

Update, 27 September: the previously held **May 2025 and May 2026** papers are
now reviewed and active alongside 2023/2024 in the
[150-item non-essay suite](../nonessay-evaluation.md). That work does not change
the acquisition-only status of the eight additional sessions listed above.

## Source and verification

The publisher is CKE; acquisition used public copies on
[Arkusze.pl](https://arkusze.pl/historia-matura-poziom-rozszerzony/), the same
mirror used for the prior May downloads. This is explicitly a third-party
download host, not a direct CKE download or a claim of byte identity against an
official-host copy. The migrated official catalogue was inspected but returned
May 2026 when the requested additional session was selected.

Each landing page supplied exactly one matching exam and one marking-guide PDF.
All 16 PDFs parse; first-page subject/year and marking-guide identity were
checked. All eight exam covers were rendered and visually inspected, confirming
history, extended level and the formulas/maximum scores shown above. Published
bytes are preserved, including empty-reader-password PDF permission flags.

This is acquisition, not full question extraction or proof that every diagram
has been reviewed. In particular, the 2021 file has 40 PDF pages while its cover
instructions mention 39, and the 2020 file has 40 while its cover mentions 35.
Keep those discrepancies visible until the complete documents are reviewed.
The 2020 archive-session label and printed cover date are also kept distinct.

No new exam or marking guide entered the RAG corpus, active solver inputs,
prepared essay bank or current development runs. Question contents of June 2026
were not inspected by the assistant, apart from its cover metadata; reserve it
before tuning further. Search discovery exposed short marking snippets for
June 2024 and June 2025, so those must not be described as completely uninspected.
Reservation does not establish absence from a model's pretraining data.

## Reproduce

Use Python 3.10+, `curl`, `lxml` and `pypdf`:

```sh
python3 scripts/exams/download_history_papers.py \
  --config configs/exams/history-more-papers-v1.json \
  --output data/raw/exams/history-more-papers-v1
```

Existing completed snapshots are hash-checked before reuse. Downloads stop on
unexpected links, PDF identity, structure or network errors. Before evaluation,
extract candidate questions, inspect source images and boundaries, attach the
separate official grading records, and validate the complete point denominator.
Downloading a marking guide alone does not create reliable automatic answer keys.
