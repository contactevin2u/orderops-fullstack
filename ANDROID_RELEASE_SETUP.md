# Android Release Setup Guide

## Prerequisites Setup

### 1. Generate Gradle Wrapper (one-time setup)
```bash
cd driver-app
# This will create the wrapper files
gradle wrapper --gradle-version 8.9
# Make gradlew executable
chmod +x gradlew
```

### 2. Create Release Keystore (one-time setup)
```bash
keytool -genkeypair -v -keystore keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias your-key-alias
```
Save the keystore file and passwords securely. **Never commit keystore to git.**

## GitHub Secrets Configuration

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

### Required Secrets:

1. **KEYSTORE_FILE**
   ```bash
   # Encode your keystore file to base64
   base64 -i keystore.jks -o keystore_base64.txt
   # Copy the contents of keystore_base64.txt to this secret
   ```

2. **KEYSTORE_PASSWORD**
   - The password you used when creating the keystore

3. **KEY_ALIAS**
   - The alias you used when creating the keystore (e.g., "your-key-alias")

4. **KEY_PASSWORD**
   - The key password (usually same as keystore password)

5. **API_BASE_URL**
   - Your production API base URL (e.g., "https://api.yourcompany.com")

6. **GOOGLE_SERVICES_JSON**
   ```bash
   # Encode your google-services.json file to base64
   base64 -i driver-app/app/google-services.json -o google_services_base64.txt
   # Copy the contents of google_services_base64.txt to this secret
   ```

## Release Process

### Option 1: Tag-based Release
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Option 2: Manual Trigger
1. Go to GitHub → Actions → "Android Release Build"
2. Click "Run workflow"
3. Select branch and run

## Download Release Files

After the workflow completes:
1. Go to the workflow run page
2. Download artifacts:
   - `release-aab` - Upload this to Google Play Store
   - `release-apk` - Use this for testing

## Google Play Store Upload

1. Go to [Google Play Console](https://play.google.com/console)
2. Create new app or select existing app
3. Go to "Production" → "Create new release"
4. Upload the `.aab` file from the workflow artifacts
5. Fill out release notes and submit for review

## Version Management

Update version in `driver-app/app/build.gradle.kts`:
```kotlin
versionCode = 2  // Increment for each release
versionName = "1.1.0"  // Semantic versioning
```

## Troubleshooting

### Build Fails - Missing Gradle Wrapper
```bash
cd driver-app
gradle wrapper --gradle-version 8.9
git add gradle/wrapper/ gradlew
git commit -m "Add gradle wrapper"
```

### Build Fails - Keystore Issues
- Verify all keystore secrets are set correctly
- Ensure KEYSTORE_FILE is properly base64 encoded
- Check that keystore passwords match

### Firebase Issues
- Ensure GOOGLE_SERVICES_JSON secret is set
- Verify the base64 encoding is correct
- Make sure Firebase project is properly configured

## Security Notes

- **Never commit keystore files to git**
- Store keystore backup securely
- Use different keystores for debug/release
- Regularly rotate API keys and update secrets