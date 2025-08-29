// driver-app/scripts/ci/validate-package.js
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..', '..');
const gsPath = path.join(projectRoot, 'android', 'app', 'google-services.json');
const expected = 'com.yourco.driverAA';

const raw = fs.readFileSync(gsPath, 'utf8');
const gs = JSON.parse(raw);
const pkg = gs?.client?.[0]?.client_info?.android_client_info?.package_name;

if (pkg !== expected) {
  console.error(`google-services.json package_name=${pkg} != ${expected}`);
  process.exit(1);
}
console.log('google-services.json package OK:', pkg);
