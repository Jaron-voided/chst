./check.sh --self-test > /dev/null || true
r=target/acceptance/report.json
jq -e '.mode == "self-test"' $r
for id in SELFTEST-EMPTY-TARGET SELFTEST-ZERO-FILTER SELFTEST-MISSING-CHECK SELFTEST-CANT-RUN; do
  jq -e --arg id $id '.results[] | select(.id == $id) | .status == "FAIL"' $r
done
jq -e '.results[] | select(.id == "SELFTEST-PASS") | .status == "PASS"' $r
