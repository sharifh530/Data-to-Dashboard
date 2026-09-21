import React, { useEffect, useRef, useState } from "react";
import { connectRenderer } from "../../packages/renderer-bridge/host";
import { DashboardFallback } from "./DashboardFallback";

interface DashboardViewerProps {
  runId: string;
  csrf: string;
  onClose: () => void;
}

interface DashboardViewResponse {
  run_id: string;
  spec: any;
  bundle_artifact_id?: string | null;
  render_mode: "generated" | "fallback";
  status: string;
}

export function DashboardViewer({
  runId,
  csrf,
  onClose,
}: DashboardViewerProps) {
  const [dashboard, setDashboard] = useState<DashboardViewResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [nonce, setNonce] = useState(() => crypto.randomUUID());
  const [connected, setConnected] = useState(false);
  const [useFallback, setUseFallback] = useState(false);
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let active = true;
    async function fetchDashboard() {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/runs/${runId}/dashboard`, {
          headers: { "X-CSRF-Token": csrf },
        });
        if (!res.ok) {
          throw new Error(`Failed to load dashboard: ${res.status}`);
        }
        const data = await res.json();
        if (active) {
          setDashboard(data);
          if (data.render_mode === "fallback") {
            setUseFallback(true);
          }
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : String(err));
          setUseFallback(true);
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void fetchDashboard();
    return () => {
      active = false;
    };
  }, [runId, csrf]);

  useEffect(() => {
    if (
      !frameRef.current ||
      useFallback ||
      dashboard?.render_mode !== "generated"
    )
      return;

    return connectRenderer({
      frame: frameRef.current,
      nonce,
      runId,
      onConnected: () => setConnected(true),
      query: async (req) => {
        const res = await fetch(`/api/v1/runs/${runId}/queries`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf,
          },
          body: JSON.stringify({
            query_id: req.queryId || (req as any).query_id,
            filters: (req as any).filters || {},
            cursor: (req as any).cursor || 0,
            page_size: (req as any).page_size || (req as any).pageSize || 50,
            sort_by: (req as any).sort_by || (req as any).sortBy || null,
            sort_direction:
              (req as any).sort_direction ||
              (req as any).sortDirection ||
              "asc",
          }),
        });
        if (!res.ok) {
          throw new Error(`Query failed: ${res.status}`);
        }
        return await res.json();
      },
    });
  }, [nonce, runId, csrf, useFallback, dashboard]);

  if (loading) {
    return (
      <div
        className="card"
        style={{ marginTop: "24px", textAlign: "center", padding: "32px" }}
      >
        <p role="status">Loading dashboard specification…</p>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="card error-card" style={{ marginTop: "24px" }}>
        <h3>Failed to load dashboard</h3>
        <p>{error}</p>
        <button onClick={onClose}>Close</button>
      </div>
    );
  }

  return (
    <section className="dashboard-viewer-section" style={{ marginTop: "24px" }}>
      <div
        className="toolbar"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            role="status"
            className="badge"
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              backgroundColor: useFallback
                ? "#fef3c7"
                : connected
                  ? "#dcfce7"
                  : "#e0f2fe",
              color: useFallback
                ? "#b45309"
                : connected
                  ? "#15803d"
                  : "#0369a1",
              fontWeight: 600,
              fontSize: "13px",
            }}
          >
            {useFallback
              ? "Standard Layout (Fallback)"
              : connected
                ? "Isolated Generated React Active"
                : "Connecting Renderer…"}
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          {dashboard?.render_mode === "generated" && (
            <>
              {useFallback ? (
                <button
                  className="secondary"
                  onClick={() => {
                    setUseFallback(false);
                    setConnected(false);
                    setNonce(crypto.randomUUID());
                  }}
                >
                  Use Generated Layout
                </button>
              ) : (
                <>
                  <button
                    className="secondary"
                    onClick={() => {
                      setConnected(false);
                      setNonce(crypto.randomUUID());
                    }}
                  >
                    Reset Renderer
                  </button>
                  <button
                    className="secondary"
                    onClick={() => setUseFallback(true)}
                  >
                    Use Standard Layout
                  </button>
                </>
              )}
            </>
          )}
          <button onClick={onClose}>Close Dashboard</button>
        </div>
      </div>

      {useFallback ? (
        <DashboardFallback runId={runId} csrf={csrf} onClose={onClose} />
      ) : (
        <iframe
          key={nonce}
          ref={frameRef}
          title="Generated Dashboard Sandbox"
          sandbox="allow-scripts"
          referrerPolicy="no-referrer"
          src={`/api/v1/runs/${runId}/dashboard/render#${nonce}`}
          style={{
            width: "100%",
            minHeight: "800px",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            backgroundColor: "#ffffff",
          }}
        />
      )}
    </section>
  );
}
