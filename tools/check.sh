#!/usr/bin/env bash
# Runs the given make targets in parallel and prints a summary. Shows output only for the ones that failed.
# Usage: tools/check.sh lint-js unit-js ...   (normally via `make test`)
set -u
log=$(mktemp -d "${TMPDIR:-/tmp}/soundboard-check.XXXXXX") || exit 1
trap 'rm -rf "$log"' EXIT
start=$(date +%s)

echo "Running in parallel: $*"
for t in "$@"; do
  (
    s=$(date +%s)
    make --no-print-directory "$t" >"$log/$t.out" 2>&1
    echo "$? $(($(date +%s) - s))" >"$log/$t.rc"
  ) &
done
wait

failed=0
for t in "$@"; do
  read -r rc _ <"$log/$t.rc"
  if [ "$rc" -ne 0 ]; then
    failed=$((failed + 1))
    printf '\n\033[31m── %s ──\033[0m\n' "$t"
    cat "$log/$t.out"
  fi
done

echo
for t in "$@"; do
  read -r rc sec <"$log/$t.rc"
  if [ "$rc" -eq 0 ]; then mark='\033[32m✔\033[0m'; else mark='\033[31m✘\033[0m'; fi
  printf "  $mark %-9s %3ss\n" "$t" "$sec"
done

total=$(($(date +%s) - start))
if [ "$failed" -eq 0 ]; then
  printf '\n\033[32mAll passed\033[0m (%d checks, %ds)\n' "$#" "$total"
else
  printf '\n\033[31m%d of %d failed\033[0m (%ds)\n' "$failed" "$#" "$total"
  exit 1
fi
