python3.14 -I tools/acceptance/flip_sweep.py "$CHST" $FX/core/valid/worked-example/container.chst \
  $FX/core/valid/empty/container.chst $FX/core/valid/dedup/container.chst
python3.14 -I tools/acceptance/flip_sweep.py --rehash --min-distinct 15 "$CHST" \
  $FX/core/valid/worked-example/container.chst
