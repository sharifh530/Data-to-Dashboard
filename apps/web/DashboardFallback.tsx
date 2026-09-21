import { useEffect, useState, useId } from "react";
import type { components } from "../../packages/contracts/api";

type DashboardView = components["schemas"]["DashboardView"];
type QueryResponse = components["schemas"]["DashboardQueryResponse"];
type FilterValue = components["schemas"]["FilterValue"];

export function DashboardFallback({
  runId,
  csrf,
  onClose,
}: {
  runId: string;
  csrf: string;
  onClose?: () => void;
}) {
  const [dashboard, setDashboard] = useState<DashboardView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<Record<string, FilterValue>>({});
  const [chartData, setChartData] = useState<Record<string, QueryResponse>>({});
  const [tableData, setTableData] = useState<QueryResponse | null>(null);
  const [tablePage, setTablePage] = useState(0);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const baseId = useId();

  // Load Dashboard Spec
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        setLoading(true);
        setError("");
        const res = await fetch(`/api/v1/runs/${runId}/dashboard`, {
          signal: controller.signal,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => null);
          throw new Error(
            err?.error?.message ?? "Failed to load dashboard specification.",
          );
        }
        const data: DashboardView = await res.json();
        setDashboard(data);
      } catch (e) {
        if (!controller.signal.aborted) {
          setError(e instanceof Error ? e.message : "Connection failed.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [runId]);

  // Query Charts and Table when filters or pagination change
  useEffect(() => {
    if (!dashboard?.spec) return;
    const controller = new AbortController();

    async function executeQuery(
      queryId: string,
      page = 0,
      sortCol: string | null = null,
      sortDir: "asc" | "desc" = "asc",
    ): Promise<QueryResponse> {
      const res = await fetch(`/api/v1/runs/${runId}/queries`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({
          query_id: queryId,
          filters,
          cursor: page * 50,
          page_size: 50,
          sort_by: sortCol,
          sort_direction: sortDir,
        }),
        signal: controller.signal,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message ?? `Query ${queryId} failed.`);
      }
      return res.json();
    }

    // Run chart queries
    const chartsList = dashboard.spec.charts ?? [];
    chartsList.forEach((chart) => {
      void executeQuery(chart.query_id).then((res) => {
        if (!controller.signal.aborted) {
          setChartData((prev) => ({ ...prev, [chart.query_id]: res }));
        }
      });
    });

    // Run table query
    void executeQuery("table", tablePage, sortBy, sortDirection).then((res) => {
      if (!controller.signal.aborted) {
        setTableData(res);
      }
    });

    return () => controller.abort();
  }, [dashboard, runId, filters, tablePage, sortBy, sortDirection, csrf]);

  function resetFilters() {
    setFilters({});
    setTablePage(0);
  }

  function handleFilterChange(col: string, val: string) {
    setTablePage(0);
    if (!val) {
      setFilters((prev) => {
        const next = { ...prev };
        delete next[col];
        return next;
      });
    } else {
      setFilters((prev) => ({
        ...prev,
        [col]: { operator: "eq", value: val },
      }));
    }
  }

  if (loading) {
    return (
      <div className="card" role="status" style={{ marginTop: "20px" }}>
        <p>Loading dashboard specification…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card error" role="alert" style={{ marginTop: "20px" }}>
        <p>{error}</p>
        {onClose && (
          <button className="secondary" onClick={onClose}>
            Back
          </button>
        )}
      </div>
    );
  }

  if (!dashboard?.spec) return null;
  const { spec } = dashboard;
  const filtersList = spec.filters ?? [];
  const kpisList = spec.kpis ?? [];
  const chartsList = spec.charts ?? [];
  const matchingRows = tableData?.total_matching_rows ?? 0;

  return (
    <section
      className="card dashboard-fallback"
      aria-label="Dashboard"
      style={{ marginTop: "24px" }}
    >
      {/* Header & Status Notice */}
      <div className="section-title">
        <div>
          <span className="step">DASHBOARD / REVIEWED FALLBACK</span>
          <h2>{spec.title}</h2>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span className="status" role="status">
            Standard layout active (Fallback mode)
          </span>
          {onClose && (
            <button
              className="text-button"
              onClick={onClose}
              aria-label="Close dashboard"
            >
              ✕ Close
            </button>
          )}
        </div>
      </div>
      <p style={{ marginTop: "6px", color: "#59685e" }}>{spec.summary}</p>

      {/* Filter Bar */}
      {filtersList.length > 0 && (
        <div
          className="filters-bar"
          style={{
            background: "#edf2e8",
            padding: "16px",
            borderRadius: "8px",
            marginTop: "16px",
            display: "flex",
            flexWrap: "wrap",
            gap: "16px",
            alignItems: "flex-end",
          }}
        >
          {filtersList.map((f, i) => {
            const current = (filters[f.column]?.value as string) || "";
            const filterInputId = `${baseId}-filter-${f.column}-${i}`;
            return (
              <div key={f.column} style={{ minWidth: "160px", flex: "1" }}>
                <label
                  htmlFor={filterInputId}
                  style={{ margin: "0 0 6px 0", fontSize: "12px" }}
                >
                  Filter: {f.label}
                </label>
                {f.type === "category" && f.options ? (
                  <select
                    id={filterInputId}
                    aria-label={`Filter by ${f.label}`}
                    value={current}
                    onChange={(e) =>
                      handleFilterChange(f.column, e.target.value)
                    }
                    style={{ padding: "8px", fontSize: "13px" }}
                  >
                    <option value="">All {f.label}</option>
                    {f.options.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={filterInputId}
                    aria-label={`Filter by ${f.label}`}
                    type="text"
                    placeholder={`Filter ${f.label}`}
                    value={current}
                    onChange={(e) =>
                      handleFilterChange(f.column, e.target.value)
                    }
                    style={{ padding: "8px", fontSize: "13px" }}
                  />
                )}
              </div>
            );
          })}
          <button
            className="secondary"
            onClick={resetFilters}
            disabled={Object.keys(filters).length === 0}
            style={{ padding: "8px 14px", fontSize: "12px", height: "38px" }}
          >
            Reset filters
          </button>
        </div>
      )}

      {/* Empty State warning */}
      {matchingRows === 0 && (
        <div className="boundary" style={{ marginTop: "16px" }} role="status">
          <strong>No matching records.</strong>
          <p>
            The active filters returned 0 rows. Reset or change your filter
            selections to view data.
          </p>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div
        className="kpis-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "16px",
          margin: "24px 0",
        }}
      >
        {kpisList.map((kpi) => (
          <div
            key={kpi.id}
            style={{
              background: "#fff",
              border: "1px solid #dde3d8",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                color: "#657363",
                fontWeight: 700,
                textTransform: "uppercase",
              }}
            >
              {kpi.label}
            </span>
            <div
              style={{
                fontSize: "24px",
                fontWeight: 600,
                color: "#214e42",
                margin: "8px 0 4px 0",
              }}
            >
              {typeof kpi.value === "number"
                ? kpi.value.toLocaleString()
                : kpi.value}
            </div>
            {kpi.description && (
              <span
                style={{ fontSize: "11px", color: "#69776b", display: "block" }}
              >
                {kpi.description}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div
        className="charts-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
          margin: "24px 0",
        }}
      >
        {chartsList.map((chart) => {
          const res = chartData[chart.query_id];
          const data = res?.data ?? [];
          return (
            <div
              key={chart.id}
              style={{
                background: "#fff",
                border: "1px solid #dde3d8",
                borderRadius: "8px",
                padding: "18px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                }}
              >
                <h3
                  style={{
                    fontSize: "16px",
                    margin: "0 0 6px 0",
                    color: "#244b3f",
                  }}
                >
                  {chart.title}
                </h3>
                <span className="pill">{chart.chart_type.toUpperCase()}</span>
              </div>
              <p
                style={{
                  fontSize: "12px",
                  color: "#657363",
                  margin: "0 0 14px 0",
                }}
              >
                {chart.summary}
              </p>

              {/* Render SVG Chart */}
              <div
                style={{ height: "180px", width: "100%", marginTop: "auto" }}
              >
                {data.length === 0 ? (
                  <p
                    style={{
                      textAlign: "center",
                      color: "#7a8476",
                      paddingTop: "60px",
                      fontSize: "12px",
                    }}
                  >
                    No data available
                  </p>
                ) : chart.chart_type === "bar" ? (
                  <svg
                    width="100%"
                    height="100%"
                    viewBox="0 0 300 160"
                    preserveAspectRatio="none"
                  >
                    {(() => {
                      const maxVal = Math.max(
                        ...data.map((d) => (d.value as number) || 0),
                        1,
                      );
                      const barWidth = 260 / data.length;
                      return data.map((d, idx) => {
                        const val = (d.value as number) || 0;
                        const h = (val / maxVal) * 120;
                        return (
                          <g key={idx}>
                            <rect
                              x={20 + idx * barWidth + 4}
                              y={130 - h}
                              width={Math.max(barWidth - 8, 4)}
                              height={h}
                              fill="#395a47"
                              rx="2"
                            />
                            <text
                              x={20 + idx * barWidth + barWidth / 2}
                              y={150}
                              fontSize="9"
                              textAnchor="middle"
                              fill="#657363"
                            >
                              {String(d.label).slice(0, 8)}
                            </text>
                          </g>
                        );
                      });
                    })()}
                  </svg>
                ) : chart.chart_type === "histogram" ? (
                  <svg
                    width="100%"
                    height="100%"
                    viewBox="0 0 300 160"
                    preserveAspectRatio="none"
                  >
                    {(() => {
                      const maxVal = Math.max(
                        ...data.map((d) => (d.count as number) || 0),
                        1,
                      );
                      const barWidth = 260 / data.length;
                      return data.map((d, idx) => {
                        const val = (d.count as number) || 0;
                        const h = (val / maxVal) * 120;
                        return (
                          <g key={idx}>
                            <rect
                              x={20 + idx * barWidth + 2}
                              y={130 - h}
                              width={Math.max(barWidth - 4, 4)}
                              height={h}
                              fill="#64856e"
                              rx="1"
                            />
                            <text
                              x={20 + idx * barWidth + barWidth / 2}
                              y={150}
                              fontSize="8"
                              textAnchor="middle"
                              fill="#657363"
                            >
                              {String(d.min ?? "")}
                            </text>
                          </g>
                        );
                      });
                    })()}
                  </svg>
                ) : (
                  <svg
                    width="100%"
                    height="100%"
                    viewBox="0 0 300 160"
                    preserveAspectRatio="none"
                  >
                    {/* Scatter or Line Plot */}
                    {(() => {
                      const xs = data.map((d) =>
                        typeof d.x === "number" ? d.x : idxFromStr(d.x),
                      );
                      const ys = data.map((d) => (d.y as number) || 0);
                      const minX = Math.min(...xs, 0);
                      const maxX = Math.max(...xs, 1);
                      const minY = Math.min(...ys, 0);
                      const maxY = Math.max(...ys, 1);
                      const spanX = maxX - minX || 1;
                      const spanY = maxY - minY || 1;

                      const pts = data.map((_, i) => {
                        const valX = xs[i] ?? 0;
                        const valY = ys[i] ?? 0;
                        const x = 20 + ((valX - minX) / spanX) * 260;
                        const y = 140 - ((valY - minY) / spanY) * 120;
                        return `${x},${y}`;
                      });

                      return (
                        <>
                          <polyline
                            fill="none"
                            stroke="#214e42"
                            strokeWidth="2"
                            points={pts.join(" ")}
                          />
                          {data.map((_, i) => {
                            const [x = "0", y = "0"] = (pts[i] ?? "").split(
                              ",",
                            );
                            return (
                              <circle
                                key={i}
                                cx={x}
                                cy={y}
                                r="3"
                                fill="#214e42"
                              />
                            );
                          })}
                        </>
                      );
                    })()}
                  </svg>
                )}
              </div>
              {res?.sample_indicator && (
                <span
                  style={{
                    fontSize: "10px",
                    color: "#9fa77b",
                    marginTop: "6px",
                  }}
                >
                  * Showing top 500 samples
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Paginated Data Table */}
      <div
        className="card listing"
        style={{ padding: "20px", border: "1px solid #dde3d8" }}
      >
        <div className="section-title">
          <h3>Filtered Data Preview ({matchingRows.toLocaleString()} rows)</h3>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              className="secondary"
              disabled={tablePage === 0}
              onClick={() => setTablePage((p) => Math.max(0, p - 1))}
              style={{ padding: "6px 12px", fontSize: "12px" }}
            >
              ← Prev
            </button>
            <span style={{ fontSize: "12px", color: "#657363" }}>
              Page {tablePage + 1} of{" "}
              {Math.max(1, Math.ceil(matchingRows / 50))}
            </span>
            <button
              className="secondary"
              disabled={(tablePage + 1) * 50 >= matchingRows}
              onClick={() => setTablePage((p) => p + 1)}
              style={{ padding: "6px 12px", fontSize: "12px" }}
            >
              Next →
            </button>
          </div>
        </div>

        <div
          className="preview-scroll"
          tabIndex={0}
          role="region"
          aria-label="Dataset table preview"
        >
          <table>
            <thead>
              <tr>
                {spec.table.columns.map((col) => (
                  <th
                    key={col}
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortBy === col) {
                        setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
                      } else {
                        setSortBy(col);
                        setSortDirection("asc");
                      }
                    }}
                  >
                    {col}{" "}
                    {sortBy === col
                      ? sortDirection === "asc"
                        ? "▲"
                        : "▼"
                      : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {!tableData?.data.length ? (
                <tr>
                  <td
                    colSpan={spec.table.columns.length}
                    style={{ textAlign: "center", padding: "20px" }}
                  >
                    No rows to display.
                  </td>
                </tr>
              ) : (
                tableData.data.map((row, idx) => (
                  <tr key={idx}>
                    {spec.table.columns.map((col) => (
                      <td key={col}>
                        {String((row as Record<string, unknown>)[col] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function idxFromStr(val: unknown): number {
  if (typeof val === "number") return val;
  const s = String(val);
  let hash = 0;
  for (let i = 0; i < s.length; i++)
    hash = (hash << 5) - hash + s.charCodeAt(i);
  return Math.abs(hash) % 100;
}
