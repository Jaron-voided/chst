tc=$(sed -n 's/^channel = "\(.*\)"$/\1/p' fuzz/rust-toolchain.toml)
for t in open_verify open_verify_rehash list inspect; do
  cargo +"$tc" fuzz run $t -- -max_total_time=600 -rss_limit_mb=512 -timeout=10 \
    fuzz/corpus/$t $FX/core/valid $FX/core/invalid
  test -z "$(ls -A fuzz/artifacts/$t 2>/dev/null)"
done
