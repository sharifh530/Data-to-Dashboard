"""Allowlisted Server-Side Query Broker using standard Python library."""

import csv
import io
import math
from collections import Counter
from typing import Any

from dtd_api.dashboard_contracts import (
    DashboardQueryRequest,
    DashboardQueryResponse,
    FilterValue,
)


def _apply_filters(
    rows: list[dict[str, str]],
    filters: dict[str, FilterValue],
    allowed_columns: set[str],
) -> list[dict[str, str]]:
    """Safely filter rows using allowlisted column names and operators."""
    if not filters:
        return rows

    filtered = []
    for row in rows:
        match = True
        for col, filter_clause in filters.items():
            if col not in allowed_columns or col not in row:
                continue

            op = filter_clause.operator
            val = filter_clause.value
            cell_val = row.get(col, "")

            if op == "eq":
                if cell_val != str(val):
                    match = False
                    break
            elif op == "in" and isinstance(val, list):
                str_set = {str(v) for v in val}
                if cell_val not in str_set:
                    match = False
                    break
            elif op == "between" and isinstance(val, (list, tuple)) and len(val) == 2:
                try:
                    c_num = float(cell_val)
                    if not (float(val[0]) <= c_num <= float(val[1])):
                        match = False
                        break
                except (ValueError, TypeError):
                    match = False
                    break
            elif op == "gte":
                try:
                    c_num = float(cell_val)
                    if c_num < float(val):  # type: ignore[arg-type]
                        match = False
                        break
                except (ValueError, TypeError):
                    match = False
                    break
            elif op == "lte":
                try:
                    c_num = float(cell_val)
                    if c_num > float(val):  # type: ignore[arg-type]
                        match = False
                        break
                except (ValueError, TypeError):
                    match = False
                    break

        if match:
            filtered.append(row)

    return filtered


def execute_dashboard_query(
    csv_bytes: bytes,
    query: DashboardQueryRequest,
    allowed_columns: set[str],
) -> DashboardQueryResponse:
    """Execute a typed, bounded query over cleaned CSV data without external libraries."""
    try:
        text = csv_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        all_rows = list(reader)
    except Exception:
        return DashboardQueryResponse(
            query_id=query.query_id,
            data=[],
            total_matching_rows=0,
        )

    # Restrict row keys to allowlisted columns
    sanitized_rows: list[dict[str, str]] = [
        {k: v for k, v in r.items() if k in allowed_columns} for r in all_rows
    ]

    filtered_rows = _apply_filters(
        sanitized_rows, query.filters, allowed_columns)
    total_matching = len(filtered_rows)

    # 1. Table query
    if query.query_id == "table":
        sort_col = query.sort_by
        if sort_col and filtered_rows and sort_col in filtered_rows[0]:
            reverse = query.sort_direction == "desc"

            def sort_key(item: dict[str, str]) -> tuple[int, Any]:
                val = item.get(sort_col, "")
                try:
                    return (0, float(val))
                except ValueError:
                    return (1, val)

            filtered_rows = sorted(
                filtered_rows, key=sort_key, reverse=reverse)

        page_size = min(max(1, query.page_size), 100)
        offset = max(0, query.cursor)
        sliced = filtered_rows[offset: offset + page_size]
        next_cursor = str(offset + page_size) if offset + \
            page_size < total_matching else None
        return DashboardQueryResponse(
            query_id="table",
            data=[dict(r) for r in sliced],
            total_matching_rows=total_matching,
            next_cursor=next_cursor,
        )

    # 2. KPI query
    if query.query_id == "kpis":
        return DashboardQueryResponse(
            query_id="kpis",
            data=[{"total_matching_rows": total_matching}],
            total_matching_rows=total_matching,
        )

    # 3. Bar chart query
    if query.query_id.startswith("bar_"):
        col = query.query_id.removeprefix("bar_")
        values = [r[col] for r in filtered_rows if col in r and r[col] != ""]
        counter = Counter(values)
        sample_indicator = len(counter) > 500
        most_common = counter.most_common(500)
        data = [{"label": k, "value": v} for k, v in most_common]
        return DashboardQueryResponse(
            query_id=query.query_id,
            data=data,
            total_matching_rows=total_matching,
            sample_indicator=sample_indicator,
        )

    # 4. Histogram query
    if query.query_id.startswith("hist_"):
        col = query.query_id.removeprefix("hist_")
        nums = []
        for r in filtered_rows:
            if col in r:
                try:
                    nums.append(float(r[col]))
                except (ValueError, TypeError):
                    continue

        if nums:
            min_val = min(nums)
            max_val = max(nums)
            num_bins = 10
            span = max_val - min_val
            if span == 0:
                bin_width = 1.0
            else:
                bin_width = span / num_bins

            bins = [0] * num_bins
            for n in nums:
                idx = int((n - min_val) / bin_width) if bin_width > 0 else 0
                if idx >= num_bins:
                    idx = num_bins - 1
                bins[idx] += 1

            data = [
                {
                    "bin": f"{min_val + i * bin_width:.1f} - {min_val + (i + 1) * bin_width:.1f}",
                    "count": bins[i],
                    "min": round(min_val + i * bin_width, 2),
                    "max": round(min_val + (i + 1) * bin_width, 2),
                }
                for i in range(num_bins)
            ]
            return DashboardQueryResponse(
                query_id=query.query_id,
                data=data,
                total_matching_rows=total_matching,
            )

    # 5. Line chart query
    if query.query_id.startswith("line_"):
        col = query.query_id.removeprefix("line_")
        values = [r[col] for r in filtered_rows if col in r and r[col] != ""]
        counter = Counter(values)
        sorted_keys = sorted(counter.keys())
        sample_indicator = len(sorted_keys) > 500
        sampled_keys = sorted_keys[:500]
        data = [{"x": k, "y": counter[k]} for k in sampled_keys]
        return DashboardQueryResponse(
            query_id=query.query_id,
            data=data,
            total_matching_rows=total_matching,
            sample_indicator=sample_indicator,
        )

    # 6. Scatter chart query
    if query.query_id.startswith("scatter_"):
        parts = query.query_id.removeprefix("scatter_").split("_")
        if len(parts) >= 2:
            x_col = parts[0]
            y_col = "_".join(parts[1:])
            pts: list[dict[str, object]] = []
            for r in filtered_rows:
                if x_col in r and y_col in r:
                    try:
                        x = float(r[x_col])
                        y = float(r[y_col])
                        if not (math.isnan(x) or math.isnan(y)):
                            pts.append({"x": x, "y": y})
                    except (ValueError, TypeError):
                        continue
            sample_indicator = len(pts) > 500
            return DashboardQueryResponse(
                query_id=query.query_id,
                data=pts[:500],
                total_matching_rows=total_matching,
                sample_indicator=sample_indicator,
            )

    return DashboardQueryResponse(
        query_id=query.query_id,
        data=[],
        total_matching_rows=total_matching,
    )
