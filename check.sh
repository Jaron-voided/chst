#!/usr/bin/env bash
# check.sh: the acceptance runner (ACCEPTANCE.md §1).
#
#   ./check.sh                 fast mode: every applicable ID except the full-only and done-only ones
#   ./check.sh --full          full mode: also the full-only IDs
#   ./check.sh --done RUN-ID   import every ID's status from the CI run's three reports, then run AC-XP-1
#   ./check.sh --only ID,ID    only the named IDs (development aid); every other ID is NOT RUN
#   ./check.sh --list-ids      print every acceptance ID
#   ./check.sh --self-test     run the harness's own self-test IDs (AC-META-7)
#
# Before any ID, fast, full and --only runs run the TODO coverage preflight (tools/todo_coverage.py).
#
# Every applicable ID runs its script, tools/acceptance/checks/<ID>.sh, under `bash -euo pipefail`
# in a fresh $W. Statuses and exit codes are those of ACCEPTANCE.md §1.1. N/A comes only from two
# facts read from ACCEPTANCE.md: CURRENT_CUT (§2) and each ID's OS line. A missing check script, a
# check that can't run and a failed build are all FAIL, never N/A.
#
# Written for bash 3.2 (the macOS default): no associative arrays, no mapfile.

set -euo pipefail
cd "$(dirname "$0")"

OUT=target/acceptance
LOGS=$OUT/logs
CHECKS=tools/acceptance/checks

case "$(uname -s)" in
  Linux*) CHST_OS=linux ;;
  Darwin*) CHST_OS=macos ;;
  MINGW* | MSYS* | CYGWIN*) CHST_OS=windows ;;
  *) CHST_OS=unknown ;;
esac
EXE=""
if [ "$CHST_OS" = windows ]; then EXE=.exe; fi

usage() {
  echo "usage: ./check.sh [--full | --done CI-RUN-ID | --only ID,ID | --list-ids | --self-test]" >&2
  exit 64
}

list_ids() {
  grep -oE '^#### AC-[A-Z0-9-]+' ACCEPTANCE.md | cut -c6-
}

MODE=fast
ONLY=""
DONE_ID=""
MODE_SET=0
set_mode() {
  if [ "$MODE_SET" = 1 ]; then usage; fi
  MODE=$1
  MODE_SET=1
}
while [ $# -gt 0 ]; do
  case "$1" in
    --full) set_mode full ;;
    --only)
      [ $# -ge 2 ] || usage
      set_mode only
      ONLY=$2
      shift
      ;;
    --done)
      [ $# -ge 2 ] || usage
      case "$2" in '' | *[!0-9]*) usage ;; esac
      set_mode done
      DONE_ID=$2
      shift
      ;;
    --list-ids) set_mode list-ids ;;
    --self-test) set_mode self-test ;;
    *) usage ;;
  esac
  shift
done

if [ "$MODE" = list-ids ]; then
  list_ids
  exit 0
fi

# Per-ID facts from ACCEPTANCE.md: id, tier (core|extended), OS list, kind (fast|full|done).
META=$(awk '
  /^#### AC-/ {
    id = $2; getline; line = $0
    tier = (line ~ /^Extended/) ? "extended" : "core"
    os = line; sub(/^.*OS /, "", os); sub(/ ·.*$/, "", os); gsub(/ /, "", os)
    kind = (line ~ /full-only/) ? "full" : (line ~ /done-only/) ? "done" : "fast"
    print id "\t" tier "\t" os "\t" kind
  }' ACCEPTANCE.md)
CUT=$(sed -n 's/^CURRENT_CUT = //p' ACCEPTANCE.md | head -1 | tr 'A-Z' 'a-z')
case "$CUT" in core | extended) ;; *)
  echo "check.sh: can't read CURRENT_CUT from ACCEPTANCE.md" >&2
  exit 1
  ;;
esac

if [ "$MODE" = only ]; then
  for id in $(echo "$ONLY" | tr ',' ' '); do
    if ! list_ids | grep -qx "$id"; then
      echo "check.sh: unknown ID $id" >&2
      exit 64
    fi
  done
fi

rm -f "$OUT/report.json"
mkdir -p "$LOGS"
RES=$(mktemp)
trap 'rm -f "$RES"' EXIT

# Preflight: TODO.md must assign every acceptance ID to exactly one task. It's a harness check, not
# an acceptance ID, so it isn't in --list-ids or in the results. It also runs under --only, so the
# log exists after a development run.
if [ "$MODE" != self-test ] && [ "$MODE" != done ]; then
  if ! python3.14 -I tools/todo_coverage.py > "$LOGS/todo-coverage.log" 2>&1; then
    echo "check.sh: TODO coverage preflight failed:" >&2
    cat "$LOGS/todo-coverage.log" >&2
    exit 1
  fi
fi

