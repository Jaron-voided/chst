for e in $FX/compat/*.expect.json; do
  f=${e%.expect.json}.chst
  set +e; $CHST verify --json "$f" > "$W/r.json"; rc=$?; set -e
  test $rc = "$(jq .extended.exit $e)"
  jq -e --slurpfile x $e '($x[0].extended.detail == null) or (.error.detail == $x[0].extended.detail)' "$W/r.json"
done
