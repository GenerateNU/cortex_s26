import json
import os
from typing import Any

from app.core.litellm import LLMClient, ModelType


class PdfExtractionStrategy:
    _ALLOWED_FILE_TYPES = {"RFQ", "PO", "Product Spec", "Sales", "Customers"}

    def __init__(self):
        self.model = LLMClient()
        self._extraction_prompt = (
            "You are a PDF→JSON structurer for manufacturing/robotics documents. "
            "Return ONE valid JSON object only (no markdown). Keep only meaningful specs "
            "(manufacturer, model, document identifiers, key specs like payload/reach/"
            "repeatability/mass/mounting/protection/environment, axis JT1..JTn ranges & speeds). "
            "Preserve symbols like ±, °/s, φ. Normalize ranges as strings (e.g., '±180', '+140 to -105'). "
            "Do not invent values; omit if missing."
        )
        self._summary_prompt = (
            "You classify extracted business documents and summarize them for relationship mapping. "
            "Return one JSON object only with keys: file_type and llm_summary. "
            "file_type must be exactly one of: RFQ, PO, Product Spec, Sales, Customers. "
            "llm_summary must be 1-2 concise sentences describing what the document is about, "
            "highlighting broad product/service categories (e.g., robotic arms, hydraulic systems, tires), "
            "and avoiding model-number-heavy details."
        )
        self.model.set_system_prompt(self._extraction_prompt)

    async def _classify_and_summarize(
        self,
        extracted_json: dict[str, Any],
        file_name: str,
    ) -> dict[str, str]:
        self.model.set_system_prompt(self._summary_prompt)
        response = await self.model.chat(
            (
                f"Filename: {file_name}\n"
                f"Extracted JSON:\n{json.dumps(extracted_json, ensure_ascii=False)}\n\n"
                "Classify the document and generate the requested summary."
            ),
            json_response=True,
            max_tokens=220,
        )

        text = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {}

        file_type = parsed.get("file_type")
        if file_type not in self._ALLOWED_FILE_TYPES:
            file_type = "Product Spec"

        llm_summary = parsed.get("llm_summary")
        if not isinstance(llm_summary, str) or not llm_summary.strip():
            llm_summary = (
                f"Document related to {file_type.lower()} information for manufacturing "
                "or industrial products."
            )

        return {"file_type": file_type, "llm_summary": llm_summary.strip()}

    async def extract_data(
        self,
        pdf_bytes: bytes,
        file_name: str,
        file_id: str | None = None,
        llm_model: ModelType = (
            ModelType.GEMINI_FLASH
            if os.getenv("ENVIRONMENT") == "development"
            else ModelType.GEMINI_PRO
        ),
    ) -> dict:
        self.model.set_model(llm_model)
        self.model.set_system_prompt(self._extraction_prompt)
        response = await self.model.chat(
            "Extract tables", pdf_bytes=pdf_bytes, json_response=True
        )

        text = response.choices[0].message.content.strip()

        print("JSON response received", flush=True)
        try:
            data = json.loads(text)
        except Exception:
            data = {"error": "LLM did not return JSON"}

        print("JSON response parsed", flush=True)
        classification_payload = await self._classify_and_summarize(data, file_name)
        self.model.set_system_prompt(self._extraction_prompt)

        return {
            "file_id": file_id,
            "filename": file_name,
            "file_type": classification_payload["file_type"],
            "extracted_json": data,
            "llm_summary": classification_payload["llm_summary"],
            # Backward-compatible fields used by current pipeline
            "file_name": file_name,
            "result": data,
            "meta": {
                "llm_model": llm_model.value,
                "source": "gemini-pdf-only",
                "summary_model": llm_model.value,
            },
        }


def get_pdf_extraction_strategy() -> PdfExtractionStrategy:
    return PdfExtractionStrategy()
