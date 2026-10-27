mkdir -p "$W/t" && truncate -s 1G "$W/t/big.bin"
for cmd in "pack $W/t -o $W/o.chst" "verify $W/o.chst" "extract $W/o.chst -C $W/x"; do
  /usr/bin/time -f '%M' -o "$W/rss" $CHST $cmd
  test "$(cat "$W/rss")" -lt 65536      # peak RSS < 64 MiB (KiB units)
done
