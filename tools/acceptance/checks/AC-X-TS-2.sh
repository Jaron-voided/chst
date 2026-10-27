# ACCEPTANCE.md gives this ID no script block. Its text says: "The same script as AC-NEG-2 and
# AC-COMPAT-1, with `node ts-reader/dist/cli.js` in place of `$CHST`." The two scripts below are
# those two, unchanged, run with that command in place of $CHST (and $CHST_CORE).
CHST="node ts-reader/dist/cli.js"
CHST_CORE=$CHST
for e in $FX/core/invalid/*.expect.json; do
  f=$(fixture_file $e); args=$(jq -r '.args // [] | join(" ")' $e)
  set +e; $CHST verify --json $args "$f" > "$W/r.json" 2> "$W/err"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  test "$(jq -r .error.category "$W/r.json")" = "$(jq -r .category $e)"
  test "$(jq -r .error.detail "$W/r.json")" = "$(jq -r .detail $e)"
  test "$(jq -c 'keys' "$W/r.json")" = '["command","error","ok","schema","warnings"]'
  head -1 "$W/err" | grep -qF "chst: error[$(jq -r .category $e)/$(jq -r .detail $e)]: "
done
for e in $FX/compat/*.expect.json; do
  f=${e%.expect.json}.chst
  set +e; $CHST_CORE verify --json "$f" > "$W/r.json"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  jq -e --slurpfile x $e '($x[0].detail == null) or (.error.detail == $x[0].detail)' "$W/r.json"
  if [ "$rc" = 0 ]; then for c in list verify inspect; do
    $CHST_CORE $c --json "$f" > "$W/c.json"; diff <(jqn "$W/c.json") <(jqn ${e%.expect.json}.$c.json)
  done; fi
done
