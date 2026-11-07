/* Looping entity sound: the producer half, C1's start and stop.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 playloopsound 0x0054d760 and stoploopsound 0x00541320 do exactly two
 * things each, in this order:
 *   0x0054d781 / 0x0054132f   svFlags &= ~SVF_NOCLIENT   (gentity+0x116 bit 0)
 *   0x0054d78b / 0x00541336   entityState loop field = index / 0
 * and nothing else. In particular neither writes a broadcast time: the whole
 * C1 image has no snapshot-side reader of the loop field, so a looping entity
 * gets no privileged visibility there and is transmitted when PVS and the
 * ordinary flags allow it. The retained methods instead set
 * r.broadcastTime = -1 on start and level.time + 300 on stop, which forces the
 * entity into every client's snapshot (sv_snapshot.c:867..881, sv_game.c:668).
 * Clearing SVF_NOCLIENT is what actually matters for both edges - a hidden
 * entity can deliver neither the start nor the stop - so this follows C1 and
 * the retained broadcast writes stay in the non-CoDOL build.
 *
 * The index comes from the shared bank: retained G_SoundAliasIndex is
 * G_FindConfigstringIndex(name, CS_SOUNDS, 0x100, 1, 0) returning a byte, C1's
 * equivalent is 0x00570920 scanning slots 1..255 of the 256-entry table at
 * 0x27d5740 and registering CS 0xd43+i, and the client resolves the loop alias
 * from CS 3395+index at 0x0043ec5d - the same bank codol_sv_assets.c already
 * mirrors for LocalSound and for the one-shot sound event parameter.
 */
#ifdef CODOL_SERVER
#include "codol_loop_sound.h"
#include "codol_playerstate_ext.h"
#include "g_shared.h"
#include "g_public.h"
#include "entity.h"

/* Engine producer, declared like the other native CoDOL script files do. */
int __cdecl G_SoundAliasIndex(const char *name);

static unsigned loop_misses;
unsigned CODOL_PlayerLoopSoundMisses(void) { return loop_misses; }

/* C1 (0x0054d78b) and IW4 (0x005f6c37) write the entity field for
 * every receiver. Do not turn this into a persistent playerState write:
 * the later player-to-entity transfer is a separate measured operation.
 * The original producer of C1 ps+0x1f4 remains to be established. */
static int store(gentity_t *entity, unsigned sound)
{
    entity->s.loopSound = (int)sound;
    return 1;
}

int CODOL_EntityLoopSoundStart(gentity_t *entity, const char *alias)
{
    int index;
    if (!entity) return 0;
    entity->r.svFlags &= ~SVF_NOCLIENT;
    /* An empty or unregisterable alias leaves the entity silent rather than
     * looping the previous one: C1 stores whatever byte the index function
     * returned, and that function returns 0 when it cannot place the name. */
    index = (!alias || !*alias) ? 0 : G_SoundAliasIndex(alias);
    if (index < 0 || index > CODOL_LOOP_SOUND_MAX) index = 0;
    if (!store(entity, (unsigned)index)) return 0;
    return index > 0;
}

void CODOL_EntityLoopSoundStop(gentity_t *entity)
{
    if (!entity) return;
    entity->r.svFlags &= ~SVF_NOCLIENT;
    store(entity, 0);
}

void CODOL_PlayerStateLoopSoundToEntity(const playerState_t *ps, entityState_t *es)
{
    unsigned sound = 0;
    if (!ps || !es) return;
    /* Unconditional, like C1 0x0040d09d and IW4 0x0056e88a: the entity state a
     * playerState produces carries that playerState's loop sound, including 0.
     * A storage this server does not track transfers silence and is counted -
     * the transfer runs for every state, so a warning per frame would say
     * nothing a counter does not. */
    if (!CODOL_PlayerStateLoopSoundRead(ps, &sound)) { ++loop_misses; sound = 0; }
    es->loopSound = (int)sound;
}
#endif
