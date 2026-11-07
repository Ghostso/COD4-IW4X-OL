# Living-player world weapons / 玩家手持武器实体

Status: native investigation September26; integrated on base `985cea1` and
accepted in two-real-client Factory and same-build Nuketown FFA playtests on
September27. Original baseline observations below describe the missing producer,
not the corrected build. Remote networking and every weapon class remain unverified.

## Failure and native contract

Two real Factory clients had valid player entities, ready weapon definitions and
matching current/presentation weapon selectors (1159 and 1165), but both players'
characterInfo `+394/+398` child references were zero in both clients. Their body
DObjs contained character/clothing models. These read-only observations identify
a missing producer rather than an asset-loading explanation.

Exact x86 `out.exe` SHA256:
`044C396C90A7CFA63EAC32BEA194BF4DFA4D1EAB547D9082AE8A575EB49257F9`.
IDA analysis was complete. Addresses are preferred VAs at base `00400000`:

* `0040AB30` records the selected player weapon in characterInfo `+388`.
  `004534A0` attaches auxiliary models; it does not append the ordinary full gun.
* `005201B0 -> 0051FE00` builds the separate ET_SCRIPTMOVER DObj from entity
  state `+68`, including the existing native modular-weapon path `00431B00`.
* ClientState netfield table `00DA8078` has field 0 at `+140`, width 11.
  `0054BD7A..8C` copies it to characterInfo `+394`. It is a raw child entity
  number; zero means absent. Field 41 / `+144 -> +398` is a second child reference
  and is deliberately not populated by this ordinary single-firearm increment.
* Child `+EC` low word is parent entity number plus one; byte `+EE` selects the
  tag configstring in band `12248 + index` (`00523910`). Resolve the name for the
  current session; a numeric tag from one recording is not portable.
* `00453460` selects `tag_weapon_right` for ordinary type-0 firearms unless
  class 13 or characterInfo `+290` selects the left-hand variant. That mutable
  animation-state case and special/dual-hand classes remain outside this scope.
* `00522040` renders the child. Child or linked-parent NoDraw prevents rendering.
  At `00522B7B..9B`, the local player's normal first-person path suppresses its
  own world gun; no observer-specific server filter is needed.

Five original Factory theater recordings decoded 46,664/46,664 snapshot endpoints
exactly. All 1,324 nonzero field-0 assertions named an active ET6 weapon child;
630/630 locally comparable samples matched playerstate current weapon. Recorded
switches retire one child and create another. The candidate's generation-owned
stable child with updated selector is an adapter policy, not a recovered server
lifetime algorithm. Read-only live captures were not atomic; stable roots and
process identity were checked. Native files, raw captures, decoder outputs and
IDBs remain local, outside the contribution.

## Shared implementation boundary

`SvServerWorld::endFrame` produces one generation-owned, noncolliding child per
eligible living player after candidate loadout finalization. Client-info field 0
and the child are published in the same candidate snapshot. Child allocation and
retirement share the existing staged missile pool; native-mirror rejection must
roll back entity storage, ownership and pool together. Death, ineligibility,
disconnect and reset clear ownership. Tag registration is session-scoped and
must succeed before publication.

This is shared world/snapshot code, with no Zombies/FFA or loopback/remote branch.
It adds no protocol message or native ABI field. Mode rules remain in the mode
controller; session membership, endpoint selection and launch policy remain
outside entity replication. Ordinary single-firearm eligibility is deliberately
bounded to a matching resolved type-0 definition excluding class 13.

## Verification

Seven canonical suites, Release build,50ms scheduler regression and196-entry
partial source audit pass. Focused cases cover field-0 encoding, generation-zero
ownership, weapon switching, native-mirror rejection/rollback, pool exhaustion,
missile-to-child slot reuse and server disable/re-enable. Same-build two-real-client
Factory and Nuketown FFA playtests pass. These live acceptance results are separate
from the source assertions; they do not establish remote-network readiness.

## 中文摘要

同版本IDA与五份原始录像确认：普通手持世界武器由独立ET6子实体渲染，
不是人物DObj的普通附件。修复前双客户端均缺少clientState字段0的武器引用。
本次在共享世界快照事务中生成并管理子实体，复用现有网络字段与原生第一人称
隐藏逻辑；僵尸、FFA及远程地址不分叉。特殊双持、左手动画状态与跨网络验证
仍未完成；稳定复用子实体的生命周期属于重建适配策略。

同构建双客户端Factory与Nuketown FFA验收通过；七项套件、Release、50ms与196项局部证据检查通过。
