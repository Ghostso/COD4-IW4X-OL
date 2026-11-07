# September29 accepted arrival movement hold / 入场移动锁定验收

The earlier accepted adapter below omitted the native input hold. The new candidate
adds it under the same Factory entry opt-in. Exact original Factory playerstate:
first armed spawn20250 has pm_flags0x800;20350 adds0x20000000;23350 clears both.
The player remains at the authored platform until release. This establishes an
approximately3100ms hold at the recording's snapshot resolution. The existing FX
start at+100/+600ms and their carriers end at+3600/+6100ms, so movement resumes
before all arrival effects disappear. A Sumpf entry also records0x800 with the
effect, but its timing is not substituted for Factory.

Fresh exact-build CODOL IDA41CB40 at41CB97 tests ps+0xC bit0x800;41CDCA..41CDE3
masks command buttons with0x1300, zeros forward/right and velocity. IDA41AA90 and
419A20 keep normal view-angle processing unless the separate0x80000 condition is
present. Therefore this candidate applies the native movement flag, keeps normal
pm_type, and does not pin origin or invent a camera lock. The unrelated0x20000000
flag is not copied without a recovered purpose.

The hold begins inside the existing successful armed ClientSpawn transaction,
before the first Playing snapshot. Each client owns a3100ms clock and generation;
late join does not depend on the lobby's first player's clock. Ordinary respawns
do not replay it. Disconnect/rejoin and map reset reset ownership. The begin-frame
native-mirror failure restores the side owner together with playerstate. Expiry
clears only0x800, preserving a separate match-completion freeze owner. No native
player structure, netfield, source movement algorithm or FFA behavior changes.
Applying the solo measured duration to every cooperative slot is reconstruction.

Machine checks cover first snapshot, boundary release, staggered joins, subsequent
respawn, slot reuse and FFA exclusion. Seven suites and50ms pass; exact candidate Factory and two-client FFA playtests passed. This section supersedes earlier statements
below that the current adapter has no input hold; those describe the prior build.

原版Factory出生后约3100ms解除0x800移动锁定，早于入场特效结束。IDA确认该位由
原生Pmove消费，保留正常视角更新。每个合作玩家独立计时；普通复活不重播，FFA
不启用。将单人录像时序推广到合作槽位属于重建，同构建Factory与双客户端FFA实测通过。

# Factory class-confirmed arrival: evidence and accepted scope

Status: accepted on September 24, based on e1faa84. Factory and exact-build
Nuketown two-client FFA playtests passed. The original server entry controller
has not been recovered; the adapter uses native consumers and recorded data.
Enable with `OLMOD_FACTORY_ENTRY=1` on `zm` / `zm_factory_sh`.

This increment includes class confirmation, authored platform spawn/facing,
stationary arrival particles, recorded vision transitions and localized text.
Sound choreography, original camera/input lock and co-op admission policy are
not restored. Earlier candidate failures below explain corrected boundaries.

## September24: BG failure and BH response correction

BG failed the interactive class-confirmation test: the menu reopened after the
orange confirmation button. The session log records repeated valid `custom1`
responses with no pending loadout. Cancellation tokens were not the problem.
The Factory response table now names index1 correctly as `changeclass`, but the
old dispatcher accepts only the marines/opfor names, rejecting generic choices.

The accepted run recorded `index=1 menu=changeclass choice=custom1 accepted=1`,
then first Playing and particle events at +100/+100/+600ms.
A read-only census of the owned client verified native menu indexes0..5 and
bias0: ac130timer/changeclass/changeclass_marines/changeclass_opfor/class/
class_marines. Exact IDA5C9910/5DD4F0 independently resolve the responding menu
name by scanning configstrings before constructing `mr serverId index choice`.
Opening q2 does not prove every response carries index2. The generic UI route
must be recognized; raw index/name/choice/accepted logging now accompanies it.

BH opts into generic-class dispatch only for Factory with the corrected native
menu table. It accepts the same bounded custom1..5/class0..4 tokens, preserves
the current character faction, and leaves other maps' dispatch unchanged.
Back/cancel/noop/bad and invalid class numbers still cannot create a loadout.
Leave remains a legitimate match exit. No attempt is made to trap that action.

The regression now runs a generic `mr 0 1 custom1` through parsing and dispatch,
verifies it is rejected without explicit Factory policy, checks generic cancel
rejection, and checks subsequent armed spawn clears the waiting hide flag.
BG's earlier test used an already faction-specific response and therefore
missed this integration defect. This correction is not a new native timing
claim. The corrected Factory flow and exact-build FFA subsequently passed.

## September24: Class-confirmed entry candidate BG

Original five ZM recordings request q2 before spawn and dismiss r2 in the
spawn cluster. Exact out.exe IDA610A30/6111E0 -> 514880 ->661C50 and the shipped
common_mp NCS menu table resolve index2 to changeclass_marines (1 generic,
3 opfor). Solo10950..19950 waits with pm_type5,eFlags31;20250 becomes Playing
at the platform;20350 starts arrival FX. The delay is not a fixed timer.

