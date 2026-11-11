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
- **Nutrient API** — text extraction from PDFs to Markdown with reading order preserved. This is the current text baseline (see section 5.1).
- **PyMuPDF (fitz)** — page metadata access: page dimensions, image counts, and page identifiers.
- **Python dataclasses** — explicit data models for extracted document structures.
- **pytest** — automated testing.

### Planned

- Azure OpenAI — embedding generation and LLM-based answer generation.
- A vision-capable model (provider to be selected) — extraction of knowledge from figures, diagrams, and tables. Deferred to a later phase (see section 5.4).
- Azure AI Search — vector and hybrid retrieval.
- FastAPI — HTTP API for the RAG application.
- Azure AI Document Intelligence — optional layout-aware extraction for difficult PDFs. Lower priority now that the Nutrient API provides the text baseline.
- A lightweight web interface — optional user-facing question-and-answer application.

Keep the initial implementation explicit and modular. Introduce additional libraries and managed services only when they provide a clear benefit.

## 4. Architecture and Processing Pipeline

The application follows a staged document-processing and retrieval pipeline:

```text
Aviation PDFs
     |
     v
Nutrient API (text extraction, reading order preserved)
     |
     v
Markdown file per document
     |
     v
SectionBuilder
     |
     v
Structured sections and subsections (with page references)
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

`PdfDocumentLoader` (PyMuPDF) runs alongside the Nutrient extraction to supply page metadata, image counts, and page identifiers.

The ingestion pipeline must remain independent of the embedding provider, search backend, and LLM provider wherever practical. The same applies to the PDF text-extraction provider: the Nutrient API must be wrapped behind a small interface so that it can be replaced.

## 5. Current Implementation Status

### 5.1 PDF text extraction (new baseline)

The geometric approach to reading order (PyMuPDF spans/blocks plus `LayoutAnalyzer`) proved error-prone on the multi-column layouts of `chapter15_Airspace.pdf`. The project therefore changed approach:

- The **Nutrient API** extracts the text of each PDF and produces a Markdown file in the correct reading order. This Markdown is the new baseline for all downstream text processing.
- Extracted Markdown is stored under `data/extracted/` (for example `data/extracted/chapter15_Airspace.md`) so that downstream stages can be run and tested without repeated API calls.
- The extraction stage must be wrapped behind a small interface (planned name: `MarkdownExtractor`) that takes a PDF path and returns Markdown text plus the page-mapping information needed for citations.

**Known limitations of this baseline:**

- Images, figures, diagrams, and tables are **not** contained in the Markdown output. Their content is therefore absent from the text baseline and must be handled separately (section 5.4).
- Page traceability must be verified. Chunks must still cite a document and page, so the page boundaries in the Markdown must be recoverable, either from per-page output or from page markers. This must be confirmed against real output before the chunker depends on it.
- The Markdown reading order must be validated against representative pages (`chapter15_Airspace.pdf`, particularly pages 2, 3, and 4) and covered by regression tests. Do not claim the extraction is correct for all PDFs based on a single document.
- Some source PDFs contain figure labels or captions embedded in the text layer. Examples in `chapter15_Airspace.pdf`: the figure 15-1 labels on page 2 (block 004 in the loader check output) and the figure 15-4 caption interrupting a sentence on page 4 (block 037). These do not affect the rendered page but break automatic processing at that location.

**Planned cleanup step (before SectionBuilder):** an AI-based cleanup stage will remove such embedded figure labels and captions from the extracted Markdown, and repair text interrupted by them. It operates on the Markdown output, not on the PDF, and its results must be validated against the sample document and covered by regression tests.

`PdfDocumentLoader` uses PyMuPDF's `page.get_text("dict")` to preserve text spans, lines, blocks, font properties, and bounding-box coordinates. It is retained for page metadata (page dimensions, image counts, identifiers). Its geometry and font data are not inputs to `SectionBuilder` (see section 5.3). It is no longer the source of the text baseline.

The current data model includes:

- `TextSpan`
- `TextLine`
- `TextBlock`
- `DocumentPage`
- `Section` (initial model)

### 5.2 Layout analysis (superseded)

`LayoutAnalyzer` estimated reading order from the geometry of PyMuPDF text blocks. Because the Nutrient API now provides reading order, `LayoutAnalyzer` is superseded and must not be extended.

Its existing code and tests are kept until the Markdown baseline is validated. Once the replacement is in place, the team decides whether to remove it. Any layout cases it previously solved should be checked against the Markdown output and carried into regression tests.

The geometric approach revealed the following challenges, which the Markdown baseline must be validated against:

- Two-column layouts on several pages.
- Full-width content alongside column-based content.
- Paragraphs that continue from one column into another.
- Text embedded in figures.
- Tables whose cell relationships are not preserved by simple text extraction.
- Extraction order that differs from visual reading order.

### 5.3 Section building

`SectionBuilder` has not yet been implemented.

Its sole responsibility is to build sections from the Markdown produced by the extraction stage. It relies only on the Markdown heading markers (`#`, `##`, `###`, …) to determine each section's title, hierarchy level, and boundaries, and assigns the content that follows each heading to that section.

