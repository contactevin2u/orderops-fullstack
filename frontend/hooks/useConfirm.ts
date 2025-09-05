import { useState, useCallback } from 'react';

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'danger';
}

export interface ConfirmState {
  isOpen: boolean;
  options: ConfirmOptions;
  resolve: (confirmed: boolean) => void;
}

export function useConfirm() {
  const [state, setState] = useState<ConfirmState | null>(null);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({
        isOpen: true,
        options: {
          confirmText: 'Confirm',
          cancelText: 'Cancel',
          variant: 'default',
          ...options,
        },
        resolve,
      });
    });
  }, []);

  const handleClose = useCallback((confirmed: boolean) => {
    if (state) {
      state.resolve(confirmed);
      setState(null);
    }
  }, [state]);

  return {
    confirm,
    confirmState: state,
    handleClose,
  };
}