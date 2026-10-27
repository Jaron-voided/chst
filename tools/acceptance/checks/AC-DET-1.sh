for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/o.chst"
  $GEN materialize --reverse "$d/tree.json" "$W/t"
  (umask 077; $CHST pack "$W/t" -o "$W/o.chst")
  cmp "$W/o.chst" "$d/container.chst"
done
