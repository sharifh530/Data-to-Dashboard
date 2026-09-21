import { isReady, RequestGate, type QueryRequest } from './protocol';

/** Opaque-origin sandboxed renderer bridge. */
export function connectRenderer(options: {
  frame: HTMLIFrameElement;
  nonce: string;
  runId: string;
  query: (request: QueryRequest) => Promise<unknown> | unknown;
  onConnected: () => void;
}): () => void {
  const { frame, nonce, runId, query, onConnected } = options;
  const gate = new RequestGate(nonce, runId);
  let channel: MessageChannel | undefined;
  let disposed = false;

  function ready(event: MessageEvent<unknown>) {
    if (disposed || channel || event.source !== frame.contentWindow || event.origin !== 'null') return;
    if (!isReady(event.data, nonce)) return;
    channel = new MessageChannel();
    channel.port1.onmessage = async (message: MessageEvent<unknown>) => {
      if (!gate.accept(message.data)) return;
      const req = message.data;
      try {
        const result = await Promise.resolve(query(req));
        if (disposed) return;
        channel?.port1.postMessage({
          version: 1,
          type: 'result',
          nonce,
          runId,
          requestId: req.requestId,
          data: result,
        });
      } catch (err) {
        if (disposed) return;
        channel?.port1.postMessage({
          version: 1,
          type: 'error',
          nonce,
          runId,
          requestId: req.requestId,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    };
    channel.port1.start();
    // Opaque-origin recipients require '*'; the exact window, nonce and port bind this instance.
    frame.contentWindow?.postMessage({ version: 1, type: 'init', nonce, runId }, '*', [channel.port2]);
    onConnected();
  }

  window.addEventListener('message', ready);
  return () => {
    disposed = true;
    gate.dispose();
    window.removeEventListener('message', ready);
    if (channel) {
      channel.port1.onmessage = null;
      channel.port1.close();
      channel.port2.close();
    }
  };
}
