from datetime import date


def test_monthly_and_summary_exclude_adjustments(db_conn, seed_transactions):
    seed_transactions(
        [
            {"id": "s1", "account_id": "acc1", "posted_at": date(2024, 1, 1), "amount": -10.0, "currency": "USD", "description_norm": "coffee"},
            {"id": "s2", "account_id": "acc1", "posted_at": date(2024, 1, 2), "amount": 100.0, "currency": "USD", "description_norm": "payroll"},
            {"id": "s3", "account_id": "acc1", "posted_at": date(2024, 1, 3), "amount": 5.0, "currency": "USD", "description_norm": "cashback"},
        ]
    )
    db_conn.execute("UPDATE transaction SET is_adjustment = TRUE WHERE id = ?", ["s3"])

    from kashat.api.routes import analytics as analytics_routes

    monthly = analytics_routes.monthly_summary(start_date=None, end_date=None, account_id=None)
    assert len(monthly) == 1
    assert float(monthly[0]["income"]) == 100.0
    assert float(monthly[0]["spend"]) == 10.0

    summary = analytics_routes.summary(start_date=None, end_date=None, include_transfers=False)
    assert float(summary["totals"]["income"]) == 100.0
    assert float(summary["totals"]["spend"]) == 10.0
    assert float(summary["totals"]["net"]) == 90.0
