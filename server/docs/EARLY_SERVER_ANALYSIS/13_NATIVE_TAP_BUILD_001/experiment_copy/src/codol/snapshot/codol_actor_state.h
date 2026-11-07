#ifndef CODOL_ACTOR_STATE_H
#define CODOL_ACTOR_STATE_H
#ifdef CODOL_SERVER

/* CoDOL actor state: production, archive and per-recipient capture.
 *
 * The actor channel is the non-player half of the composition channels. C1
 * (C1.exe 1.1.1.13, base 0x400000) carries it beside the entity and client
 * channels with its own netfield table at 0xc37158 (24 entries of
 * {offset, bits, hint}, matching src/codol_actor_fields.inc), its own server
 * ring (base svs+0x9ce8 stored XOR 0x2711f6dc, capacity svs+0x9cd0, cursor
 * svs+0x341c) and its own per-frame span (frame+0x339c first, frame+0x338c
 * count). The count handed to the game is clamped to 32 (0x4871b3) and the
 * records are copied into snapshot+0x54b2c, 0xb80 = 32 * 0x5c bytes.
 *
 * Field meaning is taken from C1's client applier 0x42a6f0, which is a
 * straight field-by-field application of a record onto a 0x29c-byte client
 * composition slot indexed by the record's number:
 *   +0x00  record number, the composition slot 0..31
 *   +0x04  entity number (11 bits); 0x46c48e indexes the client entity array
 *          with it, so the record composes that entity
 *   +0x0c  base model: a CS_MODELS-relative index (the applier resolves it
 *          through stringOffsets[1315 + value], and 1315 is CODOL_CS_MODELS)
 *   +0x14/+0x18/+0x1c/+0x20  four part models, same table
 *   +0x24/+0x28/+0x2c/+0x30  four part name ids, resolved through
 *          stringOffsets[5299 + value], and 5299 is CODOL_CS_TAGS
 *   +0x34  per-part boolean bit field, bit i for part i, read by the client's
 *          composition builder at 0x428cae while it walks the four parts
 * Parts are contiguous: the client's builder stops at the first part with no
 * model (0x428c70). The parts are the entity's own native attachment state -
 * gentity_s::model, attachModelNames[19], attachTagNames[19] and
 * attachIgnoreCollision, written by G_EntAttach / G_EntDetach / G_SetModel and
 * composed server-side by G_DObjUpdate - so this producer publishes what the
 * server itself builds its DObj from. Model indices and tag script strings are
 * different namespaces: the tag goes through SL_ConvertToString and G_TagIndex
 * before the CS_TAGS wire mapping, exactly as ClientEndFrame does for a
 * player's attachments.
 * The remaining fields (+0x08, +0x10, +0x38, +0x3c, +0x40, +0x44..46,
 * +0x48, +0x4c, +0x50..+0x58) are applied to slot members whose consumers this
 * pass did not establish. The current partial producer zero-initializes them;
 * it does not preserve a previous delta baseline. Full composition support
 * requires establishing their semantics and implementing their producers.
 *
 * Snapshot discipline: an actor table is produced from live state only at
 * capture time. A recipient whose snapshot came from a cached (archived)
 * snapshot receives the table archived with that snapshot, never a live
 * lookup, exactly like the entity states it is paired with. */

#include "codol_actors.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Archived tables are keyed by the engine's archived-frame number, which is
 * the only identity both archive paths agree on: SV_ArchiveSnapshot stamps it
 * into the cached snapshot it fills, and SV_GetCachedSnapshotInternal stamps
 * the same number when it decodes an archived frame back into another cache
 * slot. The ring holds as many frames as the engine can be asked for
 * (NUM_ARCHIVED_FRAMES), and each slot re-checks the frame number and the
 * snapshot time so a recycled slot is never mistaken for the one archived. */
#define CODOL_ACTOR_ARCHIVE_SLOTS 1200

/* Build the current actor table from live state. Records are emitted in
 * ascending slot order, which is what the wire writer requires. */
int CODOL_ProduceActorStates(codol_actor_state_t *out, unsigned capacity, unsigned *count);

/* Archive the current table with an archived snapshot. */
int CODOL_ArchiveSnapshotActors(int archivedFrame, int time);
void CODOL_ClearActorArchive(void);

/* Per recipient, keyed by the outgoing sequence, exactly like the HUD
 * capture. archivedFrame < 0 captures live state; otherwise the table archived
 * with that archived frame is copied. Failure leaves the recipient without a
 * capture, which fails its frame instead of publishing another frame's
 * actors. */
int CODOL_CaptureClientSnapshotActors(unsigned client, uint32_t sequence,
                                      int archivedFrame, int archiveTime);
int CODOL_CopyClientSnapshotActors(unsigned client, uint32_t sequence,
                                   codol_actor_state_t *out, unsigned capacity,
                                   unsigned *count);
void CODOL_InvalidateClientSnapshotActors(unsigned client);
void CODOL_ClearClientSnapshotActors(unsigned client);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif
