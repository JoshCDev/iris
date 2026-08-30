// apps/web/__tests__/chat-a11y.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeAll } from "vitest";
import { AssistantClient } from "@/app/assistant/AssistantClient";
import { LocaleProvider } from "@/lib/i18n";
import { PlotContext } from "@/lib/PlotContext";

// AssistantClient reads ?q= via useSearchParams; jsdom has no router, so
// provide a bare search-params hook.
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

// jsdom's Element has no scrollTo; the chat log's mount effect calls it.
beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
});

const ctx = {
  plots: [],
  activePlotId: null,
  activePlot: null,
  today: null,
  status: null,
  history: null,
  reports: [],
  error: null,
  refresh: () => {},
  selectPlot: () => {},
};

describe("AssistantClient", () => {
  it("labels the textarea and exposes a live log", () => {
    render(
      <LocaleProvider>
        <PlotContext.Provider value={ctx}><AssistantClient /></PlotContext.Provider>
      </LocaleProvider>,
    );
    expect(screen.getByLabelText(/ask/i)).toBeInTheDocument();
    expect(screen.getByRole("log")).toBeInTheDocument();
  });
});
