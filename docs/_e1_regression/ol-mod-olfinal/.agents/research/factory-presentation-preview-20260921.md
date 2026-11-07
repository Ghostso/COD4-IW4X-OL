# Factory outfit and death presentation preview

Status: accepted in Factory and same-build two-client Nuketown FFA; local commit
preparation. Release, seven repository suites and 50ms scheduler tests passed.
Accepted DLL: 2D1FFADB7755E5A7D8E062B51697E1C0EA2907A4AE077502E35355ABD2AF35D1.

The existing path selects one ordinary death and expires it at 2500 ms. This
opt-in preview resolves matched outfits and seven death leaves once at map load.
`OLMOD_FACTORY_PRESENTATION=1` enables it only inside the Factory zombies setup.
No model loading, table scanning, effect allocation or animation restarts occur
per tick. Empty configuration preserves the existing script-selected appearance
and death fallback. The live actor and player paths retain their existing wire
layouts; persistent actor corpses use a separate recovered eType21 writer.

Native evidence: exact CODOL out.exe SHA256
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9,
IDA 0x786E70 (leaf clock/clamp), 0x789570 (goal weight), 0x7888B0 (fade).
BO1 XAnimGetLength 0x7ED5C0 and Ghosts 0x14024F070 corroborate duration
semantics, not CODOL server death selection. Original July31 Factory recording
SHA256 a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97
has ordinary v1/v2 and Tesla a/b/c/d/e commands. Resident headers measure
2/2.2667/4.5/4.2667/4.5/4.2667/3.3667 seconds respectively.

Reconstructed policy: each clip gets its measured duration plus 250ms settling;
50% ordinary and 50% electrical over a deterministic 20-death cycle. This is
not the original hit-condition/weapon selector. Original captures also include
loop/down phases and earlier ragdoll handoffs; these remain excluded pending
sequence recovery. No head removal, blue blood, sparks or special-death sounds
are claimed by this animation-only stage.

The outfit sequence interleaves garbageman/worker/secunityguard and five body
suffixes, using only resident matching body/head pairs. It reproduces the earlier
preview mix. Missing pairs are omitted, never replaced with another outfit's head.
Native outfit weights remain unknown. Per-life sequence advances only on successful
spawn; rejected routes and unavailable slots do not consume a choice.

## 中文摘要

本候选仅恢复 Factory 的服装组合与已在原始录像出现的普通/Tesla死亡动画。
按地图加载时解析名称，逐帧不扫描资源。模型与头部配对，缺失资源安全跳过。
服装比例、死亡选择与结束缓冲为明确的重建策略，不能称为原版服务端控制器。
原始循环/倒下/布娃娃链路、爆头拆件、蓝色血液及火花效果尚未实现。
Factory 与同构建双客户端 Nuketown FFA 实测通过；未发布。

## Retained corpses and collision / 尸体保留与碰撞

After its selected death clip, the same entity changes from actor19 to corpse21.
Exact-build IDA 0x530BB0 selects presentation ownership and 0x530AF0 transfers
the 0x2AC-byte record and six animation-tree pointers. The separate corpse
descriptor table starts at0xDA60E8 with12-byte rows. Original Factory recordings
show a32-slot corpse pool and same-snapshot replacement; they do not establish
the original victim-selection algorithm. The implemented100seconds from death,
maximum32 and oldest-first replacement are explicit reconstructed policy.

Corpse ownership uses generation-qualified handles outside the guarded player
layout. Conversion releases the live agent slot and stops live actor animation
commands, pursuit and damage registration. Slot replacement is rolled back if
the native mirror or victim removal fails. Map reset clears retained ownership.

The initial retained-body candidate omitted descriptor36 (+0xAC,24bits), so
server unlink alone could leave client collision state inherited from the actor.
Exact IDA0x46DAE0 reads centity+0x1A0 (entityState+0xAC) and skips collision when
zero. The corrected writer explicitly emits zero across19-to21. The first
terminal-health frame also clears live actorField00AC, solid and collision
contents, covering the falling animation before corpse conversion.

Synthetic tests cover33 conversions, slot reuse, continuing allocation,
100second expiry, rejection/rollback and packet admission. An independent
field-reader check on the emitted transition confirms explicit field36=0,
clearing an inherited0x68010F capsule with complete packet consumption. These
checks are not natural gameplay traces. Factory and exact-build two-client
FFA playtests passed; both multiplayer slots were separately observed Playing.
Individual combat actions and corpse lifetime/cap timing were not separately
instrumented. The253 source/test C/C++ files match the frozen tested package.

This does not implement neck spray, torso destruction, head removal, original
damage-dependent death choice or complete ragdoll chains. Other campaign modes
were not playtested; do not extrapolate the Factory/FFA result to all modes.

尸体使用独立的21类型描述符与原生客户端表现所有权转移，释放活动agent槽。
死亡起始即清除碰撞，19到21转换显式发送solid零值，避免客户端继承活动碰撞。
最多32具、死亡后100秒及最早死亡优先移除为重建策略，不是已恢复的原版淘汰算法。
结构/线协议检查与实机验证分开记录；Factory和同构建双客户端FFA通过。
颈部蓝色喷溅、躯干破损与原版伤害条件选择仍待恢复，其他战役模式未实测。
