f=$FX/core/valid/worked-example/container.chst
test "$(wc -c < $f | tr -d ' ')" = 556
test "$(sha256 $f)" = 1939236c4b281cf517f7ca1b1746b93b75a0e6afb485107f56d1eea1a7e33332
python3.14 -I tools/acceptance/spec_hexdump.py FORMAT_SPEC.md | cmp - $f
