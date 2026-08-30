// apps/web/__tests__/smoke.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("smoke", () => {
  it("renders a labelled element", () => {
    render(<button aria-label="Hi">Hi</button>);
    expect(screen.getByRole("button", { name: "Hi" })).toBeInTheDocument();
  });
});
