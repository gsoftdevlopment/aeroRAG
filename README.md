# AeroRAG

AeroRAG is an aviation knowledge assistant built with Retrieval-Augmented Generation (RAG). The goal is to answer aviation questions from a curated set of learning documents, with every answer traceable to its source document and page.

This is also a learning and portfolio project for document processing, information retrieval, embeddings, and LLM integration.

> **Safety notice:** AeroRAG is a study aid. Its answers are not flight instruction and do not replace official, current aviation publications.

## Status

The project is at an early stage. The text-extraction baseline is in place; the later stages are not.

| Stage | Status |
| --- | --- |
| PDF → Markdown extraction (Nutrient API) | Implemented (`PdfContentExtractor`) |
| Markdown loading into page-numbered blocks | Implemented (`MarkdownDocumentLoader`) |
| Section building from heading markers | Planned (`SectionBuilder`) |
| Chunking | Planned |
| Embeddings and search index | Planned |
| Retrieval | Planned |
| Grounded answer generation with citations | Planned |
| Figures, diagrams, and tables | Deferred |
| API and web interface | Planned |

## Pipeline

```text
Aviation PDFs
  -> Nutrient API (reading-ordered Markdown)
  -> Markdown file per document (data/extracted/)
  -> MarkdownDocumentLoader (page-numbered blocks)
  -> SectionBuilder            [planned]
  -> Chunker                   [planned]
  -> Embeddings / search index [planned]
  -> Retriever                 [planned]
  -> LLM answer with sources   [planned]
```

`PdfDocumentLoader` (PyMuPDF) supplies page metadata such as page dimensions, image counts, and page identifiers alongside this pipeline.

Images, figures, diagrams, and tables are not part of the Markdown baseline. Pages that depend on them are flagged, and answers that depend on them say so.

## Project layout

```text
src/
  ingestion/
    nutrient_pdf_content_extractor.py   PdfContentExtractor: PDF -> Markdown via Nutrient API
    markdown_document_loader.py         MarkdownDocumentLoader: Markdown -> page-numbered blocks
    models.py                           MarkdownBlock, MarkdownDocument, BlockType
    llamaParse_pdf_content_extractor.py Standalone LlamaParse experiment (script, not a module)
tests/
  ingestion/test_markdown_document_loader.py  Unit tests and sample-document checks
  document_loader_output_check.py             Diagnostic script for loader output
data/
  documents/   Source PDFs (not committed)
  extracted/   Cached Markdown output (committed, so tests need no API calls)
```

## Requirements

- Python 3.11 or newer
- A Nutrient API key, if you need to run extraction again

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate in cmd/PowerShell
pip install -e .
pip install pytest
```

Create a `.env` file in the project root (it is git-ignored):

```text
NUTRIENT_API_KEY=your-key-here
```

Never commit `.env` or put API keys in source files, tests, or committed data.

## Usage

Extract a PDF to Markdown (calls the Nutrient API and uses credits):

```python
from ingestion.nutrient_pdf_content_extractor import PdfContentExtractor

extractor = PdfContentExtractor.from_env()
markdown = extractor.extract_markdown("data/documents/chapter15_Airspace.pdf")
```

Load cached Markdown into page-numbered blocks (no API call):

```python
from ingestion.markdown_document_loader import MarkdownDocumentLoader

document = MarkdownDocumentLoader().load("data/extracted/chapter15_Airspace.md")
```

Inspect the loader output for the sample document:

```bash
python tests/document_loader_output_check.py
```

## Testing

```bash
python -m pytest
```

Tests use cached Markdown in `data/extracted/` and do not call the Nutrient API. The tests follow the Given-When-Then pattern.

## Data and licensing

Source PDFs in `data/documents/` are excluded from version control because they may be copyrighted. Place your own copies there to run extraction.

## Contributing

- Read `CLAUDE.md` for the architecture rules and design principles.
- Keep each component to one responsibility, and add tests for new behavior.
- Validate extraction changes against the sample document before claiming they work.
