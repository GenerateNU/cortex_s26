from datetime import date, datetime, time
from io import BytesIO
import pandas as pd


class CsvExcelExtractionStrategy:
    """
    Unified extraction strategy for CSV and Excel files using pandas.
    Returns one JSON object per row for all file types.
    """

    def _normalize_cell(self, value):
        """Normalize cell values - strip whitespace, handle dates, convert NaN to None"""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        return value

    def _build_results(self, df: pd.DataFrame, base_name: str, meta: dict) -> list[dict]:
        """
        Build a list of results - one per row.
        Each row becomes a separate extracted file.
        """
        if df.empty:
            return []
        
        # Normalize column names
        columns = [str(col).strip() for col in df.columns]
        df.columns = columns
        
        # Convert to list of dicts, handling NaN/None
        rows = df.where(df.notna(), None).to_dict('records')
        
        results = []
        for idx, row_data in enumerate(rows, start=1):
            # Normalize values
            normalized_row = {}
            for key, value in row_data.items():
                normalized_row[key] = self._normalize_cell(value)
            
            results.append({
                "file_name": f"{base_name}_row{idx}",
                "result": normalized_row,
                "meta": {
                    **meta,
                    "row_number": idx,
                    "total_rows": len(rows),
                },
            })
        
        return results

    def _extract_csv(self, file_bytes: bytes, file_name: str) -> list[dict]:
        """Extract CSV file using pandas"""
        df = None
        encoding = None
        
        # Try different encodings
        for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
            try:
                df = pd.read_csv(
                    BytesIO(file_bytes),
                    encoding=enc,
                    dtype=object,
                    keep_default_na=False,
                )
                encoding = enc
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        if df is None:
            # Fallback with error handling
            df = pd.read_csv(
                BytesIO(file_bytes),
                encoding="utf-8",
                encoding_errors="replace",
                dtype=object,
                keep_default_na=False,
            )
            encoding = "utf-8-replace"
        
        base_name = file_name.rsplit('.', 1)[0]
        meta = {
            "source": "csv-parser",
            "encoding": encoding,
            "original_file": file_name,
        }
        
        return self._build_results(df, base_name, meta)

    def _extract_excel(self, file_bytes: bytes, file_name: str) -> list[dict]:
        """Extract Excel file (.xlsx or .xls) using pandas"""
        workbook = pd.ExcelFile(BytesIO(file_bytes))
        sheet_names = workbook.sheet_names

        if len(sheet_names) > 1:
            print(
                f"Warning: Multiple sheets detected in '{file_name}'. "
                f"Using first sheet '{sheet_names[0]}'.",
                flush=True,
            )

        df = workbook.parse(sheet_name=sheet_names[0], dtype=object)
        
        base_name = file_name.rsplit('.', 1)[0]
        file_format = "xlsx" if file_name.lower().endswith(".xlsx") else "xls"
        
        meta = {
            "source": "excel-parser",
            "sheet_name": sheet_names[0],
            "sheet_count": len(sheet_names),
            "format": file_format,
            "original_file": file_name,
        }
        
        return self._build_results(df, base_name, meta)

    def extract_data(self, file_bytes: bytes, file_name: str) -> list[dict]:
        """
        Route to correct parser based on file extension.
        Handles .csv, .xlsx, and .xls files.
        """
        lower_name = file_name.lower()
        
        if lower_name.endswith(".csv"):
            return self._extract_csv(file_bytes, file_name)
        elif lower_name.endswith((".xlsx", ".xls")):
            return self._extract_excel(file_bytes, file_name)
        else:
            raise ValueError(
                f"Unsupported file extension for '{file_name}'. "
                f"Supported formats: .csv, .xlsx, .xls"
            )


# Export both strategies with the same class
def get_csv_extraction_strategy() -> CsvExcelExtractionStrategy:
    return CsvExcelExtractionStrategy()


def get_excel_extraction_strategy() -> CsvExcelExtractionStrategy:
    return CsvExcelExtractionStrategy()