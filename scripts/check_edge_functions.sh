#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUNCTIONS_DIR="$ROOT/supabase/functions"

if ! command -v deno >/dev/null 2>&1; then
  echo "::error::Deno is required to validate Supabase Edge Functions."
  exit 127
fi

if [[ ! -d "$FUNCTIONS_DIR" ]]; then
  echo "::error::Supabase functions directory not found: $FUNCTIONS_DIR"
  exit 1
fi

mapfile -t ENTRYPOINTS < <(
  find "$FUNCTIONS_DIR" -mindepth 2 -maxdepth 2 -type f -name index.ts -print | sort
)

if [[ ${#ENTRYPOINTS[@]} -eq 0 ]]; then
  echo "::error::No Supabase Edge Function index.ts entrypoints were discovered."
  exit 1
fi

mapfile -t FUNCTION_DIRS < <(
  find "$FUNCTIONS_DIR" -mindepth 1 -maxdepth 1 -type d -print | sort
)

if [[ ${#ENTRYPOINTS[@]} -ne ${#FUNCTION_DIRS[@]} ]]; then
  echo "::error::Every immediate Supabase function directory must contain exactly one index.ts entrypoint. Found ${#FUNCTION_DIRS[@]} directories and ${#ENTRYPOINTS[@]} entrypoints."
  exit 1
fi

mapfile -t DENO_TESTS < <(
  find "$FUNCTIONS_DIR" -mindepth 2 -type f -name '*_test.ts' -print | sort
)

printf 'Deno: '
deno --version | head -n 1
echo "Discovered ${#ENTRYPOINTS[@]} Supabase Edge Function entrypoints."

for entrypoint in "${ENTRYPOINTS[@]}"; do
  relative="${entrypoint#$ROOT/}"
  function_name="$(basename "$(dirname "$entrypoint")")"
  echo "::group::Edge compile · $function_name"
  echo "Checking $relative"
  if ! deno check --quiet "$entrypoint"; then
    echo "::endgroup::"
    echo "::error file=$relative::Deno type/syntax check failed for Edge Function $function_name"
    exit 1
  fi
  echo "PASS $relative"
  echo "::endgroup::"
done

if [[ ${#DENO_TESTS[@]} -gt 0 ]]; then
  echo "Discovered ${#DENO_TESTS[@]} Deno Edge unit test file(s)."
  for test_file in "${DENO_TESTS[@]}"; do
    relative="${test_file#$ROOT/}"
    echo "::group::Edge unit test · $relative"
    if ! deno test --quiet "$test_file"; then
      echo "::endgroup::"
      echo "::error file=$relative::Deno unit tests failed"
      exit 1
    fi
    echo "PASS $relative"
    echo "::endgroup::"
  done
else
  echo "No Deno Edge unit tests discovered."
fi

echo "All ${#ENTRYPOINTS[@]} Supabase Edge Functions passed deno check; ${#DENO_TESTS[@]} Deno unit test file(s) passed."
