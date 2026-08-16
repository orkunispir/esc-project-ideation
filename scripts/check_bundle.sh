#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_dir="$root_dir/skill/esc-project-ideation"

required_files=(
  "$root_dir/README.md"
  "$root_dir/NOTICE.md"
  "$root_dir/.gitignore"
  "$root_dir/.env.example"
  "$root_dir/docs/CONFIG.example.md"
  "$root_dir/docs/IMPLEMENTATION_PLAN.md"
  "$root_dir/docs/SUPABASE_INTEGRATION.md"
  "$root_dir/docs/SMOKE_TEST.md"
  "$root_dir/.github/workflows/validate.yml"
  "$root_dir/scripts/check_bundle.sh"
  "$skill_dir/SKILL.md"
  "$skill_dir/agents/openai.yaml"
  "$skill_dir/references/esc-context.md"
  "$skill_dir/references/esc-method-routing.md"
  "$skill_dir/references/esc-ideation-rubric.md"
  "$skill_dir/references/esc-output-templates.md"
  "$skill_dir/references/hermes-attribution.md"
  "$skill_dir/references/supabase-retrieval.md"
  "$skill_dir/scripts/search_esc.py"
  "$root_dir/tests/test_search_esc.py"
  "$root_dir/supabase/schema.sql"
  "$root_dir/supabase/config.toml"
  "$root_dir/supabase/functions/esc-search/index.ts"
  "$root_dir/supabase/functions/esc-search/request.ts"
  "$root_dir/supabase/functions/esc-search/admin.ts"
  "$root_dir/supabase/functions/esc-indexer/index.ts"
  "$root_dir/supabase/tests/request_test.ts"
)

missing=0
for file_path in "${required_files[@]}"; do
  if [[ ! -f "$file_path" ]]; then
    printf 'missing required file: %s\n' "${file_path#"$root_dir/"}" >&2
    missing=1
  fi
done
test "$missing" = "0" || exit 1

method_count="$(find "$skill_dir/references/methods" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
test "$method_count" = "22" || {
  printf 'expected 22 methods, found %s\n' "$method_count" >&2
  exit 1
}

if command -v rg >/dev/null 2>&1; then
  if rg -n 'TODO|Structuring This Skill' "$skill_dir"; then
    printf 'unfinished template markers found\n' >&2
    exit 1
  fi

  secret_patterns=(
    'https://[^[:space:]]*supabase\.com/dashboard/project/[A-Za-z0-9_-]{8,}'
    'https://[A-Za-z0-9_-]{20,}\.supabase\.co/functions/v1/'
    'https://[A-Za-z0-9_-]{20,}\.supabase\.co'
    'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{20,}'
    'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
  )
  for pattern in "${secret_patterns[@]}"; do
    if rg -n --hidden --glob '!.git/**' "$pattern" "$root_dir"; then
      printf 'public-boundary pattern matched: %s\n' "$pattern" >&2
      exit 1
    fi
  done

  rg -q 'results_platform_project_card' "$root_dir/supabase/schema.sql"
  rg -q 'results_platform_project_card' "$skill_dir/scripts/search_esc.py"
  rg -q 'MAX_MATCH_COUNT = 20' "$root_dir/supabase/functions/esc-search/request.ts"
  rg -q 'MAX_QUERY_LENGTH = 1000' "$skill_dir/scripts/search_esc.py"
fi

printf 'ESC Project Ideation bundle is structurally valid (%s method files; implementation snapshot present).\n' "$method_count"