# --- build, done once and only when a script needs $CHST or $CHST_CORE ---
BUILD=none # none | ok | failed
CHST_VAR='\$\{?CHST(_CORE)?([^A-Za-z0-9_]|$)'
ensure_build() {
  if [ "$BUILD" != none ]; then return 0; fi
  if [ ! -f Cargo.toml ]; then
    BUILD=ok # nothing to build yet; a script that needs the binary fails on its own
    return 0
  fi
  # The scripts get copies, so that a build inside a check (AC-ENG-1 builds without default
  # features into target/release) can't change which binary the other checks run.
  if {
    cargo build --release --locked -p chst-cli &&
      CARGO_TARGET_DIR=target/core cargo build --release --locked -p chst-cli --no-default-features &&
      mkdir -p "$OUT/bin" &&
      cp "target/release/chst$EXE" "$OUT/bin/chst$EXE" &&
      cp "target/core/release/chst$EXE" "$OUT/bin/chst-core$EXE"
  } > "$LOGS/build.log" 2>&1; then
    BUILD=ok
    export CHST="$OUT/bin/chst$EXE" CHST_CORE="$OUT/bin/chst-core$EXE"
  else
    BUILD=failed
  fi
}

# --- running one ID ---
R_STATUS="" R_EXIT="" R_DUR=0
finish() { # finish STATUS [EXIT]
  R_STATUS=$1
  R_EXIT=${2:-}
}

