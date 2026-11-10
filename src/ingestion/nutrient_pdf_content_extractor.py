from pathlib import Path
import json
import os

import requests
from dotenv import load_dotenv


NUTRIENT_EXTRACTION_URL = "https://api.nutrient.io/extraction/parse"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_PDF_PATH = PROJECT_ROOT / "data" / \
    "documents" / "chapter15_Airspace.pdf"

""" If we keep this class, some refactoring may be needed. url and timeout shoul be read from a property file instead of being passed to the constructor. Secong I actually don't like how the class is initialized with from_env() """


class PdfContentExtractor:
    """Sends a PDF to the Nutrient extraction API and returns its markdown text."""

    def __init__(self, api_key: str, url: str = NUTRIENT_EXTRACTION_URL, timeout: int = 300) -> None:
        self.api_key = api_key
        self.url = url
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "PdfContentExtractor":
        load_dotenv(ENV_FILE)
        api_key = os.environ.get("NUTRIENT_API_KEY")
        if not api_key:
            raise RuntimeError(
                "NUTRIENT_API_KEY is not set in .env or the environment.")
        return cls(api_key=api_key)

    def extract_markdown(self, pdf_path: str | Path) -> str:
        pdf_path = Path(pdf_path)
        instructions = {"mode": "text", "output": {"format": "markdown"}}

        with pdf_path.open("rb") as pdf_file:
            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": pdf_file},
                data={"instructions": json.dumps(instructions)},
                timeout=self.timeout,
            )

        response.raise_for_status()
        result = response.json()
        return result["output"]["markdown"]


if __name__ == "__main__":
    extractor = PdfContentExtractor.from_env()
    print(extractor.extract_markdown(DEFAULT_PDF_PATH))
