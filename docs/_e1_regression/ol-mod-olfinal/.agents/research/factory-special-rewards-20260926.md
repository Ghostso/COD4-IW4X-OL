# Current review status — September27

The combined CL gameplay source has Factory feature acceptance and exact-build
two-real-client Nuketown FFA acceptance. Historical candidate status and failed trials below describe
their own snapshots; current publication status belongs to AGENTS.md.

Known unresolved performance defect: the accepted feature test recorded
about138ms average fixed-frame cost late in the run, dominated by begin/end
work. Slow frames predate equipping Tesla. Network/trace costs were small;
no logged native fault or pool exhaustion was established. The process exited
before live profiling. This contribution does not claim to fix that slowdown.
Separate monkey speech, rail flash timing and reload appearance remain unknown.

当前CL功能与同构建双客户端FFA验收通过。已知Factory性能问题未解决；以下历史记录不构成
当前版本的性能或多人模式通过证明。

---
## September27 CL: Wunderwaffe ammunition-dependent tube lighting

CK feedback confirms box sounds, monkey extra audio, traps and pickups. Reload
appearance and separate monkey speech remain uncertain; no blanket acceptance
or inherited FFA PASS. CL changes presentation only and needs a new playtest.

Original July31 Factory demo SHA256
a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97:
2,459 snapshots decode exactly through259000ms. At215050ms the server publishes
cs4537="183tag_brass" and repeatedly emits eType140, parm2, every100ms.
Clip1143 has3 rounds. At221350ms clip becomes2 and cs4539="184tag_brass"
appears with parm6. At248750ms the next spent round selects cs4540=
"186tag_brass", parm8. Common ZM NCS entries and the existing effect namespace
identify tube_view, tube_view2 and tube_view3; production resolves these names
rather than hardcoding their indices. Slots are allocated without replacing
occupied configstrings. No loop/animation-tree is created by the server tick.

Fresh IDA, exact out.exe SHA044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9:
532910 case117 targets local DObj2048+(parm&1);5328D0 reads configstring
4536+(parm>>1);452A00 parses the effect number and tag;531A40 resolves the
actual DObj bone and invokes bolted FX. Native event names atDAEA98/DAEA7C
identify play/stop viewmodel FX. This is a client attachment, not a world emitter.
The py_eval MCP method was unavailable; direct decompile/disassembly succeeded.

CL admits only eType140 through the existing event descriptor/writer, archives
source-only recipient metadata and filters current AND baseline entity lists.
Unowned events fail closed. Generation checks and existing300ms event cleanup
bound retention; emission is at most one per100ms per active Tesla holder.
WorldClientState/native ABI, FFA rules, weapons, damage, reload speed and FOV
are unchanged. Ordinary guns receive no effect. Reload updates use actual clip
counts. Six-round upgraded Tesla behavior is outside this candidate.

Tests cover owner-only bytes, a missing owner, changed baseline ownership,
invalid slots, repeated publication and retirement. First lifecycle assertion
incorrectly required all pre-existing unrelated transient events to survive;
corrected it to require no retained view FX and no increase in entity count.
This fixture correction is not evidence of a gameplay leak.

Limits: rail_view/tag_flash is also recorded (cs4538,parm4), but its exact
trigger differs from a simple shot-only rule; leave that flash unmodified until
the timing is established. Do not claim all weapon lighting is restored.
Dedicated Ray/Tesla reload assets exist but the reported odd appearance has not
been reproduced or attributed to FOV. Three CODOL monkey song files exist;
separate child speech remains unverified and no campaign voice is substituted.
Local evidence: factory-special-followup-20260927/CL-retail-presentation.json,
CL-tesla-events.json, CL-viewfx-events.json and ida-cl. Native media/IDBs stay local.

CL恢复原生Wunderwaffe弹药数量对应的灯管效果；仅发送给持有者，当前帧与基线均过滤。
Factory/FFA人工验收待定。枪轨闪光触发、独立猴子语音及换弹外观问题仍未确认。

## September27 CK: sound registration and reach correction candidate

CJ focused playtest confirmed the grounded monkey animation, shrink trap/contact
kills and descending rewards. It rejected excessive radius reduction and choppy
box shake; monkey song was absent. Exact CK Factory/FFA remain pending.

