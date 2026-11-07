$f = 'CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs'
$crlf = "`r`n"
$c = [System.IO.File]::ReadAllText((Resolve-Path $f), [System.Text.Encoding]::UTF8)

$old = '            // [P0-SMOOTH-MOVE] 首帧下发出生点，后续帧省略位置(omit_motion)，完全由客户端本地 Pmove 推进，彻底杜绝拉扯与橡皮筋' + $crlf + '            if (!omitMotion)'
$new = @(
'            // [MOVEFIX 2026-10-16] 恢复服务端权威位置下发：',
'            //   之前为让客户端接受快照把 omitMotion 设为 true（完全靠客户端本地 Pmove 预测），',
'            //   但服务器端没有任何移动积分回写（位置恒为出生点），客户端永远收不到位置更新，',
'            //   表现为"能进图但走不动、延迟巨大"。',
'            //   修复：客户端入场后（first==false），每帧都下发权威位置+速度，',
'            //   由 GameWorld.IntegratePlayer 根据 usercmd 实时更新坐标。',
'            bool sendMotion = !omitMotion || !first;',
'            if (sendMotion)'
) -join $crlf

if (-not $c.Contains($old)) { Write-Host 'ABORT: pattern not found'; exit 1 }
$c = $c.Replace($old, $new)
$utf8bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText((Resolve-Path $f), $c, $utf8bom)
Write-Host 'MotionSnapshot.cs patched OK'
