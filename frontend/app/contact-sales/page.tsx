import type { Metadata } from "next";
import { ContactSalesClient } from "./contact-sales-client";

export const metadata: Metadata = {
  title: "Contact Sales",
  description: "Talk to Sakan AI about Enterprise plans, licensed data feeds, or team billing.",
  robots: { index: false },
};

export default function ContactSalesPage() {
  return <ContactSalesClient />;
}
