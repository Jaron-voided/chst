for e in $FX/core/attacks/*.expect.json; do
  f=${e%.expect.json}.chst; rm -rf "$W/p"; mkdir -p "$W/p/sentinel"
  expect_exit "$(jq .exit $e)" $CHST extract "$f" -C "$W/p/out"
  test "$(ls -A "$W/p")" = sentinel && test -z "$(ls -A "$W/p/sentinel")"
done
