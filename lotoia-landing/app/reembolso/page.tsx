import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";
import { COMPANY, supportWhatsappUrl } from "@/lib/company";

export const metadata: Metadata = {
  title: "Reembolso — LotoIA",
  description: "Política de devolução e reembolso do LotoIA.",
};

export default function ReembolsoPage() {
  return (
    <LegalPage title="Política de devolução e reembolso">
      <p>
        Esta política descreve as condições de cancelamento e reembolso das assinaturas digitais
        contratadas no site LotoIA.
      </p>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Direito de arrependimento</h2>
        <p>
          Em compras realizadas pela internet, o consumidor pode solicitar cancelamento em até{" "}
          <strong className="text-white">7 (sete) dias corridos</strong> após a contratação, nos
          termos do Código de Defesa do Consumidor (Art. 49), desde que o serviço{" "}
          <strong className="text-white">não tenha sido utilizado</strong>.
        </p>
        <p>
          Considera-se <strong className="text-white">utilizado</strong> quando o cliente já
          solicitou e recebeu ao menos uma geração de jogos pelo bot WhatsApp durante o período
          contratado.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Como solicitar reembolso</h2>
        <p>Envie sua solicitação para:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            E-mail:{" "}
            <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
              {COMPANY.email}
            </a>
          </li>
          <li>
            WhatsApp:{" "}
            <a
              href={supportWhatsappUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              {COMPANY.supportWhatsappDisplay}
            </a>
          </li>
        </ul>
        <p>Informe: nome completo, WhatsApp cadastrado, data da compra e comprovante PIX.</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Prazo de estorno</h2>
        <p>
          Reembolsos aprovados são processados em até 10 dias úteis, pelo mesmo meio de pagamento
          (PIX), conforme regras do intermediador financeiro (Asaas).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Casos sem reembolso</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Serviço já utilizado (geração de jogos solicitada no WhatsApp).</li>
          <li>Prazo de 7 dias expirado.</li>
          <li>Violação dos Termos de Uso.</li>
        </ul>
      </section>
    </LegalPage>
  );
}
