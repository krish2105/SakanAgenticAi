import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="max-w-md text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-text-muted">404</p>
        <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">
          This page doesn&apos;t exist
        </h1>
        <p className="mt-2 text-sm text-text-muted">
          The page you&apos;re looking for may have moved, or the link is incomplete.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link href="/">
            <Button>Back to command deck</Button>
          </Link>
          <Link href="/deals">
            <Button variant="outline">My deals</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