- `SectionBuilder` does not use font size, boldness, whitespace, indentation, position on the page, or any other PDF geometry to confirm, reject, or re-level a heading.
- `SectionBuilder` does not use text-pattern heuristics (for example, numbered-heading regexes or heading-like wording) to detect headings.
- Page references for each section, including sections that continue across pages, come from the page mapping established in section 5.1, not from geometry analysis.
- The existing `HeadingClassifier` (font- and bold-based) is not part of this design and must not feed `SectionBuilder`.
- If Markdown heading markers prove missing, inconsistent, or wrong, the problem is handled by inspecting and validating the extraction output, not by adding heuristics to `SectionBuilder`.

### 5.4 Images, figures, and tables (deferred)

Images, figures, diagrams, and tables are out of scope for the current phase. The text baseline is intentionally text-only.

In a later phase, a vision-capable model will read these elements, extract the relevant knowledge, and store it as additional retrievable content linked to the source document and page. Until then:

- Do not treat the Markdown as a complete representation of a page that contains figures or tables.
- Keep image counts and page identifiers from `PdfDocumentLoader` so that pages with non-text content can be identified and flagged.
- Answers that depend on figure or table content must acknowledge that this content is not yet indexed.

### 5.5 Chunking and retrieval

Chunking, embedding generation, indexing, retrieval, and LLM answer generation are planned stages.

Do not assume these components already exist. Implement and validate each stage incrementally.

## 6. Design Principles

### Separation of concerns

Each component must have one clear responsibility:

- `MarkdownExtractor`: convert a PDF into reading-ordered Markdown via the Nutrient API, behind a provider-independent interface.
- `PdfDocumentLoader`: extract physical page metadata and geometry (PyMuPDF).
- `SectionBuilder`: build the logical section hierarchy from the Markdown heading markers. Its sole responsibility is section building; it uses no PDF geometry or font data.
- `Chunker`: produce retrieval-ready passages.
- `EmbeddingService`: convert text into vectors.
- `SearchService`: retrieve relevant passages.
- `AnswerService`: generate grounded answers using retrieved evidence.
- `LayoutAnalyzer`: superseded; do not extend (see section 5.2).

Do not mix section building, embedding generation, or LLM calls into the PDF loader or the extraction stage.

### Preserve source information

Keep document IDs, page numbers, original text, and useful layout metadata throughout ingestion.

Every generated chunk should be traceable to its source document and page. Preserve additional section metadata when available.

### Explicit and testable implementation

Prefer small Python classes with clear interfaces and type hints. Avoid unnecessary abstractions, premature optimization, and large orchestration frameworks.

Use unit tests for isolated algorithms (for example heading detection and chunking on Markdown fixtures) and integration tests for the actual PDF-processing pipeline. Tests that call the Nutrient API must not run on every test run; use cached Markdown in `data/extracted/` or recorded fixtures instead.

### Secrets and configuration

Nutrient API credentials and Azure keys are read from environment variables or local, uncommitted configuration. They must never be written into source files, tests, or committed data.

### Evidence-based iteration

Inspect extracted output before changing algorithms. Validate changes against representative pages and preserve regression tests for previously solved cases.

Do not claim that a heuristic or extraction works for every PDF based on a single document.

### Grounded answers

The eventual RAG application should answer from retrieved document evidence, identify supporting sources, and acknowledge when the available evidence is insufficient.

Aviation information can be safety-critical. The assistant must not present unsupported generated content as authoritative flight instruction or a substitute for official, current aviation publications.

## 7. Development Roadmap

Work through the following milestones in order:

1. **Establish the Markdown text baseline:** wrap the Nutrient API extraction behind `MarkdownExtractor`, store the output under `data/extracted/`, and validate reading order on `chapter15_Airspace.pdf` (pages 2, 3, and 4). Confirm that page boundaries can be recovered for citations. Add regression tests.
2. **Implement SectionBuilder:** build sections, subsections, and section boundaries from the Markdown heading markers only, with page references.
3. **Implement Chunker:** create coherent chunks with document, page, and section metadata.
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
- Do not extend `LayoutAnalyzer`; build on the Markdown baseline instead.
- Do not skip ahead to embeddings, LLM integration, or image interpretation while the current ingestion milestone remains unresolved.
- Do not call the Nutrient API from tests or routine runs when cached Markdown is available.
- When changing data models, update all dependent code and tests.
- Treat the actual PDF contents and observed diagnostics (including the Markdown output) as the source of truth for extraction- and layout-specific decisions.

## 9. Immediate Next Task

Wrap the Nutrient API extraction behind a `MarkdownExtractor` interface and validate the resulting Markdown for `chapter15_Airspace.pdf`, particularly pages 2, 3, and 4. Confirm that page numbers can be recovered for each section and chunk.

Once the reading order and page traceability are validated and regression tests pass, implement `SectionBuilder` as the next component, operating on the Markdown baseline.

The immediate objective is a reliable, inspectable ingestion pipeline that transforms raw aviation PDFs into reading-ordered Markdown, then into structured, traceable document sections and retrieval-ready chunks. Images, figures, and tables are handled in a later phase.


## Testing Standards
- **Pattern:** Always use the **Given-When-Then** (BDD) pattern when writing tests.
- Clearly separate or comment the steps in your test functions:
  - `# Given` (Setup inputs and mocks)
  - `# When` (Execute the function under test)
  - `# Then` (Assert expected outcomes)
