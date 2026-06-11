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

export function normalizeCpfCnpj(value: string): string {
  return value.replace(/\D/g, "");
}

function hasRepeatedDigits(digits: string): boolean {
  return /^(\d)\1+$/.test(digits);
}

function isValidCpfChecksum(digits: string): boolean {
  let sum = 0;
  for (let index = 0; index < 9; index += 1) {
    sum += Number(digits[index]) * (10 - index);
  }
  let remainder = (sum * 10) % 11;
  if (remainder === 10) {
    remainder = 0;
  }
  if (remainder !== Number(digits[9])) {
    return false;
  }

  sum = 0;
  for (let index = 0; index < 10; index += 1) {
    sum += Number(digits[index]) * (11 - index);
  }
  remainder = (sum * 10) % 11;
  if (remainder === 10) {
    remainder = 0;
  }
  return remainder === Number(digits[10]);
}

function isValidCnpjChecksum(digits: string): boolean {
  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let index = 0; index < 12; index += 1) {
    sum += Number(digits[index]) * weights1[index];
  }
  let remainder = sum % 11;
  const digit1 = remainder < 2 ? 0 : 11 - remainder;
  if (digit1 !== Number(digits[12])) {
    return false;
  }

  sum = 0;
  for (let index = 0; index < 13; index += 1) {
    sum += Number(digits[index]) * weights2[index];
  }
  remainder = sum % 11;
  const digit2 = remainder < 2 ? 0 : 11 - remainder;
  return digit2 === Number(digits[13]);
}

export function isValidCpf(value: string): boolean {
  const digits = normalizeCpfCnpj(value);
  if (digits.length !== 11 || hasRepeatedDigits(digits)) {
    return false;
  }
  return isValidCpfChecksum(digits);
}

export function isValidCnpj(value: string): boolean {
  const digits = normalizeCpfCnpj(value);
  if (digits.length !== 14 || hasRepeatedDigits(digits)) {
    return false;
  }
  return isValidCnpjChecksum(digits);
}

export function isValidCpfCnpj(value: string): boolean {
  const digits = normalizeCpfCnpj(value);
  if (digits.length === 11) {
    return isValidCpf(digits);
  }
  if (digits.length === 14) {
    return isValidCnpj(digits);
  }
  return false;
}
