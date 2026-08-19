/**
 * formatMoney
 *
 * Renders a monetary amount with thousands separators and a fixed
 * 2-decimal-place format, e.g. 10000 -> "10,000.00", "6000.5" -> "6,000.50".
 * Accepts numbers, numeric strings (including what the API sends for
 * Decimal fields), null/undefined (renders as "0.00").
 */
const formatter = new Intl.NumberFormat("en-PH", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatMoney(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "0.00";
  return formatter.format(n);
}

/**
 * formatNumber
 *
 * Same thousands-separator treatment but without forcing 2 decimals --
 * for quantities/counts (e.g. stock on hand) where "62" should stay
 * "62", not "62.00", while "1234" still renders as "1,234".
 */
const plainFormatter = new Intl.NumberFormat("en-PH", {
  maximumFractionDigits: 4,
});

export function formatNumber(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "0";
  return plainFormatter.format(n);
}
