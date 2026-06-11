import type { PlanId } from "@/lib/plans";

export type CheckoutRequest = {
  nome: string;
  whatsapp: string;
  plano: PlanId;
};

export type CheckoutResponse = {
  pix_qr_code: string;
  pix_copia_cola: string;
  valor: number;
  plano: PlanId;
  expiracao: string;
};

export async function createCheckout(payload: CheckoutRequest): Promise<CheckoutResponse> {
  const response = await fetch("/api/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(errorBody?.error ?? "Não foi possível iniciar o pagamento.");
  }

  return response.json() as Promise<CheckoutResponse>;
}
