#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_dir="$root_dir/skill/esc-project-ideation"

required_files=(
  "$root_dir/README.md"
  "$root_dir/NOTICE.md"
  "$skill_dir/SKILL.md"
  "$skill_dir/agents/openai.yaml"
  "$skill_dir/references/esc-context.md"
  "$skill_dir/references/esc-method-routing.md"
  "$skill_dir/references/esc-ideation-rubric.md"
  "$skill_dir/references/esc-output-templates.md"
  "$skill_dir/references/hermes-attribution.md"
  "$root_dir/docs/SMOKE_TEST.md"
)

for file_path in "${required_files[@]}"; do
  test -f "$file_path" || { printf 'missing: %s\n' "$file_path" >&2; exit 1; }
done

method_count="$(find "$skill_dir/references/methods" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
test "$method_count" = "22" || { printf 'expected 22 methods, found %s\n' "$method_count" >&2; exit 1; }

if command -v rg >/dev/null 2>&1 && rg -n 'TODO|Structuring This Skill' "$skill_dir"; then
  printf 'unfinished template markers found\n' >&2
  exit 1
fi

printf 'ESC Project Ideation bundle is structurally valid (%s method files).\n' "$method_count"

