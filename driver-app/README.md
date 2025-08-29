# Driver Android App

This module contains the native Kotlin implementation of the OrderOps driver app.

## Building
Install [Gradle](https://gradle.org/install/) 8.9+ and a JDK 17+.

```bash
gradle :app:assembleDebug
```

To create a Gradle wrapper later (not included in repo):

```bash
gradle wrapper --gradle-version 8.9
```

Place `google-services.json` in the project root when running locally. Icons are XML vectors; no bitmap assets are committed.
