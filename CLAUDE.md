# AeroRAG — Aviation Knowledge Assistant

## 1. Project Overview

AeroRAG is an aviation-focused Retrieval-Augmented Generation (RAG) application that answers questions using a curated collection of aviation learning documents, including PDFs containing text, figures, diagrams, and tables.

The primary goal is to build a reliable, source-grounded aviation knowledge assistant that retrieves relevant passages from the supplied documents and uses a Large Language Model (LLM) to generate answers with traceable source references.

The project also serves as a learning and portfolio project for exploring modern AI application development, document processing, information retrieval, embeddings, and LLM integration.

## 2. Project Goals

- Build an end-to-end RAG pipeline for aviation documents.
- Extract text in correct reading order from multi-column PDFs.
- Extract and preserve document structure and metadata.
- Identify document sections and subsections.
- Create semantically coherent chunks suitable for retrieval.
- Implement embedding generation and semantic search.
- Evaluate hybrid keyword and vector search.
- Generate answers grounded in retrieved source passages.
- Provide citations that identify the source document and page.
- Evaluate retrieval quality, answer correctness, and citation accuracy.
- Progressively support figures, diagrams, and tables.

The initial document collection consists of approximately ten aviation PDFs. The documents contain a mixture of machine-readable text, images, and structured layouts.

## 3. Technology Stack

### Currently used

- **Python** — primary implementation language.
- **LlamaParse (LlamaCloud Extract API)** — extraction of each PDF into structured JSON: document title, page label, and sections with start/end page labels and content. This is the current extraction baseline and the foundation for chunking (see section 5.1).
- **llama-cloud** (Python client) — calls the LlamaParse Extract API.
- **python-dotenv** — loads API keys from the local, git-ignored `.env` file.
- **PyMuPDF (fitz)** — page metadata access: page dimensions, image counts, and page identifiers.
- **Python dataclasses** — explicit data models for extracted document structures.
- **pytest** — automated testing.

### Planned

- Azure OpenAI — embedding generation and LLM-based answer generation.
- A vision-capable model (provider to be selected) — extraction of knowledge from figures, diagrams, and tables. Deferred to a later phase (see section 5.4).
- Azure AI Search — vector and hybrid retrieval.
- FastAPI — HTTP API for the RAG application.
- Azure AI Document Intelligence — optional layout-aware extraction for difficult PDFs. Lower priority now that LlamaParse provides the structured baseline.
- A lightweight web interface — optional user-facing question-and-answer application.

Keep the initial implementation explicit and modular. Introduce additional libraries and managed services only when they provide a clear benefit.

## 4. Architecture and Processing Pipeline

The application follows a staged document-processing and retrieval pipeline:

```text
Aviation PDFs
     |
     v
LlamaParse Extract API (structured extraction: sections, page labels, content)
     |
     v
JSON file per document (data/extracted/<name>.json)
     |
     v
Sections with page ranges (read from the JSON)
     |
     v
Chunker
     |
     v
Text chunks with metadata
     |
     v
Embedding generation
     |
     v
Search index
     |
     v
Retriever
     |
     v
LLM answer generation
     |
     v
Answer with source references
```

`PdfDocumentLoader` (PyMuPDF) runs alongside the LlamaParse extraction to supply page metadata, image counts, and page identifiers.

The ingestion pipeline must remain independent of the embedding provider, search backend, and LLM provider wherever practical. The same applies to the PDF extraction provider: the LlamaParse Extract API must be wrapped behind a small interface so that it can be replaced.

## 5. Current Implementation Status

### 5.1 Structured extraction (current baseline)

The geometric approach to reading order (PyMuPDF spans/blocks plus `LayoutAnalyzer`) proved error-prone on the multi-column layouts of `chapter15_Airspace.pdf`. The project therefore uses a structured extraction service:

- The **LlamaParse Extract API** (`LlamaParseDocumentExtractor` in `src/ingestion/llamaParse_document_extractor.py`) extracts each PDF into JSON using a schema. Directories come from `config/application.yml` (`ExtractionConfig` in `src/ingestion/config.py`). The schema asks for `document_title`, `page number`, and a `sections` list. Each section has `section_title`, `start_page`, `end_page`, and `content`. Page labels use the `NN-N` form (for example `15-3`).
- The JSON is stored under `data/extracted/` (for example `data/extracted/chapter15_Airspace.json`) so that downstream stages can be run and tested without repeated API calls.
- **The JSON is the foundation for chunking.** Sections, their page ranges, and their text come from this file. Chunks inherit `document_id`, `start_page`, `end_page`, and `section_title` from it.
- The earlier **Nutrient API** Markdown (`data/extracted/chapter15_Airspace.md`) is kept for reference and comparison only. It is no longer an input to any stage.
- The extraction stage must be wrapped behind a small provider-independent interface. `LlamaParseDocumentExtractor.extract(document_name)` takes a document name from the configured documents directory and writes the JSON to the configured output directory. The client is injected, so tests use a fake client. The extraction stage must not mix in section building, chunking, or LLM calls.

