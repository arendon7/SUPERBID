export const IDENTITY_HINT_GUARDRAIL = "AUTOMATED_IDENTITY_HINT_NOT_HUMAN_EVIDENCE_OR_MATCH";
export const ENGINE_CC_NOMINAL_TOLERANCE = 50;

export type IdentityHints = {
  engineCc: number | null;
  transmission: "MANUAL" | "AUTOMATIC" | null;
  drivetrain: "4X4_AWD" | "4X2_2WD" | null;
  fuel: "GASOLINE" | "DIESEL" | "HYBRID" | "ELECTRIC" | "CNG" | null;
};

export type HintComparisonStatus = "CONSISTENT" | "NOMINAL_COMPATIBLE" | "DIFFERS" | "LOT_UNKNOWN" | "CANDIDATE_UNKNOWN";
export type HintComparison = {
  lot: string | number | null;
  candidate: string | number | null;
  status: HintComparisonStatus;
};

const ENGINE_CC_RE = /\b(\d{3,5})\s*CC\b/gi;
const MANUAL_TRANSMISSION_RE = /\b(?:MT|MANUAL|MEC[ÁA]NIC[AO])\b/i;
const AUTOMATIC_TRANSMISSION_RE = /\b(?:AT|TP|CVT|DCT|DSG|AUT|AUTOM[ÁA]TIC[AO])\b/i;
const DRIVE_4X4_RE = /\b(?:4\s*[Xx]\s*4|4WD|AWD)\b/i;
const DRIVE_4X2_RE = /\b(?:4\s*[Xx]\s*2|2WD)\b/i;
const HYBRID_RE = /\b(?:H[IÍ]BRID[AO]|HYBRID|HEV|PHEV)\b/i;
const ELECTRIC_RE = /\b(?:EL[EÉ]CTRIC[AO]|ELECTRIC|EV|BEV)\b/i;
const DIESEL_RE = /\b(?:DI[EÉ]SEL|DIESEL)\b/i;
const CNG_RE = /\b(?:GNV|GNC|CNG|GAS\s+NATURAL)\b/i;
const GASOLINE_RE = /\b(?:GASOLINA|GASOLINE|PETROL)\b/i;

function uniqueEngineCc(text: string): number | null {
  const values = new Set<number>();
  for (const match of text.matchAll(ENGINE_CC_RE)) values.add(Number(match[1]));
  return values.size === 1 ? [...values][0] : null;
}

function exclusiveFlag<T extends string>(text: string, rules: Array<[T, RegExp]>): T | null {
  const values = new Set<T>();
  for (const [label, pattern] of rules) if (pattern.test(text)) values.add(label);
  return values.size === 1 ? [...values][0] : null;
}

function fuelHint(text: string): IdentityHints["fuel"] {
  if (HYBRID_RE.test(text)) return "HYBRID";
  if (ELECTRIC_RE.test(text)) return "ELECTRIC";
  return exclusiveFlag(text, [
    ["DIESEL", DIESEL_RE],
    ["CNG", CNG_RE],
    ["GASOLINE", GASOLINE_RE],
  ]);
}

export function extractVehicleIdentityHints(value: unknown): IdentityHints {
  const text = String(value ?? "");
  return {
    engineCc: uniqueEngineCc(text),
    transmission: exclusiveFlag(text, [
      ["MANUAL", MANUAL_TRANSMISSION_RE],
      ["AUTOMATIC", AUTOMATIC_TRANSMISSION_RE],
    ]),
    drivetrain: exclusiveFlag(text, [
      ["4X4_AWD", DRIVE_4X4_RE],
      ["4X2_2WD", DRIVE_4X2_RE],
    ]),
    fuel: fuelHint(text),
  };
}

function compareOne(lot: string | number | null, candidate: string | number | null): HintComparison {
  if (lot == null) return { lot, candidate, status: "LOT_UNKNOWN" };
  if (candidate == null) return { lot, candidate, status: "CANDIDATE_UNKNOWN" };
  return { lot, candidate, status: lot === candidate ? "CONSISTENT" : "DIFFERS" };
}

function compareEngineCc(lot: number | null, candidate: number | null): HintComparison {
  if (lot == null) return { lot, candidate, status: "LOT_UNKNOWN" };
  if (candidate == null) return { lot, candidate, status: "CANDIDATE_UNKNOWN" };
  if (lot === candidate) return { lot, candidate, status: "CONSISTENT" };
  if (Math.abs(lot - candidate) <= ENGINE_CC_NOMINAL_TOLERANCE) {
    return { lot, candidate, status: "NOMINAL_COMPATIBLE" };
  }
  return { lot, candidate, status: "DIFFERS" };
}

export function compareVehicleIdentityHints(lotText: unknown, candidateText: unknown) {
  const lot = extractVehicleIdentityHints(lotText);
  const candidate = extractVehicleIdentityHints(candidateText);
  return {
    engine_cc: compareEngineCc(lot.engineCc, candidate.engineCc),
    transmission: compareOne(lot.transmission, candidate.transmission),
    drivetrain: compareOne(lot.drivetrain, candidate.drivetrain),
    fuel: compareOne(lot.fuel, candidate.fuel),
  };
}
