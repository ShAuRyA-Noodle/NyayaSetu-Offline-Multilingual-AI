import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Capacitor configuration for the NyayaSetu Android build.
 *
 * The web app (Vite build in `dist/`) is wrapped into a native Android APK via
 * Capacitor. Build steps are documented in docs/MOBILE_BUILD.md. Requires the
 * Android SDK / Android Studio to produce the APK.
 */
const config: CapacitorConfig = {
  appId: 'in.nyayasetu.app',
  appName: 'NyayaSetu',
  webDir: 'dist',
  backgroundColor: '#060B18',
  android: {
    allowMixedContent: false,
  },
  server: {
    androidScheme: 'https',
  },
};

export default config;
