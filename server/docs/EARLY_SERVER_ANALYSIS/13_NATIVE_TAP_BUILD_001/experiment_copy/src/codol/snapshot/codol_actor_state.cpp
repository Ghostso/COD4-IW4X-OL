#ifdef CODOL_SERVER
/* Actor state producer, archive and capture - see codol_actor_state.h for the
 * C1 evidence behind the record layout and the field meanings used here. */

#include "codol_actor_state.h"
#include "codol_sentient.h"
#include "codol_actor_lifecycle.h"
#include "codol_configstrings.h"
#include "g_shared.h"
#include "entity.h"
#include "server.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"

#include <stdlib.h>
#include <string.h>

/* Write one 32-bit field at its measured record offset. codol_actors.c reads
 * every field the same way (little endian, four bytes at fields[i].offset),
 * including the three overlapping byte fields at 0x44/0x45/0x46, which is why
 * the record is one byte image and not a struct of named members. */
static void actor_put(codol_actor_state_t *state, unsigned offset, uint32_t value)
{
    uint8_t *p = state->data + offset;

    p[0] = (uint8_t)(value & 0xff);
    p[1] = (uint8_t)((value >> 8) & 0xff);
    p[2] = (uint8_t)((value >> 16) & 0xff);
    p[3] = (uint8_t)((value >> 24) & 0xff);
}

/* C1 record offsets, from the applier 0x42a6f0. */
#define CODOL_ACTOR_OFF_NUMBER 0x00
#define CODOL_ACTOR_OFF_ENTITY 0x04
#define CODOL_ACTOR_OFF_MODEL 0x0c
#define CODOL_ACTOR_OFF_PART_MODEL 0x14
#define CODOL_ACTOR_OFF_PART_TAG 0x24
#define CODOL_ACTOR_OFF_PART_FLAGS 0x34
/* C1 0x428cd9: the client composes four parts beside the base model. */
#define CODOL_ACTOR_WIRE_PARTS 4
/* gentity_s::attachModelNames / attachTagNames, src/entity.h. */
#define CODOL_ENTITY_ATTACH_SLOTS 19

extern "C"
{
/* src/asmsource/_g_utils_mp.asm: G_TagIndex(name) is
 * G_FindConfigstringIndex(name, CS_TAGS, MAX_TAGS, 1, 0), the same call
 * ClientEndFrame makes when it publishes a player's attachment tags. */
int G_TagIndex(const char *name);
}

/* An attachment tag is a script string in the entity array and a CS_TAGS
 * index on the wire - two different namespaces. This is the conversion
 * ClientEndFrame (_g_active_mp.asm:466..473) already performs for players. */
static int actor_attach_tag_index(unsigned scriptString)
{
    const char *name;

    if (!scriptString)
    {
        return 0;
    }
    name = SL_ConvertToString(scriptString);
    if (!name || !*name)
    {
        return 0;
    }
    return G_TagIndex(name);
}

/* Truncation beyond the wire capacity is the native reference behaviour
 * (ClientEndFrame publishes 6 of the 19 native slots the same way), but it is
 * reported rather than silent: once per entity, and again whenever the number
 * of unpublished parts changes. */
static void actor_report_overflow(const gentity_s *entity, unsigned dropped)
{
    static unsigned char reported[MAX_GENTITIES];

    if (entity->s.number < 0 || entity->s.number >= MAX_GENTITIES)
    {
        return;
    }
    if (reported[entity->s.number] == (unsigned char)dropped)
    {
        return;
    }
    reported[entity->s.number] = (unsigned char)dropped;
    if (dropped)
    {
        Com_DPrintf(CON_CHANNEL_SERVER,
                    "actor entity %i carries %u attachments past the %u the actor channel "
                    "publishes; the server DObj keeps all of them\n",
                    entity->s.number, dropped, (unsigned)CODOL_ACTOR_WIRE_PARTS);
    }
}

