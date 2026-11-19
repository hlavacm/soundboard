import { defineConfig, devices } from '@playwright/test';

const PORT = 8123; // not 8000, so tests do not clash with a manually started server

export default defineConfig({
  testDir: 'tests',
  testMatch: '*.spec.js',
  // one worker: with several pages at once, the toy python server resets connections
  // (net::ERR_CONNECTION_RESET) and some tiles never load
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  // locally reuse a running server on the port, in CI always start a fresh one
  webServer: { command: `python3 -m http.server ${PORT}`, port: PORT, reuseExistingServer: !process.env.CI },
  use: {
    baseURL: `http://localhost:${PORT}`,
    launchOptions: { args: ['--autoplay-policy=no-user-gesture-required'] },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
