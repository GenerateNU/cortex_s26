import pytest
from app.services.extraction.csv_strategy import CsvExtractionStrategy



@pytest.fixture
def strategy():
    return CsvExtractionStrategy()


@pytest.fixture
def simple_csv():
    return b"name,amount\nAlice,100\nBob,200"


@pytest.fixture
def sales_csv():
    return (
        b"customer_name,product,total_amount\n"
        b"Acme Corp,Robot Arm,15000\n"
        b"Globex,Conveyor Belt,8500\n"
        b"Initech,Sensor Array,3200\n"
    )



@pytest.mark.asyncio
async def test_one_result_per_row(strategy, simple_csv):
    """Each CSV data row produces exactly one result dict."""
    # ARRANGE: 2-row CSV
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert len(results) == 2


@pytest.mark.asyncio
async def test_three_row_csv(strategy, sales_csv):
    """A three-row CSV produces exactly three results."""
    # ARRANGE: 3-row CSV
    # ACT
    results = await strategy.extract_data(sales_csv, "orders.csv")
    # ASSERT
    assert len(results) == 3


@pytest.mark.asyncio
async def test_required_keys_present(strategy, simple_csv):
    """Every result contains the required top-level keys."""
    # ARRANGE: 2-row CSV
    # ACT
    first = (await strategy.extract_data(simple_csv, "sales.csv"))[0]
    # ASSERT
    assert {"file_name", "row_index", "result", "meta"} <= first.keys()


@pytest.mark.asyncio
async def test_row_naming(strategy, simple_csv):
    """Row names follow the '<filename> - Row N' convention (1-indexed)."""
    # ARRANGE: 2-row CSV
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert results[0]["file_name"] == "sales.csv - Row 1"
    assert results[1]["file_name"] == "sales.csv - Row 2"


@pytest.mark.asyncio
async def test_row_naming_preserves_path(strategy, simple_csv):
    """File names with directory paths are preserved as-is in row names."""
    # ARRANGE: filename with nested path
    filename = "uploads/q1/sales.csv"
    # ACT
    results = await strategy.extract_data(simple_csv, filename)
    # ASSERT
    assert results[0]["file_name"] == "uploads/q1/sales.csv - Row 1"


@pytest.mark.asyncio
async def test_row_index_is_zero_based(strategy, simple_csv):
    """row_index is 0-based to match standard list indexing."""
    # ARRANGE: 2-row CSV
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert results[0]["row_index"] == 0
    assert results[1]["row_index"] == 1


@pytest.mark.asyncio
async def test_file_type_defaults_to_sales(strategy, simple_csv):
    """file_type defaults to 'Sales' for every row in a CSV."""
    # ARRANGE: 2-row CSV
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert all(r["result"]["file_type"] == "Sales" for r in results)


@pytest.mark.asyncio
async def test_extracted_json_matches_row_data(strategy, simple_csv):
    """extracted_json is the raw parsed dict of the original CSV row."""
    # ARRANGE: 2-row CSV with name/amount columns
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert results[0]["result"]["extracted_json"] == {"name": "Alice", "amount": "100"}
    assert results[1]["result"]["extracted_json"] == {"name": "Bob", "amount": "200"}


@pytest.mark.asyncio
async def test_extracted_json_multi_row(strategy, sales_csv):
    """extracted_json for all rows matches the source CSV data in order."""
    # ARRANGE: 3-row sales CSV with customer_name column
    # ACT
    results = await strategy.extract_data(sales_csv, "orders.csv")
    # ASSERT
    names = [r["result"]["extracted_json"]["customer_name"] for r in results]
    assert names == ["Acme Corp", "Globex", "Initech"]


@pytest.mark.asyncio
async def test_summary_is_non_empty_string(strategy, simple_csv):
    """Every row has a non-empty summary string for downstream relationship detection."""
    # ARRANGE: 2-row CSV
    # ACT
    results = await strategy.extract_data(simple_csv, "sales.csv")
    # ASSERT
    assert all(isinstance(r["result"]["summary"], str) and r["result"]["summary"] for r in results)


# ── _generate_summary ─────────────────────────────────────────────────────────

def test_summary_includes_customer_value(strategy):
    """Summary contains the customer name when a customer column is present."""
    # ARRANGE
    row = {"customer_name": "Acme Corp", "amount": "5000"}
    # ACT
    summary = strategy._generate_summary(row, 0)
    # ASSERT
    assert "Acme Corp" in summary


def test_summary_includes_amount_value(strategy):
    """Summary contains the amount value when an amount column is present."""
    # ARRANGE
    row = {"customer_name": "Globex", "total_amount": "8500"}
    # ACT
    summary = strategy._generate_summary(row, 0)
    # ASSERT
    assert "8500" in summary


def test_summary_fallback_is_non_empty(strategy):
    """Summary falls back gracefully to a non-empty string for unrecognised columns."""
    # ARRANGE
    row = {"widget_id": "W-001"}
    # ACT
    summary = strategy._generate_summary(row, 5)
    # ASSERT
    assert isinstance(summary, str) and summary


def test_summary_fallback_includes_row_number(strategy):
    """Fallback summary references the 1-indexed row number to distinguish rows."""
    # ARRANGE
    row = {"obscure_col": "value"}
    # ACT
    summary = strategy._generate_summary(row, 3)
    # ASSERT
    assert "4" in summary  # implementation uses index + 1