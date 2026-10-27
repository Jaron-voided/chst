d=$FX/core/sparse/huge-5g
mk_sparse "$W/h.chst" "$(jq .file_length $d/recipe.json)"
$GEN materialize-sparse $d/recipe.json "$W/h.chst"
for c in list inspect verify; do
  expect_exit 0 $CHST $c --json "$W/h.chst" > "$W/r.json"; diff <(jqn "$W/r.json") <(jqn $d/$c.json)
done
