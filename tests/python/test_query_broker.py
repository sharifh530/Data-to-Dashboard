"""Tests for allowlisted server query broker."""

from dtd_api.dashboard_contracts import DashboardQueryRequest, FilterValue
from dtd_api.query_broker import execute_dashboard_query

CSV_DATA = b"""order_id,channel,category,quantity,unit_price,revenue
1,Direct,Apparel,2,50,100
2,Direct,Electronics,1,300,300
3,Organic,Apparel,5,20,100
4,Organic,Home,3,40,120
5,Referral,Electronics,2,150,300
6,Direct,Home,1,80,80
"""

ALLOWED_COLUMNS = {"order_id", "channel",
                   "category", "quantity", "unit_price", "revenue"}


def test_query_broker_table():
    req = DashboardQueryRequest(
        query_id="table",
        cursor=0,
        page_size=2,
        sort_by="revenue",
        sort_direction="desc",
    )
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.query_id == "table"
    assert res.total_matching_rows == 6
    assert len(res.data) == 2
    assert res.next_cursor == "2"
    # Verify descending sort by revenue (300 first)
    assert res.data[0]["revenue"] == "300"


def test_query_broker_filter_eq():
    req = DashboardQueryRequest(
        query_id="table",
        filters={"channel": FilterValue(operator="eq", value="Direct")},
    )
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.total_matching_rows == 3
    assert all(r["channel"] == "Direct" for r in res.data)


def test_query_broker_filter_in():
    req = DashboardQueryRequest(
        query_id="table",
        filters={"channel": FilterValue(
            operator="in", value=["Organic", "Referral"])},
    )
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.total_matching_rows == 3
    assert all(r["channel"] in ("Organic", "Referral") for r in res.data)


def test_query_broker_filter_between():
    req = DashboardQueryRequest(
        query_id="table",
        filters={"revenue": FilterValue(operator="between", value=[100, 200])},
    )
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    # matching: 100, 100, 120 -> 3 rows
    assert res.total_matching_rows == 3


def test_query_broker_bar_chart():
    req = DashboardQueryRequest(query_id="bar_channel")
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.query_id == "bar_channel"
    assert res.total_matching_rows == 6
    labels = {r["label"]: r["value"] for r in res.data}
    assert labels["Direct"] == 3
    assert labels["Organic"] == 2
    assert labels["Referral"] == 1


def test_query_broker_histogram():
    req = DashboardQueryRequest(query_id="hist_revenue")
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.query_id == "hist_revenue"
    assert len(res.data) == 10
    total_binned = sum(b["count"] for b in res.data)
    assert total_binned == 6


def test_query_broker_scatter():
    req = DashboardQueryRequest(query_id="scatter_quantity_revenue")
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.query_id == "scatter_quantity_revenue"
    assert len(res.data) == 6
    assert isinstance(res.data[0]["x"], float)
    assert isinstance(res.data[0]["y"], float)


def test_query_broker_ignores_unallowed_column():
    req = DashboardQueryRequest(
        query_id="table",
        filters={"malicious_col": FilterValue(
            operator="eq", value="drop table")},
    )
    # Should not error or filter
    res = execute_dashboard_query(CSV_DATA, req, ALLOWED_COLUMNS)
    assert res.total_matching_rows == 6
