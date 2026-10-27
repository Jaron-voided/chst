for e in $FX/core/invalid/*.expect.json; do
  case "$(jq -r .rule $e)" in BLB-6|LIM-5) continue;; esac   # step 11 / verify+extract only
  f=$(fixture_file $e); args=$(jq -r '.args // [] | join(" ")' $e)
  for c in list inspect; do expect_exit "$(jq .exit $e)" $CHST $c --json $args "$f" >/dev/null; done
done
# F34: list and inspect MUST NOT perform step 11, so a blob-hash error is invisible to them
for c in list inspect; do expect_exit 0 $CHST $c --json $FX/core/invalid/BLB-6.chst > /dev/null; done
