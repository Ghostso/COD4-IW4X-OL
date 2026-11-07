# Bot killcam victim visibility audit — 2026-09-14

Status: source audit only. No proven rendering fix, no process changes or tests.

`SV_BuildClientSnapshot` captures the receiving player's followed playerstate,
then changes its local `clientNum` to `frame->ps.clientNum`. The archived
visibility query therefore excludes the followed killer's entity, not the
receiving victim. `SV_AddCachedEntitiesVisibleFromPoint` evaluates the archived
clientMask and archived entity bounds against that followed viewpoint. This is
not evidence of an unconditional victim exclusion.

The archived client composition is not fetched from live playerdata.
`CODOL_ReadArchivedClientAbilities` records the root model and sixteen model/tag
pairs beside each cached clientState. `CODOL_CaptureArchivedClientAbilities`
copies that record to the snapshot ring. `CODOL_OverlayCapturedClientAbilities`
checks sequence and client identity before publishing it. Missing known
appearance can leave the retained six-part composition, but the audit did not
establish that condition in the user's failing killcam.

Player entity publication copies archived `clientNum` to C1 entityState+9c,
which C1 45bc70 uses for clientInfo selection. It copies archived eFlags directly
to C1+8. No recipient-based hide branch exists in that overlay. Corpse appearance
has a separate captured original identity path; do not replace either with live
model fallback.

Next discriminating evidence: in one actual failing killcam, capture the
receiving client id, followed ps.clientNum, archive frame/time, victim's presence
in the cached entity list and selected output list, archived clientMask/flags,
root and attachment model IDs, and C1 rendered entity/clientInfo. If the victim
is present in the native frame, inspect C1 local-identity/eFlags draw gates;
otherwise inspect the specific archive/PVS exclusion. Do not change visibility
or force broadcast until that evidence exists.
