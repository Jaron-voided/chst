for e in $FX/core/hostile64/*.expect.json; do
  set +e; $CHST verify --json "${e%.expect.json}.chst" > "$W/r.json"; rc=$?; set -e
  test $rc = 6
  jq -e --slurpfile x $e '.error.detail as $d | $x[0].details | index($d) != null' "$W/r.json"
done
