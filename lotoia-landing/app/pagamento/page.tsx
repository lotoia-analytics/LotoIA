"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Logo } from "@/components/Logo";
import type { CheckoutResponse } from "@/lib/api";
import { getPlanById } from "@/lib/plans";

export default function PagamentoPage() {
  const [checkout, setCheckout] = useState<CheckoutResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("lotoia_checkout");
    if (!raw) {
      return;
    }
    try {
      setCheckout(JSON.parse(raw) as CheckoutResponse);
    } catch {
      setCheckout(null);
    }
  }, []);

  const plan = checkout ? getPlanById(checkout.plano) : undefined;

  async function copyPix() {
    if (!checkout?.pix_copia_cola) {
      return;
    }
    await navigator.clipboard.writeText(checkout.pix_copia_cola);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2500);
  }

  if (!checkout) {
    return (
      <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-16">
        <h1 className="text-3xl font-bold text-white">Pagamento não encontrado</h1>
        <p className="mt-3 text-muted">Volte para a landing e inicie uma nova assinatura.</p>
        <Link href="/" className="mt-6 inline-flex text-accent hover:underline">
          Voltar para www.lotoia.chat
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-2xl px-4 py-10 sm:py-16">
      <Logo />
      <Link href="/" className="mt-6 inline-block text-sm text-accent hover:underline">
        ← Voltar
      </Link>
      <h1 className="mt-6 text-3xl font-bold text-white sm:text-4xl">Pagamento PIX</h1>
      <p className="mt-3 text-muted">
        Plano {plan?.name ?? checkout.plano} · R$ {checkout.valor.toFixed(2).replace(".", ",")} · expira em{" "}
        {checkout.expiracao}
      </p>

      <div className="mt-8 rounded-2xl border border-white/10 bg-primary/80 p-6 shadow-card">
        <div className="mx-auto flex max-w-[220px] justify-center rounded-xl bg-white p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={checkout.pix_qr_code} alt="QR Code PIX" className="h-auto w-full" />
        </div>

        <p className="mt-6 text-sm text-muted">Copia e cola PIX</p>
        <textarea
          readOnly
          value={checkout.pix_copia_cola}
          className="mt-2 h-28 w-full rounded-xl border border-white/10 bg-[#0f1328] p-4 text-xs text-white"
        />
        <button
          type="button"
          onClick={copyPix}
          className="mt-4 w-full rounded-xl bg-accent px-4 py-4 font-semibold text-white transition hover:bg-[#3f7be0]"
        >
          {copied ? "PIX copiado!" : "Copiar código PIX"}
        </button>
      </div>

      <p className="mt-6 text-sm text-muted">
        Após a confirmação do pagamento, seu WhatsApp será ativado automaticamente. Em seguida,
        mande <strong className="text-white">olá</strong> para o bot LotoIA.
      </p>
    </main>
  );
}
