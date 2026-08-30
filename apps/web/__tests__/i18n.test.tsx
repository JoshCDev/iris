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
      <span data-testid="rain-check">{t("today.rainCheckReview")}</span>
      <span data-testid="plot-concern">{t("today.plotConcern")}</span>
      <button onClick={() => setLocale("en")}>to-en</button>
    </div>
  );
}

describe("i18n", () => {
  it("defaults to Indonesian and switches to English", async () => {
    render(<LocaleProvider><Probe /></LocaleProvider>);
    expect(screen.getByTestId("locale").textContent).toBe("id");
    expect(screen.getByTestId("nav-today").textContent).toBe("Hari Ini");
    expect(screen.getByTestId("rain-check").textContent).toBe("Pemeriksaan hujan tambahan perlu ditinjau");
    expect(screen.getByTestId("plot-concern").textContent).toBe("Kekhawatiran gabungan lahan");
    await userEvent.click(screen.getByText("to-en"));
    await waitFor(() => expect(screen.getByTestId("locale").textContent).toBe("en"));
    expect(screen.getByTestId("nav-today").textContent).toBe("Today");
    expect(screen.getByTestId("rain-check").textContent).toBe("Additional rain check needs review");
    expect(screen.getByTestId("plot-concern").textContent).toBe("Combined plot concern");
  });
});
