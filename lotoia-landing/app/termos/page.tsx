import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";
import { COMPANY, formatCompanyAddress } from "@/lib/company";
import { PLANS } from "@/lib/plans";

export const metadata: Metadata = {
  title: "Termos e Condições — LotoIA",
  description: "Termos de uso do serviço LotoIA.",
};

export default function TermosPage() {
  return (
    <LegalPage title="Termos e Condições de Uso">
      <p>
        Ao contratar o LotoIA, você concorda com estes Termos. Leia com atenção antes de assinar
        qualquer plano.
      </p>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">1. Objeto do serviço</h2>
        <p>
          O LotoIA oferece <strong className="text-white">análise estatística estrutural</strong> e
          geração de combinações para Lotofácil, entregues por assinatura digital via WhatsApp. O
          serviço <strong className="text-white">não garante prêmios</strong> nem resultados
          futuros.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">2. Planos e preços (BRL)</h2>
        <p>Valores em Real brasileiro (R$), por assinatura de 30 dias:</p>
        <ul className="list-disc space-y-1 pl-5">
          {PLANS.map((plan) => (
            <li key={plan.id}>
              {plan.name}: R$ {plan.price.toFixed(2).replace(".", ",")} — formatos {plan.formats}
            </li>
          ))}
        </ul>
        <p>Cada plano inclui até 30 jogos por dia no período contratado, conforme descrição no site.</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">3. Pagamento</h2>
        <p>
          Pagamento exclusivamente via PIX, processado por intermediador financeiro (Asaas). A
          liberação do acesso ocorre após confirmação do pagamento, em até{" "}
          {COMPANY.pixActivationMinutes} minutos em condições normais.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">4. Uso responsável</h2>
        <p>
          O usuário declara ter 18 anos ou mais. Jogos de loteria envolvem risco. Jogue com
          responsabilidade e dentro de seus limites financeiros.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">5. Limitação de responsabilidade</h2>
        <p>
          O LotoIA não se responsabiliza por perdas financeiras decorrentes de apostas. A
          plataforma fornece ferramenta de apoio estatístico, não consultoria financeira.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">6. Foro e empresa</h2>
        <p>
          <strong className="text-white">Prestadora:</strong> {COMPANY.legalName}
          {COMPANY.cnpj ? ` — CNPJ ${COMPANY.cnpj}` : ""}
        </p>
        <p>
          <strong className="text-white">Endereço:</strong> {formatCompanyAddress()}
        </p>
        <p>
          <strong className="text-white">Contato:</strong> {COMPANY.email}
        </p>
        <p>
          Fica eleito o foro da comarca de Água Boa/MT para dirimir controvérsias, salvo direito do
          consumidor de optar pelo foro de seu domicílio.
        </p>
      </section>

      <p className="text-xs">Última atualização: junho de 2026.</p>
    </LegalPage>
  );
}
