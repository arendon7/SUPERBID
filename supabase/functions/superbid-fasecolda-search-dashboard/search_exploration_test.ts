import {
  MAX_SEARCH_VARIANTS,
  SEARCH_EXPLORATION_GUARDRAIL,
  buildSearchExplorationVariants,
  classifySearchExplorationCase,
} from "./search_exploration.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function terms(result: ReturnType<typeof buildSearchExplorationVariants>) {
  return result.variants.map((x) => x.term);
}

Deno.test("guardrail and max-variant contract stay explicit", () => {
  assert(SEARCH_EXPLORATION_GUARDRAIL === "AUTOMATED_SEARCH_VARIANT_NOT_OVERRIDE_OR_MATCH", "guardrail changed");
  assert(MAX_SEARCH_VARIANTS === 4, "matrix must remain bounded to four probes");
});

Deno.test("current and suggested Toyota terms are deduplicated", () => {
  const result = buildSearchExplorationVariants({
    title: "TOYOTA COROLLA CROSS MOD. 2023, PLACA: 4",
    brand: "TOYOTA",
    modelYear: 2023,
    currentTerm: "TOYOTA COROLLA",
    suggestedTerm: "TOYOTA COROLLA CROSS",
  });
  assert(result.disposition === "EXPLORABLE", "Toyota case should be explorable");
  const got = terms(result);
  assert(got.length === 2, `expected 2 deduped terms, got ${got.length}`);
  assert(got[0] === "TOYOTA COROLLA", "current term should stay first");
  assert(got[1] === "TOYOTA COROLLA CROSS", "suggested term should stay second");
});

Deno.test("title-prefix expansion adds a bounded extra hypothesis", () => {
  const result = buildSearchExplorationVariants({
    title: "HYUNDAI HB20S ACCENT ADVANCE AT MOD. 2024",
    brand: "HYUNDAI",
    modelYear: 2024,
    currentTerm: "HYUNDAI HB20S",
    suggestedTerm: "HYUNDAI HB20S ACCENT",
  });
  const got = terms(result);
  assert(got.includes("HYUNDAI HB20S ACCENT ADVANCE"), "expected one deeper title prefix");
  assert(!got.some((term) => term.includes(" AT")), "technical transmission token must stop expansion");
});

Deno.test("generic or contaminated brand routes to identity review", () => {
  for (const [brand, title] of [
    ["COMBO:", "COMBO: REPUESTOS + RENAULT DUSTER DYNAMIQUE 4X4 MOD. 2018"],
    ["VOLQUETA", "VOLQUETA CHEVROLET C 70 MT MOD. 1989"],
    ["AUTOMÓVIL", "AUTOMÓVIL SEDÁN COMPACTO"],
  ]) {
    const result = buildSearchExplorationVariants({ title, brand, modelYear: 2020, currentTerm: null, suggestedTerm: null });
    assert(result.disposition === "IDENTITY_INPUT_REVIEW", `${brand} should not be probed automatically`);
    assert(result.variants.length === 0, `${brand} must not generate variants`);
  }
});

Deno.test("suggested term that violates canonical brand is blocked", () => {
  const disposition = classifySearchExplorationCase({
    brand: "VOLKSWAGEN",
    modelYear: 2024,
    suggestedTerm: "TOYOTA COROLLA CROSS",
  });
  assert(disposition === "IDENTITY_INPUT_REVIEW", "brand mismatch must fail closed");
});

Deno.test("missing model year blocks exploration", () => {
  const result = buildSearchExplorationVariants({
    title: "CAMIÓN MEDIANO DE CARGA Ubic.: Bogotá",
    brand: "FOTON",
    modelYear: null,
    currentTerm: null,
    suggestedTerm: "FOTON AUMAN",
  });
  assert(result.disposition === "MISSING_YEAR", "missing year should route out of search exploration");
  assert(result.variants.length === 0, "missing year must not generate probes");
});

Deno.test("long titles never exceed four deterministic variants", () => {
  const result = buildSearchExplorationVariants({
    title: "RENAULT NUEVA DUSTER ZEN INTENS PLUS PREMIUM 4X2 MT 1600 CC MOD. 2023",
    brand: "RENAULT",
    modelYear: 2023,
    currentTerm: "RENAULT NUEVA",
    suggestedTerm: "RENAULT NUEVA DUSTER",
  });
  assert(result.disposition === "EXPLORABLE", "Renault should be explorable");
  assert(result.variants.length <= MAX_SEARCH_VARIANTS, "probe matrix exceeded bounded size");
  assert(new Set(terms(result)).size === result.variants.length, "variants must be unique");
});
