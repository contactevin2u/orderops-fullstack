// driver-app/scripts/ci/patch-gradle.js
const fs = require('fs');
const path = require('path');

const root = path.join('driver-app', 'android');

// gradle.properties
const gp = path.join(root, 'gradle.properties');
let gpTxt = fs.existsSync(gp) ? fs.readFileSync(gp, 'utf8') : '';
const ensure = (k, v) => {
  const line = `${k}=${v}`;
  const re = new RegExp(`^${k}=.*$`, 'm');
  gpTxt = re.test(gpTxt) ? gpTxt.replace(re, line) : (gpTxt.trim() + '\n' + line + '\n');
};
ensure('org.gradle.jvmargs', '-Xmx4g -Dkotlin.daemon.jvm.options=-Xmx2g -XX:+UseParallelGC');
ensure('android.useAndroidX', 'true');
ensure('android.enableJetifier', 'true');
ensure('kotlin.jvm.target', '17');
ensure('kotlin.code.style', 'official');
ensure('kotlin.compiler.execution.strategy', 'in-process');
ensure('android.suppressUnsupportedCompileSdk', '34');
fs.writeFileSync(gp, gpTxt);

// build.gradle (project)
const proj = path.join(root, 'build.gradle');
let projTxt = fs.readFileSync(proj, 'utf8');

// Force Kotlin plugin version 1.9.24 in plugins {}
projTxt = projTxt.replace(
  /id\s+['"]org\.jetbrains\.kotlin\.android['"]\s+version\s+['"][^'"]+['"]/,
  `id 'org.jetbrains.kotlin.android' version '1.9.24'`
);

// Ensure resolutionStrategy to align kotlin artifacts
if (!projTxt.includes('resolutionStrategy.eachDependency')) {
  projTxt = projTxt.replace(
    /allprojects\s*\{\s*repositories\s*\{[^}]*\}\s*\}/s,
    m => `${m}
allprojects {
  configurations.all {
    resolutionStrategy.eachDependency { details ->
      if (details.requested.group == "org.jetbrains.kotlin") {
        details.useVersion("1.9.24")
      }
    }
  }
}`
  );
}
fs.writeFileSync(proj, projTxt);

// app/build.gradle
const app = path.join(root, 'app', 'build.gradle');
let appTxt = fs.readFileSync(app, 'utf8');

// Ensure Java 17 + Kotlin jvmTarget 17
appTxt = appTxt.replace(/compileOptions\s*\{[\s\S]*?\}/, `
compileOptions {
  sourceCompatibility JavaVersion.VERSION_17
  targetCompatibility JavaVersion.VERSION_17
}
`);

if (appTxt.includes('kotlinOptions')) {
  appTxt = appTxt.replace(/kotlinOptions\s*\{[\s\S]*?\}/, `
kotlinOptions {
  jvmTarget = '17'
}
`);
} else {
  appTxt = appTxt.replace(/android\s*\{/, `android {\n  kotlinOptions { jvmTarget = '17' }`);
}

// Ensure google services plugin at bottom (safe if duplicated by plugin)
if (!/com\.google\.gms\.google-services/.test(appTxt)) {
  appTxt = appTxt.replace(/apply plugin: 'com\.android\.application'/, (m) => `${m}\napply plugin: 'com.google.gms.google-services'`);
}

fs.writeFileSync(app, appTxt);

console.log('Patched gradle for Kotlin 1.9.24 / Java 17 and google-services');
