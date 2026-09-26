# tasks-data

A local Python package for source-preserving matura task datasets and retrieval of stored complete essays. It keeps task inputs separate from grading records, preserves PDF pages and marks uncertain extraction for review.

From the repository root:

```sh
python3 -m pip install -e 'packages/tasks-data[pdf,test]'
python3 -m unittest discover -s packages/tasks-data/tests -v
tasks-data --help
```

PDF rendering also requires Poppler (`pdftoppm`). The core schemas, structured JSON importer and dataset validation use only the Python standard library; PDF text extraction uses the optional `pypdf` dependency.

See [tasks and imports](../../docs/tasks-data.md) for the schema, commands and current imports. Essay retrieval is implemented separately; see [the essay-bank guide](../../docs/essay-bank.md).

The older experimental task generator is paused and is not included in this package.
