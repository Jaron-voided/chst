(umask 022; $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/x")
test -z "$(find "$W/x" -perm -4000 -o -perm -2000 -o -perm -1000)"
test "$(find "$W/x" -type f ! -perm 644 | wc -l)" -eq 0
test "$(find "$W/x" -type d ! -perm 755 | wc -l)" -eq 0
if [ "$CHST_OS" = linux ]; then                    # P2: a setgid parent leaks no S_ISGID into the tree
  mkdir "$W/sg" && chmod 2775 "$W/sg"
  (umask 022; $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/sg/x")
  test -z "$(find "$W/sg/x" -perm -2000)"
  test "$(find "$W/sg/x" -type d ! -perm 755 | wc -l)" -eq 0
fi
