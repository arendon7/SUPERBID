import {
  CANDIDATE_DISCRIMINATOR_GUARDRAIL,
  MAX_LITERAL_DELTA_TOKENS,
  buildCandidateDiscriminatorMap,
} from "./candidate_discriminators.ts";

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

Deno.test("guardrail and bounded literal delta contract stay explicit", () => {
  assert(CANDIDATE_DISCRIMINATOR_GUARDRAIL === "CANDIDATE_DISCRIMINATOR_MAP_NOT_EVIDENCE_OR_RECOMMENDATION", "guardrail changed");
  assert(MAX_LITERAL_DELTA_TOKENS === 12, "literal delta bound changed");
});

Deno.test("structured discriminators require two distinct known values", () => {
  const map = buildCandidateDiscriminatorMap([
    { code: "A", description: "TOYOTA HILUX MT 2500CC 4X4 TD" },
    { code: "B", description: "TOYOTA HILUX MT 2500CC 4X2 TD" },
    { code: "C", description: "TOYOTA HILUX AT 3000CC 4X4 TD" },
  ]);
  assert(map.structuredDiscriminators.includes("engine_cc"), "engine should discriminate");
  assert(map.structuredDiscriminators.includes("transmission"), "transmission should discriminate");
  assert(map.structuredDiscriminators.includes("drivetrain"), "drivetrain should discriminate");
});

Deno.test("unknown structured values do not become artificial discriminators", () => {
  const map = buildCandidateDiscriminatorMap([
    { code: "A", description: "RENAULT OROCH CARGO" },
    { code: "B", description: "RENAULT OROCH ZEN MT 1300CC" },
  ]);
  assert(!map.structuredDiscriminators.includes("engine_cc"), "one known engine is not a discriminator");
  assert(!map.structuredDiscriminators.includes("transmission"), "one known transmission is not a discriminator");
});

Deno.test("literal deltas expose trim and use tokens without choosing a winner", () => {
  const map = buildCandidateDiscriminatorMap([
    { code: "A", description: "RENAULT OROCH CARGO MT 1300CC 4X4" },
    { code: "B", description: "RENAULT OROCH ZEN MT 1300CC 4X4" },
    { code: "C", description: "RENAULT OROCH INTENS OUTSIDER MT 1300CC 4X4" },
  ]);
  const a = map.entries.find((entry) => entry.code === "A")!;
  const b = map.entries.find((entry) => entry.code === "B")!;
  const c = map.entries.find((entry) => entry.code === "C")!;
  assert(a.literalDeltaTokens.includes("CARGO"), "CARGO delta missing");
  assert(b.literalDeltaTokens.includes("ZEN"), "ZEN delta missing");
  assert(c.literalDeltaTokens.includes("INTENS") && c.literalDeltaTokens.includes("OUTSIDER"), "trim deltas missing");
  assert(!("winner" in map) && !("recommendedCandidate" in map) && !("score" in map), "helper must not recommend a candidate");
});

Deno.test("duplicate normalized descriptions are grouped as indistinguishable", () => {
  const map = buildCandidateDiscriminatorMap([
    { code: "A", description: "CHEVROLET NKR MT 3000CC 4X2" },
    { code: "B", description: "  Chevrolet NKR   MT 3000CC 4X2 " },
    { code: "C", description: "CHEVROLET NKR LWB MT 3000CC 4X2" },
  ]);
  assert(map.hasIndistinguishableDescriptions, "duplicate warning missing");
  assert(map.duplicateDescriptionGroupCount === 1, "wrong duplicate group count");
  assert(map.candidatesInDuplicateDescriptionGroups === 2, "wrong duplicate row count");
  assert(map.entries[0].indistinguishableByDescription && map.entries[1].indistinguishableByDescription, "duplicate entries not marked");
  assert(!map.entries[2].indistinguishableByDescription, "unique entry incorrectly marked");
});

Deno.test("candidate order is preserved and token deltas are deterministic and bounded", () => {
  const long = Array.from({ length: 30 }, (_, i) => `TRIM${i}`).join(" ");
  const map = buildCandidateDiscriminatorMap([
    { code: "Z", description: `FORD RANGER ${long}` },
    { code: "A", description: "FORD RANGER BASE" },
  ]);
  assert(map.entries.map((entry) => entry.code).join(",") === "Z,A", "candidate order changed");
  assert(map.entries[0].literalDeltaTokens.length === MAX_LITERAL_DELTA_TOKENS, "literal delta bound not enforced");
  const second = buildCandidateDiscriminatorMap([
    { code: "Z", description: `FORD RANGER ${long}` },
    { code: "A", description: "FORD RANGER BASE" },
  ]);
  assert(JSON.stringify(map) === JSON.stringify(second), "map is not deterministic");
});

Deno.test("fuel only discriminates when multiple known propulsion values exist", () => {
  const map = buildCandidateDiscriminatorMap([
    { code: "A", description: "KIA NIRO HYBRID AT" },
    { code: "B", description: "KIA NIRO ELECTRIC AT" },
    { code: "C", description: "KIA NIRO AT" },
  ]);
  assert(map.structuredDiscriminators.includes("fuel"), "known HYBRID/ELECTRIC difference should discriminate");
});
