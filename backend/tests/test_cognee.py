"""
End-to-end (e2e) tests for the Cognee pipeline.

These tests call the real Cognee SDK — add, cognify, search, prune — so they
require a live LLM API key.  They use Cognee's embedded defaults (LanceDB for
vectors, KuzuDB for graph, SQLite for relational) so no PostgreSQL or external
vector store is needed.

Skipped automatically when LLM_API_KEY is not set.

Usage:
    cd backend && pytest tests/test_cognee.py -v          # skips if no creds
    cd backend && pytest tests/test_cognee.py -v -m e2e   # explicit marker
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

from dotenv import load_dotenv

# Load real credentials from project root .env
load_dotenv(override=True)

import cognee  # noqa: E402
import pytest  # noqa: E402
from cognee.api.v1.search import SearchType  # noqa: E402

# ---------------------------------------------------------------------------
# Skip the entire module when LLM credentials are not available
# ---------------------------------------------------------------------------

_REQUIRED_VARS = ("LLM_API_KEY",)
_missing = [v for v in _REQUIRED_VARS if not os.getenv(v)]

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        len(_missing) > 0,
        reason=f"Missing env vars for e2e Cognee tests: {', '.join(_missing)}",
    ),
]

E2E_DATASET = "e2e-smoke-test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_file(tmp_path_factory) -> Path:
    """Create a small text file to ingest — no external mock_data needed."""
    p = tmp_path_factory.mktemp("cognee_e2e") / "sample.txt"
    p.write_text(
        textwrap.dedent("""\
            Acme Corp Deep Fryer Model X200 — Safety Manual

            Chapter 1: Installation
            The X200 must be installed on a level, heat-resistant surface at least
            24 inches from combustible materials.  A dedicated 240V/30A circuit is
            required.  Do not use extension cords.

            Chapter 2: Operation
            Fill the basin with oil to the MIN line before powering on.  Maximum
            oil temperature is 375 degrees F.  Never leave the fryer unattended
            while in use.  The auto-shutoff triggers at 400 degrees F.

            Chapter 3: Maintenance
            Drain and filter oil after every 40 hours of use.  Clean the heating
            element monthly with a non-abrasive cloth.  Replace the thermostat
            annually.
        """)
    )
    return p


def _setup_cognee_for_test():
    """Configure Cognee with LLM + embeddings only.

    Uses Cognee's embedded defaults (LanceDB, KuzuDB, SQLite) so the test
    works without PostgreSQL or an external vector store.  Only needs
    LLM_API_KEY and optionally EMBEDDING_API_KEY from the environment.
    """
    llm_provider = os.getenv("LLM_PROVIDER")
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")

    if llm_provider and llm_api_key:
        cognee.config.set_llm_config(
            {
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_api_key": llm_api_key,
            }
        )

    embedding_provider = os.getenv("EMBEDDING_PROVIDER")
    embedding_model = os.getenv("EMBEDDING_MODEL")
    embedding_api_key = os.getenv("EMBEDDING_API_KEY")

    if embedding_provider and embedding_api_key:
        cognee.config.set_embedding_config(
            {
                "embedding_provider": embedding_provider,
                "embedding_model": embedding_model,
                "embedding_api_key": embedding_api_key,
            }
        )


# ---------------------------------------------------------------------------
# Tests
#
# Cognee uses KuzuDB (embedded graph DB) which holds a file lock.  Running
# add → cognify → search across separate test functions can cause lock
# conflicts.  We therefore run the full pipeline in a single test and do
# cleanup at the end.
# ---------------------------------------------------------------------------


async def test_cognee_ingest_and_search(test_file: Path):
    """Full pipeline: configure → add → cognify → search (chunks + graph)."""

    _setup_cognee_for_test()

    # ── Ingest ─────────────────────────────────────────────────────────
    await cognee.add(str(test_file), dataset_name=E2E_DATASET)
    await cognee.cognify(datasets=[E2E_DATASET])

    # ── Search: CHUNKS ─────────────────────────────────────────────────
    chunk_results = await cognee.search(
        query_text="deep fryer installation",
        query_type=SearchType.CHUNKS,
        datasets=[E2E_DATASET],
    )
    assert chunk_results is not None
    assert len(chunk_results) > 0, "CHUNKS search returned 0 results after cognify"

    # ── Search: GRAPH_COMPLETION ───────────────────────────────────────
    graph_results = await cognee.search(
        query_text="What safety features does the fryer have?",
        query_type=SearchType.GRAPH_COMPLETION,
        datasets=[E2E_DATASET],
    )
    assert graph_results is not None
    assert len(graph_results) > 0, "GRAPH_COMPLETION search returned 0 results"

    # ── Cleanup ────────────────────────────────────────────────────────
    await cognee.prune.prune_system(graph=True, vector=True, metadata=False)
