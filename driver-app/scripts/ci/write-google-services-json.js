// driver-app/scripts/ci/write-google-services-json.js
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..', '..');
const out = path.join(projectRoot, 'android', 'app', 'google-services.json');

const envValue = process.env.GOOGLE_SERVICES_JSON;
if (!envValue) {
  console.error('GOOGLE_SERVICES_JSON is missing.');
  process.exit(1);
}

let text = envValue.trim();
// Try base64 decode first; if not JSON, treat as escaped string with \n
try {
  const decoded = Buffer.from(text, 'base64').toString('utf8');
  if (decoded.trim().startsWith('{')) text = decoded;
} catch {}
if (!text.trim().startsWith('{')) text = text.replace(/\\n/g, '\n');

let parsed;
try {
  parsed = JSON.parse(text);
} catch (e) {
  console.error('google-services.json is not valid JSON (after decode/unescape).');
  throw e;
}

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(parsed, null, 2));
console.log(`Wrote ${out}`);
