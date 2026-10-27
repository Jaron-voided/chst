f=$FX/core/valid/worked-example/container.chst
expect_exit 8 $CHST verify --max-entries 4 $f;        expect_exit 0 $CHST verify --max-entries 5 $f
expect_exit 8 $CHST verify --max-index-bytes 458 $f;  expect_exit 0 $CHST verify --max-index-bytes 459 $f
expect_exit 8 $CHST verify --max-total-bytes 14 $f;   expect_exit 0 $CHST verify --max-total-bytes 15 $f
expect_exit 8 $CHST extract --max-total-bytes 14 $f -C "$W/a"; test ! -e "$W/a"
expect_exit 0 $CHST extract --max-total-bytes 15 $f -C "$W/b"
