// driver-app/scripts/ci/validate-package.js
const fs = require('fs');
const path = require('path');

const gs = JSON.parse(fs.readFileSync(path.join('driver-app/android/app/google-services.json'), 'utf8'));
const expected = 'com.yourco.driverAA';

let packageName;
try {
  // prefer client[0].client_info.android_client_info.package_name
  const c0 = gs.client?.[0];
  packageName = c0?.client_info?.android_client_info?.package_name;
} catch {}

if (packageName !== expected) {
  console.error(`google-services.json package_name=${packageName} does not match android.package=${expected}`);
  process.exit(1);
}
console.log('google-services.json package name OK:', packageName);