/* The composition of one actor entity, read from the native entity state the
 * server itself composes its DObj from:
 *
 *   base model      gentity_s::model      (+0x168) - the field G_SetModel
 *                                          writes and G_DObjUpdate composes
 *                                          parts[0] from
 *   part models     attachModelNames[i]   (+0x220) - model indices written by
 *                                          G_EntAttach through G_ModelIndex
 *   part tags       attachTagNames[i]     (+0x246) - script strings written by
 *                                          G_EntAttach through Scr_SetString
 *   part flags      attachIgnoreCollision (+0x178) - bit i, the same bit
 *                                          G_DObjUpdate_120 turns into the
 *                                          third member of each DObj part
 *
 * The list is contiguous and ends at the first empty model, which is the rule
 * G_DObjUpdate_100, ClientEndFrame and C1's client builder (0x428c70) all
 * follow. Every translation failure fails the capture, because a rejected
 * model or tag would otherwise be published as index 0 - an empty name, which
 * the client reads as "the parts list ends here" or as no model at all. */
static int actor_from_entity(codol_actor_state_t *out, int slot, gentity_s *entity)
{
    unsigned published = 0;
    unsigned dropped = 0;
    uint32_t flags = 0;
    unsigned i;
    int model;

    if (!entity || !entity->r.inuse)
    {
        return 0;
    }
    if (entity->s.number < 0 || entity->s.number >= MAX_GENTITIES)
    {
        return 0;
    }
    /* gentity_s::model is the field G_SetModel writes and G_DObjUpdate builds
     * parts[0] from, so publishing it is what keeps the client's composition
     * and the server's DObj on the same base. entityState::index is a separate
     * IW3 field that G_SetModel does not touch; it is only used here as a
     * fallback for an entity whose model reached the entity channel and not
     * the DObj. */
    model = CODOL_ServerModelToWire((unsigned)(entity->model ? entity->model
                                                             : (uint16_t)entity->s.index));
    if (model < 0 || (unsigned)model >= CODOL_MODEL_SLOTS)
    {
        return 0;
    }

    memset(out, 0, sizeof(*out));
    out->number = (unsigned)slot;
    /* C1 stores the number inside the record too (0x49d522, 0x5d676d); the
     * writer never deltas offset 0, so this only keeps the byte image
     * faithful. */
    actor_put(out, CODOL_ACTOR_OFF_NUMBER, (uint32_t)slot);
    actor_put(out, CODOL_ACTOR_OFF_ENTITY, (uint32_t)entity->s.number);
    actor_put(out, CODOL_ACTOR_OFF_MODEL, (uint32_t)model);
    {
        /* T5 dogs carry a second model shown to everyone but the owner's team
         * (level.enemyDogModel). Capture the metadata with the record so the
         * per-recipient choice below reads this archived actor, never a live
         * one that may already have been freed or recycled. */
        unsigned alternate = CODOL_ActorEnemyModel(entity);
        int enemyModel = alternate ? CODOL_ServerModelToWire(alternate) : 0;
        codol_sentient_t *sentient;
        if (enemyModel < 0 || (unsigned)enemyModel >= CODOL_MODEL_SLOTS)
        {
            return 0;
        }
        out->enemyModel = (unsigned)enemyModel;
        sentient = CODOL_Sentient_ForEntity(entity);
        out->actorTeam = sentient ? (unsigned)sentient->team : 0;
        out->ownerClient = entity->r.ownerNum.isDefined() ?
            entity->r.ownerNum.entnum() : -1;
    }

    for (i = 0; i < CODOL_ENTITY_ATTACH_SLOTS; ++i)
    {
        int partModel;
        int partTag;

        if (!entity->attachModelNames[i])
        {
            break;
        }
        if (published >= CODOL_ACTOR_WIRE_PARTS)
        {
            /* The native array reaches further than the wire does. Publishing
             * the first four in native order is what ClientEndFrame does with
             * the six a clientState carries; the rest stay on the server DObj
             * and are reported below. */
            ++dropped;
            continue;
        }
        partModel = CODOL_ServerModelToWire((unsigned)entity->attachModelNames[i]);
        if (partModel <= 0 || (unsigned)partModel >= CODOL_MODEL_SLOTS)
        {
            return 0;
        }
        partTag = CODOL_ServerTagToWire(
            (unsigned)actor_attach_tag_index(entity->attachTagNames[i]));
        if (partTag < 0 || (unsigned)partTag >= CODOL_TAG_SLOTS)
        {
            return 0;
        }
        actor_put(out, CODOL_ACTOR_OFF_PART_MODEL + published * 4, (uint32_t)partModel);
        actor_put(out, CODOL_ACTOR_OFF_PART_TAG + published * 4, (uint32_t)partTag);
        if (entity->attachIgnoreCollision & (1u << i))
        {
            flags |= 1u << published;
        }
        ++published;
    }
    /* Bits beyond the published parts stay clear: the client only reads bit i
     * while it is walking part i. */
    actor_put(out, CODOL_ACTOR_OFF_PART_FLAGS, flags);
    actor_report_overflow(entity, dropped);
    return 1;
}

