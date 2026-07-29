from datetime import datetime, timedelta

from app import build_report_window


def test_build_report_window_uses_last_7_days():
    today = datetime.now().date()
    start, end, _ = build_report_window("7d")
    assert start.date() == today - timedelta(days=6)
    assert end.date() == today


def test_build_report_window_uses_last_30_days():
    today = datetime.now().date()
    start, end, _ = build_report_window("30d")
    assert start.date() == today - timedelta(days=29)
    assert end.date() == today


def test_build_report_window_uses_last_24_hours():
    today = datetime.now().date()
    start, end, _ = build_report_window("24h")
    assert start.date() == today
    assert end.date() == today
