import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["**/*.test.ts", "**/*.test.tsx"],
  },
  resolve: {
    alias: {
      // Mirror tsconfig's "@/*" path alias so imports resolve in tests.
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
});
