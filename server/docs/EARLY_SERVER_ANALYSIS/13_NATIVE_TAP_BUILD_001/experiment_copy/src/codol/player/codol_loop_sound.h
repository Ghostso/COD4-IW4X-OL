/* CoDOL looping entity sound. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * A looping sound is not an event: it is a state an entity carries until it is
 * cleared, and C1 transmits it as one byte of the entityState.
 *
 * The field, measured five ways (loop-finish-report.md has the listings):
 *   entityState +0x08c, 8 bits, present in all 22 eType netfield tables.
 *   C1 playloopsound  0x0054d760  writes the alias index there and clears
 *                                 svFlags bit 0 at gentity+0x116
 *   C1 stoploopsound  0x00541320  writes 0 there and clears the same bit
 *   C1 BG_PlayerStateToEntityState 0x0040d09d  es[0x8c] = ps[0x1f4], beside
 *                                 es[0x9c] = ps[0x140] which is the clientNum
 *                                 alpha0022 measured (ENT_CLIENTNUM 0x09C)
 *   C1 turret think   0x0057b310  is retained turret_think_client
 *                                 (_g_misc_mp.asm:1584) with [ent+0x8c]
 *                                 wherever the retained code writes s.loopSound
 *   C1 CG_AddCEntity  0x00443c74  tests cent+0x170 (== es+0x8c) before its
 *                                 per-eType dispatch and calls the loop-sound
 *                                 adder 0x0043eba0, which reads the alias NAME
 *                                 from configstring 3395 + index (0x0043ec5d
 *                                 indexes STRING_OFFSETS+4*3395 at 0x6d1063c)
 *
 * The index space is therefore the same sound bank the one-shot EV_SOUND_ALIAS
 * parameter and C1's LocalSound command use: 1..255, 0 meaning "no loop",
 * registered by the alias-index function (C1 0x00570920, retained
 * G_SoundAliasIndex = G_FindConfigstringIndex(name, CS_SOUNDS, 0x100, 1, 0))
 * and mirrored to CS 3395+index by codol_sv_assets.c.
 *
 * The retained entityState already has the value (s.loopSound, +0x80, 8-bit
 * netfield, and AEF(s.loopSound) in the archived-entity table), so the snapshot
 * ring and the archive stream carry it for free and a delayed spectator hears
 * the loop the archived state was taken with. What was missing is the wire
 * mapping below, without which every CoDOL snapshot left field 0x08c at its
 * delta baseline - silence - for every entity.
 */
#ifndef CODOL_LOOP_SOUND_H
#define CODOL_LOOP_SOUND_H
#include "entity.h"
#include "player.h"
#include "codol_entities.h"
#include "codol_playerstate.h"
#ifdef __cplusplus
extern "C" {
#endif

/* The measured wire offsets.
 *
 * The playerState half is not optional and not a mirror: the client
 * synthesises the local player's own centity from the playerState, so a loop
 * sound the owner is meant to hear can only travel at 0x1f4, and both engines
 * keep the two equal by copying ps -> es in the transfer, every frame, for
 * every client:
 *
 *   IW4  playerState netfield table 0x00742020 entry 149 names the field:
 *        loopSound, ps+0x190, 8 bits (entity side: es+0x88, 8 bits)
 *   IW4  BG_PlayerStateToEntityState 0x0056e88a  s->loopSound = ps->loopSound
 *   C1   playerState netfield 0x01f4, 8 bits (codol_player_fields.inc:176)
 *   C1   BG_PlayerStateToEntityState 0x0040d09d  es[0x8c] = ps[0x1f4]
 *
 * T5, the fallback, has no playerState loop sound at all (its named
 * playerStateFields at 0x00ce2e20 carry none), so it does not model this. */
#define CODOL_LOOP_SOUND_ENTITY_FIELD 0x08c
#define CODOL_LOOP_SOUND_PLAYER_FIELD 0x1f4
/* C1 0x00570920 scans slots 1..255 of a 256-entry table; 0 is "no sound". */
#define CODOL_LOOP_SOUND_MAX 255

/* Validate a retained entityState_t::loopSound as a bank index. Out of range
 * fails rather than truncating: eight bits carry the whole bank, so a value
 * that does not fit is a producer that did not use the bank. */
int CODOL_LoopSoundToWire(int loop_sound, uint32_t *out);
/* Publish it into entity field 0x08c of whatever eType the state maps to. */
int CODOL_OverlayEngineLoopSound(codol_entity_state_t *wire, const entityState_t *es);
/* Publish a captured playerState's loop sound into player field 0x1f4. The
 * value is supplied by the caller, which reads it from the state being
 * serialized (its extension), so an archived or spectator-followed state
 * publishes what it carried and no live entity or client is consulted. */
int CODOL_OverlayPlayerLoopSound(codol_player_fields_t *wire, unsigned sound);

/* Producer half (codol_loop_sound_native.c, server build only): C1's own
 * start/stop semantics against the retained gentity. */
struct gentity_s;
int CODOL_EntityLoopSoundStart(struct gentity_s *entity, const char *alias);
void CODOL_EntityLoopSoundStop(struct gentity_s *entity);
/* The transfer both engines make (C1 0x0040d09d, IW4 0x0056e88a):
 * es->loopSound = ps->loopSound, unconditional. Called from the retained
 * BG_PlayerStateToEntityState in the same position. A playerState with no
 * extension storage transfers silence and is counted, not warned about, because
 * the transfer also runs for scratch states. */
void CODOL_PlayerStateLoopSoundToEntity(const playerState_t *ps, entityState_t *es);
unsigned CODOL_PlayerLoopSoundMisses(void);

#ifdef __cplusplus
}
#endif
#endif
