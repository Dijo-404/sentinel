import type { Metadata } from "next";
import { DesignGallery } from "./gallery";

export const metadata: Metadata = { title: "Sentinel — design system" };

/** Component gallery: every Night Ledger primitive on labelled sample data. */
export default function DesignPage() {
  return <DesignGallery />;
}
