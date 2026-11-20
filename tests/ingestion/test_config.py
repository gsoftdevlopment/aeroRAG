from pathlib import Path

from ingestion.config import (
    DEFAULT_DOCUMENTS_DIR,
    DEFAULT_OUTPUT_DIR,
    PROJECT_ROOT,
    load_extraction_config,
)


def test_missing_config_file_uses_default_directories(tmp_path: Path) -> None:
    # Given
    config_file = tmp_path / "application.yml"

    # When
    config = load_extraction_config(config_file)

    # Then
    assert config.documents_dir == DEFAULT_DOCUMENTS_DIR
    assert config.output_dir == DEFAULT_OUTPUT_DIR


def test_relative_paths_are_resolved_from_project_root(tmp_path: Path) -> None:
    # Given
    config_file = tmp_path / "application.yml"
    config_file.write_text(
        "extraction:\n"
        "  documents_dir: my/pdfs\n"
        "  output_dir: my/json\n",
        encoding="utf-8",
    )

    # When
    config = load_extraction_config(config_file)

    # Then
    assert config.documents_dir == PROJECT_ROOT / "my" / "pdfs"
    assert config.output_dir == PROJECT_ROOT / "my" / "json"


def test_absolute_paths_are_kept_as_configured(tmp_path: Path) -> None:
    # Given
    documents_dir = tmp_path / "documents"
    output_dir = tmp_path / "output"
    config_file = tmp_path / "application.yml"
    config_file.write_text(
        f"extraction:\n"
        f"  documents_dir: '{documents_dir.as_posix()}'\n"
        f"  output_dir: '{output_dir.as_posix()}'\n",
        encoding="utf-8",
    )

    # When
    config = load_extraction_config(config_file)

    # Then
    assert config.documents_dir == documents_dir
    assert config.output_dir == output_dir


def test_missing_key_falls_back_to_default(tmp_path: Path) -> None:
    # Given
    config_file = tmp_path / "application.yml"
    config_file.write_text("extraction:\n  output_dir: custom/out\n", encoding="utf-8")

    # When
    config = load_extraction_config(config_file)

    # Then
    assert config.documents_dir == DEFAULT_DOCUMENTS_DIR
    assert config.output_dir == PROJECT_ROOT / "custom" / "out"
