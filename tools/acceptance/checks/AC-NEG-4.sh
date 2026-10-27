for e in $FX/core/invalid/*.expect.json $FX/extended/invalid/*.expect.json; do
  jq -e '(.base|length>0) and (.mutation|length>0) and (.rule|test("^[A-Z]+-[0-9]+$"))' $e >/dev/null
done
