import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";
import { COMPANY, formatCompanyAddress } from "@/lib/company";

export const metadata: Metadata = {
  title: "Política de Privacidade — LotoIA",
  description: "Como o LotoIA coleta, usa e protege seus dados pessoais (LGPD).",
};

export default function PrivacidadePage() {
  return (
    <LegalPage title="Política de Privacidade">
      <p>
        Esta Política descreve como {COMPANY.legalName} trata dados pessoais no site e no serviço
        WhatsApp, em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).
      </p>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">1. Dados que coletamos</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Nome</li>
          <li>Número de WhatsApp</li>
          <li>CPF ou CNPJ (para emissão e conciliação de cobrança PIX)</li>
          <li>Dados de pagamento (processados pelo Asaas; não armazenamos dados bancários completos)</li>
          <li>Histórico de gerações de jogos e uso do serviço</li>
          <li>Dados técnicos de acesso (IP, navegador — quando aplicável)</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">2. Finalidade do tratamento</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Prestação do serviço contratado (liberação e operação no WhatsApp)</li>
          <li>Processamento de pagamentos e suporte ao cliente</li>
          <li>Cumprimento de obrigações legais e prevenção a fraudes</li>
          <li>Melhoria operacional e segurança da plataforma</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">3. Compartilhamento</h2>
        <p>Podemos compartilhar dados estritamente necessários com:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong className="text-white">Asaas</strong> — processamento de pagamentos PIX
          </li>
          <li>
            <strong className="text-white">Evolution API / WhatsApp</strong> — entrega de mensagens
          </li>
          <li>
            <strong className="text-white">Railway / provedores de infraestrutura</strong> — hospedagem
            e banco de dados
          </li>
        </ul>
        <p>Não vendemos seus dados pessoais a terceiros.</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">4. Seus direitos (LGPD)</h2>
        <p>Você pode solicitar:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Confirmação e acesso aos dados</li>
          <li>Correção de dados incompletos ou desatualizados</li>
          <li>Eliminação de dados desnecessários, quando aplicável</li>
          <li>Revogação de consentimento, quando cabível</li>
        </ul>
        <p>
          Solicitações:{" "}
          <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
            {COMPANY.email}
          </a>
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">5. Retenção e segurança</h2>
        <p>
          Mantemos os dados pelo tempo necessário à prestação do serviço, obrigações legais e
          resolução de disputas. Adotamos medidas técnicas e organizacionais para proteger as
          informações armazenadas em servidores seguros (PostgreSQL, acesso restrito).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">6. Controlador</h2>
        <p>
          <strong className="text-white">{COMPANY.legalName}</strong>
          {COMPANY.cnpj ? ` — CNPJ ${COMPANY.cnpj}` : ""}
        </p>
        <p>{formatCompanyAddress()}</p>
        <p>
          E-mail do encarregado/contato:{" "}
          <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
            {COMPANY.email}
          </a>
        </p>
      </section>

      <p className="text-xs">Última atualização: junho de 2026.</p>
    </LegalPage>
  );
}