**Known limitations of this baseline:**

- Section boundaries and page labels are produced by the extraction model, not by PDF geometry. They must be validated against the PDF before the chunker relies on them. Validation must check `start_page` and `end_page` on representative pages of `chapter15_Airspace.pdf` (particularly pages 2, 3, and 4) and be covered by regression tests.
- Do not claim the extraction is correct for all PDFs based on a single document.
- Page labels are printed page labels (for example `15-3`), not PDF page indexes. Confirm the mapping against the PDF before using them as citation targets.
- `content` still contains figure references (for example `[Figure 15-2]`) and figure captions (for example `Figure 15-2. An example of a prohibited area`). A cleanup step is needed before chunking: remove figure references and captions, and repair text they interrupt. The cleanup must be validated against the sample document and covered by regression tests. Whether it is AI-based or rule-based is a decision for later.
- `content` contains U+FFFD replacement characters (`�`) where quotation marks were lost. These must be repaired or documented before retrieval.
- The JSON file does not store the per-field citation and confidence metadata that the extraction script prints. Decide whether to store it.

`PdfDocumentLoader` uses PyMuPDF's `page.get_text("dict")` to preserve text spans, lines, blocks, font properties, and bounding-box coordinates. It is retained for page metadata (page dimensions, image counts, identifiers). Its geometry and font data are not inputs to sections or chunks. It is no longer the source of the text baseline.

The current data model includes:

- `TextSpan`
- `TextLine`
- `TextBlock`
- `DocumentPage`
- `Section` (initial model)

The JSON-based section model is not yet defined in code. Any earlier section model (for example `MarkdownSection`) was written for the Markdown-based design and must be reviewed against the JSON fields before it is used.

### 5.2 Layout analysis (superseded)

`LayoutAnalyzer` estimated reading order from the geometry of PyMuPDF text blocks. Because the LlamaParse extraction now provides structured sections in reading order, `LayoutAnalyzer` is superseded and must not be extended.

Its existing code and tests are kept until the extraction baseline is validated. Once the replacement is in place, the team decides whether to remove it. Any layout cases it previously solved should be checked against the extracted output and carried into regression tests.

The geometric approach revealed the following challenges, which the extraction baseline must be validated against:

- Two-column layouts on several pages.
- Full-width content alongside column-based content.
- Paragraphs that continue from one column into another.
- Text embedded in figures.
- Tables whose cell relationships are not preserved by simple text extraction.
- Extraction order that differs from visual reading order.

### 5.3 Sections

Sections come from the LlamaParse JSON (section 5.1). The earlier design, in which a `SectionBuilder` derived sections from Markdown heading markers, is superseded by this change.

- Each JSON section provides `section_title`, `start_page`, `end_page`, and `content`. These are the section's title, page range, and text.
- The JSON has no heading level. The current extraction schema does not expose subsections, so the section hierarchy is flat. Adding a hierarchy requires a schema change and validation against the sample document.
- The JSON section list is the input to the Chunker. Whether a separate stage is still needed to validate and normalise these sections (the role `SectionBuilder` was meant to play) is an open decision.
- Whatever that stage does, it must not use PDF geometry, font data, or `HeadingClassifier` output. Section boundaries must not be re-derived with text-pattern heuristics on the content. Errors in section boundaries or page labels are handled by changing the extraction schema or prompt and re-validating against the PDF.

### 5.4 Images, figures, and tables (deferred)

Images, figures, diagrams, and tables are out of scope for the current phase. The text baseline is intentionally text-only.

In a later phase, a vision-capable model will read these elements, extract the relevant knowledge, and store it as additional retrievable content linked to the source document and page. Until then:

- Do not treat the extracted text (JSON `content`) as a complete representation of a page that contains figures or tables.
- Keep image counts and page identifiers from `PdfDocumentLoader` so that pages with non-text content can be identified and flagged.
- Answers that depend on figure or table content must acknowledge that this content is not yet indexed.

### 5.5 Chunking and retrieval

Chunking, embedding generation, indexing, retrieval, and LLM answer generation are planned stages.

Do not assume these components already exist. Implement and validate each stage incrementally.

## 6. Design Principles

### Separation of concerns

Each component must have one clear responsibility:

- Extraction stage: convert a PDF into structured JSON (sections, page labels, content) via the LlamaParse Extract API, behind a provider-independent interface.
- `PdfDocumentLoader`: extract physical page metadata and geometry (PyMuPDF).
- Section handling: read and validate the sections in the extracted JSON. It uses no PDF geometry or font data (see section 5.3).
- `Chunker`: produce retrieval-ready passages from the JSON sections.
- `EmbeddingService`: convert text into vectors.
- `SearchService`: retrieve relevant passages.
- `AnswerService`: generate grounded answers using retrieved evidence.
- `LayoutAnalyzer`: superseded; do not extend (see section 5.2).