int CODOL_ProduceActorStates(codol_actor_state_t *out, unsigned capacity, unsigned *count)
{
    unsigned produced = 0;
    int slot;

    if (!out || !count)
    {
        return 0;
    }
    for (slot = 0; slot < CODOL_MAX_ACTOR_SLOTS; ++slot)
    {
        codol_sentient_t *sentient = CODOL_Sentient_ActorBySlot(slot);

        if (!sentient || !sentient->entity)
        {
            continue;
        }
        if (produced >= capacity)
        {
            return 0;
        }
        if (!actor_from_entity(&out[produced], slot, sentient->entity))
        {
            /* A live registered actor with an unpublishable model is a failed
             * capture, not an actor removal in an otherwise valid table. */
            return 0;
        }
        ++produced;
    }
    *count = produced;
    return 1;
}

/* ------------------------------------------------------------------ archive */

typedef struct
{
    codol_actor_state_t *actors;
    unsigned capacity;
    unsigned count;
    int archivedFrame;
    int time;
    int valid;
} codol_actor_archive_t;

static codol_actor_archive_t s_archive[CODOL_ACTOR_ARCHIVE_SLOTS];

void CODOL_ClearActorArchive(void)
{
    unsigned i;

    for (i = 0; i < CODOL_ACTOR_ARCHIVE_SLOTS; ++i)
    {
        free(s_archive[i].actors);
        s_archive[i].actors = NULL;
        s_archive[i].capacity = 0;
        s_archive[i].count = 0;
        s_archive[i].valid = 0;
    }
}

/* A frame with no actors stores no records and allocates nothing, so the ring
 * only costs what is actually published. */
static int archive_reserve(codol_actor_archive_t *slot, unsigned count)
{
    codol_actor_state_t *grown;

    if (count <= slot->capacity)
    {
        return 1;
    }
    grown = (codol_actor_state_t *)realloc(slot->actors, count * sizeof(*grown));
    if (!grown)
    {
        return 0;
    }
    slot->actors = grown;
    slot->capacity = count;
    return 1;
}

int CODOL_ArchiveSnapshotActors(int archivedFrame, int time)
{
    codol_actor_state_t produced[CODOL_MAX_ACTOR_SLOTS];
    codol_actor_archive_t *slot;
    unsigned count = 0;

    if (archivedFrame < 0)
    {
        return 0;
    }
    slot = &s_archive[(unsigned)archivedFrame % CODOL_ACTOR_ARCHIVE_SLOTS];
    slot->valid = 0;
    if (!CODOL_ProduceActorStates(produced, CODOL_MAX_ACTOR_SLOTS, &count))
    {
        return 0;
    }
    if (!archive_reserve(slot, count))
    {
        return 0;
    }
    if (count)
    {
        memcpy(slot->actors, produced, count * sizeof(*produced));
    }
    slot->count = count;
    slot->archivedFrame = archivedFrame;
    slot->time = time;
    slot->valid = 1;
    return 1;
}

/* ------------------------------------------------------------------ capture */

typedef struct
{
    codol_actor_state_t *actors;
    unsigned count;
    uint32_t sequence;
    int valid;
} codol_actor_capture_t;

static codol_actor_capture_t s_captures[MAX_CLIENTS];

