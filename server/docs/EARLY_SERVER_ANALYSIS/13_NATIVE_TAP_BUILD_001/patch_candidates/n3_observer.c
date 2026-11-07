/* Candidate-only native message observer.
 *
 * This file is NOT part of the original source tree. It is a review artifact
 * for the isolated experiment copy created by EARLY-NATIVE-TAP-BUILD-001.
 *
 * The whole translation unit is a no-op unless CODOL_SERVER is defined, so it
 * does not perturb non-CODOL build targets that also glob src/*.c.
 *
 * It records only target message metadata by default. Full plaintext payload
 * recording is opt-in via codol_nativeTapPayload and is limited to messages
 * whose kind was supplied by the call site (gamestate/snapshot).
 *
 * The observer never writes msg->data, msg->cursize, msg->bit, msg->maxsize,
 * msg->overflowed, client state, netchan state, or any send result.
 *
 * IMPORTANT: msg->data[0] is the first byte of the whole netchan message
 * (the reliable-acknowledge prefix), NOT the internal gamestate/snapshot
 * segment opcode. It is therefore logged as wire_byte0 and never used to
 * derive segment_opcode. Only the caller-supplied `kind` labels the message.
 */
#ifdef CODOL_SERVER

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "q_shared.h"
#include "qcommon.h"
#include "server.h"
#include "msg.h"
#include "n3_observer.h"

#define CODOL_NATIVE_TAP_MAX_MESSAGE (4 * 1024 * 1024)
#define CODOL_NATIVE_TAP_FILE "codol_native_tap.log"

extern cvar_t *codol_nativeTapLog;
extern cvar_t *codol_nativeTapPayload;

static FILE *codol_nativeTapFile;

static int CODOL_NativeTapEnabled(void)
{
    return codol_nativeTapLog && codol_nativeTapLog->integer > 0;
}

static FILE *CODOL_NativeTapHandle(void)
{
    if (!codol_nativeTapFile)
        codol_nativeTapFile = fopen(CODOL_NATIVE_TAP_FILE, "ab");
    return codol_nativeTapFile;
}

/* `kind` is authoritative: it is supplied by the call site, which sits in the
 * gamestate and snapshot send paths respectively. It is never inferred from
 * wire bytes. When kind is NULL the message is logged as "unclassified"; the
 * first byte is never promoted to a segment opcode. */
static const char *CODOL_NativeTapKind(const char *kind)
{
    if (kind && kind[0]) return kind;
    return "unclassified";
}

void CODOL_NativeTapObserveMessage(const char *kind, struct client_s *client, msg_t *msg)
{
    const char *klass;
    uint32_t seq = 0;
    int i;
    unsigned long long fnv = 1469598103934665603ULL;

    if (!CODOL_NativeTapEnabled() || !msg || !msg->data ||
        msg->cursize < 1 || msg->cursize > CODOL_NATIVE_TAP_MAX_MESSAGE)
        return;

    klass = CODOL_NativeTapKind(kind);
    if (client) seq = (uint32_t)client->netchan.outgoingSequence;

    for (i = 0; i < msg->cursize; ++i) {
        fnv ^= (unsigned char)msg->data[i];
        fnv *= 1099511628211ULL;
    }

    {
        FILE *f = CODOL_NativeTapHandle();
        if (!f) return;
        fprintf(f,
            "tap=1 kind=%s direction=s2c state=%d client=%d seq=%u len=%d "
            "wire_byte0=0x%02x segment_opcode=unknown fnv64=%016llx\n",
            klass,
            client ? (int)client->state : -1,
            client ? (int)(client - svs.clients) : -1,
            seq, msg->cursize, (unsigned)msg->data[0],
            (unsigned long long)fnv);
        if (codol_nativeTapPayload && codol_nativeTapPayload->integer > 0 &&
            (strcmp(klass, "gamestate") == 0 || strcmp(klass, "snapshot") == 0)) {
            fprintf(f, "tap_payload kind=%s seq=%u len=%d hex=", klass, seq,
                    msg->cursize);
            for (i = 0; i < msg->cursize; ++i) fprintf(f, "%02x", msg->data[i]);
            fputc('\n', f);
        }
        fflush(f);
    }
}

#endif /* CODOL_SERVER */
