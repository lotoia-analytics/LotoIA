import { NextResponse } from "next/server";

import { getPlanById, isOfficialPlan } from "@/lib/plans";
import { canonicalWhatsapp, isValidBrazilianWhatsapp } from "@/lib/validation";

type CheckoutBody = {
  nome?: string;
  whatsapp?: string;
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

  if (!isOfficialPlan(plano)) {
    return NextResponse.json({ error: "Plano inválido." }, { status: 400 });
  }

  const plan = getPlanById(plano);
  if (!plan) {
    return NextResponse.json({ error: "Plano não encontrado." }, { status: 404 });
  }

  const phone = canonicalWhatsapp(whatsapp);
  const valor = plan.price;
  const pixCopiaCola = `00020126580014BR.GOV.BCB.PIX0136${phone}520400005303986540${valor
    .toFixed(2)
    .replace(".", "")}5802BR5925LotoIA Assinatura6009SAO PAULO62070503***6304ABCD`;

  return NextResponse.json({
    pix_qr_code: `data:image/svg+xml;base64,${Buffer.from(
      `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><rect width="100%" height="100%" fill="#fff"/><text x="50%" y="50%" text-anchor="middle" font-size="14" fill="#1a1f3c">PIX MOCK</text></svg>`,
    ).toString("base64")}`,
    pix_copia_cola: pixCopiaCola,
    valor,
    plano,
    expiracao: "30 minutos",
  });
}
