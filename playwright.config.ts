import { defineConfig } from "@playwright/test";

const backendUrl = "http://127.0.0.1:8001";
const dashboardUrl = "http://localhost:5174";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: dashboardUrl },
  webServer: [
    {
      command: "uv run -m uvicorn backend.tests.e2e_app:app --port 8001",
      url: `${backendUrl}/api/health`,
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: dashboardUrl,
      reuseExistingServer: false,
      env: { BACKEND_URL: backendUrl },
    },
  ],
});
