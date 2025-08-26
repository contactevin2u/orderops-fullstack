import { describe, it, expect, vi } from 'vitest';
import { request } from '@/utils/api';

describe('api request', () => {
  it('uses provided method even with json body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => '',
      headers: { get: () => 'application/json' },
    });
    (global as any).fetch = mockFetch;

    await request('/test', { method: 'DELETE', json: { foo: 'bar' } });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({
        method: 'DELETE',
        body: JSON.stringify({ foo: 'bar' }),
      })
    );
  });
});
