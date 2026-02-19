import json
import os

from app.core.litellm import LLMClient, ModelType


class PdfExtractionStrategy:
    def __init__(self):
        self.model = LLMClient()
        self.model.set_system_prompt(
            "You are a PDF→JSON structurer for manufacturing/robotics documents. "
            "Return ONE valid JSON object only (no markdown). Keep only meaningful specs "
            "(manufacturer, model, document identifiers, key specs like payload/reach/"
            "repeatability/mass/mounting/protection/environment, axis JT1..JTn ranges & speeds). "
            "Preserve symbols like ±, °/s, φ. Normalize ranges as strings (e.g., '±180', '+140 to -105'). "
            "Do not invent values; omit if missing."
        )

    async def extract_data(
        self,
        pdf_bytes: bytes,
        file_name: str,
        llm_model: ModelType = (
            ModelType.GEMINI_FLASH
            if os.getenv("ENVIRONMENT") == "development"
            else ModelType.GEMINI_PRO
        ),
    ) -> dict:
        """
        Extracts structured data, classification, and summary from PDF.
        Returns: { "file_type": ..., "summary": ..., "extracted_json": ... }
        """
        self.model.set_model(llm_model)

        # Updated Prompt for Classification, Summary, and Extraction
        prompt = (
            "Analyze this document. Return a JSON object with exactly these 3 keys:\n"
            "1. 'file_type': Must be one of ['RFQ', 'PO', 'ProdSpec', 'Sales', 'Customers']. "
            "Infer based on content.\n"
            "2. 'summary': A 1-2 sentence summary of the document.\n"
            "3. 'extracted_json': The structured data extracted from the document (tables, specs, dates, amounts).\n"
            "Do not return markdown formatting, just the raw JSON."
        )

        response = await self.model.chat(
            prompt, pdf_bytes=pdf_bytes, json_response=True
        )

        text = response.choices[0].message.content.strip()

        print("JSON response received", flush=True)
        try:
            data = json.loads(text)

            # Validate/Normalize keys
            if "extracted_json" not in data:
                 # Fallback if model puts data at root
                 if "data" in data:
                     data["extracted_json"] = data.pop("data")
                 else:
                     # Assess if the whole object is the data (minus type/summary)
                     data["extracted_json"] = {k:v for k,v in data.items() if k not in ["file_type", "summary"]}

        except Exception:
            data = {
                "file_type": "ProdSpec", # Default fallback
                "summary": "Extraction failed.",
                "extracted_json": {"error": "LLM did not return JSON"}
            }

        print("JSON response parsed", flush=True)

        return {
            "file_name": file_name,
            "result": data, # Contains file_type, summary, extracted_json
            "meta": {"llm_model": llm_model.value, "source": "gemini-pdf-only"},
        }

def get_pdf_extraction_strategy() -> PdfExtractionStrategy:
    return PdfExtractionStrategy()