Factory entry now suppresses diagnostic AUTO_LOADOUT even if the launcher
sets it. A real validated class response enters the existing loadout-resolution
and atomic spawn path. The Factory parser's menu-name indexes match NCS;
other maps retain the existing table. Invalid/cancel/back/noop responses cannot
commit a class. While first selection is pending, a rejected menu response
re-requests q2 once per response; this cancellation policy is reconstruction.
No timer repeatedly interrupts a valid selection. The accepted Factory playtest covers the corrected selection flow; the exact
original Escape policy remains reconstruction.

The transient world input carries this Factory-only policy without changing
native player/client layout. Waiting uses pm_type5 plus eFlags bit0x10.
Exact out.exe53C650 at53C6AA..53C704 tests ps+0xFC bit0x10 before calling
59CC70, whose weapon-kind9 branch can dereference a null viewmodel. That bit
keeps pre-class zero-weapon snapshots out of this unsafe draw path. Clear it
before a successful first atomic spawn; failed spawn remains waiting and
reasserts it. No random stand-in weapon or early playable spawn is supplied.
Only the required hide bit is restored, not every unrelated bit in retail31.

Tests cover multiple cancellation tokens, five seconds of valid non-playing
waiting snapshots, no collision/spawn, then armed confirmed spawn and removal
of the hide bit. The corrected Factory flow and exact-build FFA passed. Button color/click is not recoverable from server snapshots.

# Factory opening transition and localized text

Historical BF iteration on e1faa84; superseded by accepted BH above.
BE particles visually confirmed; its position/facing were incorrect.
September24 visual candidate adds fixed world-space arrival particles.
This restores vision/text and tests native world particles, not the entire arrival scene.
Sound playback, scripted camera and input-lock behavior remain incomplete.

## Evidence

Exact out.exe SHA256044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9;
IDA instance settled at35783 functions. 0x46CEF0 blends positive durations;
0x46CE80 is the instant setter. Three original Factory recordings agree on
N "zm_begin"100 followed400ms later by N "zm_factory_sh"2000.
These are vision commands, not relocation commands.

C-2021-7-31[15-32-16]zm: first player spawn20250. Current HUD text516..519
has births20500,21500,21750,23000; x10; y-192,-172,-152,-132; font11;
scale1.6; alignment0x8A/2; flags5; sort1. Colors00FFB240->FFFFB240
over300ms. All four fade out at40300 over500ms and are removed.
The decoder follows acknowledged snapshot baselines and checks exact message
consumption. Two other recordings prove vision timing but do not establish
these four text lines as universal for every native join.

Exact IDA0x538B70 consumes type1 text at+0x8C;0x538250 adds952 and resolves
through0x514880 before localization. Constant-string descriptor type4 at
0xDA9838 has base952 and one-based prefix1. The shipped localized_ui_mp
NCS includes ZOMBIE_STORY_INTRO_FACTORY1..4. The candidate uses the four
recorded Factory text identifiers, not authored replacement strings. The final Factory presentation passed its playtest on the installed asset set.

## Platform arrival and facing correction

BE live logs resolved model121/tag_origin root0 and FX147/174/173 and the
arrival particles were visually confirmed. Its spawn still selected the lone
mp_dm_spawn(-73,-54,8), not the four authored initial_spawn_points.
Factory MapEnts records81..84 contain (23,99,120)/yaw105,
(27,344,124)/yaw120,(-140,103,121)/yaw80,(-137,343,124)/yaw60.
The authored origins sit above the floor and must pass the existing native
standing-capsule ground trace; they are not final feet positions.

Original solo recording, exact baseline-aware decode: before20250 pm_type5
and origin(-286.5,-585,392); at20250 normal pm_type0,origin(23,99,94.125),
delta-yaw encodedAB4A=105.001831degrees. FX carriers appear100ms afterward.
At23350 flags clear and the player begins moving. This proves the platform
placement/facing for that solo entry, not a universal pre-arrival location.
The earlier92 description was the carrier-derived approximate floor, not the
actual first playerState Z94.125; raw playerState is authoritative here.

Exact out.exe IDA41CB40 calls41AA90, which calls419A20. At419AA5 native
view update adds usercmd angle*(360/65536) to deltaAngles(+0xB4+axis*4).
The existing atomic ClientSpawn already establishes that usercmd-relative
orientation. BF supplies the map's angle through that path; no repeated yaw
forcing, new Pmove patch or live scripted-position hold is introduced.

Only opted-in zm/zm_factory_sh substitutes its authored platform spawn pool.
Ordinary MP and connection parking are unchanged. Four unique records1..4
are required; malformed sets fail explicitly. Each goes through the original
world-capsule clearance/walkable-floor check. Existing deterministic spawn
rotation chooses among them in map order; its multiplayer assignment and use
on later respawns remain reconstruction, not recovered original policies.
There is no invented initial delay or extra teleport flash. Arrival timing
still starts at the first Playing snapshot and particles remain fixed there.

## Adapter and boundaries

