const test = require('node:test');
const assert = require('node:assert/strict');

process.env.API_BASE = 'https://example.com';
process.env.FIREBASE_PROJECT_ID = 'demo';

const { api, setTokenGetter } = require('../build/lib/api.js');

test('api injects auth and parses json', async () => {
  setTokenGetter(async () => 'token123');
  global.fetch = async (url, opts) => {
    assert.equal(url, 'https://example.com/test');
    assert.equal(opts.headers['Authorization'], 'Bearer token123');
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  };
  const res = await api.get('/test');
  assert.equal(res.ok, true);
  assert.deepEqual(res.data, { ok: true });
});

test('api handles non-json error', async () => {
  setTokenGetter(async () => undefined);
  global.fetch = async () => new Response('nope', { status: 500, headers: { 'content-type': 'text/plain' } });
  const res = await api.get('/err');
  assert.equal(res.ok, false);
  assert.equal(res.error, 'nope');
  assert.equal(res.status, 500);
});

