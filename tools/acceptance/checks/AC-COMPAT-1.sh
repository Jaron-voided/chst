for e in $FX/compat/*.expect.json; do
  f=${e%.expect.json}.chst
  set +e; $CHST_CORE verify --json "$f" > "$W/r.json"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  jq -e --slurpfile x $e '($x[0].detail == null) or (.error.detail == $x[0].detail)' "$W/r.json"
  if [ "$rc" = 0 ]; then for c in list verify inspect; do
    $CHST_CORE $c --json "$f" > "$W/c.json"; diff <(jqn "$W/c.json") <(jqn ${e%.expect.json}.$c.json)
  done; fi
done
