# Private Distribution for Driver App

## iOS – Apple Business Manager
1. Create the app in App Store Connect with bundle ID `com.yourco.driver`.
2. Under **Pricing and Availability**, choose **Private (Custom App)**.
3. Add the Apple Business Manager Organization IDs allowed to install.
4. Use `eas build --platform ios --profile production --auto-submit`.
5. In Apple Business Manager, the app appears under **Custom Apps** for the listed orgs.

## Android – Managed Google Play
1. Create a private app in Google Play Console using the `.aab` from `eas build --platform android --profile production`.
2. In **Advanced Settings → Managed Google Play**, list allowed Organization IDs.
3. Submit with `eas submit --platform android --profile production` once service account is configured.
4. Organizations see the app in their private Managed Play store within minutes.

_Placeholder for screenshots_
