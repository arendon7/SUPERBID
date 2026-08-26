import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// v0.52 compatibility shim.
// The legacy resolver used dashboard_set_fasecolda_manual_resolution directly.
// That write surface is intentionally retired: candidate confirmation now requires
// source-bound structured evidence in superbid-fasecolda-candidate-cockpit.
// This function preserves only validated numeric lot context and performs no business write.

function safeLot(v: unknown) {
  const lot=String(v??"").trim();
  return /^\d{5,12}$/.test(lot)?lot:"";
}

Deno.serve((req: Request) => {
  const u=new URL(req.url);
  const lot=safeLot(u.searchParams.get("lot"));
  const target=lot
    ? `/functions/v1/superbid-fasecolda-candidate-cockpit/lots/${encodeURIComponent(lot)}`
    : "/functions/v1/superbid-fasecolda-candidate-cockpit";

  return new Response(null,{
    status:303,
    headers:{
      location:target,
      "cache-control":"no-store",
      "x-superbid-guardrail":"LEGACY_FASECOLDA_RESOLVER_REDIRECT_NO_BUSINESS_WRITE",
    },
  });
});
