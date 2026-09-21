/**
 * Offline UI compiler for generated React dashboard components.
 * Bundles the component with React runtime and the bridge communicator
 * into an IIFE standalone bundle, enforcing offline isolation and script caps.
 */
import { build } from "esbuild";
import { createHash } from "node:crypto";
import { stdin, stdout } from "node:process";

const MAX_BUNDLE_BYTES = 500 * 1024; // 500 KiB limit

async function readAllStdin() {
  const chunks = [];
  for await (const chunk of stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

function hashScript(content) {
  return `'sha256-${createHash("sha256").update(content).digest("base64")}'`;
}

async function main() {
  try {
    const rawInput = await readAllStdin();
    if (!rawInput.trim()) {
      stdout.write(
        JSON.stringify({ status: "error", error: "Empty compilation input" }),
      );
      return;
    }

    const payload = JSON.parse(rawInput);
    const { source, run_id } = payload;
    if (!source || !run_id) {
      stdout.write(
        JSON.stringify({ status: "error", error: "Missing source or run_id" }),
      );
      return;
    }

    // Wrap the component into the runtime harness that connects to the iframe bridge
    const entrypoint = `
import React, { useState, useEffect, useCallback } from 'react';
import { createRoot } from 'react-dom/client';

${source}

function App() {
  const [port, setPort] = useState(null);
  const [nonce, setNonce] = useState(() => location.hash.slice(1));
  const callbacks = React.useRef(new Map());

  useEffect(() => {
    const n = location.hash.slice(1);
    setNonce(n);

    function onInit(event) {
      if (event.source !== window.parent) return;
      const data = event.data;
      if (!data || data.type !== 'init' || data.version !== 1 || data.nonce !== n || data.runId !== '${run_id}') return;
      if (!event.ports || event.ports.length === 0) return;

      const p = event.ports[0];
      p.onmessage = (msg) => {
        const res = msg.data;
        if (!res || res.type !== 'result' || typeof res.requestId !== 'string') return;
        const cb = callbacks.current.get(res.requestId);
        if (cb) {
          cb(res.data);
          callbacks.current.delete(res.requestId);
        }
      };
      p.start();
      setPort(p);
    }

    window.addEventListener('message', onInit);
    // Notify parent that iframe is ready to receive port
    window.parent.postMessage({ version: 1, type: 'ready', nonce: n }, '*');

    return () => {
      window.removeEventListener('message', onInit);
    };
  }, []);

  const queryBridge = useCallback((req) => {
    return new Promise((resolve, reject) => {
      if (!port) {
        reject(new Error('Bridge port not connected'));
        return;
      }
      const requestId = crypto.randomUUID();
      const timeout = setTimeout(() => {
        callbacks.current.delete(requestId);
        reject(new Error('Query timed out'));
      }, 15000);

      callbacks.current.set(requestId, (data) => {
        clearTimeout(timeout);
        resolve(data);
      });

      port.postMessage({
        version: 1,
        type: 'query',
        nonce,
        runId: '${run_id}',
        requestId,
        ...req,
      });
    });
  }, [port, nonce]);

  if (!port) {
    return (
      <div className="renderer-loading" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
        <p>Connecting to secure data channel…</p>
      </div>
    );
  }

  return <Dashboard query={queryBridge} />;
}

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(<App />);
}
`;

    const buildResult = await build({
      stdin: {
        contents: entrypoint,
        resolveDir: process.cwd(),
        loader: "tsx",
      },
      bundle: true,
      minify: true,
      format: "iife",
      platform: "browser",
      target: "es2022",
      define: {
        "process.env.NODE_ENV": '"production"',
      },
      legalComments: "none",
      write: false,
    });

    if (!buildResult.outputFiles || buildResult.outputFiles.length === 0) {
      stdout.write(
        JSON.stringify({
          status: "error",
          error: "Compiler produced no output",
        }),
      );
      return;
    }

    const bundleText = buildResult.outputFiles[0].text;

    // Safety checks on bundle
    if (/<\/script/i.test(bundleText)) {
      stdout.write(
        JSON.stringify({
          status: "error",
          error: "Unsafe inline asset terminator in compiled bundle",
        }),
      );
      return;
    }

    const bundleBytes = Buffer.byteLength(bundleText, "utf8");
    if (bundleBytes > MAX_BUNDLE_BYTES) {
      stdout.write(
        JSON.stringify({
          status: "error",
          error: `Bundle size ${bundleBytes} exceeded ${MAX_BUNDLE_BYTES} limit`,
        }),
      );
      return;
    }

    const sha256 = hashScript(bundleText);
    stdout.write(
      JSON.stringify({
        status: "ready",
        bundle: bundleText,
        sha256,
        size_bytes: bundleBytes,
      }),
    );
  } catch (err) {
    stdout.write(
      JSON.stringify({
        status: "error",
        error: err instanceof Error ? err.message : String(err),
      }),
    );
  }
}

void main();
