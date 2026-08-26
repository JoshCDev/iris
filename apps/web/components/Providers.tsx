"use client";

import type { ReactNode } from "react";
import { PlotProvider } from "@/lib/PlotContext";

export function Providers({ children }: { children: ReactNode }) {
  return <PlotProvider>{children}</PlotProvider>;
}
