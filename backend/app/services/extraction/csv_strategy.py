import csv
import io
import json
from typing import Any, List

class CsvExtractionStrategy:
    def __init__(self):
        pass

    async def extract_data(self, file_bytes: bytes, file_name: str) -> List[dict]:
        """
        Parses CSV bytes into a list of extraction results (one per row).
        Returns: List of { "file_name": ..., "result": { "file_type": ..., "summary": ..., "extracted_json": ... } }
        """
        
        # Decode bytes to string
        try:
            content = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = file_bytes.decode('latin-1') # Fallback
            
        csv_reader = csv.DictReader(io.StringIO(content))
        
        results = []
        for i, row in enumerate(csv_reader):
            # 1. extracted_json is the row itself
            extracted_json = row
            
            # 2. Determine file_type (Default to Sales for now as per user request context, or Generic)
            file_type = "Sales" 
            
            # 3. Generate Summary
            # We could use an LLM here, but for CSV rows it might be overkill/expensive to do it for every row.
            # Let's generate a template summary for now.
            # "Sales Record for {Customer} on {Date}"
            summary = self._generate_summary(row, i)
            
            # 4. Generate Name
            # "file_name - Row X" or something from the data?
            # User said: "every row of a given csv will have its own name"
            # We'll append row index or use a primary column if identified.
            row_name = f"{file_name} - Row {i+1}"
            
            results.append({
                "file_name": row_name,
                "row_index": i,
                "result": {
                    "file_type": file_type,
                    "summary": summary,
                    "extracted_json": extracted_json
                },
                "meta": {"source": "csv-strategy"}
            })
            
        return results

    def _generate_summary(self, row: dict, index: int) -> str:
        """
        Generates a simple summary string from row data.
        """
        # Try to find common descriptive columns
        keys = list(row.keys())
        summary_parts = []
        
        # Look for "Customer", "Product", "Date", "Amount"
        for key in keys:
            k_lower = key.lower()
            if "customer" in k_lower or "client" in k_lower:
                summary_parts.append(f"Customer: {row[key]}")
            elif "product" in k_lower or "item" in k_lower:
                summary_parts.append(f"Item: {row[key]}")
            elif "amount" in k_lower or "price" in k_lower or "total" in k_lower:
                summary_parts.append(f"Value: {row[key]}")
                
        if summary_parts:
            return ", ".join(summary_parts)
        
        # Fallback
        return f"CSV Row {index+1}: {str(row)[:50]}..."

def get_csv_extraction_strategy() -> CsvExtractionStrategy:
    return CsvExtractionStrategy()
