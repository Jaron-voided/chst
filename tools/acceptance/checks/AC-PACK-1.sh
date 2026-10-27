for n in 'a:b' 'CON.txt' 'trail.' 'sp ' $'bad\xff' 'Aa' ; do
  rm -rf "$W/t" "$W/o"; mkdir -p "$W/t" "$W/o"; touch "$W/t/$n"
  [ "$n" = Aa ] && touch "$W/t/aa"
  expect_exit 9 $CHST pack "$W/t" -o "$W/o/c.chst" 2> "$W/err"
  grep -q 'error\[refused/pack.unportable-name\]' "$W/err" && test -z "$(ls -A "$W/o")"
done
