/* CoDOL script sound methods. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_SOUND_H
#define CODOL_SCRIPT_SOUND_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
/* C1 has two distinct sound producers and this header exposes both.
 *
 * Positional form: registers alias in the engine sound bank (CS_SOUNDS,
 * republished to C1 as CS 3395+index by the asset publisher), then spawns a
 * broadcast event entity at origin carrying that index, mirroring C1's
 * playsoundatpos helper 0x54cf30 - index at entityState +0xac, owning entity
 * at +0x80, 2046 when nothing owns it. parent is an entity number or
 * CODOL_SOUND_NO_PARENT; as_master selects EV_SOUND_ALIAS_AS_MASTER.
 * Engine side the owner is stored in otherEntityNum biased by one, so a zero
 * from a retained producer still reaches the wire as C1's unowned sentinel.
 * Returns 1 and stores the registered index; 0 when the alias is empty, the
 * sound bank is exhausted or the event entity cannot be spawned. */
enum { CODOL_SOUND_NO_PARENT = 2046 };
int CODOL_EmitSoundAlias(const float origin[3], const char *alias, int parent,
                         int as_master, unsigned *index);
/* Attached form, the one C1 uses for an entity's own sound (0x5730c0): clear
 * the receiver's SVF_NOCLIENT so the event can be transmitted, then queue
 * EV_SOUND_ALIAS with the registered index on the player state when the entity
 * has a client and on the entity event queue otherwise. No temp entity and no
 * owner field are involved; the sound rides the entity's own state.
 * 1 queued, -1 registered but refused by the entity event gate, 0 when the
 * alias is empty or the sound bank is exhausted. */
int CODOL_PlaySoundOnEntity(gentity_t *entity, const char *alias, int as_master, unsigned *index);
/* 1 when the mounted archives define alias and its first entry is a looping
 * alias, 0 when it is one-shot, -1 when no mounted archive defines it. */
int CODOL_SoundAliasIsLooping(const char *alias);
/* Playing length in milliseconds from the sound/soundlength.csv string table
 * (column 0 alias, column 1 milliseconds), which C1 reads the same way in
 * 0x73d250. Aliases the table does not list use C1's 2000 ms default. */
enum { CODOL_SOUND_DEFAULT_MSEC = 2000 };
int CODOL_SoundAliasLengthMsec(const char *alias);
/* Unintegrated event-budget draft. C1 compares a counter with four, but its
 * frame/reset lifecycle has not been established. G_AddEvent DOES NOT call
 * CODOL_EntityEventAllowed; Pending consequently sees an unconsumed counter.
 * Do not wire the consuming gate until the reset policy is verified: its
 * current entity-free-only reset would impose a permanent lifetime cutoff.
 * Queue epochs and the 300 ms freeAfterEvent timer are separate state. */
enum { CODOL_ENTITY_EVENT_LIMIT = 4 };
int CODOL_EntityEventAllowed(gentity_t *entity, int event);
int CODOL_EntityEventPending(const gentity_t *entity);
unsigned CODOL_EntityEventDrops(void);
/* Fires due playsound completion notifications once per simulation frame,
 * after animation time setup and before script scheduling in G_RunFrame.
 * Releases their script string references. C1 frame ordering is unverified. */
void CODOL_RunSoundFrame(int time);
/* Drops every pending notification and event count, releasing string
 * references. Must run while the script string system is still up, so it
 * belongs in SV_ShutdownGameProgs before the game VM is torn down. */
void CODOL_ResetSoundState(void);
/* Release pending notification references before this entity slot is freed. */
void CODOL_ResetEntitySoundState(unsigned entity);
/* <entity> playsound(<alias> [, <notify> [, <int> ]]) - C1's own dispatch
 * 0x54d1f0: the alias, a completion notification string, and an integer that
 * suppresses the second-notification error. There is no parameter-count error:
 * 0x54d2f7 arms a notification for exactly two parameters, 0x54d301 for three,
 * and every other count plays the sound with no notification (0x54d32b).
 * Arming while a notification is still outstanding is a script error and plays
 * nothing. Registering a notification requires CODOL_RunSoundFrame to be
 * called each server frame, otherwise it is never delivered. */
void CODOL_Scr_PlaySound(scr_entref_t);
/* <entity> playsoundasmaster(<alias>) - IW4 0x5f6bb0 contract, exactly one
 * parameter, since C1 has no producer or dispatch for this name. */
void CODOL_Scr_PlaySoundAsMaster(scr_entref_t);
/* playsoundatpos(<origin>, <alias>) - a global function, not a method.
 * Vector first, alias second in both IW4 0x5f6960 and C1 0x54d340. The count
 * rule follows C1: at least two parameters, extra ones ignored, and C1's
 * message "playsoundatpos needs at least 2 parameters - you had %i
 * parameters"; IW4 instead demands exactly two and words it "needs 2
 * parameters". Alias faults are parameter-zero errors in both engines even
 * though the alias is parameter one, because one shared helper reports them.
 * No return value. */
void CODOL_Scr_PlaySoundAtPos(void);
/* playsoundatposition(<alias>, <origin>) - a global function, the T5 spelling
 * of the same operation: alias first, position second, exactly two parameters
 * (T5 Scr_PlaySoundAtPosition 0x647d70, "playsoundatposition has %d
 * parameters.  There should be two."), no return value. The emission and the
 * alias validation are C1's, since T5's own producer carries a 32-bit alias id
 * on a different wire and silently drops names it cannot resolve. */
void CODOL_Scr_PlaySoundAtPosition(void);
/* <entity> playsoundontag(<alias> [, <tag>]) - T5 0x6476d0 contract: no count
 * error, an absent or empty alias plays nothing, and a tag the receiver's
 * model does not carry is a parameter-one error after the DObj is dumped. The
 * tag is resolved to a world position here, because C1's sound event has no
 * tag field, and the event is emitted unowned. No return value. */
void CODOL_Scr_PlaySoundOnTag(scr_entref_t);
/* <entity> stopsounds() - IW4 0x5ecb80 and C1 0x536120 contract. */
void CODOL_Scr_StopSounds(scr_entref_t);
/* soundAliasSubtitle(<alias>) - a global function with no IW4/C1 script
 * counterpart. Returns the localize reference in snd_alias_t.subtitle (record
 * +4, C1 loader 0x4b84b0) of one variant of the alias list, chosen uniformly
 * among the variants that carry one, or undefined when the alias is unknown or
 * has no subtitled variant. _hud_message uses it to decide whether an
 * announcer line gets C1's top-right caption menu (announcer_line): the client
 * prints the subtitle of the variant it actually plays into message window 2
 * on its own, so the server only needs to know that one exists. */
void CODOL_Scr_SoundAliasSubtitle(void);
#ifdef __cplusplus
}
#endif
#endif
