const MIN_WHATSAPP_DIGITS = 10;
const MAX_WHATSAPP_DIGITS = 13;

export function normalizeWhatsapp(value: string): string {
  return value.replace(/\D/g, "");
}

export function isValidBrazilianWhatsapp(value: string): boolean {
  const digits = normalizeWhatsapp(value);
  if (digits.length < MIN_WHATSAPP_DIGITS || digits.length > MAX_WHATSAPP_DIGITS) {
    return false;
  }
  if (digits.startsWith("55")) {
    const local = digits.slice(2);
    return local.length === 10 || local.length === 11;
  }
  return digits.length === 10 || digits.length === 11;
}

export function canonicalWhatsapp(value: string): string {
  const digits = normalizeWhatsapp(value);
  if (digits.startsWith("55")) {
    return digits;
  }
  if (digits.length === 10 || digits.length === 11) {
    return `55${digits}`;
  }
  return digits;
}