Dedicated log at14:57:00 resolved monkey model248, animation294, tree11,
but song0. A resident sound asset is not a networked alias registration. Original
Factory gamestates have cs3625=zmb_box_lp, then live commands publish sound names:
July31 cs3674=zmb_box_open,3675=zmb_music_box,3676=zmb_box_cycle,
3677=zmb_box_select,3678=zmb_box_close. August30 uses3676..3680 for the
same sequence. Therefore name-to-index assignment is server-owned and varies
by match. Extracted only gamestate/command records, not a new snapshot analysis.

CK registers missing box cues and zmb_monkey_song in the existing dynamic
sound band after every connected client is Active, following the existing sound
registration boundary. Slots50..90 avoid the ordinary hit/kill aliases24..28;
occupied slots are preserved, equal names reused, exhaustion fails closed.
Assignments stay in the source gamestate for later joins, reset with the match,
and remain Factory/interactables-only. No protocol fields or client ABI changed.
The allocated order is reconstructed, not a replay of retail's indices. Native
IDA514540 verifies the live CCS update guard and IDA410BD0 confirms linear-stop
trajectory evaluation. Fresh decompilations retained locally. A read-only live
slot probe failed safely because the previous client was already closed; it is
not evidence of slot values. Retail commands supply the dynamic-band evidence.

Fire/shock radius becomes base/3+12 (about95.33 units for base250). Twelve units
are a practical interpretation of approximately one foot, not recovered native
damage tuning. Boundary tests include94 and exclude97. The failed lateral shake
is removed entirely: both box pieces keep their previously accepted continuous
50-unit/five-second native rise. Exact CODOL shake is still unrecovered; no
replacement shaking animation is claimed. Resident teddy selection/raise,
departure, announcer, poof and arrival cues retain their existing boundaries and
can now register when missing. Monkey speech remains unavailable; its song
playback and the restored box cues require fresh audible confirmation.

Regression: sound allocation reuse, occupied-slot preservation and exhaustion;
radius boundaries; existing lifetime/contact checks retained. Initial test build
failed after removing a numbers include still used by reward alignment; restored
it without changing alignment. Record final machine and human gates separately.

CK候选：补齐Factory动态声音注册，缩小后的伤害半径增加12单位，移除卡顿横移
并保留原生连续上升轨迹。猴子语音未恢复；歌曲及箱体音效需重新实测。

## September27 CJ: monkey presentation, trap reach and box audio candidate (historical)

CI trap effects were visually accepted in focused feedback; overall Factory
and exact-build FFA acceptance for CJ are pending. CJ preserves the native
ground effects and offer descent. Fire/shock damage radius is one third of
the configured base radius (250/3 units with the fallback), explicitly
reconstructed tuning. Freeze/shrink/monkey radius and weapon combat are unchanged.

The resident CODOL assets include weapon_zombie_monkey_bomb, o_monkey_bomb,
animtrees/zombie_cymbal_monkey.atr and zmb_monkey_song (song00/01/02.wav).
The grounded missile keeps simulation ownership while a generation-owned
script model plays the animation; its duplicate static snapshot is suppressed
only after the presentation tree and animation bind successfully. Expiry retires
both the animated model and attraction target. This follows BO1's separate
grenade/model pattern using CODOL assets and the existing recovered tree adapter;
it is not a recovered complete CODOL monkey script. Song playback is pending
live verification. No zmb_vox_monkey_explode alias was found in the inspected
OLfinal zones; monkey speech is NOT claimed restored. Other monkey-named
localized campaign strings do not establish the correct zombie voice asset.

Box sounds now use positional event entities at the active site. Opening keeps
the demo-supported zmb_box_open/zmb_music_box pair; closing uses zmb_box_close.
Asset inspection maps zmb_box_select to box_bear_select.wav, so ordinary rewards
no longer play it. Departure adds resident zmb_vox_ann_magicbox and arrival adds
zmb_couch_slam using BO1 choreography as a reference. The five-second rise gains
a bounded horizontal sinusoid (amplitude10, period500ms), shared by lid/base.
Exact CODOL shake and added cue timing remain reconstructed. Bear, departure
and relocation branches precede buyer-liveness validation; sound origin uses
the new site only after arrival commits. This disconnect behavior is reviewed
in source, not claimed as a completed multiplayer playtest.

