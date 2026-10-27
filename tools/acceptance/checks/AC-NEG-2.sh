for e in $FX/core/invalid/*.expect.json; do
  f=$(fixture_file $e); args=$(jq -r '.args // [] | join(" ")' $e)
  set +e; $CHST verify --json $args "$f" > "$W/r.json" 2> "$W/err"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  test "$(jq -r .error.category "$W/r.json")" = "$(jq -r .category $e)"
  test "$(jq -r .error.detail "$W/r.json")" = "$(jq -r .detail $e)"
  test "$(jq -c 'keys' "$W/r.json")" = '["command","error","ok","schema","warnings"]'
  head -1 "$W/err" | grep -qF "chst: error[$(jq -r .category $e)/$(jq -r .detail $e)]: "
done
