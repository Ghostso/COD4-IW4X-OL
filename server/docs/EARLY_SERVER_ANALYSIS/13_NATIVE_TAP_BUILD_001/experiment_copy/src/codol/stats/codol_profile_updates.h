/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PROFILE_UPDATES_H
#define CODOL_PROFILE_UPDATES_H
#include <stddef.h>
#include <stdint.h>
#include "codol_stats.h"
#include "codol_structured_schema.h"

/* Server-side modification state for the client-uploaded (public) playerdata
 * blob: what C1 1.1.1.13 records when a script writes it, and nothing else.
 *
 * Per-client layout, client array pointer [0x27f2e44], stride 0xf3da0:
 *   +0x62009  uploaded blob      chunk 0 destination            (0x5cf8fc)
 *   +0x6200d  structured record  0x7ffc bytes                   (0x55376a,0x5543b2)
 *   +0x6a009  dirty map          0x1000 bytes, one bit per record byte
 *   +0x6b009  dirty flag         stored as 1 after a script write
 *                                (0x553788, 0x554377, 0x5543e8, 0x5546c9)
 *   +0x6b00c  received mask      chunks uploaded, complete 0x7ffffff (0x5cf915)
 *
 * Marking semantics come from C1's own byte writer at 0x61f640, which every
 * typed def setter calls once per storage byte (0x61f680 int, 0x61f7a0 bool,
 * 0x61f860 enum/string, 0x61f9e0 float, 0x61fb70):
 *
 *     if(record[offset] == value) return 0;      // unchanged: no dirty bit
 *     record[offset] = value;
 *     if(map) map[offset >> 3] |= 1 << (offset & 7);
 *
 * so a dirty bit covers exactly one record byte, is set only for bytes whose
 * value actually changed, and is set only for bytes the setter wrote. The flag
 * store that follows the writer (0x553788) is unconditional and does not depend
 * on anything having changed. Both properties are reproduced below: callers
 * name the storage range the setter would have written, and only bytes that
 * differ from the pre-write image are marked.
 *
 * DELIVERY IS NOT IMPLEMENTED AND NOT DESIGNED FOR HERE. No C1 code that reads
 * this flag or this map has been identified, and no server->client transfer of
 * the record has been found; the client-side public blob (0x722d06c) is filled
 * by the account/profile decode path (0x592f30), not by a game-server message.
 * The upload chunking and "statResponse" mask are client->server only and are
 * not evidence about this direction, so this module deliberately provides no
 * encoder, no chunk mask, no send/ack/resend accounting and no delivery
 * predicate. Attaching a transport requires first proving the receiver; see
 * obj/claude-workers/profile-updates-report.md, including the limits of a
 * static search against C1's virtualized .tvm0 section and indirect base
 * pointers.
 *
 * The public blob is the only thing tracked. The attached secure profile has a
 * different def, a different owner and different authentication, and is never
 * read or exposed here.
 */

#define CODOL_PROFILE_RECORD_SIZE  0x7ffcu   /* 0x5543b2 */
#define CODOL_PROFILE_DIRTY_BYTES  0x1000u   /* 0x5cf933 */

/* Connection, disconnection and map reset: drops the pre-write image, the dirty
 * map and the flag for this client. */
void CODOL_ResetProfileUpdates(unsigned client);

/* Upload completion, mirroring 0x5cf933: clears the 0x1000-byte dirty map and
 * only that. C1's memset ends exactly where the flag byte begins, so a flag
 * raised before a re-upload survives it there and here. The pre-write image is
 * dropped with the bytes it described. */
void CODOL_ProfileUploadReplaced(unsigned client);

/* Take the pre-write image of the public record. Required before marking, since
 * C1's per-byte "did this change" test needs the previous contents. Returns 0
 * without a complete upload, or when the image cannot be taken; marking after a
 * failed begin marks nothing rather than a wrong range. */
int CODOL_BeginProfileUpdate(unsigned client);

/* Mark the storage bytes of a write that has already been applied to the shared
 * public view, and raise the dirty flag. offset is record-relative: the record
 * starts after the stored blob's four CRC bytes, which the map does not cover.
 * Only bytes differing from the pre-write image are marked, and the image is
 * advanced so several writes can share one begin. Returns the number of bytes
 * marked; the flag is raised for any in-range call, including a zero return.
 * An out-of-range or partly out-of-range range marks nothing, raises nothing
 * and returns 0. */
size_t CODOL_MarkProfileWrite(unsigned client, size_t offset, size_t length);

/* Same, for a field resolved through the structured schema, so callers do not
 * repeat the layout arithmetic. Storage follows the serialized offset map:
 * bool (2) is a bit position, everything else a byte address; widths are 4 for
 * int32 (0) and float (8), 2 for short (9) and named enum (4), 1 for byte (1)
 * and bool, and text_length+1 bytes for a string (3) written with its
 * terminator. text_length is ignored for other kinds. Returns 0 when the field
 * or its storage cannot be located. */
size_t CODOL_MarkProfileField(unsigned client, const codol_structured_layout_t *layout,
                              const codol_structured_field_t *field, size_t text_length);

/* The state itself. The map is CODOL_PROFILE_DIRTY_BYTES bytes, bit (i & 7) of
 * byte (i >> 3) for record byte i. */
int CODOL_ProfileUpdatePending(unsigned client);
const uint8_t *CODOL_ProfileUpdateDirtyMap(unsigned client, size_t *size);

/* Walk the marked record bytes as maximal ranges, starting at record offset
 * from. Returns 0 when no marked byte remains at or after from, otherwise 1
 * with *offset and *length set. This reads the verified state; it does not
 * imply a wire format. */
int CODOL_ProfileUpdateNextRange(unsigned client, size_t from,
                                 size_t *offset, size_t *length);

#endif