Fully shrunken actors can be killed by a moving living player's authoritative
touch after the500ms shrink ramp. Attribution and normal damage notification
are retained, protection flags respected, and dead actors cannot score twice.
Regression checks stationary touch, movement without touch, and one credited
moving-contact kill. Only a contact from the current simulation frame qualifies;
an early touch cannot linger and kill after the shrink ramp completes. The
additional stale-contact regression covers this review correction. Tests inject
the touch array; live native contact generation
still needs confirmation. No collision-capsule resize or recovered native stomp
algorithm is claimed. Existing shock target connector beams remain deferred.

Local provenance: FACTORY-FOLLOWUP-HANDOFF.md and asset scans in the classic
research workspace; copied evidence is kept outside Git. Seven suites pass,
including radius80/90 boundaries, stale contacts and monkey lifecycle checks.
Release and50ms checks pass;192-entry source-audit validation passes and remains
partial (not a full native audit). Factory and exact-build FFA remain pending.

CJ候选：火焰/电击半径缩至原配置的三分之一；猴子使用原生模型、动画和歌曲，
语音尚未恢复。箱体声音改为位置事件并加入重建晃动；缩小僵尸接触击杀通过伤害事件。
接触输入的回归测试不等于原生现场验证。Factory及同构建FFA验收待定。

## September27 CI: grounded traps, actor shrink and descending offers (historical)

CH playtest confirmed Ray Gun, Wunderwaffe and monkey behavior, but rejected
spinning trap presentation, missing trap effects and invisible shrink. CI is
a new candidate; Factory and same-build FFA acceptance remain pending.

Original Factory demo C-2021-8-30[22-12-10]zm
(SHA256 af211ec38566127a9c5676bd61d06e4ab3bcc6ec2c51c4e2e342543913e09b80):
fire1144 at289500 lands upright at(189,1073,5); emitter534 at289600 uses
event113/167, origin+14Z, angles(-90,0,0), model121/tag_origin. Freeze1145
at615150 uses emitter471, effect145, +5Z. Shock1146 at987700 and994300
uses effect189, +20Z, with the same axis. All three retain non-spinning
flight yaw and land at pitch/roll0. Sumpf C-2021-8-30[21-43-53]zm shrink
deployment940150 uses effect172 at device origin. Actor875's wire+54
steps .95,.85,.75,.65,.55,.5 across944150..944650. Source previously wrote
the unused mover modelScale field; CI writes actorField0054 and ramps it.

Read-only exact-build client effect table resolves167 to
maps/zombie/fx_zombie_fire_trap_med_sh,145 to
maps/zombie/fx_freeze_trap_active_loop,172 to
maps/zombie/fx_zombie_shrink_trap_looping. Common-ZM constant list maps189
to maps/zombie/fx_zombie_wire_spark. IDA out.exe452970 decodes low9 effect
and high8 bone into the1C243BC table;452D10 dispatches through5319B0.
Original byte-exact snapshot counts:2672/7453 for fire/shrink,10011/6340
for shock/freeze. Native files and full captures stay local.

CI removes grenade spin from trap throws and settles both tilt axes on
ground contact. A generation-qualified presentation owner creates one root
carrier per grounded trap and removes it after missile retirement. No event
replay per pulse, added native pose loop or unbounded carrier allocation.
Shrink reaches half size over500ms; repeated pulses refresh the existing
two-second status instead of restarting the ramp. Damage radius250, pulse
damage100/500ms, status duration,4x shrink vulnerability and general combat
remain reconstructed. Shrink-specific collision/stomp and shock's targeted
electro connector beams are NOT restored by this presentation correction.

All box reward types now descend40units over the existing reconstructed
ten-second offer window. Native linear-stop type3 is confirmed by IDA410BD0;
the chosen rate is reconstruction, not recovered CODOL script timing.
Claims and expiry retain the prior box owner and reward-specific alignment.

Regression development: corrected a bare-number freeEntity test call and
an incorrect expectation that actor's unused mover scale should be1 (it is0).
A persistent-FX test initially removed the input callback, causing the owner
to enter WaitingForLoadout; trap retirement was correct. Keeping the no-op
input callback permits the actual lifetime/cleanup check. Tests distinguish
source assertions from pending client visual acceptance. Launcher-only Stereo
config recovery is outside this gameplay contribution.

