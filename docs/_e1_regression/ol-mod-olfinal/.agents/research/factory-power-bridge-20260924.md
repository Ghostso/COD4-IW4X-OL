# Factory power switch and bridge motion

Status: accepted candidate based on2190239. Factory and exact-build two-client FFA passed.
Enable `OLMOD_FACTORY_POWER_MOTION=1`; admitted only for `zm/zm_factory_sh`.
This increment deliberately leaves purchased perk effects and teleporters for the
next changes. No binaries, recordings, IDBs or local launchers are included.

## Native evidence and reconstructed boundaries

Exact out.exe SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
Fresh IDA MCP decompilation of0x410BD0 on a settled35783-function database
confirms the plain36-byte trajectory evaluator and types0/3/7/8. The existing
native evaluator adapter is reused; this adds no native call ABI or netfield.

Original Factory recordings C-2021-7-31[15-32-16]zm,
C-2021-8-30[20-21-43]zm and C-2021-8-30[20-34-14]zm show matching switch and
bridge activation epochs. Qualified decoding covers27555 exact snapshots and
stops each object's lifetime before entity-slot reuse. Data was preserved in the
earlier independent build; the seven records were rechecked against their pinned
qualified inputs before this port. These are observations of the original game,
not recordings of reconstructed tests.

| Piece | Entity | Brush | Motion |
| --- | --- | --- | --- |
| Switch cabinet |343|model|off housing changes to powered housing|
| Power lever |344|model|powered named model; rises6units over300ms|
| Electric doors |494/495|176/177|recorded lowering over1000ms|
| Bridges |473/474|169/170|initial-90/+90pitch; lower to0over4000ms|
| Bridge blockers |481/482|171/172|retain until bridges finish|

The native start timestamps select phases; snapshot delivery time does not add
pauses. Both server collision poses and client trajectories use the same evaluator.
Model indices are resolved by name: `zombie_power_lever_handle_arm03_off` becomes
`zombie_power_lever_handle_arm03`, without copying session-specific sound/model IDs.

The controller remains reconstruction. In particular, deleting the blockers after
4000ms is the chosen endpoint policy; absence in a demo alone cannot prove native
collision unlink timing. No recovered original server power script is claimed.
Switch/bridge sounds beyond the authored steam group remain deferred.

## State ownership and failure behavior

All eight entities must match their entity number, brush/model and authored origin.
Generation handles prevent writes into recycled entities. Initial state is raised
and blocked. Activation stages all changes, synchronizes the native mirror, and
only then publishes logical power through the existing use-switch route. A rejected
mirror update rolls the geometry back and allows a later switch retry.

The power owner suppresses the ordinary door-opening owner for its electric doors.
Existing trigger consumption and zone unlocks remain. Blocker retirement clears
server linkage AND client brush-solid fields; hiding a brush alone is insufficient.
A frame that skips the final motion boundary still settles every piece. Once
complete, the controller does no per-frame geometry updates. Map reset clears it;
the disabled option and other maps preserve their existing paths.

## Validation scope

Focused checks cover raised initial geometry, exactly-once activation, rejected
mirror rollback/retry, sparse-snapshot versus native phase timing, blocker retention,
skipped-frame endpoints, client/server blocker removal, missing-piece refusal and
map/option isolation. These checks do not establish live rendering or crossing feel.
Release, seven canonical suites,50ms regression and source audit passed.
Factory run784165718 and exact-build two-client Nuketown FFA run784947031
playtests passed. Both FFA clients reached Playing; individual automated combat
assertions are not claimed. The opt-in remained enabled during FFA to exercise
map/mode isolation. Gameplay sources were verified against the frozen candidate.
Accepted DLL SHA256:
`127C06F080C7E73A1EEFFBBAEDFBFAC159DEBDD2A2743C7483EBFB84AABBA407`.
Local receipts, binaries and launcher infrastructure are excluded.

## Powered cabinet and native bridge steam

