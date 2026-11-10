import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://localhost:3000" },
  webServer: [
    {
      command: "python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        RIO_SUPABASE_URL: "",
        RIO_SUPABASE_ANON_KEY: "",
        RIO_SUPABASE_SERVICE_ROLE_KEY: "",
        RIO_FRONTEND_ORIGIN: "http://localhost:3000",
        RIO_ACCOUNTS_PATH: "/tmp/rio-playwright-accounts.json",
        RIO_ADMIN_EMAIL: "admin@example.com",
        RIO_HERO_PATH: "/tmp/rio-playwright-hero.json",
        NEXT_PUBLIC_RIO_API_URL: "http://localhost:8000",
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000/sign-in",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_RIO_API_URL: "http://localhost:8000",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
