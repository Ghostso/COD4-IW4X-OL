/* Entity event epoch: the entityState half of the playerState extension model.
 *
 * The problem it replaces
 * -----------------------
 * The CoDOL entity writer used to extend the retained 8-bit
 * entityState.eventSequence with a per-entity-number accumulator
 * (entity_generations[1022]) that was advanced while serializing, once per
 * recipient. It could not represent a rewind - a recipient served an archived
 * entity state moved the shared counter forward - and two recipients of the
 * same entity shared one counter, so what a client received depended on who
 * else was watching.
 *
 * Producers (measured, all of them)
 * ---------------------------------
 * Every retained producer stores the event at es->events[seq & 3], the
 * parameter at es->eventParms[seq & 3] and then es->eventSequence =
 * (seq + 1) & 0xff (entityState offsets 0xa0, 0xa4, 0xb4):
 *   G_AddEvent non-player arm        _g_utils_mp.asm:285
 *   G_PlaySoundAlias non-player arm  _g_utils_mp.asm:1753
 *   G_AnimScriptSound non-player arm _g_utils_mp.asm:1839
 *   BG_PlayerStateToEntityState      _bg_misc.asm:2321, which transfers the
 *       player's queued single-client events into the entity queue one at a
 *       time, advancing the entity counter once per transferred event
 * C1 keeps the same shape - its G_AddEvent non-player branch at 0x00572ddf
 * writes ent+0xb0/+0xb4/+0xc4 - with the counter modulo 2048, which is the
 * width of the CoDOL entity field 0x0b0.
 *
 * Storages
 * --------
 * An entityState's epoch is found from the address of the storage it lives in,
 * never from es->number, because the same entity exists concurrently in three
 * of them with different histories:
 *   live      g_entities[i].s
 *   snapshot  svs.snapshotEntities[k]            what the writer serializes
 *   archive   svs.cachedSnapshotEntities[k].s    the delayed history
 * Copies between them, and the archived-snapshot stream, carry the epoch the
 * same way the playerState extension does.
 */
#ifndef CODOL_ENTITYSTATE_EXT_H
#define CODOL_ENTITYSTATE_EXT_H
#include "entity.h"
#include "msg.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    /* Events counted into this entity state, without the 8-bit wrap the
     * retained counter carries: es->eventSequence == epoch & 0xff. */
    uint32_t epoch;
    /* 0 when this state never had an event counted into it. */
    unsigned char known;
    /* 0 when no weapon pair was ever captured into this entity state, which is
     * not the same as a captured weapon 0: consumers must not publish an
     * uncaptured state as if it carried the pair. */
    unsigned char primary_known;
    /* The primary weapon that owns the weapon this entity state was captured
     * with. C1 BG_PlayerStateToEntityState stores the current weapon to
     * entityState +0xd4 at 0x40d14d and this one to +0xd6 at
     * 0x40d0d7..0x40d0fd: the cached primary at ps+0x340 when the current
     * weapon's definition has inventory type 3 (alternate mode), and the
     * current weapon itself otherwise. The retained entityState has one weapon
     * word (+0xc4) and no second one, and the weapon alone cannot answer the
     * question afterwards - an alternate-mode weapon does not name its primary
     * and the playerState that did is gone by the time a delayed or archived
     * copy is serialized. So it is captured here, from the playerState the
     * producer was handed, and copied with the state like the epoch. */
    uint16_t primary_weapon;
    /* C1 entityState +0x60, written beside the pair by the same producer
     * (0x40d104..0x40d13d): the offhand (ps+0x328) while the weaponstate is
     * one of the offhand phases 16..20 and that offhand's player animation
     * type is "hold" (claymore, C4, bouncing betty, scrambler), else 0. The
     * client prefers it to +0xd6 for the held weapon (0x407bb3) and C1's
     * world weapon producer (0x570b76) links a model of it to the hand.
     * Captured and cleared together with the pair. */
    uint16_t held_offhand;
    /* C1 wire58: instance low4, VehicleDef slot next5. Capture when the
     * native producer resolves the definition, never from a live slot while
     * serializing an archived state. Zero known means unresolved, not slot0. */
    uint16_t vehicle_identity;
    unsigned char vehicle_known;
    /* Resolved C1 script-model animation fields, captured at the producer.
     * Known (0,0) is an explicit clear; unknown is no animation producer. */
    uint16_t model_anim_entry;
    unsigned char model_anim_tree;
    unsigned char model_anim_known;
    /* C1 network link word and local transform, captured before archives. */
    uint32_t link_info;
    float link_origin[3],link_angles[3];
    /* Hide-part mask words 4..7 (DObj bones 128-252). C1 hides parts with
     * eight words (passed to its DObj at 0x4417e6); the retained entityState
     * carries words 0..3 in es->partBits. All zero is "nothing hidden". */
    uint32_t hide_upper[4];
} codol_es_ext_t;

