# Superseded candidate: AY

Current accounting and blue rewards: [AZ review](zm-scoreboard-accounting-20260923.md). The historical 90-point/display-only/default-off-blue statements below no longer describe the candidate. Orange evidence remains applicable.

# Reconstructed cyborg score feedback (2026-09-23)

Status: uncommitted next candidate after AW. AW white-number visibility and
head/body differentiation were confirmed in play; this addition needs its own
Factory and exact-build FFA acceptance. It does not change death probabilities,
part-removal eligibility, weapon damage or the existing raw battery awards.

## What is native and what is reconstructed

Exact out.exe SHA256044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9,
IDA instanceeeah, settled35783functions. The original July31 Factory recording
decodes1669exact snapshot endpoints in the inspected180seconds.

- Native T15 reader67406E..674112 and fallback renderer561F15 establish record
  transport and orange styles3/4. The loaded default style CSV omits0..4; Factory
  mode byte0 selects this default rather than Zhunt9/TD12.
- Native Value formatter538B70 reads value+0x88/label+0x48. Label helper538250
  adds952;514880/661C50 resolve the one-based type4 name. Recorded label385
  resolves to MP_PLUS/index384 in the tested Factory client.
- Original blue HUD: x30/y-50, colorD8FFA629, scale0.9->3 over100ms, settle200ms,
  fade beginning at1000ms over750ms. These presentation values are measured.
- A1000ms accumulation window fits9/9bursts after accounting for simultaneous
  triple kills. The exact boundary is not recovered; <=1000ms is reconstruction.

**AY supersedes the unlaunched AX classification. Explicit opt-in only:** set
`OLMOD_ZM_RECONSTRUCTED_FEEDBACK=1` before starting the server. Unset, `0`,
or any other value disables reconstructed orange selection and the blue popup.
The existing native T15 transport continues emitting neutral white direct-hit
numbers. This fallback is not a claim to reproduce the original color rules.
The policy resets with the world and is admitted only for zombie mode.

**Orange criteria remain reconstructed:** positive damage with the actual native
head part-group (`hitLocation==2`), or explicitly tagged headless-decay damage,
uses style3. Ordinary lethal body damage and new torso/arm removal remain white.
No damage threshold, dismemberment union, or extra1.2 multiplier selects color.
The existing weapon-location damage calculation remains separate.

The complete original-zombie corpus contains46664snapshots,5295number transitions
and1115orange transitions. 581have a nearby same-weapon white value compatible
with floor(1.2x),239have nearby nonmatching values,295lack comparators. These are
not verified native base-damage comparisons. All23orange values<=5 coincide with
headless model aliases; Factory actor815 shows five orange3 ticks at roughly1s
with unchanged ammunition. White hits also occur alongside actual part removal.
Thus head/decay is a useful reconstruction, not proof of the lost server rule.
BO1 damage-over-time preserves `damagelocation`; that supports the hypothesis
without establishing CODOL behavior. Renderer561F15 selects orange from a
received style;561F48 formats the independently received amount, without1.2 math.
The exact original server predicate remains TODO(CODOL).

**Blue reward classification is reconstructed from video observations:**
ordinary finishing damage60; a hit that newly removes the head AND kills90;
melee100, with melee taking precedence. A nonlethal head pop awards no kill
popup; subsequent body or decay finish60. Orange head/decay damage does
not automatically gain the head-removal bonus. These displayed amounts are
separate from raw battery: original examples include blue60/raw30. Existing
raw battery policy is preserved pending a dedicated scoring comparison.

## Ownership and validation boundary

Part changes compare generation-qualified pre/post FX state. An explicit timer
parameter identifies headless decay; an empty weapon name alone is insufficient.
Feedback is emitted inside the existing accepted damage transaction. Score state
is per-client life outside native layouts; reset/disconnect/life changes retire
it. Headless source events retain the accepted frame-rotation hotfix.

Only when enabled, Factory archival HUD reserves one invisible prefix slot so reward expiry does
not shift objectives. If all31objective slots are occupied, optional score is
omitted rather than dropping an objective. MP HUD/reward projection is unchanged.
The blue accumulator never awards raw battery or feeds back into health.

Tests cover classification, same-frame sums, time-gap reset, HUD phases, actual
default-off white lethal damage/no reward, enabled head/torso source transactions, and exactly five orange headless ticks plus one
reward across a rejected terminal frame. Canonical checks and live results must
be recorded separately; source tests are not a human playtest.

## 中文摘要

AY替代未运行AX方案。`OLMOD_ZM_RECONSTRUCTED_FEEDBACK=1`显式启用重建反馈；
默认关闭，保留白色伤害数字，不声明该回退即原版规则。橙色仅按实际头部命中
或明确无头持续伤害选择；致死及部件移除本身不改变颜色，不额外乘伤害。
原始demo与IDA支持此假设但未恢复原版服务端判定。蓝色击杀显示暂定普通60、
致死断头90、近战100，累计1000毫秒边界仍属重建。双模式实测待完成。
