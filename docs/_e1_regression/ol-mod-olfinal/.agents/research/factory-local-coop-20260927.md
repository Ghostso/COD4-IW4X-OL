# Local Factory co-op / 本地Factory合作支持

Status: accepted on base `985cea1`, September27,2026.

This increment reuses the authoritative server/session/snapshot protocol for
two independent real clients. It adds no remote transport, new protocol messages or native ABI fields,
peer simulation or multiplayer-specific AI controller.

Living-player weapon attachments follow the native ET6 child representation;
see living-player-weapons-20260926.md for exact client IDA and original-demo
evidence. The existing nearest-living-Playing-player selection remains intact.
Focused regressions cover either player being nearer, relative movement,
waiting for class selection, disconnect and authoritative death.

`OLMOD_ZM_COOP_SPAWN_ZONES=1` enables a reconstructed director policy: union
the zones occupied by living Playing clients and their eligible open neighbors.
Deduplicate the final zone set, exclude unopened areas, and pause spawning
when no eligible player remains. Poll once per second. The option is disabled
by default; the existing first-player zone rule remains available. This is not
evidence of native CODOL co-op spawn weighting. Lua reports the selected source
as `cooperative-union-reconstruction` for diagnostics.

Validation: seven canonical suites, Release,50ms scheduler regression and196-entry
partial source audit pass. Same-build two-real-client Factory and Nuketown FFA
playtests pass, including visible ordinary held weapons. Existing nearest-player
target selection is covered by focused source regressions, not replaced.
Remote join, late join/rejoin, downed/revive, empty-server lifecycle and partner
disconnect recovery remain unverified. The existing early return at zero player
count is unchanged; empty-target pausing is not a complete empty-server policy.
The previously documented long-session slowdown remains open.

Enable the cooperative director with `OLMOD_ZM_COOP_SPAWN_ZONES=1` on the
server before launch and deploy the matching updated `gametypes/zm.lua` alongside
the plugin. Ordinary held-weapon publication needs no mode-specific flag.
Existing session admission and independent native loadouts are prerequisites;
this gameplay contribution does not install a remote server/client launcher.
Test-launcher changes and account configuration remain outside the patch.

本地双客户端候选沿用同一权威服务器与快照协议，不引入独立联机AI或新网络字段。
武器子实体有IDA及原版demo依据；双人区域并集刷怪为默认关闭的显式重建策略，
不是已恢复的原版权重。目标选择覆盖距离、选职业等待、离线和死亡回归。
同构建双客户端Factory/FFA验收通过；远程加入、复活、重连、空服生命周期及长时间稳定性仍待验证。
