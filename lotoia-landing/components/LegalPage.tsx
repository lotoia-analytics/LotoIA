import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/Logo";
import { SiteFooter } from "@/components/SiteFooter";

type LegalPageProps = {
  title: string;
  children: ReactNode;
};

export function LegalPage({ title, children }: LegalPageProps) {
  return (
    <main>
      <header className="border-b border-white/10 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
          <Logo />
          <Link href="/" className="text-sm font-medium text-accent hover:underline">
            Voltar ao início
          </Link>
        </div>
      </header>

      <article className="px-4 py-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <h1 className="text-3xl font-bold text-white sm:text-4xl">{title}</h1>
          <div className="prose-legal mt-8 space-y-4 text-sm leading-relaxed text-muted sm:text-base">
            {children}
          </div>
        </div>
      </article>

      <SiteFooter />
    </main>
  );
}
