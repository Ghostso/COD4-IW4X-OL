# Head-intact death animation weighting / 保留头部的死亡动画权重

Status: candidate on b0e0bf2; Factory and exact-build two-client FFA playtests PASS.

## Behavior / 行为

With the refined Factory profile enabled, ordinary deaths that retain their head
give the two ordinary death clips four times their previous weight. With all
seven clips admitted, their combined weight is40 and the five Tesla base clips
retain combined weight10: a20% aggregate Tesla share instead of50%. Selection
still uses the existing deterministic weighted cycle, not independent random
rolls. Missing clips change the available pool and its proportions.

Headless deaths retain the previous mixed base pool. Classified electrical
kills retain their existing separate Tesla sequence/FX path. No hit criteria,
damage, dismemberment, particle effects, corpse timing, scoring, wave ownership,
multiplayer protocol or animation duration changes.

开启 refined Factory 表现时，普通且未断头的死亡优先选择普通动画；完整资源池中
Tesla 基础动画总权重占比由50%降至20%。断头后的死亡及电武器序列保持原行为。
这些是重建表现的调参，不能视为原版概率。

## Evidence boundary / 证据边界

This is explicitly reconstructed tuning. The exact-build IDA/native-interface
and original-demo evidence remains in
[refined damage FX](factory-refined-damage-fx-20260922.md): Tesla BASE clips can
occur without full-body lightning, including after head loss. It does not
establish original server selection percentages. No new IDA result is claimed.

## Validation / 验证

The selector regression covers all seven weighted choices, the complete50-entry
tuned cycle, and unchanged explicit electrical selection. Existing production
damage fixtures retain the headless Tesla-base/no-lightning and true electrical
sequence checks. Seven canonical suites, the50ms server regression, Release
plugin build and source-evidence audit pass. Factory playtest accepted on AV,
DLL SHA256 41A1B0E2BB9A571AB09CCB99F5814F789119AF054E628CEC211FE943040468B3.
This is human gameplay acceptance, not individual automated visual assertions.
Exact-build two-client Nuketown FFA also passed; both real clients reached
Playing. No individual automated reciprocal combat assertions are claimed.
Factory/FFA live acceptance is distinct from source regressions.

Factory 与同构建双客户端 Nuketown FFA 实测通过；七项套件、50ms 服务端回归、
Release 构建及证据索引校验通过。无独立自动战斗断言。
