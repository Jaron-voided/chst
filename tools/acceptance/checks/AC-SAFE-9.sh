$CHST extract $FX/core/valid/worked-example/container.chst -C "$W/x"
n=$(powershell -NoProfile -Command "(Get-ChildItem -Recurse -File -LiteralPath '$(cygpath -w "$W/x")' | ForEach-Object { Get-Item -LiteralPath \$_.FullName -Stream * } | Where-Object Stream -ne ':\$DATA' | Measure-Object).Count")
test "$(echo $n | tr -d '\r')" = 0
