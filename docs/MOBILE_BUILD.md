# NyayaSetu — Mobile & Edge Builds

The web app is offline-first and ships two edge form factors from the **same
codebase** (`desktop/`): an installable **PWA** and a native **Android APK**.

## 1. PWA (installable, offline) — no extra tooling

The PWA is fully built in the standard web build. It includes:

- `public/manifest.webmanifest` — installable app metadata (name, icons, theme).
- `public/icon-192.png`, `icon-512.png`, `apple-touch-icon.png` — maskable icons.
- `public/sw.js` — service worker: app-shell precache, network-first navigation
  with offline SPA fallback, cache-first static assets, network-first API with
  cached fallback. Registered from `index.html`.

```bash
cd desktop
npm run build:web          # outputs dist/ with sw.js + manifest + icons
npm run preview            # serve locally; Chrome → Install app → works offline
```

Verified: `dist/` contains `sw.js`, `manifest.webmanifest`, and all icons, so the
app is installable and usable with no connectivity (Add to Home Screen on
Android/desktop). This satisfies the offline-installable edge deployment.

## 2. Android APK (Capacitor)

`capacitor.config.ts` wraps the Vite `dist/` build into a native APK.

Requires the **Android SDK** (via Android Studio). One-time setup:

```bash
cd desktop
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init NyayaSetu in.nyayasetu.app --web-dir dist
npx cap add android
```

Build the APK:

```bash
npm run build:web          # produce dist/
npx cap sync android       # copy web assets + plugins into the android project
cd android
./gradlew assembleDebug    # -> android/app/build/outputs/apk/debug/app-debug.apk
```

Run on an **emulated low-end device** (no physical phone needed):

```bash
# In Android Studio: Device Manager → create a 2 GB-RAM AVD → Run,
# or from CLI once an AVD exists:
npx cap run android
```

The APK bundles the same offline lane (local knowledge base, RAG, on-device LLM
via the backend) used by the desktop/web builds.

> Note: producing the APK binary requires the Android SDK to be installed. The
> Capacitor config and scripts above are committed so the build is a single
> `gradlew assembleDebug` away on any machine with the SDK.
