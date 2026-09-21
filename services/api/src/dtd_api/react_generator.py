"""React component code generator and AST safety validation for isolated dashboards."""

import re

from dtd_api.dashboard_contracts import DashboardSpec

MAX_SOURCE_BYTES = 100 * 1024  # 100 KiB maximum source limit

FORBIDDEN_PATTERNS = [
    (r"\beval\s*\(", "eval() is prohibited"),
    (r"\bFunction\s*\(", "Function constructor is prohibited"),
    (r"\bwindow\.parent\b", "window.parent access is prohibited"),
    (r"\bdocument\.cookie\b", "document.cookie access is prohibited"),
    (r"\blocalStorage\b", "localStorage access is prohibited"),
    (r"\bsessionStorage\b", "sessionStorage access is prohibited"),
    (r"\bfetch\s*\(", "Direct network fetch() is prohibited"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest is prohibited"),
    (r"\bWebSocket\b", "WebSocket is prohibited"),
    (r"<\s*script\b", "<script> injection is prohibited"),
    (r"\bdangerouslySetInnerHTML\b", "dangerouslySetInnerHTML is prohibited"),
    (r"\bimportScripts\b", "importScripts is prohibited"),
]


class ReactSecurityError(ValueError):
    """Raised when generated React source violates security rules."""

    pass


def validate_react_source(source: str) -> None:
    """Validate generated React source code against security constraints."""
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ReactSecurityError(
            f"Generated source exceeded {MAX_SOURCE_BYTES} bytes budget.")

    for pattern, reason in FORBIDDEN_PATTERNS:
        if re.search(pattern, source, re.IGNORECASE):
            raise ReactSecurityError(f"Security policy violation: {reason}")


def _bar_chart_jsx(cid: str, title: str, summary: str, x_col: str, y_col: str) -> str:
    return f"""        <div key="{cid}" className="chart-card" data-testid="chart-{cid}">
          <div className="chart-header">
            <h3>{title}</h3>
            <span className="badge">Bar Chart</span>
          </div>
          <p className="chart-summary">{summary}</p>
          <div className="chart-svg-container">
            {{chartData["{cid}"] && chartData["{cid}"].length > 0 ? (
              <svg viewBox="0 0 500 240" className="chart-svg" role="img" aria-label="{title}">
                {{(() => {{
                  const data = chartData["{cid}"].slice(0, 20);
                  const maxVal = Math.max(...data.map((d: any) => Number(d["{y_col}"] || 0)), 1);
                  const barWidth = Math.max(12, Math.floor(400 / data.length) - 8);
                  return data.map((d: any, idx: number) => {{
                    const val = Number(d["{y_col}"] || 0);
                    const h = Math.round((val / maxVal) * 180);
                    const x = 50 + idx * (barWidth + 8);
                    const y = 200 - h;
                    const lbl = String(d["{x_col}"] || "");
                    const shortLbl = lbl.length > 8 ? lbl.slice(0, 7) + "…" : lbl;
                    const dispVal = val >= 1000 ? (val / 1000).toFixed(1) + "k" : val;
                    return (
                      <g key={{idx}}>
                        <rect x={{x}} y={{y}} width={{barWidth}} height={{h}} rx="2"
                              fill="var(--color-primary, #3b82f6)" />
                        <text x={{x + barWidth / 2}} y="218" fontSize="10"
                              textAnchor="middle" fill="#64748b">
                          {{shortLbl}}
                        </text>
                        <text x={{x + barWidth / 2}} y={{Math.max(15, y - 4)}} fontSize="10"
                              textAnchor="middle" fill="#1e293b" fontWeight="600">
                          {{dispVal}}
                        </text>
                      </g>
                    );
                  }});
                }})()}}
              </svg>
            ) : (
              <p className="no-data">No data matching active filters</p>
            )}}
          </div>
        </div>"""


def _line_chart_jsx(cid: str, title: str, summary: str, x_col: str, y_col: str) -> str:
    return f"""        <div key="{cid}" className="chart-card" data-testid="chart-{cid}">
          <div className="chart-header">
            <h3>{title}</h3>
            <span className="badge">Line Trend</span>
          </div>
          <p className="chart-summary">{summary}</p>
          <div className="chart-svg-container">
            {{chartData["{cid}"] && chartData["{cid}"].length > 0 ? (
              <svg viewBox="0 0 500 240" className="chart-svg" role="img" aria-label="{title}">
                {{(() => {{
                  const data = chartData["{cid}"].slice(0, 30);
                  const maxVal = Math.max(...data.map((d: any) => Number(d["{y_col}"] || 0)), 1);
                  const minVal = Math.min(...data.map((d: any) => Number(d["{y_col}"] || 0)), 0);
                  const range = Math.max(maxVal - minVal, 1);
                  const stepX = data.length > 1 ? 400 / (data.length - 1) : 400;
                  const pts = data.map((d: any, idx: number) => {{
                    const x = 50 + idx * stepX;
                    const diff = Number(d["{y_col}"] || 0) - minVal;
                    const y = 200 - Math.round((diff / range) * 180);
                    return `${{x}},${{y}}`;
                  }}).join(" ");
                  return (
                    <g>
                      <polyline fill="none" stroke="var(--color-primary, #3b82f6)"
                                strokeWidth="3" points={{pts}} />
                      {{data.map((d: any, idx: number) => {{
                        const cx = 50 + idx * stepX;
                        const diff = Number(d["{y_col}"] || 0) - minVal;
                        const cy = 200 - Math.round((diff / range) * 180);
                        return <circle key={{idx}} cx={{cx}} cy={{cy}} r="4"
                                       fill="var(--color-primary, #3b82f6)" />;
                      }})}}
                    </g>
                  );
                }})()}}
              </svg>
            ) : (
              <p className="no-data">No data matching active filters</p>
            )}}
          </div>
        </div>"""


def _scatter_chart_jsx(cid: str, title: str, summary: str, x_col: str, y_col: str) -> str:
    return f"""        <div key="{cid}" className="chart-card" data-testid="chart-{cid}">
          <div className="chart-header">
            <h3>{title}</h3>
            <span className="badge">Scatter Plot</span>
          </div>
          <p className="chart-summary">{summary}</p>
          <div className="chart-svg-container">
            {{chartData["{cid}"] && chartData["{cid}"].length > 0 ? (
              <svg viewBox="0 0 500 240" className="chart-svg" role="img" aria-label="{title}">
                {{(() => {{
                  const data = chartData["{cid}"].slice(0, 100);
                  const maxX = Math.max(...data.map((d: any) => Number(d["{x_col}"] || 0)), 1);
                  const maxY = Math.max(...data.map((d: any) => Number(d["{y_col}"] || 0)), 1);
                  return data.map((d: any, idx: number) => {{
                    const cx = 50 + Math.round((Number(d["{x_col}"] || 0) / maxX) * 400);
                    const cy = 200 - Math.round((Number(d["{y_col}"] || 0) / maxY) * 180);
                    return <circle key={{idx}} cx={{cx}} cy={{cy}} r="4" opacity="0.7"
                                   fill="var(--color-primary, #3b82f6)" />;
                  }});
                }})()}}
              </svg>
            ) : (
              <p className="no-data">No data matching active filters</p>
            )}}
          </div>
        </div>"""


def _histogram_chart_jsx(cid: str, title: str, summary: str) -> str:
    return f"""        <div key="{cid}" className="chart-card" data-testid="chart-{cid}">
          <div className="chart-header">
            <h3>{title}</h3>
            <span className="badge">Histogram</span>
          </div>
          <p className="chart-summary">{summary}</p>
          <div className="chart-svg-container">
            {{chartData["{cid}"] && chartData["{cid}"].length > 0 ? (
              <svg viewBox="0 0 500 240" className="chart-svg" role="img" aria-label="{title}">
                {{(() => {{
                  const data = chartData["{cid}"];
                  const maxC = Math.max(...data.map((d: any) => Number(d["count"] || 0)), 1);
                  const barWidth = Math.max(16, Math.floor(400 / data.length) - 4);
                  return data.map((d: any, idx: number) => {{
                    const c = Number(d["count"] || 0);
                    const h = Math.round((c / maxC) * 180);
                    const x = 50 + idx * (barWidth + 4);
                    const y = 200 - h;
                    const bin = String(d["bin"] || "");
                    const shortBin = bin.length > 7 ? bin.slice(0, 6) + "…" : bin;
                    return (
                      <g key={{idx}}>
                        <rect x={{x}} y={{y}} width={{barWidth}} height={{h}} rx="1"
                              fill="var(--color-primary, #3b82f6)" />
                        <text x={{x + barWidth / 2}} y="218" fontSize="9"
                              textAnchor="middle" fill="#64748b">
                          {{shortBin}}
                        </text>
                        <text x={{x + barWidth / 2}} y={{Math.max(15, y - 4)}} fontSize="9"
                              textAnchor="middle" fill="#1e293b">
                          {{c}}
                        </text>
                      </g>
                    );
                  }});
                }})()}}
              </svg>
            ) : (
              <p className="no-data">No data matching active filters</p>
            )}}
          </div>
        </div>"""


def generate_react_dashboard(spec: DashboardSpec) -> str:
    """Generate a valid, standalone React TSX component from a DashboardSpec."""
    chart_renderers: list[str] = []
    for chart in spec.charts:
        cid = chart.query_id
        ctype = chart.chart_type
        title = chart.title.replace('"', '\\"')
        x_col = chart.x_axis.replace('"', '\\"')
        y_col = chart.y_axis.replace('"', '\\"')
        summary = chart.summary.replace('"', '\\"')

        if ctype == "bar":
            chart_renderers.append(_bar_chart_jsx(
                cid, title, summary, x_col, y_col))
        elif ctype == "line":
            chart_renderers.append(_line_chart_jsx(
                cid, title, summary, x_col, y_col))
        elif ctype == "scatter":
            chart_renderers.append(_scatter_chart_jsx(
                cid, title, summary, x_col, y_col))
        else:  # histogram
            chart_renderers.append(_histogram_chart_jsx(cid, title, summary))

    charts_jsx = "\n".join(chart_renderers)

    kpis_jsx = "\n".join(
        [
            f"""      <div className="kpi-card" key="{kpi.id}">
        <span className="kpi-title">{kpi.label}</span>
        <strong className="kpi-value">{kpi.value}</strong>
        <p className="kpi-desc">{kpi.description}</p>
      </div>"""
            for kpi in spec.kpis
        ]
    )

    filter_inputs: list[str] = []
    for f in spec.filters:
        col = f.column
        ftype = f.type
        label = f.label.replace('"', '\\"')
        if ftype == "category":
            options_jsx = "\n".join(
                [
                    f'            <option key="{opt}" value="{opt}">{opt}</option>'
                    for opt in (f.options or [])
                ]
            )
            filter_inputs.append(f"""
        <label key="{col}">
          <span>{label}</span>
          <select
            value={{filters["{col}"]?.value || ""}}
            onChange={{(e) => {{
              const v = e.target.value;
              handleFilterChange("{col}", v ? {{ operator: "eq", value: v }} : null);
            }}}}
          >
            <option value="">All</option>
{options_jsx}
          </select>
        </label>""")
        elif ftype in ("range", "date"):
            filter_inputs.append(f"""
        <label key="{col}">
          <span>{label} (Min)</span>
          <input
            type="number"
            placeholder="Min"
            value={{filters["{col}"]?.value || ""}}
            onChange={{(e) => {{
              const v = e.target.value;
              handleFilterChange("{col}", v ? {{ operator: "gte", value: Number(v) }} : null);
            }}}}
          />
        </label>""")

    filters_jsx = "\n".join(filter_inputs)

    table_headers = "\n".join(
        [
            f'              <th key="{col}" onClick={{() => handleSort("{col}")}} '
            f'style={{{{ cursor: "pointer" }}}}>'
            f'{col} {{sortBy === "{col}" ? (sortDir === "asc" ? "▲" : "▼") : ""}}</th>'
            for col in spec.table.columns
        ]
    )

    table_cells = "\n".join(
        [
            f'                <td key="{col}">{{String(row["{col}"] ?? "")}}</td>'
            for col in spec.table.columns
        ]
    )

    initial_chart_queries = ", ".join([f'"{c.query_id}"' for c in spec.charts])
    table_query_id = "table_page"
    default_sort_col = (
        spec.table.default_sort or (
            spec.table.columns[0] if spec.table.columns else "")
    )

    warnings_jsx = ""
    if spec.warnings:
        warn_items = "\n".join(
            [f'          <li>{w.replace("\"", "\\\"")}</li>' for w in spec.warnings]
        )
        warnings_jsx = f"""      <div className="warnings-banner" role="alert">
        <strong>Warnings:</strong>
        <ul>
{warn_items}
        </ul>
      </div>"""

    filters_container_jsx = ""
    if filter_inputs:
        filters_container_jsx = f"""      <section className="filters-section" aria-label="Filters">
{filters_jsx}
      </section>"""

    source = f"""import React, {{ useState, useEffect, useCallback }} from "react";

export interface DashboardProps {{
  query: (request: {{
    query_id: string;
    filters?: Record<string, {{ operator: string; value: any }}>;
    cursor?: number;
    page_size?: number;
    sort_by?: string;
    sort_direction?: "asc" | "desc";
  }}) => Promise<{{
    query_id: string;
    data: any[];
    total_matching_rows: number;
    sample_indicator?: boolean;
    next_cursor?: string | null;
  }}>;
}}

export default function Dashboard(props: DashboardProps) {{
  const [filters, setFilters] = useState<Record<string, {{ operator: string; value: any }}>>({{}});
  const [chartData, setChartData] = useState<Record<string, any[]>>({{}});
  const [tableRows, setTableRows] = useState<any[]>([]);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [page, setPage] = useState<number>(0);
  const [pageSize] = useState<number>(20);
  const [sortBy, setSortBy] = useState<string>("{default_sort_col}");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState<boolean>(true);

  const fetchCharts = useCallback(async (activeFilters: Record<string, any>) => {{
    const chartIds = [{initial_chart_queries}];
    const results: Record<string, any[]> = {{}};
    for (const cid of chartIds) {{
      try {{
        const res = await props.query({{ query_id: cid, filters: activeFilters }});
        results[cid] = res.data || [];
      }} catch (err) {{
        results[cid] = [];
      }}
    }}
    setChartData(results);
  }}, [props]);

  const fetchTable = useCallback(async (
    activeFilters: Record<string, any>,
    p: number,
    sBy: string,
    sDir: "asc" | "desc"
  ) => {{
    try {{
      const res = await props.query({{
        query_id: "{table_query_id}",
        filters: activeFilters,
        cursor: p * pageSize,
        page_size: pageSize,
        sort_by: sBy,
        sort_direction: sDir,
      }});
      setTableRows(res.data || []);
      setTotalRows(res.total_matching_rows || 0);
    }} catch (err) {{
      setTableRows([]);
      setTotalRows(0);
    }}
  }}, [props, pageSize]);

  useEffect(() => {{
    setLoading(true);
    Promise.all([
      fetchCharts(filters),
      fetchTable(filters, page, sortBy, sortDir),
    ]).finally(() => setLoading(false));
  }}, [filters, page, sortBy, sortDir, fetchCharts, fetchTable]);

  const handleFilterChange = (col: string, val: {{ operator: string; value: any }} | null) => {{
    setFilters((prev) => {{
      const next = {{ ...prev }};
      if (val === null) delete next[col];
      else next[col] = val;
      return next;
    }});
    setPage(0);
  }};

  const handleSort = (col: string) => {{
    if (sortBy === col) {{
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    }} else {{
      setSortBy(col);
      setSortDir("asc");
    }}
    setPage(0);
  }};

  const totalPages = Math.ceil(totalRows / pageSize) || 1;

  return (
    <article className="generated-dashboard">
      <header className="dashboard-header">
        <h2>{spec.title}</h2>
        <p className="summary">{spec.summary}</p>
{warnings_jsx}
      </header>

      <section className="kpis-section">
{kpis_jsx}
      </section>

{filters_container_jsx}

      <section className="charts-grid">
{charts_jsx}
      </section>

      <section className="table-section">
        <div className="table-header">
          <h3>Data Preview</h3>
          <span>{{totalRows}} rows matching filters</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
{table_headers}
              </tr>
            </thead>
            <tbody>
              {{tableRows.map((row, idx) => (
                <tr key={{idx}}>
{table_cells}
                </tr>
              ))}}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <button disabled={{page <= 0}} onClick={{() => setPage((p) => Math.max(0, p - 1))}}>
            ← Previous
          </button>
          <span>Page {{page + 1}} of {{totalPages}}</span>
          <button disabled={{page + 1 >= totalPages}} onClick={{() => setPage((p) => p + 1)}}>
            Next →
          </button>
        </div>
      </section>
    </article>
  );
}}
"""

    validate_react_source(source)
    return source
