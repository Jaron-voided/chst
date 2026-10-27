# Shared shell helpers and conventions for check.sh, the check scripts and TODO.md Verify lines
# (ACCEPTANCE.md §1.2). Source it from the repository root: `source tools/acceptance/lib.sh`.
# It sets no shell options, so the caller's `set -e` and `set -u` stay as they are.
# Written for bash 3.2 (the macOS default): no associative arrays, no mapfile.

case "$(uname -s)" in
  Linux*) CHST_OS=linux ;;
  Darwin*) CHST_OS=macos ;;
  MINGW* | MSYS* | CYGWIN*) CHST_OS=windows ;;
  *) CHST_OS=unknown ;;
esac
export CHST_OS

_exe=""
if [ "$CHST_OS" = windows ]; then _exe=.exe; fi

FX=fixtures
GEN="python3.14 -I fixtures/gen/gen.py"
CHST=${CHST:-target/release/chst$_exe}
CHST_CORE=${CHST_CORE:-target/core/release/chst$_exe}
CHST_BIG_ROOT=${CHST_BIG_ROOT:-${TMPDIR:-/tmp}}
CHST_DET_SEED=${CHST_DET_SEED:-chst-det-1}
PINNED_MANIFEST_HASH=$(sed -n 's/^PINNED_MANIFEST_HASH = //p' ACCEPTANCE.md | head -1)
export FX GEN CHST CHST_CORE CHST_BIG_ROOT CHST_DET_SEED PINNED_MANIFEST_HASH

# expect_exit N CMD…: run CMD, and fail unless its exit code is exactly N. A CMD that can't be
# found or isn't executable counts as exit 127 on every OS (macOS's bash 3.2 reports 1 for it).
expect_exit() {
  local want=$1 rc=0
  shift
  if command -v "$1" > /dev/null 2>&1; then
    "$@" || rc=$?
  else
    rc=127
  fi
  if [ "$rc" != "$want" ]; then
    echo "expect_exit: wanted exit $want, got $rc: $*" >&2
    return 1
  fi
}

# jqn FILE: normalised JSON for comparison (FORMAT_SPEC Appendix B).
jqn() {
  jq -S 'walk(if type == "object" then del(.message) else . end)' "$1"
}

# sha256 FILE: lowercase hex SHA-256 of FILE.
sha256() {
  if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

# mk_sparse FILE SIZE: create a sparse file of SIZE bytes.
mk_sparse() {
  local f=$1 size=$2
  if [ "$CHST_OS" = windows ]; then
    : > "$f"
    fsutil sparse setflag "$(cygpath -w "$f" 2> /dev/null || echo "$f")" > /dev/null
  fi
  if command -v truncate > /dev/null 2>&1; then
    truncate -s "$size" "$f"
  else
    python3.14 -I -c 'import os, sys; os.truncate(sys.argv[1], int(sys.argv[2]))' "$f" "$size"
  fi
}

# free_bytes DIR: free bytes on DIR's volume.
free_bytes() {
  df -Pk "$1" | awk 'NR == 2 { printf "%.0f\n", $4 * 1024 }'
}

# fixture_file EXPECT.json: the container an expect.json describes. That's the sibling .chst or,
# for a sparse recipe, a sparse file materialised under $W.
fixture_file() {
  local e=$1 base chst recipe out size
  base=${e%.expect.json}
  chst=$base.chst
  recipe=$base.recipe.json
  if [ -f "$chst" ]; then
    echo "$chst"
  elif [ -f "$recipe" ]; then
    out=$(mktemp -d "${W:?fixture_file needs \$W}/sparse.XXXXXX")/$(basename "$base").chst
    size=$(jq -r .file_length "$recipe")
    mk_sparse "$out" "$size"
    $GEN materialize-sparse "$recipe" "$out"
    echo "$out"
  else
    echo "fixture_file: no .chst or .recipe.json beside $e" >&2
    return 1
  fi
}

# cargo_test_nonempty ARGS…: the zero-test guard. Runs `cargo test ARGS…`, then sums the
# `N passed` counts of every `test result:` line. Fails on a cargo failure, on no `test result:`
# line, and on a sum of 0.
cargo_test_nonempty() {
  local out rc=0 total
  out=$(mktemp "${W:-${TMPDIR:-/tmp}}/cargo-test.XXXXXX")
  cargo test "$@" > "$out" 2>&1 || rc=$?
  cat "$out"
  if [ "$rc" != 0 ]; then
    echo "cargo_test_nonempty: cargo test exited $rc" >&2
    rm -f "$out"
    return 1
  fi
  if ! grep -q '^test result:' "$out"; then
    echo "cargo_test_nonempty: no 'test result:' line" >&2
    rm -f "$out"
    return 1
  fi
  total=$(awk '/^test result:/ { for (i = 1; i <= NF; i++) if ($i == "passed;") n += $(i - 1) } END { print n + 0 }' "$out")
  rm -f "$out"
  if [ "$total" -le 0 ]; then
    echo "cargo_test_nonempty: 0 tests passed" >&2
    return 1
  fi
}

# --- Development helpers (TODO.md "Verify lines"). No acceptance check uses them. ---

# pass_only ID,ID…: run `./check.sh --only ID,ID…`, then fail unless report.json has exactly one
# result for each named ID and every one is PASS.
pass_only() {
  local ids=$1 r=target/acceptance/report.json
  ./check.sh --only "$ids" > /dev/null || true
  jq -e --arg ids "$ids" '
    . as $r | .mode == "only" and
    all($ids | split(",")[]; . as $id | [$r.results[] | select(.id == $id)] | length == 1 and .[0].status == "PASS")
  ' "$r" > /dev/null || {
    echo "pass_only: not every named ID is PASS:" >&2
    jq -r --arg ids "$ids" '. as $r | $ids | split(",")[] | . as $id |
      "  \($id): \([$r.results[] | select(.id == $id) | .status] | join(",") | if . == "" then "missing" else . end)"' "$r" >&2
    return 1
  }
}

# ci_pass OS ID,ID…: read the newest CI run of check.yml with `gh` (read-only), download
# acceptance-report-OS, and fail unless every named ID is PASS in it.
ci_pass() {
  local os=$1 ids=$2 run d r
  run=$(gh run list --workflow check.yml --limit 1 --json databaseId -q '.[0].databaseId')
  if [ -z "$run" ]; then
    echo "ci_pass: no CI run of check.yml" >&2
    return 1
  fi
  d=$(mktemp -d "${W:-${TMPDIR:-/tmp}}/ci.XXXXXX")
  gh run download "$run" --name "acceptance-report-$os" --dir "$d"
  r=$(find "$d" -name report.json | head -1)
  test -n "$r"
  jq -e --arg ids "$ids" '
    . as $r | all($ids | split(",")[]; . as $id | [$r.results[] | select(.id == $id)] | length == 1 and .[0].status == "PASS")
  ' "$r" > /dev/null
}
