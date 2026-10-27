gh run download "$CI_RUN_ID" --pattern 'acceptance-report-*' --dir "$W/r"      # gh: read-only use
test "$(jq -r .os "$W"/r/*/report.json | sort -u | tr '\n' ' ')" = 'linux macos windows '
test "$(jq -r .commit "$W"/r/*/report.json | sort -u | wc -l | tr -d ' ')" = 1
sha=$(jq -r .commit "$W"/r/*/report.json | head -1)
test "$(gh run view "$CI_RUN_ID" --json headSha -q .headSha)" = "$sha"
for r in "$W"/r/*/report.json; do
  jq -e '.mode == "full" and .dirty == false and
         all(.results[]; if .id == "AC-XP-1" then .status == "NOT RUN" else (.status == "PASS" or .status == "N/A") end)' "$r"
  col=$(case "$(jq -r .os "$r")" in linux) echo 3;; macos) echo 4;; windows) echo 5;; esac)
  jq -r '.results[] | select(.id != "AC-XP-1") | "\(.id)\t\(.status)"' "$r" | while IFS=$'\t' read -r id st; do
    row=$(grep -E "^\| $id \|" EVIDENCE.md) || { echo "EVIDENCE.md: no row for $id"; exit 1; }
    test "$(awk -F'|' -v c=$col '{gsub(/^ +| +$/, "", $c); print $c}' <<< "$row")" = "$st"
    grep -qF "$sha" <<< "$row" && grep -qF "actions/runs/$CI_RUN_ID" <<< "$row"
  done
done
