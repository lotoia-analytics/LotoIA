import { canonicalWhatsapp } from "@/lib/validation";

const BASE_URL = process.env.ASAAS_API_URL ?? "https://api.asaas.com/v3";
const API_KEY = process.env.ASAAS_API_KEY ?? "";

type AsaasErrorBody = {
  errors?: Array<{ code?: string; description?: string }>;
};

export type AsaasPixCheckoutResult = {
  paymentId: string;
  customerId: string;
  encodedImage: string;
  payload: string;
  expirationDate: string;
};

function requireApiKey(): string {
  if (!API_KEY.trim()) {
    throw new Error("ASAAS_API_KEY não configurada.");
  }
  return API_KEY.trim();
}

function formatMobilePhoneForAsaas(whatsapp: string): string {
  const digits = canonicalWhatsapp(whatsapp);
  if (digits.startsWith("55") && digits.length >= 12) {
    return digits.slice(2);
  }
  return digits;
}

function formatDueDate(): string {
  const due = new Date();
  due.setUTCDate(due.getUTCDate() + 1);
  return due.toISOString().slice(0, 10);
}

function formatExpirationLabel(expirationDate: string): string {
  const parsed = new Date(expirationDate);
  if (Number.isNaN(parsed.getTime())) {
    return "30 minutos";
  }
  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function asaasRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiKey = requireApiKey();
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      access_token: apiKey,
      "User-Agent": "LotoIA-Checkout/1.0",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  const bodyText = await response.text();
  let body: unknown = null;
  if (bodyText) {
    try {
      body = JSON.parse(bodyText) as unknown;
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const errorBody = (body ?? {}) as AsaasErrorBody;
    const message =
      errorBody.errors?.map((item) => item.description).filter(Boolean).join(" | ") ||
      `Erro Asaas (${response.status})`;
    throw new Error(message);
  }

  return body as T;
}

export async function createCustomer(
  nome: string,
  whatsapp: string,
  cpfCnpj: string,
): Promise<string> {
  const mobilePhone = formatMobilePhoneForAsaas(whatsapp);
  const payload = await asaasRequest<{ id: string }>("/customers", {
    method: "POST",
    body: JSON.stringify({
      name: nome,
      mobilePhone,
      cpfCnpj,
    }),
  });
  return payload.id;
}

export async function createPixCharge(
  customerId: string,
  plano: string,
  valor: number,
  whatsapp: string,
): Promise<string> {
  const phone = canonicalWhatsapp(whatsapp);
  const payload = await asaasRequest<{ id: string }>("/payments", {
    method: "POST",
    body: JSON.stringify({
      customer: customerId,
      billingType: "PIX",
      value: Number(valor.toFixed(2)),
      dueDate: formatDueDate(),
      description: `LotoIA — Plano ${plano} (30 dias)`,
      externalReference: `lotoia:${plano}:${phone}`,
    }),
  });
  return payload.id;
}

export async function getPixQrCode(paymentId: string): Promise<{
  encodedImage: string;
  payload: string;
  expirationDate: string;
}> {
  return asaasRequest<{
    encodedImage: string;
    payload: string;
    expirationDate: string;
  }>(`/payments/${paymentId}/pixQrCode`, {
    method: "GET",
  });
}

export async function createPixCheckout(input: {
  nome: string;
  whatsapp: string;
  cpfCnpj: string;
  plano: string;
  valor: number;
}): Promise<AsaasPixCheckoutResult & { expiracaoLabel: string }> {
  const customerId = await createCustomer(input.nome, input.whatsapp, input.cpfCnpj);
  const paymentId = await createPixCharge(
    customerId,
    input.plano,
    input.valor,
    input.whatsapp,
  );
  const pix = await getPixQrCode(paymentId);
  return {
    paymentId,
    customerId,
    encodedImage: pix.encodedImage,
    payload: pix.payload,
    expirationDate: pix.expirationDate,
    expiracaoLabel: formatExpirationLabel(pix.expirationDate),
  };
}

export function toPixQrDataUri(encodedImage: string): string {
  if (encodedImage.startsWith("data:image")) {
    return encodedImage;
  }
  return `data:image/png;base64,${encodedImage}`;
}
