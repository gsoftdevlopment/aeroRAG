from dataclasses import dataclass
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config" / "application.yml"
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "extracted"


@dataclass(frozen=True)
class ExtractionConfig:
    """Directories used by the PDF extraction stage."""

    documents_dir: Path
    output_dir: Path


def load_extraction_config(config_file: Path = DEFAULT_CONFIG_FILE) -> ExtractionConfig:
    """Read the extraction config from a YAML file and convert it to an `ExtractionConfig` object.

    Missing file or missing keys fall back to the defaults
    (`data/documents/` and `data/extracted/`).
    """
    values: dict = {}
    if config_file.exists():
        loaded = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        values = loaded.get("extraction") or {}

    return ExtractionConfig(
        documents_dir=_resolve_path(values.get("documents_dir"), DEFAULT_DOCUMENTS_DIR),
        output_dir=_resolve_path(values.get("output_dir"), DEFAULT_OUTPUT_DIR),
    )


def _resolve_path(value: str | None, default: Path) -> Path:
    """Return the configured path, resolving relative paths against the project root."""
    if value is None:
        return default

    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
