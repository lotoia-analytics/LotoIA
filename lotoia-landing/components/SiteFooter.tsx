import Link from "next/link";

import { Logo } from "@/components/Logo";
import {
  COMPANY,
  formatCompanyAddress,
  OFFICIAL_LANDING_HOST,
  supportWhatsappUrl,
} from "@/lib/company";

const LEGAL_LINKS = [
  { href: "/contato", label: "Contato" },
  { href: "/entrega", label: "Entrega" },
  { href: "/reembolso", label: "Reembolso" },
  { href: "/termos", label: "Termos" },
  { href: "/privacidade", label: "Privacidade" },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-8 text-sm leading-relaxed text-muted">
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-3">
            <Logo href="" className="opacity-90" />
            <p>
              {COMPANY.legalName} — plataforma de análise estatística para Lotofácil. Resultados
              passados não garantem resultados futuros. Jogue com responsabilidade.
            </p>
            {COMPANY.cnpj ? <p className="text-xs">CNPJ: {COMPANY.cnpj}</p> : null}
          </div>

          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-white">Contato</h2>
            <p>{formatCompanyAddress()}</p>
            <p>
              E-mail:{" "}
              <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
                {COMPANY.email}
              </a>
            </p>
            <p>
              WhatsApp:{" "}
              <a
                href={supportWhatsappUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline"
              >
                {COMPANY.supportWhatsappDisplay}
              </a>
            </p>
            <p className="text-xs">Site: {OFFICIAL_LANDING_HOST}</p>
          </div>

          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-white">
              Informações legais
            </h2>
            <nav className="flex flex-col gap-1">
              {LEGAL_LINKS.map((link) => (
                <Link key={link.href} href={link.href} className="text-accent hover:underline">
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </div>

        <p className="text-xs">
          © {new Date().getFullYear()} {COMPANY.tradeName}. Todos os direitos reservados.
        </p>
      </div>
    </footer>
  );
}
