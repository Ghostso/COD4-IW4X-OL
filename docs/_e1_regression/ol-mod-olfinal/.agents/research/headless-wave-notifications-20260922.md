# Preserve headless timer-death notifications

Status: isolated fix on published e384059; Factory and same-build two-client FFA
playtests passed on AU, DLL SHA256
8C62165228B012C8184D6267994607613AFFF46A7BA00AF9A0A5CCC28CBFBA42.
Damage-number work is preserved separately and excluded from this change.

## Failure and scope

In Factory a zombie can lose its head, survive briefly, and die from the existing
bounded timer damage. That timer runs in stepActorEntities before beginFrame
rotates its event vectors. appendEntityDamageEvent previously appended its
EntityDamage/EntityKilled notification to the old frame vector. Rotation removed
the event before the Lua director could consume it. Health, animation and corpse
ownership advanced correctly, but the living counter did not decrease. Four such
deaths filled the compatibility population limit and prevented more spawns.

The observed run recorded20 births and16 director deaths. All four missing
notifications corresponded to headless timer deaths followed by retained corpses.
Both published OLfinal-live tips were verified at e384059 when investigated.

## Correction and evidence boundary

Only the pre-rotation headless timer producer selects the incoming begin-frame
queue. The existing rotation delivers it in the same accepted frame; on native
mirror rejection the existing rollback retains that incoming queue for retry.
Ordinary command damage keeps its current-frame delivery. No timer, probability,
model, animation, collision, scoring, wave-size or population-limit change.

This is a correction to ol-mod's event adapter, not a recovered CODOL native
queue or new original-game rule. Existing g_run_frame reference review documents
BO1 G_RunFrame0x62B320 and Ghosts G_RunFrame0x140131C80 placing entity/script work
before client projection. The precise vector ownership here is OLMOD-specific.
Existing exact-CODOL hit/FX/animation evidence remains in
[the death-FX review](factory-refined-damage-fx-20260922.md); it does not prove
these project queues or the reconstructed headless probabilities native.

## Verification

The new delayed-death event assertion fails on otherwise unchanged e384059;
the other six canonical suites pass. The old headless test checked terminal
health only, leaving script notification delivery uncovered.

The extended regression checks partial timer damage, exactly one terminal event,
victim generation, attacker and event time, including a rejected terminal frame.
All seven fixed suites, the50ms source run, Release build and source-audit
validation pass. Factory and same-build two-client Nuketown FFA playtests pass.
Factory logs reached round3, with78 births and14 head-loss/death lifecycles each
receiving one director callback. The log correlation does not distinguish every
timer death from a finishing shot. Both FFA clients reached Playing; individual
reciprocal combat outcomes were not separately instrumented. No earlier build
PASS is inherited. Local launchers, recordings, binaries and IDBs are excluded.

## 中文摘要

修复无头僵尸延迟死亡事件在帧切换时被丢弃，导致波次仍将尸体计为存活的问题。
仅将帧事件切换前产生的通知交给已有的待接收队列；普通武器伤害路径不变。
原生镜像拒绝一帧时保留通知，下一成功帧只派发一次。不改变死亡特效、概率、
计时或生成上限。此处修复的是项目事件归属边界，不宣称恢复了原版通知队列。
