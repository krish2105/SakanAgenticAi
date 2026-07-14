"use client";

/** HubSpot Forms Submit API -- free CRM tier, API access on every plan.
 * Portal/form IDs are not secrets (HubSpot's own embeddable forms expose
 * them client-side), so NEXT_PUBLIC_* is the right place for them.
 * isHubspotConfigured() lets the contact-sales page fall back to a plain
 * mailto: link when unset, same no-op-when-unconfigured posture as every
 * other optional integration in this app. */
const PORTAL_ID = process.env.NEXT_PUBLIC_HUBSPOT_PORTAL_ID;
const FORM_ID = process.env.NEXT_PUBLIC_HUBSPOT_FORM_ID;

export function isHubspotConfigured(): boolean {
  return Boolean(PORTAL_ID && FORM_ID);
}

export interface ContactSalesLead {
  email: string;
  firstname?: string;
  company?: string;
  message?: string;
}

export async function submitContactSalesLead(lead: ContactSalesLead): Promise<boolean> {
  if (!PORTAL_ID || !FORM_ID) return false;

  const fields = [
    { name: "email", value: lead.email },
    ...(lead.firstname ? [{ name: "firstname", value: lead.firstname }] : []),
    ...(lead.company ? [{ name: "company", value: lead.company }] : []),
    ...(lead.message ? [{ name: "message", value: lead.message }] : []),
  ];

  try {
    const res = await fetch(
      `https://api.hsforms.com/submissions/v3/integration/submit/${PORTAL_ID}/${FORM_ID}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fields }),
      }
    );
    return res.ok;
  } catch {
    return false;
  }
}
