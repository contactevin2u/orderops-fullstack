# Driver App

This directory contains the React Native driver application built with Expo.

## Building APKs

The repository includes GitHub Actions workflows that build Android packages
and upload them as artifacts:

- **driver-android-debug** – produces a debug APK for testing.
- **driver-android-release** – produces a release-signed APK suitable for
  distribution outside of Google Play. The workflow expects a
  `GOOGLE_SERVICES_JSON` secret containing your Firebase configuration.

Run either workflow from the Actions tab in GitHub and download the generated
APK from the workflow artifacts section.

