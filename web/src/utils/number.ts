const amountFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

interface SanitizeOptions {
  allowNegative?: boolean;
}

const sanitizeDecimal = (value: string, options: SanitizeOptions = {}): string => {
  if (!value) {
    return '';
  }
  const { allowNegative = false } = options;
  let trimmed = value.trim();
  const isNegative = allowNegative && trimmed.startsWith('-');
  if (isNegative) {
    trimmed = trimmed.slice(1);
  }

  const allowed = trimmed.replace(/[^0-9.]/g, '');
  if (!allowed) {
    return '';
  }

  const [whole = '', ...rest] = allowed.split('.');
  const decimals = rest.join('').slice(0, 2);
  const normalizedWhole = whole.replace(/^0+(?=\d)/, '');
  const safeWhole = normalizedWhole || (decimals ? '0' : whole);
  const sanitized = decimals ? `${safeWhole}.${decimals}` : safeWhole;

  if (!sanitized) {
    return '';
  }

  return isNegative ? `-${sanitized}` : sanitized;
};

export const sanitizeAmountInput = (raw: string): string => sanitizeDecimal(raw, { allowNegative: false });

export const formatAmount = (value: string | number): string => {
  if (typeof value === 'number') {
    return Number.isNaN(value) ? '' : amountFormatter.format(value);
  }
  const sanitized = sanitizeDecimal(value, { allowNegative: true });
  if (!sanitized) {
    return '';
  }
  const numeric = Number(sanitized);
  if (Number.isNaN(numeric)) {
    return '';
  }
  const [, decimalPart] = sanitized.split('.');
  const formattedWhole = amountFormatter.format(Math.trunc(numeric));
  return decimalPart !== undefined ? `${formattedWhole}.${decimalPart}` : formattedWhole;
};
