import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isReady, RequestGate } from '../../packages/renderer-bridge/protocol';

const valid = {
  version: 1, type: 'query', nonce: 'nonce-a', runId: 'run-a', requestId: 'req-1',
  queryId: 'revenue_by_channel', channel: 'Direct',
};

test('only exact, instance-bound ready messages pass', () => {
  assert.equal(isReady({ version: 1, type: 'ready', nonce: 'a' }, 'a'), true);
  for (const value of [null, [], { version: 1, type: 'ready', nonce: 'b' },
    { version: 1, type: 'ready', nonce: 'a', secret: 'extra' }]) {
    assert.equal(isReady(value, 'a'), false);
  }
});

test('query gate rejects spoofing, unknown fields/queries, and invalid values', () => {
  for (const patch of [
    { nonce: 'wrong' }, { runId: 'other-user-run' }, { queryId: 'execute_sql' },
    { sql: 'select *' }, { channel: 'secret' }, { requestId: 'x'.repeat(65) },
    { requestId: {} }, { version: 2 }, { channel: ['Direct'] },
  ]) {
    assert.equal(new RequestGate('nonce-a', 'run-a').accept({ ...valid, ...patch }), false);
  }
});

test('query gate prevents replay and has a bounded request allowance', () => {
  const gate = new RequestGate('nonce-a', 'run-a', 2);
  assert.equal(gate.accept(valid), true);
  assert.equal(gate.accept(valid), false);
  assert.equal(gate.accept({ ...valid, requestId: 'req-2' }), true);
  assert.equal(gate.accept({ ...valid, requestId: 'req-3' }), false);
});

test('disposed instances reject previously valid requests', () => {
  const gate = new RequestGate('nonce-a', 'run-a');
  gate.dispose();
  assert.equal(gate.accept(valid), false);
});
