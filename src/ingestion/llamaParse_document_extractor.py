import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from llama_cloud import LlamaCloud

from ingestion.config import (
    PROJECT_ROOT,
    ExtractionConfig,
    load_extraction_config,
)


logger = logging.getLogger(__name__)

API_KEY_ENV_VAR = "LLAMA-PARSE_API_KEY"
DEFAULT_DOCUMENT_SUFFIX = ".pdf"
TERMINAL_JOB_STATES = ("COMPLETED", "FAILED", "CANCELLED")

# Schema for the data to be extracted from the PDF. This schema defines the structure of the extracted data.
DATA_SCHEMA: dict[str, Any] = {
    "additionalProperties": False,
    "properties": {
        "document_title": {
            "description": "The title of the document.",
            "type": "string"
        },
        "page number": {
            "description": "The page number in the format NN-N, e.g. 15-2.",
            "type": "string"
        },
        "sections": {
            "description": "List of document sections with the page where each section starts and ends.",
            "items": {
                "properties": {
                    "section_title": {
                        "description": "The title or heading of the section.",
                        "type": "string"
                    },
                    "start_page": {
                        "description": "The page number where the section starts, in the format NN-N, e.g. 15-2.",
                        "type": "string"
                    },
                    "end_page": {
                        "description": "The page number where the section ends, in the format NN-N, e.g. 15-2.",
                        "type": "string"
                    },
                    "content": {
                        "description": "The text content. The text content  contained between two section markings",
                        "type": "string"
                    }
                },
                "required": ["section_title", "start_page", "end_page", "content"],
                "type": "object"
            },
            "type": "array"
        }
    },
    "required": ["document_title", "page number", "sections"],
    "type": "object"
}


class LlamaParseDocumentExtractor:
    """Extracts a PDF into structured JSON using the LlamaParse Extract API."""

    def __init__(self, config: ExtractionConfig, client: LlamaCloud) -> None:
        self.config = config
        self.client = client

    @classmethod
    def from_env(cls, config: ExtractionConfig | None = None) -> "LlamaParseDocumentExtractor":
        """Create an extractor with the API key read from the .env file or the environment."""
        load_dotenv(PROJECT_ROOT / ".env")
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if not api_key:
            raise RuntimeError(f"{API_KEY_ENV_VAR} is not set in .env or the environment")

        client = LlamaCloud(api_key=api_key)
        return cls(config or load_extraction_config(), client)

    def extract(self, document_name: str) -> Path:
        """Extract a document from the documents directory and write its JSON to the output directory.

        `document_name` is a file name relative to `documents_dir`, for example
        `chapter15_Airspace.pdf`. A missing extension defaults to `.pdf`.
        Returns the path of the written JSON file.
        """
        pdf_path = self._resolve_document(document_name)
        output_path = self.config.output_dir / f"{pdf_path.stem}.json"

        result = self._run_extract_job(pdf_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Wrote extracted JSON to %s", output_path)
        return output_path

    def _resolve_document(self, document_name: str) -> Path:
        """Return the PDF path for a document name. Fails before any API call if it is missing."""
        name = Path(document_name)
        if not name.suffix:
            name = name.with_suffix(DEFAULT_DOCUMENT_SUFFIX)

        pdf_path = self.config.documents_dir / name
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Document not found: {pdf_path}")
        return pdf_path

    def _run_extract_job(self, pdf_path: Path) -> dict[str, Any]:
        """Upload the PDF, run an extract job, and return the extracted result."""
        file_obj = self.client.files.create(file=pdf_path, purpose="extract")

        job = self.client.extract.create(
            file_input=file_obj.id,
            configuration={
                "data_schema": DATA_SCHEMA,
                "parse_tier": "agentic",
                "tier": "agentic",
                "extraction_target": "per_doc",
                "cite_sources": True,
                "confidence_scores": True
            },
        )

        # Poll until the job reaches a terminal state
        while job.status not in TERMINAL_JOB_STATES:
            time.sleep(2)
            job = self.client.extract.get(job.id)

        if job.status != "COMPLETED":
            raise RuntimeError(f"Extract job {job.id} ended in {job.status}: {job.error_message}")

        self._log_field_metadata(job)
        return job.extract_result

    @staticmethod
    def _log_field_metadata(job: Any) -> None:
        """Log per-field citation and confidence metadata. It is not stored in the JSON file."""
        if job.extract_metadata and job.extract_metadata.field_metadata:
            documents = job.extract_metadata.field_metadata.document_metadata or {}
            for field, meta in documents.items():
                logger.debug("%s: %s", field, meta)