# run_check ID SCRIPT: sets R_STATUS, R_EXIT and R_DUR.
run_check() {
  local id=$1 script=$2 log=$LOGS/$1.log start=$SECONDS w rc=0
  : > "$log"
  R_DUR=0
  if [ ! -f "$script" ]; then
    echo "check.sh: no check script $script" >> "$log"
    finish FAIL
  elif grep -nE '^! ' "$script" >> "$log"; then
    echo "check.sh: $script has a line starting with '! ' (ACCEPTANCE.md §1.2)" >> "$log"
    finish FAIL
  elif ! grep -qvE '^[[:space:]]*(#|$)' "$script"; then
    echo "check.sh: $script has no commands" >> "$log"
    finish FAIL
  else
    if grep -qE "$CHST_VAR" "$script"; then ensure_build; fi
    if [ "$BUILD" = failed ] && grep -qE "$CHST_VAR" "$script"; then
      echo "check.sh: the build failed, see $LOGS/build.log" >> "$log"
      finish FAIL
    else
      w=$(mktemp -d)
      W="$w" bash -euo pipefail -c 'source tools/acceptance/lib.sh
source "$1"' check "$script" >> "$log" 2>&1 || rc=$?
      chmod -R u+rwx "$w" 2> /dev/null || true
      if [ "$rc" != 0 ]; then
        # Diagnostics only: a script often sends a command's stderr to a file in $W, which would
        # vanish with $W. Copy the first 4 KiB of each such file into the log.
        for f in "$w"/err "$w"/*.err "$w"/*.log; do
          if [ -f "$f" ]; then
            echo "--- ${f#$w/} (from \$W)" >> "$log"
            head -c 4096 "$f" >> "$log"
          fi
        done
      fi
      rm -rf "$w"
      if [ "$rc" = 0 ]; then
        finish PASS 0
      else
        echo "check.sh: $script exited $rc" >> "$log"
        finish FAIL "$rc"
      fi
    fi
  fi
  R_DUR=$((SECONDS - start))
}

record() { # record ID STATUS EXIT DUR LOG
  local cmd="./check.sh --only $1"
  if [ "$MODE" = self-test ]; then cmd="./check.sh --self-test"; fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$cmd" "$5" >> "$RES"
  echo "$2 $1"
}

# Done mode: import each ID's status from this OS's report of the CI run, using gh (read-only).
# If the import fails, every ID that applies is FAIL: a status that can't be read is not a PASS.
IMPORTED=""
import_reports() {
  local d
  d=$(mktemp -d)
  if gh run download "$DONE_ID" --pattern 'acceptance-report-*' --dir "$d" > "$LOGS/done-import.log" 2>&1 &&
    [ -f "$d/acceptance-report-$CHST_OS/report.json" ]; then
    mkdir -p "$OUT"
    cp "$d/acceptance-report-$CHST_OS/report.json" "$OUT/imported-report.json"
    IMPORTED=$OUT/imported-report.json
  else
    echo "check.sh: can't import the reports of CI run $DONE_ID, see $LOGS/done-import.log" >&2
  fi
  rm -rf "$d"
}
imported_status() { # imported_status ID -> PASS | FAIL | NOT RUN | N/A
  local st=""
  if [ -n "$IMPORTED" ]; then
    st=$(jq -r --arg id "$1" '[.results[] | select(.id == $id) | .status][0] // ""' "$IMPORTED")
  fi
  case "$st" in PASS | FAIL | "NOT RUN" | "N/A") echo "$st" ;; *) echo FAIL ;; esac
}

has_os() { # has_os "linux,macos" -> 0 when it covers this OS
  case ",$1," in *,all,* | *,"$CHST_OS",*) return 0 ;; esac
  return 1
}

# The self-test IDs go through run_check, the code path of the real IDs. Each must report its
# required status: a check that is empty, missing or can't run must be FAIL.
SELFTEST_WANT="SELFTEST-EMPTY-TARGET:FAIL SELFTEST-ZERO-FILTER:FAIL SELFTEST-MISSING-CHECK:FAIL SELFTEST-CANT-RUN:FAIL SELFTEST-PASS:PASS"
self_test() {
  local st crate pair id want
  st=$(mktemp -d)
  crate=$st/crate
  mkdir -p "$crate/src" "$crate/tests" "$st/checks"
  printf '[package]\nname = "selftest"\nversion = "0.0.0"\nedition = "2021"\n' > "$crate/Cargo.toml"
  : > "$crate/src/lib.rs"
  : > "$crate/tests/empty.rs"
  printf '#[test]\nfn passes() {}\n' > "$crate/tests/one.rs"
  export SELFTEST_CRATE=$crate
  printf 'cd "$SELFTEST_CRATE"\ncargo_test_nonempty --test empty\n' > "$st/checks/SELFTEST-EMPTY-TARGET.sh"
  printf 'cd "$SELFTEST_CRATE"\ncargo_test_nonempty --test one -- no_such_filter\n' > "$st/checks/SELFTEST-ZERO-FILTER.sh"
  printf 'no-such-command-for-chst-selftest\n' > "$st/checks/SELFTEST-CANT-RUN.sh"
  printf 'cd "$SELFTEST_CRATE"\ncargo_test_nonempty --test one\n' > "$st/checks/SELFTEST-PASS.sh"
  # SELFTEST-MISSING-CHECK has no script, on purpose.
  SELFTEST_OK=1
  for pair in $SELFTEST_WANT; do
    id=${pair%%:*}
    want=${pair##*:}
    run_check "$id" "$st/checks/$id.sh"
    record "$id" "$R_STATUS" "$R_EXIT" "$R_DUR" "$LOGS/$id.log"
    if [ "$R_STATUS" != "$want" ]; then
      echo "check.sh: self-test $id: wanted $want, got $R_STATUS" >&2
      SELFTEST_OK=0
    fi
  done
  chmod -R u+rwx "$st" 2> /dev/null || true
  rm -rf "$st"
}

if [ "$MODE" = self-test ]; then
  self_test
else
  if [ "$MODE" = done ]; then
    import_reports
    export CI_RUN_ID=$DONE_ID
  fi
  for id in $(list_ids); do
    row=$(awk -F'\t' -v id="$id" '$1 == id' <<< "$META")
    tier=$(cut -f2 <<< "$row")
    os=$(cut -f3 <<< "$row")
    kind=$(cut -f4 <<< "$row")
    if [ "$tier" = extended ] && [ "$CUT" = core ]; then
      record "$id" "N/A" "" 0 ""
    elif ! has_os "$os"; then
      record "$id" "N/A" "" 0 ""
    elif [ "$MODE" = done ] && [ "$id" != AC-XP-1 ]; then
      record "$id" "$(imported_status "$id")" "" 0 ""
    elif [ "$MODE" = only ] && ! echo ",$ONLY," | grep -q ",$id,"; then
      record "$id" "NOT RUN" "" 0 ""
    elif [ "$kind" = full ] && [ "$MODE" != full ] && [ "$MODE" != only ]; then
      record "$id" "NOT RUN" "" 0 ""
    elif [ "$kind" = done ] && [ "$MODE" != only ] && [ "$MODE" != done ]; then
      record "$id" "NOT RUN" "" 0 ""
    else
      run_check "$id" "$CHECKS/$id.sh"
      record "$id" "$R_STATUS" "$R_EXIT" "$R_DUR" "$LOGS/$id.log"
    fi
  done
fi

# --- report ---
COMMIT=$(git rev-parse HEAD 2> /dev/null || echo unknown)
DIRTY=false
if [ -n "$(git status --porcelain 2> /dev/null)" ]; then DIRTY=true; fi
jq -R -s --arg mode "$MODE" --arg cut "$CUT" --arg os "$CHST_OS" --arg commit "$COMMIT" --argjson dirty "$DIRTY" '
  {schema: "chst-acceptance/1", mode: $mode, cut: $cut, os: $os, commit: $commit, dirty: $dirty,
   results: [split("\n")[] | select(length > 0) | split("\t") |
     {id: .[0], status: .[1], exit_code: (if .[2] == "" then null else (.[2] | tonumber) end),
      duration_s: (.[3] | tonumber), command: .[4], log: (if .[5] == "" then null else .[5] end)}]}
' "$RES" > "$OUT/report.json"

n_fail=$(grep -c "$(printf '\tFAIL\t')" "$RES" || true)
n_notrun=$(grep -c "$(printf '\tNOT RUN\t')" "$RES" || true)
echo "check.sh ($MODE, $CHST_OS, cut $CUT): $(wc -l < "$RES" | tr -d ' ') IDs, $n_fail FAIL, $n_notrun NOT RUN; report: $OUT/report.json"
if [ "$MODE" = self-test ]; then
  if [ "$SELFTEST_OK" = 1 ]; then exit 0; else exit 1; fi
fi
if [ "$n_fail" != 0 ]; then exit 1; fi
if [ "$n_notrun" != 0 ]; then exit 2; fi
exit 0
