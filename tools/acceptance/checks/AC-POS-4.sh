for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/x"
  $GEN materialize "$d/tree.json" "$W/t"
  expect_exit 0 $CHST extract "$d/container.chst" -C "$W/x"
  python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
