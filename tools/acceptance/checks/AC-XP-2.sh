w=.github/workflows/check.yml
for k in 'push:' 'pull_request:' 'workflow_dispatch:' ubuntu-latest macos-latest windows-latest 'shell: bash' \
         './check.sh --full' 'acceptance-report-' 'CHST_BIG_ROOT'; do grep -qF -- "$k" $w; done
grep -qE '^\s+run: \./check\.sh\s*$' $w     # the fast-mode step