Do not mix section handling, embedding generation, or LLM calls into the PDF loader or the extraction stage.

### Preserve source information

Keep document IDs, page numbers, original text, and useful layout metadata throughout ingestion.

Every generated chunk should be traceable to its source document and page. Preserve additional section metadata when available.

### Explicit and testable implementation

Prefer small Python classes with clear interfaces and type hints. Avoid unnecessary abstractions, premature optimization, and large orchestration frameworks.

Use unit tests for isolated algorithms (for example section validation and chunking on JSON fixtures) and integration tests for the actual PDF-processing pipeline. Tests that call the LlamaParse API must not run on every test run; use the cached JSON in `data/extracted/` or recorded fixtures instead.

### Secrets and configuration

LlamaParse credentials (`LLAMA-PARSE_API_KEY`), Nutrient API credentials (legacy), and Azure keys are read from environment variables or local, uncommitted configuration (`.env`, git-ignored). They must never be written into source files, tests, or committed data.

### Evidence-based iteration

Inspect extracted output before changing algorithms. Validate changes against representative pages and preserve regression tests for previously solved cases.

Do not claim that a heuristic or extraction works for every PDF based on a single document.

### Grounded answers

The eventual RAG application should answer from retrieved document evidence, identify supporting sources, and acknowledge when the available evidence is insufficient.

Aviation information can be safety-critical. The assistant must not present unsupported generated content as authoritative flight instruction or a substitute for official, current aviation publications.

## 7. Development Roadmap

Work through the following milestones in order:

1. **Establish the structured extraction baseline:** wrap the LlamaParse Extract API behind a provider-independent interface, store the JSON under `data/extracted/`, and validate section boundaries and page labels on `chapter15_Airspace.pdf` (pages 2, 3, and 4). Add regression tests.
2. **Validate and load JSON sections:** load the extracted JSON into section records with document ID, page range, title, and content. Clean up figure references and captions and repair U+FFFD characters, then validate against the sample document. Decide whether a separate section-normalisation stage is still needed.
3. **Implement Chunker:** create coherent chunks with document, page, and section metadata from the JSON sections.
4. **Build ingestion tests:** validate extraction, section hierarchy, and chunk quality across representative PDFs.
5. **Integrate embeddings:** generate embeddings for the processed chunks.
6. **Implement retrieval:** start with vector search and evaluate hybrid search.
7. **Implement grounded generation:** pass retrieved evidence to an LLM and produce source references.
8. **Evaluate the RAG pipeline:** measure retrieval relevance, answer correctness, citation accuracy, and behavior when evidence is missing.
9. **Improve multimodal ingestion:** use a vision-capable model to extract knowledge from figures, diagrams, and tables, and index it with source document and page references.
10. **Expose the application:** provide an API and, optionally, a web interface.

## 8. Guidance for AI Coding Assistants

When modifying AeroRAG:

- Read the existing models and implementations before proposing changes.
- Preserve existing interfaces unless a concrete problem justifies changing them.
- Do not invent project files, classes, dependencies, or test results.
- Provide complete, consistent code when asked to implement a component.
- Explain significant algorithmic decisions and their limitations.
- Prefer changes that can be validated through tests and diagnostic output.
- Keep the project suitable for a developer learning RAG internals.
- Do not extend `LayoutAnalyzer`; build on the extracted JSON baseline instead.
- Do not skip ahead to embeddings, LLM integration, or image interpretation while the current ingestion milestone remains unresolved.
- Do not call the LlamaParse API from tests or routine runs when the cached JSON is available.
- When changing data models, update all dependent code and tests.
- Treat the actual PDF contents and observed diagnostics (including the extracted JSON) as the source of truth for extraction- and layout-specific decisions.

## 9. Immediate Next Task

Validate the LlamaParse JSON in `data/extracted/chapter15_Airspace.json` against `chapter15_Airspace.pdf`, particularly pages 2, 3, and 4. Check that each section's `start_page` and `end_page` are correct and that section text follows the PDF's reading order. Add regression tests for the checks.

Then define the section model for the JSON fields, remove or repair figure references, captions, and U+FFFD characters in `content`, and implement the Chunker on top of the validated sections.

The immediate objective is a reliable, inspectable ingestion pipeline that transforms raw aviation PDFs into structured, traceable document sections and retrieval-ready chunks. Images, figures, and tables are handled in a later phase.


## Testing Standards
- **Pattern:** Always use the **Given-When-Then** (BDD) pattern when writing tests.
- Clearly separate or comment the steps in your test functions:
  - `# Given` (Setup inputs and mocks)
  - `# When` (Execute the function under test)
  - `# Then` (Assert expected outcomes)
