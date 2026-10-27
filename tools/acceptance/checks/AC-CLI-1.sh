expect_exit 2 $CHST frobnicate
expect_exit 2 $CHST verify
expect_exit 3 $CHST verify "$W/does-not-exist.chst"
head -c 100 /dev/urandom > "$W/r" && expect_exit 4 $CHST verify "$W/r"
: > "$W/e" && expect_exit 4 $CHST verify "$W/e"
f=$FX/core/valid/worked-example/container.chst                         # N23: limit values
expect_exit 2 $CHST verify --max-entries -1 $f
expect_exit 2 $CHST verify --max-entries 18446744073709551616 $f
expect_exit 0 $CHST verify --max-entries 18446744073709551615 $f
expect_exit 0 $CHST verify --max-entries 0 $FX/core/valid/empty/container.chst
for v in +5 05 00 ' 5' '5 ' 0x5 ''; do                                  # M12: ASCII digits only
  expect_exit 2 $CHST verify --max-entries "$v" $f
done
expect_exit 0 $CHST verify --max-ratio 18446744073709551615 $f          # M3: largest ratio parses
expect_exit 2 $CHST verify --max-ratio 18446744073709551616 $f
