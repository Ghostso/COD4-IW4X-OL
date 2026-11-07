$p='tests\test_weapondefs.c'; $i=0; Get-Content -LiteralPath $p -Encoding UTF8 | ForEach-Object { $i++; '{0,4}: {1}' -f $i,$_ }
