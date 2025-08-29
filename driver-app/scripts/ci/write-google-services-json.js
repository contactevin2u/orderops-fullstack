// driver-app/scripts/ci/write-google-services-json.js
const fs = require('fs');
const path = require('path');

const out = path.join(__dirname, '..', '..', 'driver-app', 'android', 'app', 'google-services.json'); // when run from repo root
const envValue = process.env.GOOGLE_SERVICES_JSON;
if (!envValue) {
  console.error('GOOGLE_SERVICES_JSON is missing.');
  process.exit(1);
}

let jsonText = envValue.trim();

// If it was pasted with GitHub Secrets line breaks escaped, fix common cases
if (jsonText.startsWith('{') === false) {
  // try base64 decode; if fails, assume it’s raw with \n
  try {
    const decoded = Buffer.from(jsonText, 'base64').toString('utf8');
    if (decoded.trim().startsWith('{')) jsonText = decoded;
  } catch {}
  jsonText = jsonText.replace(/\\n/g, '\n');
}

let parsed;
try {
  parsed = JSON.parse(jsonText);
} catch (e) {
  console.error('google-services.json is not valid JSON (after decode/unescape).');
  throw e;
}

// Ensure directories exist
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(parsed, null, 2));
console.log(`Wrote ${out}`);
