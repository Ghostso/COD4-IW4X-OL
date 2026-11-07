#ifndef CODOL_SENTIENT_H
#define CODOL_SENTIENT_H
#ifdef CODOL_SERVER

/* CoDOL sentient registry.
 *
 * C1 (Call of Duty Online 1.1.1.13, C1.exe, base 0x400000) keeps every entity
 * that can be perceived, targeted or shot at in a flat pool of 0x7c-byte
 * records. The pool base pointer is [0x24b501c] (the array itself is at
 * 0x243500c) and holds 0x4b = 75 records; a gentity points at its record
 * through gentity+0x184. The turret target family reads that pool, never the
 * client list: acquisition 0x57ccf0 walks it through the iterators 0x578e70
 * (first) and 0x578eb0 (next) with a class mask taken from the table built at
 * 0x57cc51, and the friendly blocker 0x57cb80 reads the team out of the same
 * record.
 *
 * Record fields measured in C1:
 *   +0x00  gentity_s *entity                  (Sentient_Setup 0x578963)
 *   +0x04  actor / AI struct, or NULL         (0x57899f, from gentity+0x180)
 *   +0x08  team, used as the shift for the class bit  (0x578965, 0x578e86)
 *   +0x0c  word, owning entity number + 1     (acquisition 0x57ce17)
 *   +0x18  byte, "do not target"              (acquisition 0x57cd81/0x57cdd6)
 *   +0x1c  vec3 origin snapshot               (0x5789a2)
 *   +0x76  byte, record in use                (allocator 0x5786aa, 0x578e80)
 *   +0x77  byte, expendable                   (allocator 0x5786a6)
 *
 * This fork keeps the same behaviour on its own record layout rather than
 * copying C1's 0x7c bytes: the remaining C1 fields belong to the AI/perception
 * subsystem this fork does not have, and gentity_s cannot grow a back-pointer
 * because retained assembly consumes its layout, so the entity -> record
 * mapping lives in this module instead of in gentity+0x184. */

#include "q_shared.h"
#include "g_public_mp.h"
#include "scr_vm.h"

/* C1 0x578e97 / 0x578ed1 / 0x578652: pool capacity. */
#define CODOL_MAX_SENTIENTS 75

/* Team/class values. The class bit is 1 << team, which is what the C1
 * iterators shift (0x578e88) and what the turret class table at 0x57cc51
 * selects: an axis turret (1) takes mask 0xc = allies|team3, an allies turret
 * (2) takes 0xa = axis|team3 and a team3 turret (3) takes 0x16 =
 * axis|allies|team4. */
#define CODOL_SENTIENT_TEAM_NONE 0
#define CODOL_SENTIENT_TEAM_AXIS 1
#define CODOL_SENTIENT_TEAM_ALLIES 2
#define CODOL_SENTIENT_TEAM_THREE 3
#define CODOL_SENTIENT_TEAM_FOUR 4
#define CODOL_SENTIENT_TEAM_COUNT 7

/* C1 Sentient_Alloc 0x5785b0 takes the allocation class in its only argument:
 * 2 keeps the record until it is freed, 3 marks it expendable so a later
 * allocation may recycle it (0x5786a0 stores type == 3 at +0x77). */
#define CODOL_SENTIENT_PERSISTENT 2
#define CODOL_SENTIENT_EXPENDABLE 3

/* C1 0x57862f: once 24 non-expendable records are live, the allocator recycles
 * the first expendable one instead of failing. */
#define CODOL_SENTIENT_MAX_PERSISTENT 24

#ifdef __cplusplus

struct gentity_s;
struct gclient_s;

struct codol_sentient_s
{
    struct gentity_s *entity;   /* C1 record +0x00 */
    EntHandle handle;           /* this fork's stale-slot guard for +0x00 */
    int team;                   /* C1 record +0x08 */
    int ownerNum;               /* C1 record +0x0c less one, -1 when unset */
    unsigned char dontTarget;   /* C1 record +0x18 */
    unsigned char inuse;        /* C1 record +0x76 */
    unsigned char expendable;   /* C1 record +0x77 */
    unsigned char isActor;      /* C1 gentity+0x180 != NULL, i.e. record +0x04 */
    int actorSlot;              /* wire actor slot 0..31, -1 when not an actor */
    vec3_t origin;              /* C1 record +0x1c..+0x24 */
};

