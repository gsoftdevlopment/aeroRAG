import argparse
import logging
from pathlib import Path

from ingestion.config import DEFAULT_CONFIG_FILE, load_extraction_config
from ingestion.llamaParse_document_extractor import LlamaParseDocumentExtractor


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point: extract the given documents with LlamaParse."""
    parser = argparse.ArgumentParser(description="Extract PDFs to JSON with LlamaParse.")
    parser.add_argument(
        "documents",
        nargs="+",
        help="Document names inside documents_dir, e.g. chapter15_Airspace.pdf",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_FILE,
        help="Path to the config YAML file",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    extractor = LlamaParseDocumentExtractor.from_env(load_extraction_config(args.config))
    for document in args.documents:
        extractor.extract(document)


if __name__ == "__main__":
    main()
