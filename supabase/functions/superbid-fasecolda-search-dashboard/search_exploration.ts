export const SEARCH_EXPLORATION_GUARDRAIL = "AUTOMATED_SEARCH_VARIANT_NOT_OVERRIDE_OR_MATCH";
export const MAX_SEARCH_VARIANTS = 4;

export type SearchExplorationDisposition =
  | "EXPLORABLE"
  | "IDENTITY_INPUT_REVIEW"
  | "MISSING_YEAR";

export type SearchVariant = {
  term: string;
  origin: "CURRENT" | "SUGGESTED" | "TITLE_PREFIX";
};

const TECHNICAL_STOP = new Set([
  "CC", "MT", "AT", "TP", "TD", "ABS", "4X2", "4X4", "RWD", "AWD",
  "MEC", "AUT", "AUTOMATICO", "MECANICO", "PLACA", "RP", "UBIC", "MOD",
  "MODELO", "GASOLINA", "DIESEL", "ELECTRICO", "ELECTRICA", "HIBRIDO", "HIBRIDA",
]);

const GENERIC_BRANDS = new Set([
  "COMBO", "AUTOMOVIL", "CAMION", "CAMIONETA", "VEHICULO", "VOLQUETA",
  "TRACTOCAMION", "TRACTOMULA", "BUS", "MICROBUS",
]);

function norm(value: unknown): string {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function normalizeTerm(value: unknown): string {
  return norm(value).slice(0, 80).trim();
}

function preservesBrand(term: string, brand: string): boolean {
  return term === brand || term.startsWith(`${brand} `);
}

export function classifySearchExplorationCase(input: {
  brand: unknown;
  modelYear: unknown;
  suggestedTerm: unknown;
}): SearchExplorationDisposition {
  const brand = norm(input.brand);
  const suggested = normalizeTerm(input.suggestedTerm);
  const modelYear = Number(input.modelYear);

  if (!Number.isInteger(modelYear) || modelYear < 1900 || modelYear > 2100) return "MISSING_YEAR";
  if (!brand || GENERIC_BRANDS.has(brand)) return "IDENTITY_INPUT_REVIEW";
  if (suggested && !preservesBrand(suggested, brand)) return "IDENTITY_INPUT_REVIEW";
  return "EXPLORABLE";
}

function titlePrefixTerms(title: unknown, brand: string): string[] {
  const normalizedTitle = norm(String(title ?? "").replace(/\[[^\]]+\]/g, " "));
  if (!normalizedTitle) return [];

  const beforeMod = normalizedTitle.split(/\s+MOD(?:ELO)?\b/, 1)[0] || normalizedTitle;
  const tokens = beforeMod.split(" ").filter(Boolean);
  const brandTokens = brand.split(" ").filter(Boolean);
  if (brandTokens.length === 0) return [];

  let start = -1;
  for (let i = 0; i <= tokens.length - brandTokens.length; i++) {
    if (brandTokens.every((token, j) => tokens[i + j] === token)) {
      start = i;
      break;
    }
  }
  if (start < 0) return [];

  const result: string[] = [];
  const prefix = tokens.slice(start, start + brandTokens.length);
  for (let i = start + brandTokens.length; i < tokens.length; i++) {
    const token = tokens[i];
    if (TECHNICAL_STOP.has(token) || /^\d{3,5}$/.test(token)) break;
    prefix.push(token);
    if (prefix.length > brandTokens.length) result.push(prefix.join(" "));
    if (prefix.length >= brandTokens.length + 4) break;
  }
  return result;
}

export function buildSearchExplorationVariants(input: {
  title: unknown;
  brand: unknown;
  modelYear: unknown;
  currentTerm: unknown;
  suggestedTerm: unknown;
}): { disposition: SearchExplorationDisposition; variants: SearchVariant[] } {
  const brand = norm(input.brand);
  const disposition = classifySearchExplorationCase({
    brand: input.brand,
    modelYear: input.modelYear,
    suggestedTerm: input.suggestedTerm,
  });
  if (disposition !== "EXPLORABLE") return { disposition, variants: [] };

  const out: SearchVariant[] = [];
  const seen = new Set<string>();
  const add = (raw: unknown, origin: SearchVariant["origin"]) => {
    const term = normalizeTerm(raw);
    if (!term || term.length < 2 || !preservesBrand(term, brand) || seen.has(term)) return;
    seen.add(term);
    out.push({ term, origin });
  };

  add(input.currentTerm, "CURRENT");
  add(input.suggestedTerm, "SUGGESTED");
  for (const term of titlePrefixTerms(input.title, brand)) add(term, "TITLE_PREFIX");

  return { disposition, variants: out.slice(0, MAX_SEARCH_VARIANTS) };
}
