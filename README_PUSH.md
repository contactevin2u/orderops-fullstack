# Push Notification Smoke Tests

## Env

Ensure on Render:

FIREBASE_SERVICE_ACCOUNT_JSON = full JSON

DATABASE_URL set

PUSH_ANDROID_CHANNEL_ID=orders (or whatever matches app)

Optional local .env example:

PUSH_ANDROID_CHANNEL_ID=orders

## Audit routes check

```bash
curl -s https://<API_BASE>/_audit/routes | jq
```

## FCM health

```bash
curl -s https://<API_BASE>/_audit/fcm | jq
# expect: {"ok":true,"project_id":"...","access_token_len":...}
```

## Get device token from the app

Open the driver app (RN), ensure it creates channel "orders" and logs/shows FCM token.

## DB & token presence

```bash
curl -s "https://<API_BASE>/_audit/db?driver_id=<DRIVER_ID>" | jq
# expect: tokens array with recent entries
```
