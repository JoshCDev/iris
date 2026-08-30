"use client";

import type { ReactNode } from "react";
import { LocaleProvider } from "@/lib/i18n";
import { PlotProvider } from "@/lib/PlotContext";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <PlotProvider>
      <LocaleProvider>{children}</LocaleProvider>
    </PlotProvider>
  );
}
