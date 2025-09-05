// Currency and date formatting utilities

/**
 * Format currency to Malaysian Ringgit
 */
export function formatCurrency(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return 'RM 0.00';
  
  return new Intl.NumberFormat('ms-MY', {
    style: 'currency',
    currency: 'MYR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format date for display
 */
export function formatDate(date: string | Date | null): string {
  if (!date) return '-';
  
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '-';
  
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: '2-digit', 
    year: 'numeric',
  }).format(d);
}

/**
 * Format date for form inputs (YYYY-MM-DD)
 */
export function formatDateForInput(date: string | Date | null): string {
  if (!date) return '';
  
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  
  return d.toISOString().split('T')[0];
}

/**
 * Format relative time (e.g., "2 days ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Parse currency string to number
 */
export function parseCurrency(value: string): number {
  return parseFloat(value.replace(/[^0-9.-]/g, '')) || 0;
}

/**
 * Format phone number for Malaysian numbers
 */
export function formatPhone(phone: string | null): string {
  if (!phone) return '-';
  
  // Remove all non-digits
  const cleaned = phone.replace(/\D/g, '');
  
  // Format Malaysian mobile numbers (01X-XXX XXXX)
  if (cleaned.length === 10 && cleaned.startsWith('01')) {
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 6)} ${cleaned.slice(6)}`;
  }
  
  // Format Malaysian landlines (0X-XXXX XXXX)  
  if (cleaned.length === 9 && cleaned.startsWith('0')) {
    return `${cleaned.slice(0, 2)}-${cleaned.slice(2, 6)} ${cleaned.slice(6)}`;
  }
  
  return phone; // Return original if doesn't match patterns
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return text.slice(0, length) + '...';
}