import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ingestion.llamaParse_document_extractor import LlamaParseDocumentExtractor
from ingestion.config import ExtractionConfig


SAMPLE_RESULT = {
    "document_title": "Chapter 15 Airspace",
    "page number": "15-3",
    "sections": [
        {
            "section_title": "Uncontrolled Airspace",
            "start_page": "15-3",
            "end_page": "15-3",
            "content": "Class G Airspace – uncontrolled.",
        }
    ],
}


class FakeFiles:
    def __init__(self) -> None:
        self.created: list[Path] = []

    def create(self, file: Path, purpose: str) -> Any:
        self.created.append(file)
        return SimpleNamespace(id="file-1")


class FakeExtract:
    def __init__(self, status: str = "COMPLETED", result: dict | None = None) -> None:
        self.status = status
        self.result = result
        self.configurations: list[dict] = []

    def create(self, file_input: str, configuration: dict) -> Any:
        self.configurations.append(configuration)
        return self.get("job-1")

    def get(self, job_id: str) -> Any:
        return SimpleNamespace(
            id=job_id,
            status=self.status,
            extract_result=self.result,
            extract_metadata=None,
            error_message="boom" if self.status == "FAILED" else None,
        )


class FakeClient:
    def __init__(self, status: str = "COMPLETED", result: dict | None = SAMPLE_RESULT) -> None:
        self.files = FakeFiles()
        self.extract = FakeExtract(status=status, result=result)


@pytest.fixture
def directories(tmp_path: Path) -> tuple[Path, Path]:
    documents_dir = tmp_path / "documents"
    output_dir = tmp_path / "extracted"
    documents_dir.mkdir()
    (documents_dir / "chapter15_Airspace.pdf").write_bytes(b"%PDF-1.4 test")
    return documents_dir, output_dir


def make_extractor(directories: tuple[Path, Path], client: FakeClient) -> LlamaParseDocumentExtractor:
    documents_dir, output_dir = directories
    config = ExtractionConfig(documents_dir=documents_dir, output_dir=output_dir)
    return LlamaParseDocumentExtractor(config, client)  # type: ignore[arg-type]


def test_extract_writes_json_named_after_document(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient()
    extractor = make_extractor(directories, client)
    _, output_dir = directories

    # When
    output_path = extractor.extract("chapter15_Airspace.pdf")

    # Then
    assert output_path == output_dir / "chapter15_Airspace.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == SAMPLE_RESULT


def test_extract_uploads_pdf_from_documents_directory(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient()
    extractor = make_extractor(directories, client)
    documents_dir, _ = directories

    # When
    extractor.extract("chapter15_Airspace.pdf")

    # Then
    assert client.files.created == [documents_dir / "chapter15_Airspace.pdf"]


def test_extract_appends_pdf_extension_when_missing(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient()
    extractor = make_extractor(directories, client)
    documents_dir, output_dir = directories

    # When
    output_path = extractor.extract("chapter15_Airspace")

    # Then
    assert client.files.created == [documents_dir / "chapter15_Airspace.pdf"]
    assert output_path == output_dir / "chapter15_Airspace.json"


def test_extract_missing_document_fails_before_calling_api(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient()
    extractor = make_extractor(directories, client)

    # When
    with pytest.raises(FileNotFoundError):
        extractor.extract("does_not_exist.pdf")

    # Then
    assert client.files.created == []


def test_extract_failed_job_raises_and_writes_nothing(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient(status="FAILED", result=None)
    extractor = make_extractor(directories, client)
    _, output_dir = directories

    # When
    with pytest.raises(RuntimeError, match="FAILED"):
        extractor.extract("chapter15_Airspace.pdf")

    # Then
    assert not (output_dir / "chapter15_Airspace.json").exists()


def test_extract_requests_schema_with_required_fields(directories: tuple[Path, Path]) -> None:
    # Given
    client = FakeClient()
    extractor = make_extractor(directories, client)

    # When
    extractor.extract("chapter15_Airspace.pdf")

    # Then
    schema = client.extract.configurations[0]["data_schema"]
    assert schema["required"] == ["document_title", "page number", "sections"]
