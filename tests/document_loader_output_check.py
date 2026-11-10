"""
Manual check for MarkdownDocumentLoader output.

Run from the project root:
    python tests/document_loader_output_check.py

Prints the blocks of the sample document that belong to the first 5 pages.
This file is not collected by pytest (its name does not start with test_).
"""

from pathlib import Path

from ingestion.markdown_document_loader import MarkdownDocumentLoader
from ingestion.models import MarkdownDocument


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_MARKDOWN_PATH = PROJECT_ROOT / "data" / "extracted" / "chapter15_Airspace.md"
PAGES_TO_PRINT = 5


def first_pages(document: MarkdownDocument, page_count: int) -> MarkdownDocument:
    """Return a copy of the document that keeps only blocks up to page_count."""
    return MarkdownDocument(
        document_id=document.document_id,
        document_name=document.document_name,
        blocks=[
            block
            for block in document.blocks
            if block.page_number is not None and block.page_number <= page_count
        ],
    )


def format_document(document: MarkdownDocument) -> str:
    lines = [
        f"MarkdownDocument(document_id={document.document_id!r}, "
        f"document_name={document.document_name!r})",
        "",
    ]
    for index, block in enumerate(document.blocks, start=1):
        level = f" level={block.heading_level}" if block.heading_level else ""
        lines.append(
            f"[{index:03d}] page={block.page_number} "
            f"type={block.block_type.value}{level}"
        )
        lines.append(block.content)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    document = MarkdownDocumentLoader().load(SAMPLE_MARKDOWN_PATH)
    print(format_document(first_pages(document, PAGES_TO_PRINT)))


if __name__ == "__main__":
    main()
