export const OFFICIAL_LANDING_HOST = "www.lotoia.chat";
export const OFFICIAL_LANDING_URL = `https://${OFFICIAL_LANDING_HOST}`;

export const COMPANY = {
  tradeName: "LotoIA",
  legalName: process.env.NEXT_PUBLIC_COMPANY_LEGAL_NAME?.trim() || "LotoIA",
  cnpj: process.env.NEXT_PUBLIC_COMPANY_CNPJ?.trim() || "",
  address: {
    street: "Rua G3, Tropical 3",
    city: "Água Boa",
    state: "MT",
    zipCode: "78635-000",
    country: "Brasil",
  },
  email: "ajuda@lotoia.chat",
  supportWhatsapp: "5565996694266",
  supportWhatsappDisplay: "(65) 99669-4266",
  refundPolicyDays: 7,
  pixActivationMinutes: 10,
} as const;

export function formatCompanyAddress(): string {
  const { street, city, state, zipCode, country } = COMPANY.address;
  return `${street} — ${city} - ${state} — CEP ${zipCode} — ${country}`;
}

export function supportWhatsappUrl(): string {
  return `https://wa.me/${COMPANY.supportWhatsapp}`;
}
