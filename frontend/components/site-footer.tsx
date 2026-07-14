import Link from "next/link";
import { T } from "@/components/t";

export function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-surface px-6 py-10 text-sm">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 sm:flex-row sm:justify-between">
        <div className="max-w-xs">
          <span className="font-display text-lg font-semibold text-text-primary">Sakan AI</span>
          <p className="mt-2 text-text-muted">
            <T k="footer.tagline" />
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 sm:flex sm:gap-12">
          <div>
            <p className="font-medium text-text-primary">
              <T k="footer.product" />
            </p>
            <ul className="mt-3 flex flex-col gap-2 text-text-muted">
              <li>
                <Link href="/pricing" className="hover:text-text-primary">
                  <T k="footer.pricing" />
                </Link>
              </li>
              <li>
                <Link href="/comps" className="hover:text-text-primary">
                  <T k="nav.comps" />
                </Link>
              </li>
              <li>
                <Link href="/market" className="hover:text-text-primary">
                  <T k="nav.analytics" />
                </Link>
              </li>
              <li>
                <Link href="/guides" className="hover:text-text-primary">
                  <T k="footer.guides" />
                </Link>
              </li>
              <li>
                <Link href="/status" className="hover:text-text-primary">
                  <T k="footer.status" />
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="font-medium text-text-primary">
              <T k="footer.legal" />
            </p>
            <ul className="mt-3 flex flex-col gap-2 text-text-muted">
              <li>
                <Link href="/legal/terms" className="hover:text-text-primary">
                  <T k="footer.terms" />
                </Link>
              </li>
              <li>
                <Link href="/legal/privacy" className="hover:text-text-primary">
                  <T k="footer.privacy" />
                </Link>
              </li>
              <li>
                <Link href="/legal/dpa" className="hover:text-text-primary">
                  <T k="footer.dpa" />
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="font-medium text-text-primary">
              <T k="footer.contact" />
            </p>
            <ul className="mt-3 flex flex-col gap-2 text-text-muted">
              <li>
                <Link href="/contact-sales" className="hover:text-text-primary">
                  <T k="footer.contactSales" />
                </Link>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-8 flex max-w-5xl flex-col gap-2 border-t border-border pt-6 text-xs text-text-muted sm:flex-row sm:items-center sm:justify-between">
        <p>
          © {year} Sakan AI. <T k="footer.rights" />
        </p>
        <p className="max-w-md">
          <T k="footer.dataNotice" />
        </p>
      </div>
    </footer>
  );
}