CI final checks: seven suites, Release,50ms and192-entry partial source-audit
validation pass. One parallel run failed localnetworking; isolated execution
and the unchanged complete rerun pass. That failure is retained, not treated
as explained. Human Factory/FFA remain pending.

CI按原始录像恢复四种陷阱的静止朝向及发射器位置；缩小效果写入actor+54，
而不是mover字段。神秘箱奖品在现有重建的十秒领取窗口内下降。
伤害范围、持续时间及部分连接电弧仍属重建/未恢复；Factory及同构建FFA待验收。

# Temporary Factory special rewards — September 26, 2026

Status: opt-in experimental reconstruction. Machine checks do not establish
retail behavior or visual acceptance. Factory and same-build FFA are pending.

## September 27 CG missing items and CH collision-view correction

CG's throw animation completes in the playtest, but thrown items disappear.
Two trap_fire_zm releases at00:58:31/42 are followed by native mirror refusals:
mirror363 versus query359 entities. The missing four entries are the actors
excluded from the navigation collision view. `rebuildCollisionView` publishes
`bulletCollisionEntities_` to the native mirror, while the new special-flight
adapter incorrectly supplied `collisionEntities_` to BulletLocational.
`nativeServerEntityMirrorMatches` correctly rejects this different view;
the special step's missing-trace fallback then retires the projectile.

CH passes the existing complete bullet view for special flight and monkey
world-only visibility. It neither relaxes the mirror guard nor adds per-item
mirror rebuilds, pose evaluation loops or new native calls. The extended
whole-world regression reproduces the old view mismatch with a live actor
present and checks that outgoing trap/monkey entities survive flight and
floor contact. These checks exercise source publication; client rendering
and native collision geometry still require a new Factory playtest.

The equipped class items logged as unsupported are throwingbat_mp983 and
tabun_gas_zhunt_mp976. They are not evidence that the box trap release failed;
their combat/presentation paths remain unimplemented. No substituted frag or
flash behavior is claimed for them. CG has no overall acceptance or FFA PASS.
Native evidence remains the earlier IDA work; this correction is established
by runtime logs and the source/native adapter contract, not new decompilation.

CG投掷动作正常但物品消失：模型射线使用了缺少僵尸的导航碰撞列表，原生镜像
校验因此拒绝查询。CH改用已有完整弹道碰撞列表，保留安全校验及性能边界。
throwingbat/tabun装备仍未支持；新的Factory及FFA验收待定。

## September 27 CF failure and CG correction

CF failed its Factory playtest: inconsistent Ray contacts, missing visible
surface impacts and canceled-looking offhand animations. No FFA acceptance.
The runtime recorded eight Ray impacts; three used client entity0 as the direct
target. The filter passed the missile as `passEntityNum` and shooter as
`passOwnerEntityNum`. The existing filter excludes owned children/siblings,
not the parent entity itself. CG passes the shooter as the ignored entity.
CG also requests the existing bounded BulletLocational trace: CollisionOnly
skips actor ScriptModelDObj hitboxes and static-model tracing. Existing broadphase
and pose-cache boundaries remain intact; no full-actor pose loop is added.

Fresh CODOL IDA reads of descriptor table0xDA8520 establish field57={4C,11,0},
field77={400,24,0}, field79={48,-16,0}. PM_OffHandPrepare429640 sets flag2;
429450 sets grenade entity2047; Hold4297D0 loads the definition's fuse;
429960 enters release,429AE0 emits73,429B90 clears flag2. The snapshot writer
previously omitted these prediction fields. CG projects them with independent
retail-table decoder checks for set/release deltas and exact packet endpoints.
Native32-bit reads validate before narrower source storage. Source killcam
IDs use uint16 (still wider than their11/11/8-bit wire domains); split24-bit
flags reuse available storage. WorldClientState remains25184 bytes: its size
guard was not relaxed. All existing killcam wire golden tests still pass.

Evidence correction: the first text search missed event73 inside the event-ring
dump. CF did release trap1145 at23:27:27; it is incorrect to claim all throws
failed before release. The observed client animation interruption is consistent
with omitted prediction fields. Live confirmation of CG remains pending.
Class equipment983/976 differed from registered base offhands. CG validates and
registers equipped named frag/semtex/flash/concussion/EMP/smoke variants using
their own native definitions, logs unsupported names, and caps release reports.
Exact tactical/trap effects remain reconstructed as documented below.

