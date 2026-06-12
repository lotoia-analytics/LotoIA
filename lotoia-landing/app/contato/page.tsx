import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";
import {
  COMPANY,
  formatCompanyAddress,
  OFFICIAL_LANDING_URL,
  supportWhatsappUrl,
} from "@/lib/company";

export const metadata: Metadata = {
  title: "Contato — LotoIA",
  description: "Informações de contato e dados da empresa LotoIA.",
};

export default function ContatoPage() {
  return (
    <LegalPage title="Contato">
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Empresa</h2>
        <p>
          <strong className="text-white">Nome:</strong> {COMPANY.legalName}
        </p>
        {COMPANY.cnpj ? (
          <p>
            <strong className="text-white">CNPJ:</strong> {COMPANY.cnpj}
          </p>
        ) : null}
        <p>
          <strong className="text-white">Endereço:</strong> {formatCompanyAddress()}
        </p>
        <p>
          <strong className="text-white">Site:</strong>{" "}
          <a href={OFFICIAL_LANDING_URL} className="text-accent hover:underline">
            {OFFICIAL_LANDING_URL}
          </a>
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Canais de atendimento</h2>
        <p>
          <strong className="text-white">E-mail:</strong>{" "}
          <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
            {COMPANY.email}
          </a>
        </p>
        <p>
          <strong className="text-white">WhatsApp (suporte):</strong>{" "}
          <a
            href={supportWhatsappUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:underline"
          >
            {COMPANY.supportWhatsappDisplay}
          </a>
        </p>
        <p>Horário de resposta: dias úteis, em até 24 horas úteis.</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Assinatura</h2>
        <p>
          Para contratar um plano, acesse a página inicial, escolha o plano desejado e conclua o
          pagamento via PIX. O acesso ao bot WhatsApp é liberado após a confirmação do pagamento.
        </p>
      </section>
    </LegalPage>
  );
}
