import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";
import { COMPANY } from "@/lib/company";

export const metadata: Metadata = {
  title: "Entrega — LotoIA",
  description: "Como funciona a entrega digital do serviço LotoIA após o pagamento PIX.",
};

export default function EntregaPage() {
  return (
    <LegalPage title="Política de entrega">
      <p>
        O LotoIA é um <strong className="text-white">serviço digital</strong>. Não há envio de
        produtos físicos.
      </p>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Como você recebe o serviço</h2>
        <ol className="list-decimal space-y-2 pl-5">
          <li>Escolha um plano em nosso site e preencha nome, WhatsApp e CPF/CNPJ.</li>
          <li>Realize o pagamento via PIX (moeda: BRL — Real brasileiro).</li>
          <li>
            Após a confirmação do pagamento pelo gateway, seu acesso é liberado automaticamente no
            WhatsApp cadastrado.
          </li>
          <li>Envie <strong className="text-white">olá</strong> para o bot LotoIA e solicite seus jogos.</li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Prazo de liberação</h2>
        <p>
          A liberação do acesso ocorre em até{" "}
          <strong className="text-white">{COMPANY.pixActivationMinutes} minutos</strong> após a
          confirmação do PIX, em condições normais de operação dos sistemas de pagamento e
          notificação.
        </p>
        <p>
          Se o acesso não for liberado nesse prazo, entre em contato pelo e-mail{" "}
          <a href={`mailto:${COMPANY.email}`} className="text-accent hover:underline">
            {COMPANY.email}
          </a>{" "}
          ou WhatsApp {COMPANY.supportWhatsappDisplay}, informando o comprovante de pagamento.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Área de entrega</h2>
        <p>
          O serviço é prestado integralmente por meio digital (site + WhatsApp), disponível em todo
          o território brasileiro, desde que o usuário possua conexão à internet e número de
          WhatsApp válido.
        </p>
      </section>
    </LegalPage>
  );
}
