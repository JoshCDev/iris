import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "jsdom",
    // This environment exports NODE_ENV=production globally; without
    // overriding it React loads its production CJS build, which does not
    // ship `act`, and @testing-library/react (and `react-dom/test-utils`)
    // fail with "React.act is not a function". Force the test process to
    // run with NODE_ENV=test so React's development build (with `act`) is
    // used by both `import { act } from "react"` and Testing Library.
    env: { NODE_ENV: "test" },
    setupFiles: ["./vitest.setup.ts"],
    globals: false,
    include: ["__tests__/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
});
