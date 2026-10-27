cargo_test_nonempty --release -p chst-format --test hostile_sizes
for e in $FX/core/hostile/*.expect.json; do
  expect_exit "$(jq .exit $e)" timeout 2 $CHST verify "${e%.expect.json}.chst"
done
