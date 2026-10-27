for d in $FX/core/valid/*/; do for c in list verify inspect; do
  expect_exit 0 $CHST $c --json "$d/container.chst" > "$W/r.json"
  diff <(jqn "$W/r.json") <(jqn "$d/$c.json")
done; done
