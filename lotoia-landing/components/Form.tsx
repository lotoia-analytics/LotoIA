"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createCheckout } from "@/lib/api";
import { getPlanById, PLANS, type PlanId } from "@/lib/plans";
import { isValidBrazilianWhatsapp, isValidCpfCnpj } from "@/lib/validation";

type FormProps = {
  isOpen: boolean;
  selectedPlan: PlanId | null;
  onClose: () => void;
};

export function Form({ isOpen, selectedPlan, onClose }: FormProps) {
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [cpf, setCpf] = useState("");
  const [plano, setPlano] = useState<PlanId>("completo");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedPlan) {
      setPlano(selectedPlan);
    }
  }, [selectedPlan]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const activePlan = getPlanById(plano);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!nome.trim()) {
      setError("Informe seu nome.");
      return;
    }

    if (!isValidBrazilianWhatsapp(whatsapp)) {
      setError("WhatsApp inválido. Use DDD + número (ex.: 11999999999).");
      return;
    }

    if (!isValidCpfCnpj(cpf)) {
      setError("CPF ou CNPJ inválido.");
      return;
    }

    setLoading(true);
    try {
      const checkout = await createCheckout({
        nome: nome.trim(),
        whatsapp,
        cpf,
        plano,
      });
      sessionStorage.setItem("lotoia_checkout", JSON.stringify(checkout));
      router.push("/pagamento");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Erro ao iniciar pagamento.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-primary p-6 shadow-card sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Começar assinatura</h2>
            <p className="mt-2 text-sm text-muted">
              Use o mesmo WhatsApp que vai conversar com o bot LotoIA.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-muted transition hover:bg-white/5 hover:text-white"
            aria-label="Fechar formulário"
          >
            ✕
          </button>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm text-muted">
            Nome
            <input
              type="text"
              name="nome"
              value={nome}
              onChange={(event) => setNome(event.target.value)}
              placeholder="Seu nome"
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#0f1328] px-4 py-3 text-white outline-none transition focus:border-accent"
              autoComplete="name"
              required
            />
          </label>

          <label className="block text-sm text-muted">
            WhatsApp
            <input
              type="tel"
              name="whatsapp"
              value={whatsapp}
              onChange={(event) => setWhatsapp(event.target.value)}
              placeholder="11999999999"
              inputMode="numeric"
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#0f1328] px-4 py-3 text-white outline-none transition focus:border-accent"
              autoComplete="tel"
              required
            />
          </label>

          <label className="block text-sm text-muted">
            CPF ou CNPJ
            <input
              type="text"
              name="cpf"
              value={cpf}
              onChange={(event) => setCpf(event.target.value)}
              placeholder="000.000.000-00"
              inputMode="numeric"
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#0f1328] px-4 py-3 text-white outline-none transition focus:border-accent"
              autoComplete="off"
              required
            />
          </label>

          <label className="block text-sm text-muted">
            Plano
            <select
              name="plano"
              value={plano}
              onChange={(event) => setPlano(event.target.value as PlanId)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#0f1328] px-4 py-3 text-white outline-none transition focus:border-accent"
            >
              {PLANS.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} — R$ {plan.price.toFixed(2).replace(".", ",")}
                </option>
              ))}
            </select>
          </label>

          {activePlan ? (
            <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm">
              <p className="text-2xl font-bold text-white">
                R$ {activePlan.price.toFixed(2).replace(".", ",")}
              </p>
              <p className="mt-1 text-muted">
                {activePlan.formats} · 7 dias (15D) + 12 meses (15D + 20D) · até{" "}
                {activePlan.dailyGames} jogos/dia
              </p>
            </div>
          ) : null}

          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-accent px-4 py-4 text-base font-semibold text-white transition hover:bg-[#3f7be0] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading
              ? "Gerando PIX..."
              : activePlan
                ? `Pagar R$ ${activePlan.price.toFixed(2).replace(".", ",")} via PIX`
                : "Continuar para pagamento"}
          </button>
        </form>
      </div>
    </div>
  );
}
