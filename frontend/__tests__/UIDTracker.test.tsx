import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UIDTracker from '@/components/UIDTracker';
import * as api from '@/lib/api';

// Mock the API functions
vi.mock('@/lib/api', () => ({
  getInventoryConfig: vi.fn(),
  getOrderUIDs: vi.fn(), 
  scanUID: vi.fn(),
}));

const mockApi = api as any;

describe('UIDTracker Component', () => {
  const mockOrderId = 123;
  const mockOrderStatus = 'DELIVERED';

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock for inventory config
    mockApi.getInventoryConfig.mockResolvedValue({
      uid_inventory_enabled: true,
      uid_scan_required_after_pod: false,
      inventory_mode: 'optional'
    });

    // Default mock for order UIDs
    mockApi.getOrderUIDs.mockResolvedValue({
      order_id: mockOrderId,
      uids: [],
      total_issued: 0,
      total_returned: 0
    });
  });

  describe('Feature flag integration', () => {
    it('does not render when inventory system is disabled', async () => {
      mockApi.getInventoryConfig.mockResolvedValue({
        uid_inventory_enabled: false,
        uid_scan_required_after_pod: false,
        inventory_mode: 'off'
      });

      const { container } = render(
        <UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />
      );

      await waitFor(() => {
        expect(container.firstChild).toBeNull();
      });
    });

    it('renders when inventory system is enabled', async () => {
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('UID Tracking')).toBeInTheDocument();
      });
    });

    it('shows correct mode badge for required mode', async () => {
      mockApi.getInventoryConfig.mockResolvedValue({
        uid_inventory_enabled: true,
        uid_scan_required_after_pod: true,
        inventory_mode: 'required'
      });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Required')).toBeInTheDocument();
      });
    });

    it('shows correct mode badge for optional mode', async () => {
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Optional')).toBeInTheDocument();
      });
    });
  });

  describe('UID display', () => {
    it('shows empty state when no UIDs are present', async () => {
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('No UIDs tracked')).toBeInTheDocument();
        expect(screen.getByText(/No UIDs have been scanned for this order yet/)).toBeInTheDocument();
      });
    });

    it('displays existing UIDs correctly', async () => {
      const mockUIDs = [
        {
          id: 1,
          uid: 'TEST123456',
          action: 'ISSUE',
          sku_id: 1,
          sku_name: 'Test Product',
          scanned_at: '2024-01-15T10:00:00Z',
          driver_name: 'Test Driver',
          notes: 'Test notes'
        },
        {
          id: 2,
          uid: 'TEST789012',
          action: 'RETURN',
          sku_id: 2,
          sku_name: 'Another Product',
          scanned_at: '2024-01-15T15:00:00Z',
          driver_name: 'Another Driver',
          notes: null
        }
      ];

      mockApi.getOrderUIDs.mockResolvedValue({
        order_id: mockOrderId,
        uids: mockUIDs,
        total_issued: 1,
        total_returned: 1
      });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Total: 2 UIDs •')).toBeInTheDocument();
        expect(screen.getByText('Issued: 1 •')).toBeInTheDocument();
        expect(screen.getByText('Returned: 1')).toBeInTheDocument();
        
        expect(screen.getByText('TEST123456')).toBeInTheDocument();
        expect(screen.getByText('TEST789012')).toBeInTheDocument();
        expect(screen.getByText('Test Product')).toBeInTheDocument();
        expect(screen.getByText('Another Product')).toBeInTheDocument();
        expect(screen.getByText('Test Driver')).toBeInTheDocument();
        expect(screen.getByText('Test notes')).toBeInTheDocument();
      });
    });

    it('formats dates correctly', async () => {
      const mockUIDs = [
        {
          id: 1,
          uid: 'DATE_TEST',
          action: 'ISSUE',
          scanned_at: '2024-01-15T10:30:45Z',
          driver_name: 'Test Driver'
        }
      ];

      mockApi.getOrderUIDs.mockResolvedValue({
        order_id: mockOrderId,
        uids: mockUIDs,
        total_issued: 1,
        total_returned: 0
      });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        // Check that date is formatted (exact format may vary by locale)
        expect(screen.getByText(/1\/15\/2024|15\/1\/2024|2024-01-15/)).toBeInTheDocument();
        expect(screen.getByText(/10:30|10:30:45/)).toBeInTheDocument();
      });
    });

    it('shows correct action badges', async () => {
      const mockUIDs = [
        {
          id: 1,
          uid: 'ISSUED_UID',
          action: 'ISSUE',
          scanned_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 2,
          uid: 'RETURNED_UID',
          action: 'RETURN',
          scanned_at: '2024-01-15T15:00:00Z'
        }
      ];

      mockApi.getOrderUIDs.mockResolvedValue({
        order_id: mockOrderId,
        uids: mockUIDs,
        total_issued: 1,
        total_returned: 1
      });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Issued')).toBeInTheDocument();
        expect(screen.getByText('Returned')).toBeInTheDocument();
      });
    });
  });

  describe('Adding UIDs', () => {
    it('shows add form when Add UID button is clicked', async () => {
      const user = userEvent.setup();
      
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));

      expect(screen.getByLabelText('UID')).toBeInTheDocument();
      expect(screen.getByLabelText('Action')).toBeInTheDocument();
      expect(screen.getByLabelText('Notes (Optional)')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Add UID' })).toBeInTheDocument();
    });

    it('successfully adds a new UID', async () => {
      const user = userEvent.setup();
      
      mockApi.scanUID.mockResolvedValue({
        success: true,
        message: 'UID added successfully',
        uid: 'NEW123456',
        action: 'ISSUE'
      });

      // Mock the reload call
      mockApi.getOrderUIDs.mockResolvedValueOnce({
        order_id: mockOrderId,
        uids: [],
        total_issued: 0,
        total_returned: 0
      }).mockResolvedValueOnce({
        order_id: mockOrderId,
        uids: [{
          id: 1,
          uid: 'NEW123456',
          action: 'ISSUE',
          scanned_at: '2024-01-15T10:00:00Z'
        }],
        total_issued: 1,
        total_returned: 0
      });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      // Open form
      await user.click(screen.getByText('Add UID'));

      // Fill form
      await user.type(screen.getByLabelText('UID'), 'NEW123456');
      await user.type(screen.getByLabelText('Notes (Optional)'), 'Test notes');

      // Submit
      await user.click(screen.getByRole('button', { name: 'Add UID' }));

      expect(mockApi.scanUID).toHaveBeenCalledWith({
        order_id: mockOrderId,
        action: 'ISSUE',
        uid: 'NEW123456',
        notes: 'Test notes'
      });

      // Should reload UIDs after adding
      await waitFor(() => {
        expect(mockApi.getOrderUIDs).toHaveBeenCalledTimes(2);
      });
    });

    it('handles UID scanning errors', async () => {
      const user = userEvent.setup();
      
      mockApi.scanUID.mockRejectedValue(new Error('UID already exists'));

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));
      await user.type(screen.getByLabelText('UID'), 'DUPLICATE123');
      await user.click(screen.getByRole('button', { name: 'Add UID' }));

      await waitFor(() => {
        expect(screen.getByText('UID already exists')).toBeInTheDocument();
      });
    });

    it('validates UID input before submission', async () => {
      const user = userEvent.setup();
      
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));

      const submitButton = screen.getByRole('button', { name: 'Add UID' });
      expect(submitButton).toBeDisabled();

      await user.type(screen.getByLabelText('UID'), 'VALID123');
      expect(submitButton).not.toBeDisabled();
    });

    it('allows selecting different actions', async () => {
      const user = userEvent.setup();
      
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));

      const actionSelect = screen.getByLabelText('Action');
      expect(actionSelect).toHaveValue('ISSUE');

      await user.selectOptions(actionSelect, 'RETURN');
      expect(actionSelect).toHaveValue('RETURN');
    });

    it('cancels form and resets state', async () => {
      const user = userEvent.setup();
      
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));
      await user.type(screen.getByLabelText('UID'), 'CANCEL_TEST');

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(screen.queryByLabelText('UID')).not.toBeInTheDocument();
      
      // Open again to check reset
      await user.click(screen.getByText('Add UID'));
      expect(screen.getByLabelText('UID')).toHaveValue('');
    });
  });

  describe('Loading states', () => {
    it('shows loading state initially', () => {
      mockApi.getInventoryConfig.mockImplementation(() => new Promise(() => {}));
      
      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);
      
      // Component should not render anything while loading config
      expect(screen.queryByText('UID Tracking')).not.toBeInTheDocument();
    });

    it('shows loading state during UID submission', async () => {
      const user = userEvent.setup();
      
      // Mock a delayed response
      mockApi.scanUID.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          success: true,
          message: 'Success',
          uid: 'TEST123',
          action: 'ISSUE'
        }), 100))
      );

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Add UID'));
      await user.type(screen.getByLabelText('UID'), 'TEST123');
      
      const submitButton = screen.getByRole('button', { name: 'Add UID' });
      await user.click(submitButton);

      expect(screen.getByRole('button', { name: 'Adding...' })).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Error handling', () => {
    it('handles config loading errors gracefully', async () => {
      mockApi.getInventoryConfig.mockRejectedValue(new Error('Config load failed'));

      const { container } = render(
        <UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />
      );

      await waitFor(() => {
        // Should not render when config fails to load
        expect(container.firstChild).toBeNull();
      });
    });

    it('displays UID loading errors', async () => {
      mockApi.getOrderUIDs.mockRejectedValue(new Error('Failed to load UIDs'));

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load UID data')).toBeInTheDocument();
      });
    });

    it('clears errors after successful operations', async () => {
      const user = userEvent.setup();
      
      // First call fails, second succeeds
      mockApi.scanUID
        .mockRejectedValueOnce(new Error('First attempt failed'))
        .mockResolvedValueOnce({
          success: true,
          message: 'Success',
          uid: 'SUCCESS123',
          action: 'ISSUE'
        });

      render(<UIDTracker orderId={mockOrderId} orderStatus={mockOrderStatus} />);

      await waitFor(() => {
        expect(screen.getByText('Add UID')).toBeInTheDocument();
      });

      // First attempt
      await user.click(screen.getByText('Add UID'));
      await user.type(screen.getByLabelText('UID'), 'FAIL123');
      await user.click(screen.getByRole('button', { name: 'Add UID' }));

      await waitFor(() => {
        expect(screen.getByText('First attempt failed')).toBeInTheDocument();
      });

      // Second attempt
      await user.clear(screen.getByLabelText('UID'));
      await user.type(screen.getByLabelText('UID'), 'SUCCESS123');
      await user.click(screen.getByRole('button', { name: 'Add UID' }));

      await waitFor(() => {
        expect(screen.queryByText('First attempt failed')).not.toBeInTheDocument();
      });
    });
  });
});