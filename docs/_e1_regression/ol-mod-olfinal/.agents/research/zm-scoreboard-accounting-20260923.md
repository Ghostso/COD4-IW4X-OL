# Cyborg score, battery and scoreboard accounting

Status: accepted AZ candidate. Factory and exact-build two-client FFA PASS.
This supersedes AY's display-only blue rewards and its inferred 90-point rule.

## Evidence and limits

Exact out.exe SHA256 `044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
IDA eeah settled at 35783 functions. Original July31 Factory recording SHA256
`a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97`.

Native611AA0 rebuilds the scoreboard from J/K profile patches, reading score,
kills and headshots. 60DC50 caches it for6B1010. The zm table column16 is1;
6B27C5 hides rows outside team1/2. The previous client cached a valid Zak row
with team0 and zero stats. This is not a missing connection or name.

The omitted field is **client-info36**, not agent21. IDA descriptor0xDA8228
(table0xDA8078, stride12) is offset4,width11,type0. 54BC50 shows ebx is four
bytes into clientState;54BC8E/54BC90 copy [ebx] into characterInfo+7C. Decode
of284 exact original snapshots through40seconds confirms field36=2 for the
recorded survivor. ZM now supplies2 in this separate record; MP remains0 and
therefore emits no new field. No client filter bypass or FFA team-policy edit.

Original binary profile observations around34.4s and35.9s:

| Accepted event | Score | Raw battery | Blue popup |
|---|---:|---:|---:|
| Ordinary preceding hit |10|10|none|
| Ordinary kill |60|30|60|
| Headshot-counted kill |80|40|80|

Four ordinary hits preceded the first kill. Killing-hit amounts are complete
awards, not another ten plus the listed value. Profile headshots rises on the
second kill. This disproves treating blue rewards as battery, but does not
recover every original server predicate. Head-hit classification uses actual
partgroup2. Melee100/50 and nonlethal-decay zero are explicitly reconstructed;
original weapon/special-enemy variants and all reward multipliers remain unknown.
The separately observed video90 is not promoted to a universal native constant.
Shop prices, battery HUD scale, perk economy and barrier rewards are unchanged.

## Ownership

One admitted positive-health zombie damage transaction computes independent
score/battery outcomes, records the attacker life, and adds blue kill feedback.
The immutable world event carries that result through the existing once-only
dispatch, including pre-frame headless deaths. ServerCore credits cumulative
score/kills/headshots after checking owner life; Lua continues to count waves.
Corpse hits and unrelated props cannot create a second kill. Scoreboard credit
does not invoke multiplayer medals, score limits or team score.

White number transport and head-location weapon scaling from AW are included.
Blue rewards no longer depend on the reconstructed-orange flag. Orange remains
default-off and explicitly reconstructed: actual head hits/explicit headless
decay, not lethal damage or dismemberment alone. No new combat multiplier.
Blue accumulation1000ms is the previously documented reconstruction matching
nine original bursts. Score/battery counters do not depend on popup capacity.

## Validation

Seven canonical suites,50ms server regression,Release build,source audit and
frozen gameplay-source/package checks passed. Factory run669099921 and exact-build
two-real-client Nuketown FFA run672381796 playtests passed. Both FFA clients
reached Playing. Individual automated combat assertions are not claimed.
DLL SHA256 B8F6075483556A64AE8300DC972012059B6ACBE7CA9157A329E380266243FDE3.

## 验证与边界

Factory 与同构建双客户端 Nuketown FFA 实测通过；七项套件、50ms 服务端回归、
Release 构建、证据索引及冻结包校验通过。无独立自动战斗断言。
分数与电池独立记账；近战、无头持续伤害奖励及橙色选择保留重建标记。
不更改多人队伍规则、死亡特效概率或回合配色。
