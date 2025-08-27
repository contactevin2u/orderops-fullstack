# Push Notification Debugging

Send a test push notification using the backend debug endpoint. The backend will use the
Android channel `orders` by default (overridable via `PUSH_ANDROID_CHANNEL_ID`).

```bash
curl -X POST http://localhost:8000/debug/push \
  -H 'Content-Type: application/json' \
  -d '{"token":"<FCM_TOKEN>","title":"Test","body":"Hello","data":{}}'
```
```

