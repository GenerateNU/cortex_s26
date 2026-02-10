import csv
from io import StringIO


class CsvExtractionStrategy:
    def _decode_bytes(self, file_bytes: bytes) -> tuple[str, str]:
        for encoding in ("utf-8-sig", "utf-16", "latin-1"):
            try:
                return file_bytes.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="replace"), "utf-8-replace"

    def _detect_delimiter(self, text: str) -> str:
        sample = text[:4096]

        try:
            sniffed = csv.Sniffer().sniff(sample, delimiters=",;\t")
            return sniffed.delimiter
        except csv.Error:
            comma = sample.count(",")
            semicolon = sample.count(";")
            tab = sample.count("\t")
            if tab >= comma and tab >= semicolon:
                return "\t"
            if semicolon >= comma and semicolon >= tab:
                return ";"
            return ","

    def extract_data(self, file_bytes: bytes, file_name: str) -> dict:
        text, encoding = self._decode_bytes(file_bytes)
        delimiter = self._detect_delimiter(text)

        reader = csv.DictReader(StringIO(text), delimiter=delimiter, quotechar='"')

        rows = []
        for idx, row in enumerate(reader, start=1):
            normalized_row = {}
            for key, value in row.items():
                normalized_key = key.strip() if isinstance(key, str) else key
                if isinstance(value, str):
                    normalized_row[normalized_key] = value.strip() or None
                else:
                    normalized_row[normalized_key] = value

            rows.append({"row_number": idx, "item": normalized_row})

        result = {
            "columns": [col.strip() for col in (reader.fieldnames or [])],
            "items": rows,
            "row_count": len(rows),
        }

        return {
            "file_name": file_name,
            "result": result,
            "meta": {
                "source": "csv-parser",
                "encoding": encoding,
                "delimiter": "tab" if delimiter == "\t" else delimiter,
            },
        }


def get_csv_extraction_strategy() -> CsvExtractionStrategy:
    return CsvExtractionStrategy()
