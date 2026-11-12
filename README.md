# AeroRAG

AeroRAG is an aviation knowledge assistant built with Retrieval-Augmented Generation (RAG). The goal is to answer aviation questions from a curated set of learning documents, with every answer traceable to its source document and page.

This is also a learning and portfolio project for document processing, information retrieval, embeddings, and LLM integration.

> **Safety notice:** AeroRAG is a study aid. Its answers are not flight instruction and do not replace official, current aviation publications.

## Status

The project is at an early stage. The extraction baseline is in place; the later stages are not.

| Stage | Status |
| --- | --- |
| PDF → structured JSON (LlamaParse Extract API) | Implemented (`LlamaParseDocumentExtractor`) |
| JSON sections with page ranges as chunking input | Format defined; loader not yet implemented |
| Chunking | Planned |
| Embeddings and search index | Planned |
| Retrieval | Planned |
| Grounded answer generation with citations | Planned |
| Figures, diagrams, and tables | Deferred |
| API and web interface | Planned |

## Pipeline

```text
Aviation PDFs
  -> LlamaParse Extract API (sections, page ranges, content)
  -> JSON file per document (data/extracted/<name>.json)   <- chunking foundation
  -> Chunker                   [planned]
  -> Embeddings / search index [planned]
  -> Retriever                 [planned]
  -> LLM answer with sources   [planned]
```

`PdfDocumentLoader` (PyMuPDF) supplies page metadata such as page dimensions, image counts, and page identifiers alongside this pipeline.

Images, figures, diagrams, and tables are not part of the text baseline. Pages that depend on them are flagged, and answers that depend on them say so.

The earlier Nutrient API baseline (`data/extracted/chapter15_Airspace.md`) is kept for reference. It is no longer the source of sections.

## Extracted JSON format

Each document is extracted to one JSON file in `data/extracted/`. The file is the input to chunking.

```json
{
  "document_title": "",
  "page number": "15-3",
  "sections": [
    {
      "section_title": "Uncontrolled Airspace",
      "start_page": "15-3",
      "end_page": "15-3",
      "content": "Class G Airspace\nUncontrolled airspace or Class G airspace is ..."
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `document_title` | Document title as extracted. May be empty. |
| `page number` | Page label of the first page, in `NN-N` form (for example `15-3`). |
| `sections[]` | Ordered list of sections, produced by the extraction schema. |
| `section_title` | Section heading as extracted. May be empty for text before the first heading. |
| `start_page`, `end_page` | Page labels where the section starts and ends. Inclusive. |
| `content` | Section text. Paragraphs are separated by blank lines; bullets are kept as `* `. |

Known limitations of the current sample output:

- Page labels and section boundaries are produced by the extraction model, not read from the PDF geometry. They must be checked against the PDF before chunks rely on them.
- `content` still contains figure references (for example `[Figure 15-2]`) and figure captions (for example `Figure 15-2. An example of ...`).
- Some quotation marks are replaced by U+FFFD (`�`).
- The file does not store the per-field citation and confidence metadata that the script prints.

## Project layout

```text
config/
  application.yml                      Directory config (documents_dir, output_dir)
src/
  main.py                              Command-line entry point; triggers extraction
  ingestion/
    llamaParse_document_extractor.py   LlamaParseDocumentExtractor: PDF -> JSON via LlamaParse
    config.py                          ExtractionConfig, loaded from application.yml
tests/
  ingestion/test_config.py                           Config loading
  ingestion/test_llamaParse_document_extractor.py    Extractor with a fake client (no API calls)
data/
  documents/   Source PDFs (not committed)
  extracted/   Cached extraction output, committed so tests need no API calls
    chapter15_Airspace.json   LlamaParse output (chunking input)
    chapter15_Airspace.md     Earlier Nutrient API Markdown (reference)
requirements.txt   Runtime dependencies
pyproject.toml     Package metadata and dependencies
```

## Requirements

- Python 3.11 or newer
- A LlamaParse (LlamaCloud) API key, if you need to run extraction again

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate in cmd/PowerShell
pip install -r requirements.txt
pip install -e .
pip install pytest
```

Create a `.env` file in the project root (it is git-ignored):

```text
LLAMA-PARSE_API_KEY=your-key-here
```

The variable name matches `.env.example` and the extraction script. Never commit `.env` or put API keys in source files, tests, or committed data.

## Configuration

Directories are set in `config/application.yml`. Relative paths are resolved from the project root.

```yaml
extraction:
  documents_dir: data/documents   # source PDFs
  output_dir: data/extracted      # extracted JSON
```

If the file or a key is missing, the defaults above are used. The API key is never set in this file; it stays in `.env`.

## Usage

Extract one or more documents (calls the LlamaParse API and uses credits). Each name is a file inside `documents_dir`; a missing `.pdf` extension is added:

```bash
python src/main.py chapter15_Airspace.pdf
python src/main.py --config path/to/application.yml doc1.pdf doc2.pdf
```

The JSON is written to `output_dir` as `<document>.json`. The extractor can also be used from Python:

```python
from ingestion.llamaParse_document_extractor import LlamaParseDocumentExtractor

extractor = LlamaParseDocumentExtractor.from_env()
output_path = extractor.extract("chapter15_Airspace.pdf")
```

Load the cached JSON (no API call):

```python
import json
from pathlib import Path

data = json.loads(Path("data/extracted/chapter15_Airspace.json").read_text(encoding="utf-8"))
for section in data["sections"]:
    print(section["start_page"], section["section_title"])
```

## Testing

```bash
python -m pytest
```

Tests use cached files in `data/extracted/` and must not call the LlamaParse API. The tests follow the Given-When-Then pattern.

## Data and licensing

Source PDFs in `data/documents/` are excluded from version control because they may be copyrighted. Place your own copies there to run extraction.

## Contributing

- Read `CLAUDE.md` for the architecture rules and design principles.
- Keep each component to one responsibility, and add tests for new behavior.
- Validate extraction changes against the sample document before claiming they work.
