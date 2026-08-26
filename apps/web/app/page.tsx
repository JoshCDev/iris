import type { Metadata } from "next";
import { HomeDesk } from "./HomeDesk";

export const metadata: Metadata = {
  title: "IRIS | plot",
  description:
    "Current water action, latest leaf class, and the assistant for the active plot. AIoT ends in a smart decision a person confirms.",
};

export default function HomePage() {
  return <HomeDesk />;
}