void CODOL_InvalidateClientSnapshotActors(unsigned client)
{
    if (client < MAX_CLIENTS)
    {
        s_captures[client].valid = 0;
    }
}

void CODOL_ClearClientSnapshotActors(unsigned client)
{
    if (client >= MAX_CLIENTS)
    {
        return;
    }
    free(s_captures[client].actors);
    s_captures[client].actors = NULL;
    s_captures[client].count = 0;
    s_captures[client].valid = 0;
}

int CODOL_CaptureClientSnapshotActors(unsigned client, uint32_t sequence,
                                      int archivedFrame, int archiveTime)
{
    codol_actor_state_t produced[CODOL_MAX_ACTOR_SLOTS];
    unsigned count = 0;

    if (client >= MAX_CLIENTS)
    {
        return 0;
    }
    s_captures[client].valid = 0;

    if (archivedFrame >= 0)
    {
        /* Delayed recipient: the entity states in this snapshot came out of
         * the cached snapshot, so its actors have to come out of the table
         * archived with the same archived frame. A ring slot that has since
         * been recycled fails here rather than substituting the live table. */
        const codol_actor_archive_t *archived =
            &s_archive[(unsigned)archivedFrame % CODOL_ACTOR_ARCHIVE_SLOTS];

        if (!archived->valid || archived->archivedFrame != archivedFrame ||
            archived->time != archiveTime)
        {
            return 0;
        }
        count = archived->count;
        if (count > CODOL_MAX_ACTOR_SLOTS)
        {
            return 0;
        }
        if (count)
        {
            memcpy(produced, archived->actors, count * sizeof(*produced));
        }
    }
    else if (!CODOL_ProduceActorStates(produced, CODOL_MAX_ACTOR_SLOTS, &count))
    {
        return 0;
    }

    {
        /* T5 CG_WhatModelShouldLocalPlayerSee semantics, resolved natively for
         * C1's composition record: the owner and the owner's team see the
         * friendly model, everyone else the alternate. The metadata came from
         * this same archive, never from the current actor. */
        unsigned viewClient = client;
        team_t team;
        unsigned viewTeam;
        unsigned i;
        if (level.clients[client].sess.cs.team == TEAM_SPECTATOR && archivedFrame < 0 &&
            (unsigned)level.clients[client].spectatorClient < MAX_CLIENTS)
        {
            viewClient = (unsigned)level.clients[client].spectatorClient;
        }
        team = level.clients[viewClient].sess.cs.team;
        viewTeam = team == TEAM_RED ? 1 : team == TEAM_BLUE ? 2 : 0;
        for (i = 0; i < count; ++i)
        {
            if (produced[i].enemyModel && produced[i].ownerClient != (int)client &&
                (!produced[i].actorTeam || produced[i].actorTeam != viewTeam))
            {
                actor_put(&produced[i], CODOL_ACTOR_OFF_MODEL, produced[i].enemyModel);
            }
        }
    }

    if (!s_captures[client].actors)
    {
        s_captures[client].actors =
            (codol_actor_state_t *)malloc(sizeof(*s_captures[client].actors) * CODOL_MAX_ACTOR_SLOTS);
        if (!s_captures[client].actors)
        {
            return 0;
        }
    }
    if (count)
    {
        memcpy(s_captures[client].actors, produced, count * sizeof(*produced));
    }
    s_captures[client].count = count;
    s_captures[client].sequence = sequence;
    s_captures[client].valid = 1;
    return 1;
}

int CODOL_CopyClientSnapshotActors(unsigned client, uint32_t sequence,
                                   codol_actor_state_t *out, unsigned capacity,
                                   unsigned *count)
{
    const codol_actor_capture_t *capture;

    if (!count || client >= MAX_CLIENTS)
    {
        return 0;
    }
    capture = &s_captures[client];
    if (!capture->valid || capture->sequence != sequence)
    {
        return 0;
    }
    if (capture->count > capacity || (capture->count && !out))
    {
        return 0;
    }
    if (capture->count)
    {
        memcpy(out, capture->actors, capture->count * sizeof(*out));
    }
    *count = capture->count;
    return 1;
}

#endif
