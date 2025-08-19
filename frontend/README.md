# OrderOps Frontend (MaxFix)

A production-ready Next.js (pages router) UI for your existing OrderOps backend.

## Environment

Set the backend URL:

```bash
# .env.local
NEXT_PUBLIC_API_URL=https://orderops-api-v1.onrender.com
```

## Develop

```bash
npm i
npm run dev
```

## Build

```bash
npm run build && npm start
```

## Notes

- The Parse page sends both `{ text }` and `{ message }` in the body for maximum compatibility.
- Order creation tries `POST /orders` with the parsed JSON; if the backend expects `{ parsed }`, it retries automatically.
- Order detail supports: add/void payment, update fees/discount, mark returned/buyback (via PATCH status if `POST /orders/{id}/void` is unavailable).
- Outstanding report queries `/reports/outstanding?type=INSTALLMENT|RENTAL`.
- Invoice link opens `/documents/invoice/{id}.pdf`.
