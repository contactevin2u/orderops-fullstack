// utils/orderBadges.ts
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import tz from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(tz);

export function getOrderBadges(
  order: { deliveryDate: string | null },
  selectedDateISO: string,
): string[] {
  const badges: string[] = [];
  if (!order.deliveryDate) {
    badges.push('No date');
    return badges;
  }

  const dLocal = dayjs(order.deliveryDate).tz('Asia/Kuala_Lumpur').endOf('day');
  const selected = dayjs(selectedDateISO).tz('Asia/Kuala_Lumpur').endOf('day');
  const overdueDays = selected.diff(dLocal, 'day');
  if (overdueDays > 0) {
    badges.push(`Overdue ${overdueDays} day${overdueDays > 1 ? 's' : ''}`);
  }
  return badges;
}

