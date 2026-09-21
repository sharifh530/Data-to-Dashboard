"""Contracts for Dashboard Specification v1, Query Broker, and Dashboard View."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from dtd_api.contracts import Contract


class KpiSpec(Contract):
    id: str
    label: str
    value: float | int | str
    format: Literal["number", "currency", "percent", "text"] = "number"
    description: str = ""


class ChartSpec(Contract):
    id: str
    title: str
    chart_type: Literal["bar", "line", "scatter", "histogram"]
    query_id: str
    x_axis: str
    y_axis: str
    summary: str = ""


class FilterSpec(Contract):
    column: str
    label: str
    type: Literal["category", "range", "date"]
    allowed_operators: list[Literal["eq", "in",
                                    "between", "gte", "lte"]] = ["eq", "in"]
    options: list[str] | None = None
    min_val: float | None = None
    max_val: float | None = None


class TableSpec(Contract):
    columns: list[str]
    page_size: int = Field(default=50, ge=1, le=100)
    default_sort: str | None = None
    sort_direction: Literal["asc", "desc"] = "asc"


class DashboardSpec(Contract):
    schema_version: Literal["1"] = "1"
    dataset_version_id: str
    title: str
    summary: str
    kpis: list[KpiSpec] = Field(default_factory=list, max_length=6)
    charts: list[ChartSpec] = Field(default_factory=list, max_length=6)
    filters: list[FilterSpec] = Field(default_factory=list, max_length=4)
    table: TableSpec
    warnings: list[str] = Field(default_factory=list)
    model_report_ref: str | None = None


class FilterValue(Contract):
    operator: Literal["eq", "in", "between", "gte", "lte"]
    value: object


class DashboardQueryRequest(Contract):
    query_id: str
    filters: dict[str, FilterValue] = Field(default_factory=dict)
    cursor: int = 0
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: str | None = None
    sort_direction: Literal["asc", "desc"] = "asc"


class DashboardQueryResponse(Contract):
    query_id: str
    data: list[dict[str, object]]
    total_matching_rows: int
    sample_indicator: bool = False
    next_cursor: str | None = None


class DashboardView(Contract):
    run_id: UUID
    spec: DashboardSpec
    bundle_artifact_id: UUID | None = None
    render_mode: Literal["generated", "fallback"] = "fallback"
    status: str = "ready"
