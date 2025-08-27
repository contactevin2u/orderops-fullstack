const { test, beforeEach } = require('node:test');
const assert = require('node:assert/strict');

const { enqueue, list, replaceAll, backoff, __setStorage } = require('../build/offline/outbox.js');

const memory = (() => {
  let store = {};
  return {
    async getItem(k) {
      return store[k] ?? null;
    },
    async setItem(k, v) {
      store[k] = v;
    },
    async removeItem(k) {
      delete store[k];
    },
  };
})();

__setStorage(memory);

beforeEach(async () => {
  await replaceAll([]);
});

test('enqueue and list', async () => {
  const job = {
    id: '1',
    createdAt: Date.now(),
    attempts: 0,
    kind: 'POST',
    url: '/x',
    bodyType: 'json',
    body: {},
  };
  await enqueue(job);
  const jobs = await list();
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0].id, '1');
});

test('backoff increases and caps', () => {
  const d1 = backoff(0);
  const d2 = backoff(1);
  const d5 = backoff(5);
  assert.ok(d2 > d1);
  assert.ok(d5 <= 120000 + 2000);
});

