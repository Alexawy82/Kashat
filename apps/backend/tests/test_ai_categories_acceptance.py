import importlib
from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

import kashat.api.routes.ai_categories as ai_routes
from kashat.ai_category_schemas import BatchAcceptanceRequest, SingleAcceptanceRequest


def _routes():
    importlib.reload(ai_routes)
    return ai_routes


def _seed_for_acceptance(db_conn):
    db_conn.execute(
        "INSERT INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)",
        ["acc1", "acc1", "checking", "USD"],
    )
    db_conn.execute(
        'INSERT INTO "transaction" (id, account_id, posted_at, amount, currency, description_norm, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ["tx1", "acc1", datetime(2024, 1, 1), -12.34, "USD", "grocery store", "fp_tx1", datetime.now(UTC)],
    )
    cols = [row[1] for row in db_conn.execute("PRAGMA table_info('category')").fetchall()]
    if "normalized_name" in cols:
        db_conn.execute(
            "INSERT INTO category (id, name, normalized_name) VALUES (?, ?, ?)",
            ["cat_grocery", "Groceries", "groceries"],
        )
    else:
        db_conn.execute(
            "INSERT INTO category (id, name) VALUES (?, ?)",
            ["cat_grocery", "Groceries"],
        )


@pytest.mark.asyncio
async def test_preview_batch_acceptance_uses_shared_schema(db_conn):
    _seed_for_acceptance(db_conn)
    routes = _routes()

    req = BatchAcceptanceRequest(
        acceptances=[
            SingleAcceptanceRequest(
                transaction_id="tx1",
                suggested_category_name="Groceries",
                confidence=0.9,
                create_if_missing=True,
                auto_merge_similar=True,
            )
        ],
        create_missing_categories=True,
        auto_merge_threshold=0.85,
    )

    res = await routes.preview_batch_acceptance(req)
    preview = res["preview"]
    assert preview["total_transactions"] == 1
    assert len(preview["will_use_existing"]) == 1


@pytest.mark.asyncio
async def test_accept_batch_accepts_existing_category(db_conn):
    _seed_for_acceptance(db_conn)
    routes = _routes()

    req = BatchAcceptanceRequest(
        acceptances=[
            SingleAcceptanceRequest(
                transaction_id="tx1",
                suggested_category_name="Groceries",
                confidence=0.9,
                create_if_missing=True,
                auto_merge_similar=True,
            )
        ],
        create_missing_categories=True,
        auto_merge_threshold=0.85,
    )

    res = await routes.accept_batch_categories(req)
    assert res["successful_applications"] == 1
    assert res["categories_created"] == 0


def test_batch_acceptance_validation_error():
    with pytest.raises(ValidationError):
        BatchAcceptanceRequest.model_validate({
            "acceptances": [{"transaction_id": "tx1"}]
        })
