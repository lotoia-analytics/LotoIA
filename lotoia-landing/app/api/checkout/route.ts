import { NextResponse } from "next/server";

import { createPixCheckout, toPixQrDataUri } from "@/lib/asaas";
import { getPlanById, isOfficialPlan } from "@/lib/plans";
import {
  canonicalWhatsapp,
  isValidBrazilianWhatsapp,
  isValidCpfCnpj,
  normalizeCpfCnpj,
} from "@/lib/validation";

type CheckoutBody = {
  nome?: string;
  whatsapp?: string;
  cpf?: string;
  plano?: string;
};

export async function POST(request: Request) {
  let body: CheckoutBody;
  try {
    body = (await request.json()) as CheckoutBody;
  } catch {
    return NextResponse.json({ error: "JSON inválido." }, { status: 400 });
  }

  const nome = String(body.nome ?? "").trim();
  const whatsapp = String(body.whatsapp ?? "").trim();
  const cpf = String(body.cpf ?? "").trim();
  const plano = String(body.plano ?? "").trim().toLowerCase();

  if (!nome || nome.length < 2) {
    return NextResponse.json({ error: "Informe um nome válido." }, { status: 400 });
  }

  if (!isValidBrazilianWhatsapp(whatsapp)) {
    return NextResponse.json(
      { error: "WhatsApp inválido. Use DDD + número (ex.: 11999999999)." },
      { status: 400 },
    );
  }

  if (!isValidCpfCnpj(cpf)) {
    return NextResponse.json({ error: "CPF ou CNPJ inválido." }, { status: 400 });
  }

  if (!isOfficialPlan(plano)) {
    return NextResponse.json({ error: "Plano inválido." }, { status: 400 });
  }

  const plan = getPlanById(plano);
  if (!plan) {
    return NextResponse.json({ error: "Plano não encontrado." }, { status: 404 });
  }

  const phone = canonicalWhatsapp(whatsapp);
  const valor = plan.price;

  try {
    const result = await createPixCheckout({
      nome,
      whatsapp: phone,
      cpfCnpj: normalizeCpfCnpj(cpf),
      plano,
      valor,
    });

    return NextResponse.json({
      pix_qr_code: toPixQrDataUri(result.encodedImage),
      pix_copia_cola: result.payload,
      valor,
      plano,
      expiracao: result.expiracaoLabel,
      payment_id: result.paymentId,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erro ao gerar PIX.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
