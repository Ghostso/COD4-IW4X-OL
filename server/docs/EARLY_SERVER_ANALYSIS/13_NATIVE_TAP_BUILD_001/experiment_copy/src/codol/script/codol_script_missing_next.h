#ifndef CODOL_SCRIPT_MISSING_NEXT_H
#define CODOL_SCRIPT_MISSING_NEXT_H
#ifdef CODOL_SERVER
#include "scr_vm.h"

/* Entity use/collision state methods.
 *
 * These are the members of one contiguous IW4 builtin-method block that this
 * tree did not have. The block is, in table order at IW4 0x73d30c..0x73d36c:
 * setcontents (0x5efe80), makeusable (0x5efee0), makeunusable (0x5eff40),
 * setcursorhint (0x5f0070), sethintstring (0x5f6060), forceusehinton
 * (0x5f6110), makesoft (0x5eff90), makehard (0x5effe0). Everything except the
 * four names below is already registered by the retained engine. The usable
 * pair is now registered; soft/hard remain unregistered pending C1 evidence.
 *
 * makeusable / makeunusable (IW4 0x5efee0 / 0x5eff40)
 *   IW4 sets/clears CONTENTS_TRIGGER in entityShared::contents (IW4 +0x11c),
 *   keeps the vehicle spawnflag bit 0 (IW4 +0x180) in sync when the receiver
 *   is a vehicle, gives a still-unset cursor hint the default value 1, and
 *   tail-calls SV_LinkEntity (IW4 0x4e0880, identified through setcontents,
 *   which stores the new contents at +0x11c and calls the same address).
 *   The retained engine uses the same content bit: trigger_use_shared writes
 *   contents = 0x200000 when a trigger_use brush spawns
 *   (src/asmsource/_g_mover.asm:76) and the player-use scan traces with that
 *   mask (src/asmsource/_player_use_mp.asm:464). So the content bit is what
 *   actually decides whether "+activate" offers an entity, and relinking is
 *   what makes the change visible to that trace and to the snapshot.
 *
 *   The cursor hint is entityState_s::un2 - GScr_SetCursorHint writes
 *   [ent+0xd8] (src/asmsource/_g_scr_main_mp.asm:10672ff) and stores -1 for
 *   HINT_INHERIT - and trigger_use_shared initialises it to 1 with hint string
 *   index un1 = 0xff. hintStrings (_g_mover.asm:1373) is indexed from 1, so 1
 *   is HINT_NOICON, the engine's own default for a freshly usable trigger.
 *
 * makesoft / makehard (IW4 0x5eff90 / 0x5effe0)
 *   Set/clear EF_SOFT in the published flags: playerState eFlags when the
 *   receiver has a client, entityState lerp.eFlags otherwise. EF_SOFT is
 *   1 << 23 in the IW4 eFlags enum (iw4x-client Structs.hpp:1679). That does
 *   not establish C1's mapping or native collision behavior. The current
 *   shared wire flag mask excludes this bit. These drafts and their query
 *   helper therefore do not yet implement CoDOL soft/hard behavior.
 *
 * Receivers are plain entities: the IW4 handlers reject any entref whose high
 * 16 bits (classnum) are set. They read no arguments and ignore extras.
 */

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;

/* CONTENTS_TRIGGER as used by this tree's movers, player-use trace and
 * vehicle-usable path (src/codol_script_vehicle_motion.cpp:103). */
#define CODOL_CONTENTS_TRIGGER 0x00200000

/* Draft IW4 EF_SOFT value; C1 mapping/consumer remains unverified. */
#define CODOL_EF_SOFT 0x00800000

/* Default cursor hint applied by makeusable when the entity has none, matching
 * trigger_use_shared's own default (HINT_NOICON). */
#define CODOL_CURSORHINT_DEFAULT 1

void CODOL_Scr_MakeUsable(scr_entref_t);
void CODOL_Scr_MakeUnusable(scr_entref_t);
void CODOL_Scr_MakeSoft(scr_entref_t);
void CODOL_Scr_MakeHard(scr_entref_t);

/* Native consumers: the state the four methods publish, without spreading the
 * bit values through the tree. */
int CODOL_ScriptEntityIsUsable(const struct gentity_s *entity);
int CODOL_ScriptEntityIsSoft(const struct gentity_s *entity);

#ifdef __cplusplus
}
#endif

#endif
#endif
