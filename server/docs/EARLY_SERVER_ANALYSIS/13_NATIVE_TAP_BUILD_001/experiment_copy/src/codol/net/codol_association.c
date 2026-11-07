/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_association.h"
#include "codol_crypto.h"
#include "codol_wire.h"
#include <string.h>

static void erase(void *ptr, size_t n)
{
    volatile uint8_t *p = ptr;
    while (n--) *p++ = 0;
}
void CODOL_AssociationClear(codol_association_t *s)
{ if (s) erase(s, sizeof(*s)); }

int CODOL_AssociationStart(codol_association_t *s, const uint8_t x[28],
                           const uint8_t security[16], uint16_t local,
                           uint16_t peer)
{
    codol_association_t next = {0};
    if (!s || !x || !security || !local || !peer) return 0;
    if (!CODOL_DeriveKey(next.key, x, security)) {
        erase(&next, sizeof(next)); return 0;
    }
    memcpy(next.shared_x, x, 28);
    next.local_tag = local; next.peer_tag = peer;
    next.send_next = 1; next.active = 1;
    *s = next;
    erase(&next, sizeof(next));
    return 1;
}

size_t CODOL_AssociationSeal(codol_association_t *s, uint8_t *out, size_t cap,
                             const uint8_t *plain, size_t length)
{
    size_t n;
    if (!s || !s->active || s->send_exhausted) return 0;
    n = CODOL_EncryptRecord(out, cap, plain, length, s->send_next, s->peer_tag, s->key);
    if (n) {
        if (s->send_next == UINT32_MAX) s->send_exhausted = 1;
        else ++s->send_next;
    }
    return n;
}

int CODOL_AssociationOpenDetailed(codol_association_t *s, uint8_t *out, size_t cap,
                          size_t *out_length, const uint8_t *record, size_t length,
                          const uint8_t candidate[16], const char **reason)
{
    uint8_t replacement[24] = {0};
    uint32_t counter, decoded, window, distance;
    uint16_t low;
    size_t size;
    int rotated = 0, ok = 0;
    if (reason) *reason = "invalid record or inactive association";
    if (!s || !s->active || !out || !out_length || !record || length < 16) return 0;
    if (reason) *reason = "unexpected record type";
    if (record[0] != 6 || record[1] != 2) return 0;
    if (reason) *reason = "destination tag does not match association";
    if ((uint16_t)(record[2] | (unsigned)record[3] << 8) != s->local_tag) return 0;
    if (reason) *reason = "invalid payload length";
    size = (unsigned)record[14] | (unsigned)record[15] << 8;
    if (size != length - 16 || size > cap) return 0;
    low = (uint16_t)(record[4] | (unsigned)record[5] << 8);
    counter = s->received ? CODOL_ExtendCounter(low, s->receive_high) : low;
    window = s->receive_window;
    if (s->received && counter <= s->receive_high) {
        distance = s->receive_high - counter;
        if (reason) *reason = "counter outside replay window";
        if (distance >= 32) return 0;
        if (reason) *reason = "duplicate counter";
        if (window & (UINT32_C(1) << distance)) return 0;
        window |= UINT32_C(1) << distance;
    } else {
        distance = counter - s->receive_high;
        window = !s->received || distance >= 32 ? 1 : (window << distance) | 1;
    }
    /* Use the already resolved counter as the reference, including first DATA
     * records with a low word above 32768. No unverified epoch resync guesses. */
    if (reason) *reason = "record authentication/decryption failed with association and lobby keys";
    if (!CODOL_DecryptRecord(out, cap, &size, &decoded, record, length,
                            counter, s->local_tag, s->key)) {
        if (!candidate || !CODOL_DeriveKey(replacement, s->shared_x, candidate) ||
            !CODOL_DecryptRecord(out, cap, &size, &decoded, record, length,
                                 counter, s->local_tag, replacement)) goto done;
        rotated = 1;
    }
    if (rotated) memcpy(s->key, replacement, sizeof(s->key));
    s->receive_window = window;
    if (!s->received || counter > s->receive_high) s->receive_high = counter;
    s->received = 1;
    *out_length = size; ok = 1;
    if (reason) *reason = NULL;
done:
    erase(replacement, sizeof(replacement));
    return ok;
}

int CODOL_AssociationOpen(codol_association_t *s, uint8_t *out, size_t cap,
                          size_t *out_length, const uint8_t *record, size_t length,
                          const uint8_t candidate[16])
{
    return CODOL_AssociationOpenDetailed(s, out, cap, out_length, record, length,
                                        candidate, NULL);
}
