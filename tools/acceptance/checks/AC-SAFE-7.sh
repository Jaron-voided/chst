expect_exit 0 $CHST extract $FX/core/valid/long-names/container.chst -C "$W/x"
$GEN materialize $FX/core/valid/long-names/tree.json "$W/t"
python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
