import * as React from "react";
import { Button } from "@/components/ui/button";

export interface OrderActionsProps {
  onRecordPayment: () => void;
  onReturnCollect: () => void;
  onCancelInstalment: () => void;
  onBuyback: () => void;
  onMarkDone: () => void;
  onAssignDriver?: () => void;
  onOpenInvoice?: () => void;
}

export function OrderActions({
  onRecordPayment,
  onReturnCollect,
  onCancelInstalment,
  onBuyback,
  onMarkDone,
  onAssignDriver,
  onOpenInvoice,
}: OrderActionsProps) {
  function confirmAndRun(fn: () => void, message: string) {
    if (window.confirm(message)) fn();
  }
  return (
    <div className="flex flex-col gap-2">
      <Button variant="secondary" onClick={onRecordPayment}>Record Payment</Button>
      <Button
        variant="secondary"
        onClick={() => confirmAndRun(onReturnCollect, "Proceed with return/collect?")}
      >
        Return/Collect
      </Button>
      <Button
        variant="secondary"
        onClick={() => confirmAndRun(onCancelInstalment, "Cancel instalment?")}
      >
        Cancel Instalment
      </Button>
      <Button variant="secondary" onClick={onBuyback}>Buyback</Button>
      <Button variant="secondary" onClick={onMarkDone}>Mark Success</Button>
      {onAssignDriver && (
        <Button variant="secondary" onClick={onAssignDriver}>Assign Driver</Button>
      )}
      {onOpenInvoice && (
        <Button variant="secondary" onClick={onOpenInvoice}>Invoice PDF</Button>
      )}
    </div>
  );
}

export default OrderActions;
