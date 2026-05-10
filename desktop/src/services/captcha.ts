/**
 * Captcha service helper.
 *
 * Centralised store for the current Cloudflare Turnstile token. Components
 * use the CaptchaWidget to populate this; submit handlers use getToken() to
 * read it; logout / page transitions call clear() to reset.
 */

let currentToken: string | null = null;

export const captchaService = {
  setToken(token: string | null) {
    currentToken = token;
  },
  getToken(): string | null {
    return currentToken;
  },
  clear() {
    currentToken = null;
  },
  /** True when a Turnstile site key is configured (non-dev). */
  isConfigured(): boolean {
    return Boolean(import.meta.env.VITE_TURNSTILE_SITE_KEY);
  },
};

export default captchaService;