typedef struct codol_sentient_s codol_sentient_t;

extern "C"
{

/* Level init. Raw-clears the pool without touching the EntHandle registry,
 * which G_InitTurrets may run either side of EntHandle::Init. */
void CODOL_Sentient_ResetAll(void);

/* C1 0x5785b0 / 0x578960 / 0x5786c0. */
codol_sentient_t *CODOL_Sentient_Alloc(int allocClass);
void CODOL_Sentient_Setup(codol_sentient_t *sentient, struct gentity_s *entity, int team);
void CODOL_Sentient_Free(codol_sentient_t *sentient);

/* C1 0x578e70 / 0x578eb0: the class-mask iterators the turret acquisition
 * walks. Pass CODOL_SENTIENT_MASK_ALL to walk the whole pool. */
#define CODOL_SENTIENT_MASK_ALL 0xffffffff
codol_sentient_t *CODOL_Sentient_First(unsigned int classMask);
codol_sentient_t *CODOL_Sentient_Next(codol_sentient_t *sentient, unsigned int classMask);

/* C1 0x57cc51: the turret class table, indexed by the turret's own team. */
unsigned int CODOL_Sentient_ClassMask(int turretTeam);

/* The wire actor channel carries at most 32 records, indexed by a slot that
 * has to stay stable while the actor lives (C1 clamps the published count to
 * 32 at 0x4871b3 and its client indexes a 0x29c-byte composition slot with the
 * record's number at 0x46ce78). Slots are owned by the registry because that
 * is what knows when an actor entity appears and disappears. */
#define CODOL_MAX_ACTOR_SLOTS 32
codol_sentient_t *CODOL_Sentient_ActorBySlot(int slot);

/* Slot exhaustion is explicit rather than silent: an actor that finds every
 * slot taken keeps actorSlot == -1 and publishes nothing, and releasing a slot
 * immediately hands it to the waiting actor with the lowest entity number, so
 * the published set is deterministic and a freed slot is reused. Both counts
 * are observable, and script reads the slot through getactorslot. */
int CODOL_Sentient_PublishedActorCount(void);
int CODOL_Sentient_UnpublishedActorCount(void);

/* Pool index <-> record, for cursors that must survive a record being freed. */
int CODOL_Sentient_Index(const codol_sentient_t *sentient);
codol_sentient_t *CODOL_Sentient_ByIndex(int index);

/* C1 0x579640: the record an entity owns, NULL when it has none. */
codol_sentient_t *CODOL_Sentient_ForEntity(struct gentity_s *entity);

/* Lifecycle producers. The client hooks live in the shared client paths; the
 * entity hook is G_FreeEntity. */
void CODOL_Sentient_ClientSpawned(struct gentity_s *entity);
void CODOL_Sentient_ClientTeamChanged(struct gclient_s *client);
void CODOL_Sentient_ClientDisconnected(int clientNum);
void CODOL_Sentient_EntityFreed(struct gentity_s *entity);

/* Map spawn: C1 routes a "actor_" classname into its actor spawner (0x538da7,
 * 0x56b1ce, 0x6f0d34), which registers the entity in this same pool. Returns
 * qtrue when it consumed the classname. */
qboolean CODOL_Sentient_SpawnActorEntity(struct gentity_s *entity, const char *classname);

/* GSC. Names follow the C1 handler diagnostics, whose script names are
 * stripped in the shipped build. */
void CODOL_Scr_MakeEntitySentient(scr_entref_t ref);
void CODOL_Scr_FreeEntitySentient(scr_entref_t ref);
void CODOL_Scr_IsSentient(scr_entref_t ref);
void CODOL_Scr_SetSentientTeam(scr_entref_t ref);
void CODOL_Scr_GetSentientTeam(scr_entref_t ref);
void CODOL_Scr_SetDontTarget(scr_entref_t ref);
void CODOL_Scr_GetDontTarget(scr_entref_t ref);

}

#endif /* __cplusplus */
#ifndef __cplusplus
/* C collision consumers only need presence, not the C++ EntHandle layout. */
struct gentity_s;
struct codol_sentient_s;
struct codol_sentient_s *CODOL_Sentient_ForEntity(struct gentity_s *entity);
#endif
#endif /* CODOL_SERVER */
#endif
