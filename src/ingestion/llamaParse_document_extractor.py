import json
import time
import os
from pathlib import Path
from llama_cloud import LlamaCloud
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_PDF_PATH = PROJECT_ROOT / "data" / \
    "documents" / "page3-4.pdf"


load_dotenv(ENV_FILE)
api_key = os.environ.get("LLAMA-PARSE_API_KEY")
client = LlamaCloud(api_key=api_key)

# Schema for the  data to be extracted from the PDF. This schema defines the structure of the extracted data.
data_schema = {
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

# Upload
file_obj = client.files.create(file=DEFAULT_PDF_PATH, purpose="extract")

# Submit an extract job
job = client.extract.create(
    file_input=file_obj.id,
    configuration={
        "data_schema": data_schema,
        "parse_tier": "agentic",
        "tier": "agentic",
        "extraction_target": "per_doc",
        "cite_sources": True,
        "confidence_scores": True
    },
)

# Poll until the job reaches a terminal state
while job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
    time.sleep(2)
    job = client.extract.get(job.id)

if job.status != "COMPLETED":
    raise RuntimeError(f"Extract job {job.id} ended in {job.status}: {job.error_message}")

# Persist extracted JSON to disk
Path("llamaParse_extractor_output.json").write_text(json.dumps(job.extract_result, indent=2))
print(json.dumps(job.extract_result, indent=2))

# Per-field citation / confidence metadata
if job.extract_metadata and job.extract_metadata.field_metadata:
    for field, meta in (job.extract_metadata.field_metadata.document_metadata or {}).items():
        print(f"{field}: {meta}")