Wunderwaffe1143 registered successfully in CF. Four claimed rewards were
freeze/MaxAmmo/monkey/Ray; this is insufficient evidence of a selection defect.
Its award weight remains10, independently of the deliberately rarer preview.
CF showed no repeated world-frame rejections during play; that establishes only
that the previous fractional-origin regression did not recur in that session.

CF未通过人工验收。CG修正射手过滤、模型碰撞与投掷预测字段；IDA表和独立解码
验证支持字段布局，不代表全部特殊武器行为已还原。节点大小保持不变。

## Evidence and boundaries

The five original recordings contain 46,664 decoded snapshots. Factory final
offers establish four traps and Tesla; Prototype also establishes Ray Gun,
Max Ammo and Bowie. A monkey final offer has not been established. Native
definitions/models exist for the seven implemented special weapons, including
the monkey. Cycling appearances are not treated as final reward eligibility.

Exact client: out.exe SHA256
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
Fresh IDA 429AE0, 429E10 and 42C510 establish offhand event 73, slot selection,
and native PM ammo consumption. IDA 532910, event 98 at 536467..5365AC,
establishes weapon-dependent explosion presentation. This does not prove that
every special item originally used that event, these projectile speeds, or
these server damage rules. No original special-weapon server controller has
been recovered by this change.

Native fields are read using the existing verified WeaponDef layout and
runtime name lookup. No captured numeric asset index is a runtime constant.
Native binaries, IDBs and original recordings remain local.

## Opt-in pool

`OLMOD_FACTORY_RECONSTRUCTED_POOL=1`, together with the existing Factory
interactables option, replaces the class-derived pool with this catalogue:

| Reward | Relative weight | Experimental behavior |
| --- | ---: | --- |
| Ray Gun | 10 | Traced projectile; native definition damage, radius 160 with falloff |
| Wunderwaffe | 10 | Traced projectile; at most ten chained cyborg kills, range 250 per arc |
| Fire trap | 15 | Grounded trap, 100 damage per 500 ms pulse within 250 |
| Freeze trap | 15 | Grounded trap, refreshes a two-second movement freeze |
| Shock trap | 15 | Grounded trap, 100 damage per 500 ms pulse within 250 |
| Shrink trap | 15 | Half-scale target and temporary fourfold direct-hit vulnerability |
| Monkey | 5 | Grounded distraction within 600; explosion after eight seconds |
| Max Ammo | 15 | Existing distinct inventory refill, without replacing a gun |

These are relative weights, not confirmed percentages. Ownership, missing
definitions and full ammunition filter eligibility and renormalize the pool;
teddy relocation remains a separate outcome. All weights and combat timing
are provisional unless separately tied to a resident field below; they are not recovered CODOL server scripts.
The native `ray_gun_zm` versus `ray_gun_fire_zm` relationship remains unresolved.
Bowie is excluded until it has a validated melee grant/use owner.

## Transaction and lifetime ownership

Offhand grants replace only the selected equipment slot. They preserve guns,
unchanged equipment counts and the current life, validate private ammo slots,
and round-trip through native player-state projection before publishing.
Native PM consumes ammunition; the adapter does not consume it a second time.

Projectiles use existing staged missile ownership. Impact damage runs after
successful native mirror publication and feeds existing kill/score/round
notifications. Dead targets cannot generate repeated kill awards. Wall traces,
owner life and actor lifetime are checked. Projectiles expire after three
seconds; thrown traps/monkeys use the resident eight-second fuse; pulse scheduling never bursts to catch up after
a stalled frame. At 32 active missiles the experimental shot is discarded
rather than rejecting player movement. This saturation policy is provisional.

Factory-only lookup keeps ordinary multiplayer on its existing handlers.
No netfield, native entity ABI or native client-state layout is enlarged.

## Remaining acceptance work

Verify every inventory grant, native viewmodel/fire animation, equipment input,
projectile display, damage, wall blocking, cleanup and round progression in the
live build. Trap-specific activation FX/audio, monkey animation/audio, original
shrink/stomp behavior and exact electrical propagation remain incomplete.
Freeze currently stops movement without a recovered frozen-animation sequence.
The candidate must not be described as restoration of the complete native pool.

