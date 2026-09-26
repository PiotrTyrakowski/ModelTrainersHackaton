import argparse
from dataclasses import replace
import json
from pathlib import Path
from .dataset import Dataset
from .imports import import_structured


def _embedding_args(parser, required=False):
    parser.add_argument("--embedding-url", required=required)
    parser.add_argument("--embedding-model", required=required)
    parser.add_argument("--embedding-revision", default="unspecified")
    parser.add_argument("--api-key-env")
    parser.add_argument("--query-prefix", default="")
    parser.add_argument("--document-prefix", default="")


def _embedder(args):
    from .embeddings import HttpEmbedder

    if not args.embedding_url or not args.embedding_model:
        raise ValueError("Provide both embedding URL and model")
    return HttpEmbedder(
        args.embedding_url,
        args.embedding_model,
        args.embedding_revision,
        args.api_key_env,
        args.query_prefix,
        args.document_prefix,
    )


def _new_file(path):
    if path and (Path(path).exists() or Path(path).is_symlink()):
        raise ValueError(f"Refusing to overwrite existing output: {path}")


def _write_new(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prepare source-preserving matura datasets and keep grading separate"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("import-json")
    p.add_argument("exam")
    p.add_argument("--output", required=True)
    p.add_argument("--types")
    p.add_argument("--source-uri")
    p = commands.add_parser("import-pdf")
    p.add_argument("pdf")
    p.add_argument("--output", required=True)
    p.add_argument("--exam-id", required=True)
    p.add_argument("--source-uri")
    p.add_argument("--no-render", action="store_true")
    p.add_argument("--dpi", type=int, default=110)
    for name in ["inspect", "validate"]:
        p = commands.add_parser(name)
        p.add_argument("dataset")
    p = commands.add_parser("export-inputs")
    p.add_argument("dataset")
    p.add_argument("--output", required=True)
    p = commands.add_parser("review-task")
    p.add_argument("dataset")
    p.add_argument("id")
    p.add_argument("--type", required=True)
    p.add_argument("--points", type=float, required=True)
    p.add_argument("--prompt-file")
    p.add_argument("--source-file")
    p.add_argument("--note", required=True)
    p = commands.add_parser("essay-match")
    p.add_argument("bank")
    p.add_argument("query")
    p.add_argument("--method", choices=["lexical", "dense"], default="lexical")
    p.add_argument("--min-score", type=float)
    p.add_argument("--min-margin", type=float, default=0.03)
    p.add_argument("--index")
    p.add_argument("--query-vector")
    p.add_argument("--output")
    p.add_argument("--essay-output")
    _embedding_args(p)
    p = commands.add_parser("essay-index")
    p.add_argument("bank")
    p.add_argument("--output", required=True)
    _embedding_args(p, required=True)
    args = parser.parse_args(argv)
    if args.command in {"essay-match", "essay-index"}:
        from .essay_bank import EssayBank, EssayQuery, EmbeddingIndex

        _new_file(args.output)
        if args.command == "essay-index":
            bank = EssayBank.from_jsonl(args.bank)
            index = bank.build_index(_embedder(args))
            index.write(args.output)
            print(
                json.dumps(
                    {
                        "status": "indexed",
                        "output": args.output,
                        "encoder_id": index.encoder_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        _new_file(args.essay_output)
        if (
            args.output
            and args.essay_output
            and Path(args.output).resolve() == Path(args.essay_output).resolve()
        ):
            raise ValueError("Trace output and essay output must be different files")
        bank = EssayBank.from_jsonl(args.bank)
        query = EssayQuery.from_dict(
            json.loads(Path(args.query).read_text(encoding="utf-8"))
        )
        model_args = bool(
            args.embedding_url
            or args.embedding_model
            or args.api_key_env
            or args.query_prefix
            or args.document_prefix
            or args.embedding_revision != "unspecified"
        )
        options = {}
        if args.method == "lexical":
            if args.index or args.query_vector or model_args:
                raise ValueError("Lexical matching accepts no embedding inputs")
        else:
            if not args.index:
                raise ValueError("Dense matching requires --index")
            options["index"] = EmbeddingIndex.read(args.index)
            if args.query_vector:
                if model_args:
                    raise ValueError(
                        "Choose a precomputed query vector or an embedding service, not both"
                    )
                vector = json.loads(Path(args.query_vector).read_text(encoding="utf-8"))
                if set(vector) != {"encoder_id", "vector"}:
                    raise ValueError(
                        "Query vector file needs exactly encoder_id and vector"
                    )
                options.update(
                    query_vector=vector["vector"], encoder_id=vector["encoder_id"]
                )
            else:
                options["embedder"] = _embedder(args)
        result = bank.match(
            query,
            method=args.method,
            min_score=args.min_score,
            min_margin=args.min_margin,
            **options,
        )
        payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            _write_new(args.output, payload.encode("utf-8"))
        if result.status == "matched" and args.essay_output:
            _write_new(args.essay_output, result.essay.encode("utf-8"))
        print(payload, end="")
        if result.status == "no_match":
            raise SystemExit(2)
        return
    if args.command == "import-json":
        types = json.loads(Path(args.types).read_text()) if args.types else None
        ds = import_structured(args.exam, args.output, types, args.source_uri)
        result = ds.validate()
    elif args.command == "import-pdf":
        from .pdf_import import import_pdf

        ds = import_pdf(
            args.pdf,
            args.output,
            args.exam_id,
            args.source_uri,
            not args.no_render,
            args.dpi,
        )
        result = ds.validate()
    elif args.command in ["inspect", "validate"]:
        ds = Dataset.load(args.dataset)
        result = ds.validate()
        if args.command == "inspect":
            result["metadata"] = ds.metadata
    elif args.command == "export-inputs":
        ds = Dataset.load(args.dataset)
        result = {
            "exported": ds.export_solver_inputs(args.output),
            "output": args.output,
        }
    else:
        ds = Dataset.load(args.dataset)
        matches = [t for t in ds.tasks if t.id == args.id]
        if len(matches) != 1:
            raise ValueError("Task ID not found")
        old = matches[0]
        new = replace(
            old,
            question_type=args.type,
            max_points=args.points,
            review_status="ready",
            prompt=(
                Path(args.prompt_file).read_text() if args.prompt_file else old.prompt
            ),
            source_text=(
                Path(args.source_file).read_text()
                if args.source_file
                else old.source_text
            ),
            review_notes=old.review_notes + ("Human review: " + args.note,),
        )
        ds.tasks = [new if t.id == args.id else t for t in ds.tasks]
        ds.keys = [
            replace(k, max_points=args.points) if k.task_id == args.id else k
            for k in ds.keys
        ]
        result = ds.save()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
