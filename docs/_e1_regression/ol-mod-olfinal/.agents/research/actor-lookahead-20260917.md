# Adaptive actor path lookahead / 自适应路径前视

Status: lookahead component evidence on upstream `4e2787a`. The complete accepted navigation candidate and validation scope are recorded in [navigation-increment-20260920.md](navigation-increment-20260920.md).
This component changes post-window steering, not the accepted head attachment,
traverse lifetime, map graph, doors, crowd policy, weapons or player netfields.

## Evidence

IDA 9.3 exports were read from the canonical BO1 and Ghosts databases, with
database identity checked before each job. Long pseudocode responses were
initially truncated by MCP; those previews were not used as full-function
evidence. Bounded exports subsequently covered the relevant functions.

| Contract | BO1 Windows x86 | Ghosts PS4 x64 |
|---|---|---|
| Bend-area selection | `Path_CalcLookahead` `0x90A120`, `Path_GetDistToPathSegment` `0x9035F0` | `Path_CalcLookahead` `0x1400FF410` |
| Prediction feedback | `Path_UpdateLookaheadAmount` `0x90A670`, increase `0x90B100`, reduce `0x90B050` | `Path_UpdateLookaheadAmount` `0x140102450`, reduce `0x140101680` |
| Collision admission | `Path_LookaheadPredictionTrace` `0x907840` | `Path_LookaheadPredictionTraceExtended` `0x140100C20` |
| Initial budget | `Path_Begin` `0x906400`: `21845.334` | Not used as initialization evidence |
| Progress owner | `Path_TrimCompletedPath` `0x908820` uses saved lookahead direction | Not claimed identical in this increment |

Both selectors accumulate perpendicular offset times segment length and
interpolate inside the segment where that area reaches the budget. This is
different from the previous fixed 60-unit polyline target. A clear prediction
grows the budget by `*1.1764705 + 6.4`, capped at `65536`. BO1 reduces by `.75`
after a clear prediction and `.5625` after a failed one. Its additional momentum
and previous-target restoration branches explicitly exclude zombie mode.
Ghosts has extra moving-parent/3D/dodge state and an additional `.8` reduction
case; those branches are not copied as CODOL semantics.

BO2 IDA comparison confirms the difference: `Path_Begin` `0x889B60` initializes
`32768`, not BO1's `21845.334`; reduction `0x88A570` has the same additional
flag/dodge-dependent `.8` case as Ghosts. Increase `0x88A620` has a special
big-dog multiplier. The candidate deliberately uses the simpler BO1 zombie
reference and labels it as such; CODOL's exact initial budget, dodge flags and
special-actor policy remain unresolved. No big-dog branch is imported.

The exact CODOL client is `out.exe`, SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
Its previously IDA-reviewed trace wrapper `0x46EA60` and world trace `0x668220`
remain the collision boundary. The map nodes, receiver negotiations and
original-player-demo graph are unchanged. A symbol-name search did not identify
the original CODOL path owner; that alone is not evidence of its absence from
every supplied binary. This change remains a reconstructed adapter, not
recovered original CODOL server code.

## Explicit adapter limits

- Source routes are forward ordered, unlike the reference path representation.
  The first approach goes from the current actor position to its owned waypoint;
  no native `path_t`, field offsets, flags or ABI are imported.
- Selection is bounded to 32 nodes and 192 units. The original 100-ms prediction
  cadence and at-most-one body sweep per refresh are retained. No random routes,
  per-actor synthetic lanes, repeated A* searches or extra all-pairs traces.
- Barriers, negotiations and different-floor edges stop smoothing. Existing
  grounded movement remains authoritative at every physical step. The current
  body prediction is not claimed to recover the complete native ground/dodge
  prediction policy.
- Only a still-owned accepted chord may trim against its saved steering plane.
  Route replanning invalidates that use; node-range and floor checks remain.
- Native reference feedback is applied to accepted project predictions, including
  the existing forward-progress admission guard. A/B testing must establish
  whether this adapter improves CODOL in practice.

## Acceptance status

This file covers the lookahead component only. The same-build Factory and two-client FFA manual playtests passed. See navigation-increment-20260920.md for complete scope and evidence limits.

## 中文摘要

此候选仅调整窗口翻越后的路径前视，不更改已验收的头部绑定、翻越动画、
地图连线或玩家网络字段。IDA 证据表明 BO1/Ghosts 使用“垂直偏移 × 路段长度”
累积面积选择前视点，并根据预测碰撞结果调整预算，而非固定向前 60 单位。
原版 CODOL 服务端路径控制器尚未恢复；节点数量、距离、刷新频率及进度保护
均明确属于本项目适配边界。完整导航候选已通过 Factory 与双客户端 FFA 人工验证；范围及限制见 navigation-increment-20260920.md。