Factory `elec_body` is entity343 at(570.5,-1799.5,57), separate from lever344.
The common-zombies asset band contains `codo_asylum_electric_switch_off` and
`codo_asylum_electric_switch`, with the powered glow material. The original
power-on snapshot changes the cabinet model. That baseline-dependent model
delta does not recover an absolute index; both models are resolved by name.

Original C-2021-7-31[15-32-16]zm at173250 publishes `d 11992 500`, then
entity484 eType153/eventParm2 (power epoch173200). Exact-build IDA532910 case130
resolves11990+eventParm and calls43E5B0 to schedule the authored group. IDA43C9B0
confirms the108-byte exploder records; the loaded Factory table has exactly
four group500 entries using `maps/zombie/fx_zombie_mainframe_steam`:

| Origin | Angles |
| --- | --- |
|458.257,-1183.510,221.009|360,130,0|
|152.499,-1184.860,183.690|356,46,0|
|152.272,-1322.300,183.965|348,316,0|
|458.461,-1319.700,222.285|0,224,0|

All four have zero delay and no repeat. The client uses these authored records;
the adapter adds no manually placed particles or per-frame emitter updates.
Group800 is also present at power activation but contains additional map lights
and sounds; that wider presentation is not restored in this increment.

The recorded steam slot is admitted only if empty or already500. The dynamic group
configstring is registered before the snapshot event. The powered model IDs are
resolved from the loaded static model band; no model configstring update is sent.
An event is reserved before
geometry mutation and freed on mirror failure. The cabinet participates in the
same generation-checked transaction as the lever/bridges. A repeated switch cannot
emit again. Missing models, slot conflict or event capacity leave logical power off.
Checks cover the powered cabinet, rollback, missing model and exactly one event
after a rejected activation followed by a successful retry. Rendering remains a
separate Factory playtest; neither this source test nor the original demo is its PASS.

Integration found that the inherited exploder producer was rejected by the simple
event validator and omitted from archive/writer admission. All three gates now
admit only the recovered exploder carrier alongside the previous supported types;
the native eight-bit parameter bound and existing wire descriptors are unchanged.
Regression checks exercise real event production, snapshot admission and writing,
malformed parameter rejection, and persistent mirror-failure cleanup. The initial
new activation check failed before this correction; no failing build was deployed.

### Switch-disconnect correction

The first live presentation candidate failed at switch activation. The server kept
advancing with no snapshot rejection and completed bridge lowering; the client
returned to menus with `XBOXLIVE_CANTJOINSESSION`. Fresh exact-build IDA514540
at5145C6 checks the per-index category table before comparing old/new values.
Categories below23, except21, are forbidden in reliable configstring updates.
Both powered model slots are category0; the exploder slot11992 is255. The still
loaded Factory server confirmed these category bytes after the client cleared its
map state. IDA514880 resolves static NCS entries directly from their asset band.

The failed candidate redundantly sent `d` updates for the two already-resolved
models. Those writes are removed, not the native validation: entity model IDs
still change and the allowed dynamic group500 registration remains. Earlier
source suites could validate the server's packet production but did not execute
the native client's configstring guard. The corrected build subsequently passed fresh
Factory and exact-build FFA playtests; the failed session is not acceptance.

电源实测发现静态模型字符串重复更新触发原生客户端拒绝并退回菜单；IDA514540确认。
修正为仅使用已加载模型索引，保留动态蒸汽组注册，不绕过客户端验证。修正后同构建Factory与双客户端FFA实测通过。

电源柜独立切换到原生发光模型；下降时触发录像确认的500组四个原生蒸汽效果。
对象与事件事务失败回滚，不重复播放，不修改多人协议。更广泛的800组灯光/音效待续。

## 中文摘要

可选Factory电源与桥梁候选：依据原版录像轨迹恢复开关、初始升桥和下降过程。
IDA确认轨迹求值器；控制器及末端移除阻挡体的策略属于重建，不冒充原版脚本。
八个对象按身份绑定，事务失败回滚；同时清除服务端与客户端阻挡，避免隐形碰撞。
本次不包含购买技能效果、传送器或神秘箱。同构建Factory与双客户端FFA实测通过。
