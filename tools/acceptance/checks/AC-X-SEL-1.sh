f=$FX/core/valid/worked-example/container.chst
$CHST extract $f -C "$W/x" 'docs/*.txt'
(cd "$W/x" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n')
$CHST extract $f -C "$W/z" 'docs'
(cd "$W/z" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./docs/empty\n')
expect_exit 9 $CHST extract $f -C "$W/y" 'docs/*.txt' 'nomatch/*' 2> "$W/err"
grep -q 'error\[refused/extract.no-match\]' "$W/err" && grep -q 'nomatch/\*' "$W/err" && test ! -e "$W/y"
$CHST extract $f -C "$W/q" 'docs/?.txt' 'notes.tx[st]'                 # ? and [...]
(cd "$W/q" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./notes.txt\n')
$CHST extract $f -C "$W/r" 'docs/[!a].txt'                             # negated class
(cd "$W/r" && find . | sort) | diff - <(printf '.\n./docs\n./docs/b.txt\n')
$CHST extract $f -C "$W/s" 'docs/**'                                   # a/** matches a itself
(cd "$W/s" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./docs/empty\n')
expect_exit 2 $CHST extract $f -C "$W/u" 'docs\a.txt'                  # no escape character
expect_exit 2 $CHST extract $f -C "$W/v" 'docs/[z-a].txt'              # reversed range (N16)
# N7: a damaged blob that isn't selected doesn't fail a selective extract
expect_exit 0 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/sel" 'docs/*.txt'
expect_exit 7 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/sel2" 'notes.txt'
