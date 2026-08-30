import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { LocaleProvider, useLocale } from "@/lib/i18n";

function Probe() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="nav-today">{t("nav.today")}</span>
      <button onClick={() => setLocale("en")}>to-en</button>
    </div>
  );
}

describe("i18n", () => {
  it("defaults to Indonesian and switches to English", async () => {
    render(<LocaleProvider><Probe /></LocaleProvider>);
    expect(screen.getByTestId("locale").textContent).toBe("id");
    expect(screen.getByTestId("nav-today").textContent).toBe("Hari Ini");
    await userEvent.click(screen.getByText("to-en"));
    await waitFor(() => expect(screen.getByTestId("locale").textContent).toBe("en"));
    expect(screen.getByTestId("nav-today").textContent).toBe("Today");
  });
});
