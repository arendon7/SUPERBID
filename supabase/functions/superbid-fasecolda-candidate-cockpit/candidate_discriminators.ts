import { extractVehicleIdentityHints, type IdentityHints } from "./identity_hints.ts";

export const CANDIDATE_DISCRIMINATOR_GUARDRAIL = "CANDIDATE_DISCRIMINATOR_MAP_NOT_EVIDENCE_OR_RECOMMENDATION";
export const MAX_LITERAL_DELTA_TOKENS = 12;

export type CandidateForDiscriminatorMap = {
  code: string;
  description: string;
};

export type StructuredDiscriminatorKey = "engine_cc" | "transmission" | "drivetrain" | "fuel";

export type CandidateDiscriminatorEntry = {
  code: string;
  normalizedDescription: string;
  structuredValues: Record<StructuredDiscriminatorKey, string | number | null>;
  literalDeltaTokens: string[];
  duplicateDescriptionGroupSize: number;
  indistinguishableByDescription: boolean;
};

export type CandidateDiscriminatorMap = {
  structuredDiscriminators: StructuredDiscriminatorKey[];
  entries: CandidateDiscriminatorEntry[];
  duplicateDescriptionGroupCount: number;
  candidatesInDuplicateDescriptionGroups: number;
  hasIndistinguishableDescriptions: boolean;
};

const STRUCTURED_KEYS: StructuredDiscriminatorKey[] = ["engine_cc", "transmission", "drivetrain", "fuel"];

function normalizeText(value: unknown): string {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function normalizedDescription(value: unknown): string {
  return normalizeText(value);
}

function literalTokens(value: unknown): string[] {
  const normalized = normalizeText(value);
  if (!normalized) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const token of normalized.split(" ")) {
    if (!token || seen.has(token)) continue;
    seen.add(token);
    out.push(token);
  }
  return out;
}

function structuredValues(hints: IdentityHints): Record<StructuredDiscriminatorKey, string | number | null> {
  return {
    engine_cc: hints.engineCc,
    transmission: hints.transmission,
    drivetrain: hints.drivetrain,
    fuel: hints.fuel,
  };
}

export function buildCandidateDiscriminatorMap(candidates: CandidateForDiscriminatorMap[]): CandidateDiscriminatorMap {
  const source = candidates.map((candidate) => ({
    code: String(candidate.code ?? "").trim(),
    description: String(candidate.description ?? ""),
    normalizedDescription: normalizedDescription(candidate.description),
    hints: structuredValues(extractVehicleIdentityHints(candidate.description)),
    tokens: literalTokens(candidate.description),
  }));

  const structuredDiscriminators = STRUCTURED_KEYS.filter((key) => {
    const known = new Set<string>();
    for (const candidate of source) {
      const value = candidate.hints[key];
      if (value != null) known.add(String(value));
    }
    return known.size > 1;
  });

  const tokenPresence = new Map<string, number>();
  for (const candidate of source) {
    for (const token of candidate.tokens) tokenPresence.set(token, (tokenPresence.get(token) || 0) + 1);
  }

  const descriptionCounts = new Map<string, number>();
  for (const candidate of source) {
    const key = candidate.normalizedDescription;
    descriptionCounts.set(key, (descriptionCounts.get(key) || 0) + 1);
  }

  const duplicateGroups = [...descriptionCounts.values()].filter((count) => count > 1);
  const duplicateDescriptionGroupCount = duplicateGroups.length;
  const candidatesInDuplicateDescriptionGroups = duplicateGroups.reduce((sum, count) => sum + count, 0);

  const entries = source.map((candidate) => {
    const groupSize = descriptionCounts.get(candidate.normalizedDescription) || 1;
    const literalDeltaTokens = candidate.tokens
      .filter((token) => (tokenPresence.get(token) || 0) < source.length)
      .slice(0, MAX_LITERAL_DELTA_TOKENS);
    return {
      code: candidate.code,
      normalizedDescription: candidate.normalizedDescription,
      structuredValues: candidate.hints,
      literalDeltaTokens,
      duplicateDescriptionGroupSize: groupSize,
      indistinguishableByDescription: groupSize > 1,
    };
  });

  return {
    structuredDiscriminators,
    entries,
    duplicateDescriptionGroupCount,
    candidatesInDuplicateDescriptionGroups,
    hasIndistinguishableDescriptions: duplicateDescriptionGroupCount > 0,
  };
}
