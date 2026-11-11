import re
from pathlib import Path

from .models import (
    MAX_HEADING_LEVEL,
    MIN_HEADING_LEVEL,
    BlockType,
    MarkdownBlock,
    MarkdownDocument,
)


# "<!-- page: 12 -->" closes the page with that number.
PAGE_MARKER_PATTERN = re.compile(r"^<!--\s*page:\s*(\d+)\s*-->$")
# "<!-- Figure 15-1: Caption text. -->" holds a figure caption.
FIGURE_CAPTION_PATTERN = re.compile(r"^<!--\s*(Figure\s+\d+-\d+:.*?)\s*-->$")
HEADING_PATTERN = re.compile(r"^(#+)\s+(.+)$")
LIST_ITEM_PATTERN = re.compile(r"^(?:[-*+]|\d+\.)\s+\S")


class MarkdownDocumentLoader:
    """
    Convert structured Markdown into ordered, page-numbered text blocks.

    Page markers close the page they follow. Figure captions become
    their own FIGURE blocks. Blank lines do not end a paragraph or a list,
    so a block only ends at a heading, a list/paragraph change, a figure
    caption, or a page marker.
    """

    def load(self, markdown_path: str | Path) -> MarkdownDocument:
        markdown_path = Path(markdown_path)
        text = markdown_path.read_text(encoding="utf-8")
        return MarkdownDocument(
            document_id=markdown_path.stem,
            document_name=markdown_path.name,
            blocks=self._parse(text),
        )

    def _parse(self, text: str) -> list[MarkdownBlock]:
        blocks: list[MarkdownBlock] = []
        pending: list[str] = []
        last_page_number = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()

            marker = PAGE_MARKER_PATTERN.match(line)
            if marker:
                # A marker closes the page whose lines are still pending.
                last_page_number = int(marker.group(1))
                blocks.extend(self._parse_page(pending, last_page_number))
                pending = []
                continue

            pending.append(line)

        # Lines after the final marker belong to the following page.
        blocks.extend(self._parse_page(pending, last_page_number + 1))
        return blocks

    def _parse_page(
        self,
        lines: list[str],
        page_number: int,
    ) -> list[MarkdownBlock]:
        blocks: list[MarkdownBlock] = []
        current_type: BlockType | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if current_type is None:
                return
            separator = " " if current_type == BlockType.PARAGRAPH else "\n"
            blocks.append(
                MarkdownBlock(
                    block_type=current_type,
                    content=separator.join(current_lines),
                    page_number=page_number,
                )
            )

        for line in lines:
            if not line:
                continue

            heading = HEADING_PATTERN.match(line)
            if heading and MIN_HEADING_LEVEL <= len(heading.group(1)) <= MAX_HEADING_LEVEL:
                flush()
                current_type, current_lines = None, []
                blocks.append(
                    MarkdownBlock(
                        block_type=BlockType.HEADING,
                        content=heading.group(2).strip(),
                        page_number=page_number,
                        heading_level=len(heading.group(1)),
                    )
                )
                continue

            caption = FIGURE_CAPTION_PATTERN.match(line)
            if caption:
                flush()
                current_type, current_lines = None, []
                blocks.append(
                    MarkdownBlock(
                        block_type=BlockType.FIGURE,
                        content=caption.group(1),
                        page_number=page_number,
                    )
                )
                continue

            line_type = (
                BlockType.LIST if LIST_ITEM_PATTERN.match(line) else BlockType.PARAGRAPH
            )
            if line_type != current_type:
                flush()
                current_type, current_lines = line_type, []
            current_lines.append(line)

        flush()
        return blocks
