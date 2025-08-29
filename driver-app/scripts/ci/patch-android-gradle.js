// driver-app/scripts/ci/patch-android-gradle.js
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..', '..');
const gradleProps = path.join(root, 'android', 'gradle.properties');

try {
  let s = fs.readFileSync(gradleProps, 'utf8');
  // Ensure Kotlin 1.9.24 (compatible with Expo SDK 50 RN 0.73)
  if (!/kotlin\.version=/.test(s)) {
    s += `\nkotlin.version=1.9.24\n`;
  } else {
    s = s.replace(/kotlin\.version=.*\n/, 'kotlin.version=1.9.24\n');
  }
  // Reasonable daemon/jvm args
  if (!/org\.gradle\.jvmargs=/.test(s)) {
    s += `org.gradle.jvmargs=-Xmx4g -Dkotlin.daemon.jvm.options=-Xmx4g\n`;
  }
  if (!/android\.useAndroidX=/.test(s)) s += `android.useAndroidX=true\n`;
  if (!/android\.enableJetifier=/.test(s)) s += `android.enableJetifier=true\n`;
  fs.writeFileSync(gradleProps, s);
  console.log('Patched', gradleProps);
} catch (e) {
  console.warn('Could not patch gradle.properties (prebuild likely not run yet). Will run again post-prebuild.');
  process.exit(0);
}
