"""Clear all Cortex data: Cloudflare R2, Supabase, and the Cognee knowledge graph.

Usage:
    cd backend
    python scripts/clear_all.py                 # prompts before each step
    python scripts/clear_all.py --yes           # no prompts
    python scripts/clear_all.py --only r2       # r2 | supabase | cognee (repeatable)

Reads credentials from the project-root `.env`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
load_dotenv(REPO_ROOT / ".env")


def confirm(prompt: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    return input(f"{prompt} [y/N] ").strip().lower() in {"y", "yes"}


def clear_r2(auto_yes: bool) -> None:
    import boto3
    from botocore.exceptions import ClientError

    endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT")
    access_key = os.getenv("R2_ACCESS_KEY_ID") or os.getenv(
        "CLOUDFLARE_R2_ACCESS_KEY_ID"
    )
    secret_key = os.getenv("R2_SECRET_KEY") or os.getenv("CLOUDFLARE_R2_SECRET_KEY")
    bucket = os.getenv("CLOUDFLARE_R2_BUCKET_NAME")

    if not all([endpoint, access_key, secret_key, bucket]):
        print("[r2] missing credentials — skipping")
        return

    if not confirm(f"[r2] delete ALL objects in bucket '{bucket}'?", auto_yes):
        print("[r2] skipped")
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    deleted = 0
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket):
            objs = page.get("Contents") or []
            if not objs:
                continue
            s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in objs]},
            )
            deleted += len(objs)
    except ClientError as e:
        print(f"[r2] error: {e}")
        return
    print(f"[r2] deleted {deleted} objects from '{bucket}'")


async def clear_supabase(auto_yes: bool) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("[supabase] missing credentials — skipping")
        return

    if not confirm("[supabase] truncate table 'cortex_documents'?", auto_yes):
        print("[supabase] skipped")
        return

    from supabase import acreate_client

    sb = await acreate_client(url, key)
    res = (
        await sb.table("cortex_documents")
        .delete()
        .neq("id", "00000000-0000-0000-0000-000000000000")
        .execute()
    )
    print(f"[supabase] deleted {len(res.data or [])} rows from cortex_documents")


async def clear_cognee_local(auto_yes: bool) -> None:
    # Cognee resolves system_root and graph_file_path relative to the
    # installed package (not CWD). Ask cognee directly where the graph and
    # vector files live so we handle venv-internal paths and env-var
    # overrides (COGNEE_SYSTEM_PATH, GRAPH_FILE_PATH) consistently.
    cognee_paths: list[Path] = []
    try:
        from cognee.base_config import get_base_config

        cognee_paths.append(Path(get_base_config().system_root_directory))
    except Exception as e:
        print(f"[cognee] could not resolve system_root via cognee ({e})")

    try:
        from cognee.infrastructure.databases.graph.config import get_graph_config

        gfp = Path(get_graph_config().graph_file_path)
        # The graph file itself (Kuzu DB directory), its parent (databases/),
        # and any .wal / .lock siblings Kuzu writes next to it.
        cognee_paths.append(gfp)
        cognee_paths.append(gfp.with_suffix(gfp.suffix + ".wal"))
        cognee_paths.append(Path(str(gfp) + ".wal"))
        cognee_paths.append(Path(str(gfp) + ".lock"))
    except Exception as e:
        print(f"[cognee] could not resolve graph_file_path via cognee ({e})")

    targets = [
        *cognee_paths,
        BACKEND_ROOT / ".cognee_system",
        BACKEND_ROOT / ".data_storage",
        BACKEND_ROOT / "cortex_local.db",
        BACKEND_ROOT / "cortex_local.db-shm",
        BACKEND_ROOT / "cortex_local.db-wal",
    ]
    # Dedup while preserving order
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in targets:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    targets = deduped

    existing = [p for p in targets if p.exists()]
    if not existing:
        print("[cognee] no local storage to remove")
    else:
        if not confirm(
            f"[cognee] delete {len(existing)} local path(s): {[p.name for p in existing]}?",
            auto_yes,
        ):
            print("[cognee] local delete skipped")
        else:
            for p in existing:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                print(f"[cognee] removed {p}")

    vector_url = os.getenv("VECTOR_DB_URL")
    if not vector_url:
        print("[cognee] no VECTOR_DB_URL — skipping pgvector wipe")
        return

    if not confirm(
        "[cognee] drop all tables in pgvector database (public schema)?", auto_yes
    ):
        print("[cognee] pgvector skipped")
        return

    try:
        import asyncpg
    except ImportError:
        print(
            "[cognee] asyncpg not installed — run `pip install asyncpg` to wipe pgvector"
        )
        return

    dsn = vector_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )

    try:
        conn = await asyncpg.connect(dsn)
    except (OSError, asyncpg.PostgresError) as e:
        print(f"[cognee] could not connect to pgvector ({e}) — skipping")
        return
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        await conn.close()
    print("[cognee] dropped and recreated public schema in pgvector DB")


def warn_if_backend_running() -> None:
    """Kuzu holds file handles when uvicorn is running; warn if we detect it."""
    try:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", 8000)) == 0:
                print(
                    "[warn] backend appears to be running on :8000. "
                    "Stop uvicorn first, or Kuzu will rewrite the graph on shutdown."
                )
    except Exception:
        pass


async def main() -> int:
    warn_if_backend_running()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes", "-y", action="store_true", help="skip all confirmations"
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=["r2", "supabase", "cognee"],
        help="run only the specified step(s); repeatable",
    )
    args = parser.parse_args()

    steps = set(args.only) if args.only else {"r2", "supabase", "cognee"}

    if "r2" in steps:
        clear_r2(args.yes)
    if "supabase" in steps:
        await clear_supabase(args.yes)
    if "cognee" in steps:
        await clear_cognee_local(args.yes)

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
