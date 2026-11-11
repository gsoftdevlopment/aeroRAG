from dataclasses import dataclass
from enum import IntEnum


from dataclasses import dataclass, field
from enum import Enum


# Markdown ATX headings range from "#" (level 1) to "######" (level 6).
MIN_HEADING_LEVEL = 1
MAX_HEADING_LEVEL = 6


class BlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    FIGURE="figure"
    OTHER = "other"


@dataclass(frozen=True)
class MarkdownBlock:
    """An ordered unit of text extracted from Markdown."""

    block_type: BlockType
    content: str
    page_number: int | None = None
    heading_level: int | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("Block content must not be empty")

        if self.block_type == BlockType.HEADING:
            if self.heading_level is None or not (
                MIN_HEADING_LEVEL <= self.heading_level <= MAX_HEADING_LEVEL
            ):
                raise ValueError(
                    f"A heading must have a level between "
                    f"{MIN_HEADING_LEVEL} and {MAX_HEADING_LEVEL}"
                )
        elif self.heading_level is not None:
            raise ValueError(
                "Only heading blocks may have a heading level"
            )



@dataclass
class MarkdownDocument:
    """A document represented as ordered Markdown blocks."""

    document_id: str
    document_name: str
    blocks: list[MarkdownBlock] = field(default_factory=list)


@dataclass
class MarkdownSection:
    """A logical section identified by the Markdown heading hierarchy. A section represents how we group blocks for downstream chunking and retrieval"""

    title: str
    heading_level: int
    document_id: str
    blocks: list[MarkdownBlock] = field(default_factory=list)
    start_page: int | None = None
    end_page: int | None = None

    @property
    def text(self) -> str:
        """Return section text without its heading."""
        return "\n\n".join(
            block.content for block in self.blocks
        )
