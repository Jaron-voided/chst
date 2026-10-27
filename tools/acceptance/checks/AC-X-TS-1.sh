(cd ts-reader && npm ci && npm run build)
for d in $FX/core/valid/*/ $FX/extended/valid/*/; do for c in list verify; do
  [ -f "$d/$c.json" ] || continue
  node ts-reader/dist/cli.js $c --json "$d/container.chst" > "$W/r.json"
  diff <(jqn "$W/r.json") <(jqn "$d/$c.json")
done; done
