for d in $FX/core/valid/*/; do
  $CHST inspect --json "$d/container.chst" > "$W/i.json"
  python3.14 -I tools/acceptance/inspect_check.py "$W/i.json" "$d/container.chst"
done
