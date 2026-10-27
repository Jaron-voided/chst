cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_props
cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_swap
cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_open_race
cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_rename_race
