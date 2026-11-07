# Missing bot heads — bounded audit, 2026-09-15

No source changes, builds, tests, launches, input, or process writes.

## Fresh passive evidence

Discovered current C1 PID90404 at the expected executable path, then used the
existing signature-guarded ReadProcessMemory-only player render probe. The
probe requires nonzero current command/snapshot and checks snapshot stability.

`obj/bot-torso-audit/missing-head-capture-90404.json`, command248370 onward:
actual C1 DObjs for entities1..5 include head XModels. Names are
hea_concept_sc_m_00 (1/3/4), hea_odom_ss_m_yel_00 (2), and
hea_victor_ss_m_yel_00 (5). Entity6 had DObjId0, so its head cannot be evaluated
from this sample; do not interpret that as a head-only failure.

Follow-up `missing-head-capture-90404-followup.json`, command282400 onward:
entities0..5 each have an actual head XModel in their DObj, including the user
at entity0 with hea_odom_ss_m_yel_00. Entity6 was absent from the received player
list. Captures' snapshotStable values are true. These observations establish
model presence, not visible triangles, correct materials, bone transforms, or
head hide masks. They cannot establish that the reported visual defect is fixed.

## Native producer chain

Bots use `codol_bot_loadout.c::character`, not the human profile selector.
It reads mp/botclasstable.csv's charHEA/charHEA_sc by selected class and faction,
resolves marketplace item identity, then uses the actual item group to select
composition slot4. It derives skin tone, applies head-keyed character defaults,
resolves faction/gender model variants, and publishes via the shared appearance
builder. This path does not apply a sniper/ghillie head override.

Current loose CSV defines head choices for every class: TF odom/veiga/socomb/
socomc/victor; SC concept/socomc. The head slot is not excluded by
`CODOL_OrderCharacterParts`: ordered_slots includes slot4 after vest. The complete
client appearance is published independently of the server-only 128-bone pose
budget, so that server pose reduction does not itself remove a client head.

Publication can omit an unavailable part after warning, or silently skip a
runtime model registration failure. The current log has no unavailable-part
warnings; it includes registered head names concept, veiga, victor, socomc and
odom. Fresh DObj evidence confirms the head reached the client for sampled bots.
No specific registration failure or erroneous composition input was found.

## Conclusion and next discriminant

No evidence-backed missing-head source patch from this bounded pass. Do not
replace authored heads or force another faction as a workaround. To isolate
the remaining report, correlate the visibly headless bot with its current entity
and exact DObj, then inspect that head's active surface/material and bone hide
state. Entity6/class5 SC socomc was not inspectable here; visibility alone does
not identify it as the affected bot. World weapons/red effects remain under the
separate worker's ownership.
