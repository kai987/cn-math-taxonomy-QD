const { defineConfig } = require('@playwright/test');

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:' + (process.env.PLAYWRIGHT_PORT || '8769');

module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : 3,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    browserName: 'chromium',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off'
  },
  projects: [
    { name: 'phone', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'tablet', grepInvert: /@grading-contract/, use: { viewport: { width: 768, height: 1024 }, isMobile: true, hasTouch: true } },
    { name: 'desktop', grepInvert: /@grading-contract/, use: { viewport: { width: 1440, height: 900 } } },
    ...(process.env.PLAYWRIGHT_WEBKIT ? [
      { name: 'webkit-phone', use: { browserName: 'webkit', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
      { name: 'webkit-tablet', grepInvert: /@grading-contract/, use: { browserName: 'webkit', viewport: { width: 768, height: 1024 }, isMobile: true, hasTouch: true } }
    ] : [])
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : {
    command: 'node tests/browser/server.cjs',
    url: baseURL,
    reuseExistingServer: false,
    timeout: 30000
  }
});
