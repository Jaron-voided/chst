cargo build --release --workspace --locked
cargo build --release -p chst-cli --no-default-features --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo fmt --all --check