/* Storage bases, bound in codol_playerstate_ext_storage.c. A NULL base
 * (count 0) disables that class, which is what a test harness binds. */
const void *CODOL_EntityStateExtLiveBase(unsigned *count);
const void *CODOL_EntityStateExtSnapshotBase(unsigned *count);
const void *CODOL_EntityStateExtArchiveBase(unsigned *count);

/* Producer hook: called by each retained producer immediately after its store
 * of es->eventSequence. */
void CODOL_EntityStateEventAdded(entityState_t *es);

/* Producer hook for the weapon pair: called by BG_PlayerStateToEntityState
 * beside its store of the retained weapon word, with the primary resolved from
 * the playerState that call was handed. resolved == 0 records that this state
 * has no captured pair, which is how an unresolvable one is reported -- the
 * pair a previous frame captured must not be published for this one, and it is
 * never inferred from the entity state itself. */
void CODOL_EntityStatePrimaryWeaponCaptured(entityState_t *es, unsigned primary, int resolved);
/* The captured primary of this entity state. Fails for an untracked storage
 * and for a state that never had a pair captured into it, so an uncaptured
 * entity is never published as if it carried one. */
int CODOL_EntityStatePrimaryWeapon(const entityState_t *es, unsigned *out);
/* The C1 +0x60 held offhand captured with the pair; 0 when there is none or
 * no pair was captured. */
void CODOL_EntityStateHeldOffhandCaptured(entityState_t *es, unsigned weapon);
unsigned CODOL_EntityStateHeldOffhand(const entityState_t *es);
void CODOL_EntityStateVehicleCaptured(entityState_t *,unsigned instance,unsigned definition,int resolved);
int CODOL_EntityStateVehicleIdentity(const entityState_t *,unsigned *out);
int CODOL_EntityStateModelAnimCaptured(entityState_t *,unsigned entry,unsigned tree);
int CODOL_EntityStateModelAnim(const entityState_t *,unsigned *entry,unsigned *tree);
int CODOL_EntityStateLinkCaptured(entityState_t *,unsigned,const float [3],const float [3]);
int CODOL_EntityStateLink(const entityState_t *,unsigned *,float [3],float [3]);
/* The eight-word hide-part mask: words 0..3 are es->partBits, 4..7 live in the
 * extension. Set stores all eight (the upper half fails for an untracked
 * storage); Get reads them, with the upper half zero when untracked. */
int CODOL_EntityStateSetHidePartBits(entityState_t *,const uint32_t bits[8]);
void CODOL_EntityStateHidePartBits(const entityState_t *,uint32_t bits[8]);

/* The counter to publish for this entity state: epoch modulo 2048, the width
 * of the CoDOL field 0x0b0. Fails - and reports - when the storage is not
 * tracked, when a state carries events but no epoch, or when the epoch and the
 * retained counter disagree, so an untracked history is never published as if
 * it were tracked. */
int CODOL_EntityStateEventSequence(const entityState_t *es, unsigned *out);
uint32_t CODOL_EntityStateEventEpoch(const entityState_t *es);
unsigned CODOL_EntityStateEventDesyncs(void);

/* Propagate along an entityState copy between tracked storages, and the
 * clears for the arms that leave a storage without a state. */
int CODOL_EntityStateExtCopy(const entityState_t *dst, const entityState_t *src);
int CODOL_EntityStateExtClear(const entityState_t *es);
void CODOL_EntityStateExtClearEntity(unsigned number);
void CODOL_EntityStateExtClearArchive(void);
void CODOL_EntityStateExtClearAll(void);

/* Archived-snapshot stream record, written after every archived entity and
 * read at the matching read with the same baseline. Independent records,
 * in this order, so the epoch's framing is exactly what it was:
 *   epoch    1 bit  0 = same as the baseline entity's epoch (or "no epoch")
 *                  1 = 1 bit recorded; when recorded, 1 bit short form (4 bits
 *                      of epoch-minus-baseline, 1..16) or the 32-bit epoch
 *   primary  1 bit  0 = same as the baseline entity's captured pair (or "not
 *                      captured")
 *                  1 = 1 bit captured; when captured, 16 bits of weapon
 *   vehicle 1 bit changed; if changed, 1 bit captured; if captured, 9 bit identity
 *   animation 1 bit changed; if changed, 1 bit captured; if captured, 12 bit
 *             entry/variant and 4 bit tree. Captured (0,0) means clear.
 *   link     1 bit changed; if changed, 27 bit link word and its transform
 *   hide     1 bit changed; if changed, hide-part words 4..7 as 4 x 32 bits
 * This is the server's transient archive stream, not the client protocol. */
void CODOL_EntityStateExtWrite(msg_t *msg, const entityState_t *es, const entityState_t *baseline);
void CODOL_EntityStateExtWriteEntity(msg_t *msg, unsigned number, const entityState_t *baseline);
void CODOL_EntityStateExtRead(msg_t *msg, const entityState_t *es, const entityState_t *baseline);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
