import { 
  getInventoryConfig, 
  scanUID, 
  getLorryStock, 
  getOrderUIDs, 
  resolveSKU, 
  addSKUAlias 
} from '@/lib/api';

// Mock next/headers for server-side requests
vi.mock('next/headers', () => ({
  cookies: () => ({
    toString: () => 'sid=test_session',
  }),
}));

describe('UID Inventory API functions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('getInventoryConfig', () => {
    it('fetches inventory configuration successfully', async () => {
      const mockConfig = {
        uid_inventory_enabled: true,
        uid_scan_required_after_pod: false,
        inventory_mode: 'optional'
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockConfig),
        headers: { get: () => 'application/json' },
      });

      const result = await getInventoryConfig();
      
      expect(result).toEqual(mockConfig);
      expect(fetch).toHaveBeenCalledWith(
        '/_api/inventory/config',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Accept: 'application/json',
          }),
        })
      );
    });

    it('handles inventory config disabled state', async () => {
      const mockConfig = {
        uid_inventory_enabled: false,
        uid_scan_required_after_pod: false,
        inventory_mode: 'off'
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockConfig),
        headers: { get: () => 'application/json' },
      });

      const result = await getInventoryConfig();
      
      expect(result.uid_inventory_enabled).toBe(false);
      expect(result.inventory_mode).toBe('off');
    });
  });

  describe('scanUID', () => {
    it('successfully scans a UID for an order', async () => {
      const mockResponse = {
        success: true,
        message: 'UID scanned successfully',
        uid: 'TEST123456789',
        action: 'ISSUE',
        sku_name: 'Test Product',
        order_item_id: 1
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockResponse),
        headers: { get: () => 'application/json' },
      });

      const scanData = {
        order_id: 123,
        action: 'ISSUE' as const,
        uid: 'TEST123456789',
        sku_id: 1,
        notes: 'Test scan'
      };

      const result = await scanUID(scanData);
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        '/_api/inventory/uid/scan',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify(scanData),
        })
      );
    });

    it('handles UID scanning errors', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        text: async () => JSON.stringify({ detail: 'UID already exists' }),
        headers: { get: () => 'application/json' },
        statusText: 'Bad Request',
      });

      const scanData = {
        order_id: 123,
        action: 'ISSUE' as const,
        uid: 'DUPLICATE123',
        sku_id: 1
      };

      await expect(scanUID(scanData)).rejects.toThrow('UID already exists');
    });
  });

  describe('getLorryStock', () => {
    it('fetches lorry stock data for a driver', async () => {
      const mockStockData = {
        date: '2024-01-15',
        driver_id: 1,
        items: [
          {
            sku_id: 1,
            sku_name: 'Test Item 1',
            expected_count: 10,
            scanned_count: 8,
            variance: -2
          },
          {
            sku_id: 2,
            sku_name: 'Test Item 2', 
            expected_count: 5,
            scanned_count: 5,
            variance: 0
          }
        ],
        total_expected: 15,
        total_scanned: 13,
        total_variance: -2
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockStockData),
        headers: { get: () => 'application/json' },
      });

      const result = await getLorryStock(1, '2024-01-15');
      
      expect(result).toEqual(mockStockData);
      expect(fetch).toHaveBeenCalledWith(
        '/_api/drivers/1/lorry-stock/2024-01-15',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('handles empty stock data', async () => {
      const mockEmptyStock = {
        date: '2024-01-15',
        driver_id: 1,
        items: [],
        total_expected: 0,
        total_scanned: 0,
        total_variance: 0
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockEmptyStock),
        headers: { get: () => 'application/json' },
      });

      const result = await getLorryStock(1, '2024-01-15');
      
      expect(result.items).toHaveLength(0);
      expect(result.total_expected).toBe(0);
    });
  });

  describe('getOrderUIDs', () => {
    it('fetches UIDs for a specific order', async () => {
      const mockOrderUIDs = {
        order_id: 123,
        uids: [
          {
            id: 1,
            uid: 'UID001',
            action: 'ISSUE',
            sku_id: 1,
            sku_name: 'Test Product',
            scanned_at: '2024-01-15T10:00:00Z',
            driver_name: 'Test Driver',
            notes: 'Initial issue'
          },
          {
            id: 2,
            uid: 'UID002',
            action: 'RETURN',
            sku_id: 1,
            sku_name: 'Test Product',
            scanned_at: '2024-01-15T15:00:00Z',
            driver_name: 'Test Driver',
            notes: 'Customer return'
          }
        ],
        total_issued: 1,
        total_returned: 1
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockOrderUIDs),
        headers: { get: () => 'application/json' },
      });

      const result = await getOrderUIDs(123);
      
      expect(result).toEqual(mockOrderUIDs);
      expect(result.uids).toHaveLength(2);
      expect(result.total_issued).toBe(1);
      expect(result.total_returned).toBe(1);
    });

    it('handles orders with no UIDs', async () => {
      const mockEmptyUIDs = {
        order_id: 123,
        uids: [],
        total_issued: 0,
        total_returned: 0
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockEmptyUIDs),
        headers: { get: () => 'application/json' },
      });

      const result = await getOrderUIDs(123);
      
      expect(result.uids).toHaveLength(0);
      expect(result.total_issued).toBe(0);
      expect(result.total_returned).toBe(0);
    });
  });

  describe('resolveSKU', () => {
    it('finds exact SKU matches', async () => {
      const mockSKUMatches = {
        matches: [
          {
            sku_id: 1,
            sku_name: 'MacBook Pro 13-inch',
            confidence: 1.0,
            match_type: 'exact'
          }
        ],
        suggestions: []
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockSKUMatches),
        headers: { get: () => 'application/json' },
      });

      const result = await resolveSKU('MacBook Pro 13-inch');
      
      expect(result).toEqual(mockSKUMatches);
      expect(result.matches[0].match_type).toBe('exact');
      expect(result.matches[0].confidence).toBe(1.0);
    });

    it('finds fuzzy SKU matches with custom threshold', async () => {
      const mockFuzzyMatches = {
        matches: [
          {
            sku_id: 1,
            sku_name: 'MacBook Pro 13-inch M2',
            confidence: 0.85,
            match_type: 'fuzzy'
          }
        ],
        suggestions: ['MacBook Pro 13-inch M2', 'MacBook Pro 14-inch M2']
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockFuzzyMatches),
        headers: { get: () => 'application/json' },
      });

      const result = await resolveSKU('MacBook Pro 13', 0.8);
      
      expect(result.matches[0].match_type).toBe('fuzzy');
      expect(result.matches[0].confidence).toBeGreaterThan(0.8);
      expect(result.suggestions.length).toBeGreaterThan(0);
    });

    it('returns empty matches for unmatched queries', async () => {
      const mockNoMatches = {
        matches: [],
        suggestions: ['Try: iPhone', 'Try: MacBook', 'Try: iPad']
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockNoMatches),
        headers: { get: () => 'application/json' },
      });

      const result = await resolveSKU('Nonexistent Product');
      
      expect(result.matches).toHaveLength(0);
      expect(result.suggestions.length).toBeGreaterThan(0);
    });
  });

  describe('addSKUAlias', () => {
    it('successfully adds an alias to a SKU', async () => {
      const mockResponse = {
        success: true,
        message: 'Alias added successfully',
        alias_id: 1
      };

      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockResponse),
        headers: { get: () => 'application/json' },
      });

      const result = await addSKUAlias(1, 'New Alias');
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        '/_api/inventory/sku/alias',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            sku_id: 1,
            alias: 'New Alias'
          }),
        })
      );
    });

    it('handles duplicate alias errors', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        text: async () => JSON.stringify({ detail: 'Alias already exists' }),
        headers: { get: () => 'application/json' },
        statusText: 'Bad Request',
      });

      await expect(addSKUAlias(1, 'Duplicate Alias')).rejects.toThrow('Alias already exists');
    });
  });

  describe('Error handling', () => {
    it('handles network errors gracefully', async () => {
      (global as any).fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(getInventoryConfig()).rejects.toThrow('Unable to connect to server');
    });

    it('handles 404 errors with specific messages', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        text: async () => 'Not Found',
        headers: { get: () => null },
        statusText: 'Not Found',
      });

      await expect(getOrderUIDs(999)).rejects.toThrow('Order not found');
    });

    it('handles 403 permission errors', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        text: async () => 'Forbidden',
        headers: { get: () => null },
        statusText: 'Forbidden',
      });

      await expect(scanUID({
        order_id: 123,
        action: 'ISSUE',
        uid: 'TEST123'
      })).rejects.toThrow("You don't have permission");
    });

    it('handles server errors with retry suggestions', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
        headers: { get: () => null },
        statusText: 'Internal Server Error',
      });

      await expect(getLorryStock(1, '2024-01-15')).rejects.toThrow('server encountered an error');
    });
  });

  describe('Request format validation', () => {
    it('includes proper headers for POST requests', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify({ success: true }),
        headers: { get: () => 'application/json' },
      });

      await scanUID({
        order_id: 123,
        action: 'ISSUE',
        uid: 'TEST123'
      });

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          }),
        })
      );
    });

    it('includes credentials in requests', async () => {
      (global as any).fetch = vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify({}),
        headers: { get: () => 'application/json' },
      });

      await getInventoryConfig();

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });
  });
});