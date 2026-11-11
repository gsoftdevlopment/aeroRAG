from pathlib import Path

import pytest

from ingestion.markdown_document_loader import MarkdownDocumentLoader
from ingestion.models import BlockType


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_MARKDOWN_PATH = PROJECT_ROOT / "data" / "extracted" / "chapter15_Airspace.md"


def _write_markdown(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "sample.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_headings_from_level_1_to_6_are_stored_as_heading_blocks(tmp_path):
    # Given
    markdown = "\n\n".join(
        f"{'#' * level} Heading {level}" for level in range(1, 7)
    )
    path = _write_markdown(tmp_path, markdown + "\n\n<!-- page: 1 -->\n")
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    headings = [block for block in document.blocks if block.block_type == BlockType.HEADING]
    assert [(block.heading_level, block.content) for block in headings] == [
        (level, f"Heading {level}") for level in range(1, 7)
    ]


def test_blocks_preserve_the_original_reading_order(tmp_path):
    # Given
    markdown = (
        "# Title\n\n"
        "First paragraph line.\n\n"
        "## Section\n\n"
        "- item one\n\n"
        "- item two\n\n"
        "Closing paragraph.\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [block.block_type for block in document.blocks] == [
        BlockType.HEADING,
        BlockType.PARAGRAPH,
        BlockType.HEADING,
        BlockType.LIST,
        BlockType.PARAGRAPH,
    ]
    assert [block.content for block in document.blocks] == [
        "Title",
        "First paragraph line.",
        "Section",
        "- item one\n- item two",
        "Closing paragraph.",
    ]


def test_each_block_gets_the_page_number_of_the_page_marker_that_closes_it(tmp_path):
    # Given
    markdown = (
        "# Title\n\n"
        "Intro text.\n\n"
        "<!-- page: 1 -->\n\n"
        "## Section\n\n"
        "Body text.\n\n"
        "<!-- page: 2 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [(block.content, block.page_number) for block in document.blocks] == [
        ("Title", 1),
        ("Intro text.", 1),
        ("Section", 2),
        ("Body text.", 2),
    ]


def test_page_markers_are_not_stored_as_block_content(tmp_path):
    # Given
    markdown = "Page one text.\n\n<!-- page: 1 -->\n\nPage two text.\n\n<!-- page: 2 -->\n"
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert all("<!--" not in block.content for block in document.blocks)
    assert [block.block_type for block in document.blocks] == [
        BlockType.PARAGRAPH,
        BlockType.PARAGRAPH,
    ]


def test_every_block_has_a_page_number_and_non_empty_content_for_the_sample_document():
    # Given
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(SAMPLE_MARKDOWN_PATH)

    # Then
    assert document.blocks
    for block in document.blocks:
        assert isinstance(block.page_number, int)
        assert block.page_number >= 1
        assert block.content.strip()


def test_consecutive_paragraph_lines_are_grouped_into_one_paragraph_block(tmp_path):
    # Given
    markdown = (
        "The first line of a paragraph.\n\n"
        "The second line of the same paragraph.\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert len(document.blocks) == 1
    assert document.blocks[0].block_type == BlockType.PARAGRAPH
    assert document.blocks[0].content == (
        "The first line of a paragraph. The second line of the same paragraph."
    )


def test_a_heading_ends_the_current_paragraph_block(tmp_path):
    # Given
    markdown = (
        "Paragraph before heading.\n\n"
        "## Heading\n\n"
        "Paragraph after heading.\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [block.block_type for block in document.blocks] == [
        BlockType.PARAGRAPH,
        BlockType.HEADING,
        BlockType.PARAGRAPH,
    ]


def test_consecutive_list_items_are_grouped_into_one_list_block(tmp_path):
    # Given
    markdown = (
        "Controlled airspace consists of:\n\n"
        "- Class A\n\n"
        "- Class B\n\n"
        "- Class C\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [block.block_type for block in document.blocks] == [
        BlockType.PARAGRAPH,
        BlockType.LIST,
    ]
    assert document.blocks[1].content == "- Class A\n- Class B\n- Class C"


def test_numbered_list_items_are_list_blocks(tmp_path):
    # Given
    markdown = (
        "1. If the area is not active.\n\n"
        "2. If the area is active.\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [block.block_type for block in document.blocks] == [BlockType.LIST]
    assert document.blocks[0].page_number == 1


@pytest.mark.parametrize(
    "caption_comment",
    [
        "<!-- Figure 15-1: Airspace profile. -->",
        "<!--Figure 15-1: Airspace profile.-->",
        "<!-- Figure 15-1: Airspace profile.--> ",
    ],
)
def test_figure_caption_is_stored_as_figure_block_and_ends_the_paragraph(tmp_path, caption_comment):
    # Given
    markdown = (
        "Text before the figure.\n\n"
        f"{caption_comment}\n\n"
        "Text after the figure.\n\n"
        "<!-- page: 1 -->\n"
    )
    path = _write_markdown(tmp_path, markdown)
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert [block.block_type for block in document.blocks] == [
        BlockType.PARAGRAPH,
        BlockType.FIGURE,
        BlockType.PARAGRAPH,
    ]
    assert document.blocks[1].content == "Figure 15-1: Airspace profile."
    assert all(block.page_number == 1 for block in document.blocks)


def test_sample_document_has_a_block_for_every_figure_caption_and_no_comments():
    # Given
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(SAMPLE_MARKDOWN_PATH)

    # Then
    captions = [block for block in document.blocks if block.block_type == BlockType.FIGURE]
    assert len(captions) == 9
    assert all(caption.content.startswith("Figure 15-") for caption in captions)
    assert all("<!--" not in block.content for block in document.blocks)


def test_sample_document_figure_captions_are_on_the_page_of_their_comment():
    # Given
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(SAMPLE_MARKDOWN_PATH)

    # Then
    captions = {
        block.content: block.page_number
        for block in document.blocks
        if block.block_type == BlockType.FIGURE
    }
    assert captions["Figure 15-1: Airspace profile."] == 2
    assert captions["Figure 15-2: An example of a prohibited area, P-40 around Camp David."] == 3
    assert captions["Figure 15-4: Requirements for airspace operations."] == 4


def test_sample_document_headings_and_page_numbers_match_the_source():
    # Given
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(SAMPLE_MARKDOWN_PATH)

    # Then
    headings = {
        block.content: (block.heading_level, block.page_number)
        for block in document.blocks
        if block.block_type == BlockType.HEADING
    }
    assert headings["Chapter 15 Airspace"] == (1, 1)
    assert headings["Introduction"] == (2, 1)
    assert headings["Controlled Airspace"] == (2, 2)
    assert headings["Class A Airspace"] == (3, 2)
    # The source ends page 11 with its marker and page 12 has no text blocks.
    assert max(block.page_number for block in document.blocks) == 11


def test_document_id_and_name_come_from_the_file_path(tmp_path):
    # Given
    path = _write_markdown(tmp_path, "Some text.\n\n<!-- page: 1 -->\n")
    loader = MarkdownDocumentLoader()

    # When
    document = loader.load(path)

    # Then
    assert document.document_id == "sample"
    assert document.document_name == "sample.md"
