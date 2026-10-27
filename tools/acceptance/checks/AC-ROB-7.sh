case "$CHST_OS" in
  macos)   size=4296015872 ;;                                   # 4 GiB + 1 MiB
  windows) size=5368709120                                       # 5 GiB …
           [ "$(free_bytes "$CHST_BIG_ROOT")" -ge 12884901888 ] || size=4296015872 ;;  # … unless < 12 GiB free
  *)       size=5368709120 ;;
esac
echo "AC-ROB-7 size: $size"; df -h "$CHST_BIG_ROOT"
B=$(mktemp -d "$CHST_BIG_ROOT/chst-rob7.XXXXXX"); trap 'rm -rf "$B"' EXIT
mkdir "$B/t"; mk_sparse "$B/t/huge.bin" $size
$CHST pack "$B/t" -o "$B/o.chst"
$CHST list --json "$B/o.chst" | jq -e --argjson s $size '.entries[0].size == $s'
$CHST verify "$B/o.chst"
$CHST extract "$B/o.chst" -C "$B/x"
test "$(sha256 "$B/x/huge.bin")" = "$(sha256 "$B/t/huge.bin")"