### Stationary arrival particles (September24 iteration)

The proposed command5 screen-overlay candidate was built but never deployed.
It is excluded after the reference clarified that the lightning stays at spawn.
The native transporter-overlay research remains valid for a separate feature.

Original solo spawn is20250 at playerState(23,99,94.125). At20350, stationary scriptmover715
at(23,99,144) emits113/147 and716 at(18,118,154),yaw105 emits113/174.
At20850,716 emits113/173. Carriers716/715 disappear at23850/26350 respectively.
Current native FX names are fx_portable_teleporter, fx_zombie_spatial_switching_flash
and fx_zombie_spatial_switching, resolved by name in the active map.
Exact CODOL CG_EntityEvent0x532910 forwards113 to0x452D10/0x452970, decoding
nine-bit FX plus eight-bit composed bone and routing native attached particles.

The adapter creates two noncolliding stationary tag_origin models at first
Playing, queues existing tagged FX events after100/600ms, and frees carriers
at3600/6100ms. It uses the existing generation-checked world APIs. Player
movement never updates their transforms. The +52/+62 height and20unit forward
placement reproduce the solo relative positions; yaw rotation and first-Playing
alignment are reconstructed for other spawn slots. The current common model
band has a shared pointer at row114 (global121); tag_origin identity remains
inferred, so runtime resolves both model and named root bone and fails closed
if unavailable. There is no guessed numeric model/bone fallback.

Only resident names are resolved once per map, and only for the entry opt-in.
Missing assets suppress the effect and produce a bounded map-load diagnostic.
No screen-overlay command5, black screen, renderer hook or input lock is added.
The first temp-event adapter was rejected by its existing narrow validator.
The revised candidate uses the recorded scriptmover ring: table0xDA6828 fields
16(-75),17/22/23/24(-94), with existing sequence/event codecs. Generation/type
checks and the event113-only validity boundary remain fail-closed. No new
event entity or relaxed generic event whitelist is used. The final Factory presentation passed its playtest; exact original server
placement rules beyond the recorded solo case remain unknown.

OLMOD_FACTORY_ENTRY=1 enables this only for zm/zm_factory_sh. A source-owned
per-client clock starts at first Playing, preserving class, position, input,
audio, gameplay and native world structure layout. This readiness alignment
is reconstruction, not recovered original server scripting. It is once per
client slot/session, not every respawn; Free slots and map/reset clear ownership.
There is no new timer thread, asset scan, model rebuild or per-frame native call.

Recorded text offsets are relative to that clock. The flash is queued at4100ms,
then the map blend400ms after its actual enqueue, preventing a late frame from
collapsing both commands. Failed reliable enqueues are retried. Normal map
grading remains the pre-intro fallback; no black-screen overlay or input lock
is introduced. Existing5500ms first-round spawn delay is unchanged.

The existing HUD serializer aliases unused fields for FFA type-on effects.
Ordinary text with a nonzero fadeTime must retain its fadeStart descriptor10,
not reinterpret it as type-on birth descriptor28. Both writer and validation
now make this distinction. Existing FFA pulse fields and tests are preserved.
Entry rows are appended to the current HUD's contiguous prefix and removed
after20550ms; ordinary hit feedback and archival score/objectives remain intact.

## Validation

Focused checks cover line timing/layout, bounded lifetime, earlier clocks and
real snapshot serialization through ordinary fade fields. Canonical suites,
Release,50ms and source audit receipts are held with the local candidate.
Factory run759227953 and exact-build two-client Nuketown FFA run761313531
playtests PASS. Both FFA clients reached Playing; no individual automated
combat assertions are claimed. Seven canonical suites, Release build, 50ms
server regression and partial source-audit validation PASS. An initial local
networking suite failure passed isolated and full-suite reruns.
Tested DLL SHA256: 8468624778A59368C49AF5A3E5FD1B263389A0E7AEA9E1D19DE1E5C6D4CE08CF.
The native binary and underlying recordings/IDBs remain local. Startup graphics
reset failures were investigated independently with unchanged gameplay source;
local staggered FFA launcher recovery is outside this contribution.
No game binaries, original recordings, IDBs or launcher infrastructure belong
in this contribution. Both gameplay acceptance gates apply to the exact frozen build.

## 中文摘要

通过`OLMOD_FACTORY_ENTRY=1`恢复Factory入场选职业、地图原定平台落点、固定位置
传送粒子以及原始录像中的视效过渡和四行本地化文字。IDA确认菜单、骨骼特效事件和
HUD消费方式；录像与地图实体提供时序和落点。未选职业时保持隐藏且不可游玩，
有效选择后使用原有落地检测和原子生成流程。普通文字淡入淡出不再误判为FFA逐字效果。
首次Playing对齐、取消后重开菜单及多人落点顺序明确属于重建策略，不宣称恢复原版
服务端脚本；音效、镜头与双人Factory入场仍需继续验证。Factory、同构建双客户端FFA、
七组套件、Release、50ms回归和局部证据审计通过。启动器和原始二进制不属于本次提交。
