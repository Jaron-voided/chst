mkdir -p "$W/t/sub" && echo x > "$W/t/f"
expect_exit 9 $CHST pack "$W/t" -o "$W/t/self.chst" 2> "$W/err"
grep -q 'pack.output-in-source' "$W/err" && test ! -e "$W/t/self.chst"
expect_exit 9 $CHST pack "$W/t" -o "$W/t/sub/../sub/self.chst"           # .. route (F22)
if [ "$CHST_OS" != windows ]; then
  ln -s "$W/t/sub" "$W/alias"                                           # symlinked route
  expect_exit 9 $CHST pack "$W/t" -o "$W/alias/self.chst" && test ! -e "$W/t/sub/self.chst"
fi
