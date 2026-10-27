$CHST verify --json $FX/core/valid/dedup/container.chst | jq -e '.summary.blobs == 2 and .summary.files == 103'
