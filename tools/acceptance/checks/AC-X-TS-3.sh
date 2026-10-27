if grep -rnE 'chst-format|\.rs|target/|wasm|fixtures/gen' ts-reader/src; then exit 1; fi
grep -rqF 'node:crypto' ts-reader/src
jq -e '(.dependencies // {} | length) == 0' ts-reader/package.json
jq -e '.devDependencies // {} | keys | all(. == "typescript" or . == "@types/node")' ts-reader/package.json
node --version | grep -qE '^v24\.'
test "$(node -p process.versions.unicode)" = 16.0                    # F12: Unicode 16.0 tables