Focused regression checks cover weighted eligibility, repeated equipment
exchange/rollback, projectile wall contact, expiry/pulse bounds, owner-life
rejection, blocked damage, bounded chain range and one kill notification.
Historical prototype checks do not count as acceptance of this follow-up.

临时重建奖池为显式选装功能。资源、装备字段及事件载体有原生证据；权重、伤害、
范围、时序及部分特殊行为仍为临时策略。机器测试不代表原版一致性或人工验收。
Factory和同构建双客户端FFA待验收；未提交、未推送。

## September 27 follow-up: Ray impacts and ordinary offhands

Status: new candidate based on accepted mystery-box commit bc09068. No human
Factory/FFA acceptance yet. Deferred teleporter/PAP code remains excluded.

**Observed failure and verified cause.** Archived run967169484 records a Ray
claim (weapon1139) at21:56:15 followed by repeated WORLD FRAME REJECTED messages.
This correlates with the reported slowdown; it does not alone prove its cause.
A regression then reproduced a deterministic cause: fractional impact coordinates
fail SV_ProjectGrenadeExplosionEntity and reject the world frame before impact
damage/retirement. The old fractional-wall test fails. Truncating only the event
origin makes it pass; precise origin remains authoritative for damage. The new
whole-world regression checks damage, event98, projectile removal and a valid
snapshot together. Its first attempt incorrectly called clientThink outside a
frame; correcting the fixture to begin/think/end followed by another frame
produced the expected pass. No validator was weakened.

Fresh independent IDA databases completed auto-analysis before exporting:
CODOL out.exe 429AE0/429E10/42C510 and CG_EntityEvent532910;
BO1 Windows x86 G_ExplodeMissile62E5B0 and G_RunMissileInternal62FDC0;
Ghosts PS4 x64 G_ExplodeMissileInternal140134690,
G_RunMissileInternal140136D10 and Weapon_Throw_Grenade14016BEA0.
BO1 62E76D..62E789 and Ghosts140134C3F..140134C68 truncate explosion
coordinates toward zero. CODOL event98 consumes weapon-specific FX at
536467..5365AC. This supports the publication repair, not exact Ray combat.

The existing CODOL launch adapter reads speed2616, upward speed2620, fuse2284,
cooking3811 and timed-detonation3837. Captured resident traps and
zombie_cymbal_monkey have speed800, upward100, fuse8000 and timed=true.
The actual throw path now calls that adapter, preserves PM's already-cooked
remaining timer, then clears only the staged native timer. PM owns ammo use.
Launch visibility delay is not a reason to retire the missile: simulation uses
the trajectory clock. A regression covers a25ms tick before a38ms visibility
delay, frag reflection, Semtex sticking, unchanged fuse and valid detonation.
Bounce retention0.45 and angular toss120/75/0 remain reconstruction.

Resident frag, short frag and Semtex use native validated blast radius and
inner/outer damage. Flash/concussion/EMP use a provisional two-second cyborg
movement stun. Smoke publishes the weapon effect carrier and does no damage;
persistent smoke presentation/AI concealment are NOT proven complete. These
ordinary-offhand continuations are enabled only with the opt-in Factory pool,
not multiplayer. Trap activation visuals and monkey choreography remain open.
Native per-item weapon errors, fire/reload presentation and runtime stability
still need the focused live test; unit success is not native parity.

The box uses a separate preview RNG. Tesla preview weight1 versus8 for each
other preview reduces its cycling frequency without changing reward weight10
or mutating the reward RNG. Consecutive repeats are excluded where possible.
This visual policy is explicitly requested reconstruction, not recorded odds.
A committed impact emits one bounded diagnostic record (weapon, kind, direct
hit, target count, damage); trap pulses do not emit per-frame logs.

中文摘要：本轮修复小数爆炸坐标导致整帧被拒绝，并接入已有原生投掷/计时适配。
整帧测试验证伤害、事件与导弹释放共同成功。特殊武器战斗及震撼/烟雾部分语义
仍为重建或未完成；神秘箱预览权重独立于奖品权重。新的人工Factory/FFA验收待定。
