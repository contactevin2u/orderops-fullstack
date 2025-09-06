import React from 'react';
import { getOrderUIDs, getInventoryConfig } from '@/lib/api';

interface UIDStatusProps {
  orderId: number;
  orderStatus?: string;
  compact?: boolean;
}

interface UIDData {
  total_issued: number;
  total_returned: number;
  uids: Array<{
    id: number;
    action: 'ISSUE' | 'RETURN';
  }>;
}

export default function UIDStatus({ orderId, orderStatus, compact = false }: UIDStatusProps) {
  const [inventoryEnabled, setInventoryEnabled] = React.useState<boolean | null>(null);
  const [uidData, setUIDData] = React.useState<UIDData | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    const loadData = async () => {
      try {
        // First check if inventory is enabled
        const config = await getInventoryConfig();
        setInventoryEnabled(config.uid_inventory_enabled);
        
        if (!config.uid_inventory_enabled) return;

        // Only load UID data for delivered orders or orders with POD
        if (orderStatus === 'DELIVERED' || orderStatus === 'SUCCESS') {
          setLoading(true);
          try {
            const data = await getOrderUIDs(orderId);
            setUIDData(data);
          } catch (e) {
            // Silently fail - UID data might not exist yet
            setUIDData({ total_issued: 0, total_returned: 0, uids: [] });
          } finally {
            setLoading(false);
          }
        }
      } catch (e) {
        // Config loading failed, assume disabled
        setInventoryEnabled(false);
      }
    };

    loadData();
  }, [orderId, orderStatus]);

  // Don't render if inventory is disabled
  if (inventoryEnabled === false) return null;
  
  // Show loading state only briefly
  if (loading || inventoryEnabled === null) {
    return compact ? (
      <span className="text-xs text-gray-400">...</span>
    ) : (
      <div className="text-sm text-gray-400">Loading...</div>
    );
  }

  // Don't show for orders that haven't been delivered yet
  if (orderStatus !== 'DELIVERED' && orderStatus !== 'SUCCESS' && !uidData) {
    return compact ? null : (
      <div className="text-xs text-gray-400">Pending delivery</div>
    );
  }

  if (!uidData) return null;

  const totalUIDs = uidData.total_issued + uidData.total_returned;
  const hasUIDs = totalUIDs > 0;

  if (compact) {
    // Compact version for table cells
    if (!hasUIDs) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-600">
          No UIDs
        </span>
      );
    }

    return (
      <div className="flex flex-wrap gap-1">
        {uidData.total_issued > 0 && (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-green-100 text-green-700">
            ↗ {uidData.total_issued}
          </span>
        )}
        {uidData.total_returned > 0 && (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-orange-100 text-orange-700">
            ↘ {uidData.total_returned}
          </span>
        )}
      </div>
    );
  }

  // Full version for detail views
  return (
    <div className="space-y-1">
      <div className="text-sm font-medium">UID Tracking</div>
      {hasUIDs ? (
        <div className="flex gap-3 text-sm">
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 bg-green-500 rounded-full"></span>
            <span>Issued: {uidData.total_issued}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 bg-orange-500 rounded-full"></span>
            <span>Returned: {uidData.total_returned}</span>
          </div>
        </div>
      ) : (
        <div className="text-sm text-gray-500">No UIDs tracked</div>
      )}
    </div>
  );
}