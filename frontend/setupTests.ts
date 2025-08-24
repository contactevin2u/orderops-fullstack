import '@testing-library/jest-dom';
import { vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: any, opts?: any) => (opts && typeof opts.count === 'number' ? String(opts.count) : k) }),
}));
