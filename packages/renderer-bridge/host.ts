import { isReady, RequestGate, type QueryRequest } from './protocol';

/** Only a proof-of-concept bridge. Real data must be independently authorized by the API. */
export function connectRenderer(options: {
  frame: HTMLIFrameElement;
  nonce: string;
  runId: string;
  query: (request: QueryRequest) => unknown;
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
    channel.port1.onmessage = (message: MessageEvent<unknown>) => {
      if (!gate.accept(message.data)) return;
      channel?.port1.postMessage({
        version: 1, type: 'result', nonce, runId,
        requestId: message.data.requestId, data: query(message.data),
      });
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
