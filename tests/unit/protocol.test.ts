import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isReady, RequestGate } from '../../packages/renderer-bridge/protocol';

const valid = {
  version: 1, type: 'query', nonce: 'nonce-a', runId: 'run-a', requestId: 'req-1',
  queryId: 'revenue_by_channel', channel: 'Direct',
};

const validGeneralized = {
  version: 1, type: 'query', nonce: 'nonce-a', runId: 'run-a', requestId: 'req-g1',
  query_id: 'chart_1',
  filters: { category: { operator: 'eq', value: 'Electronics' } },
  cursor: 0,
  page_size: 20,
  sort_by: 'revenue',
  sort_direction: 'desc' as const,
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

test('query gate accepts valid generalized query requests', () => {
  const gate = new RequestGate('nonce-a', 'run-a');
  assert.equal(gate.accept(validGeneralized), true);

  // Rejects invalid generalized query fields
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g2', unknown_field: 123 }), false);
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g3', page_size: 101 }), false);
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g4', page_size: 0 }), false);
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g5', cursor: -1 }), false);
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g6', sort_direction: 'invalid' }), false);
  assert.equal(gate.accept({ ...validGeneralized, requestId: 'req-g7', query_id: 'invalid space id' }), false);
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
  assert.equal(gate.accept(validGeneralized), false);
});
