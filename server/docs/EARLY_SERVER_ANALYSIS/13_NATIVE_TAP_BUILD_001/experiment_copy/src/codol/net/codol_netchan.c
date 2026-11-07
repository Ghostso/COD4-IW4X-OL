/* Native CoDOL netchan implementation. No binary patching or hooks.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "netchan.h"
#include "codol_wire.h"
#include <string.h>

qboolean CODOL_NetchanProcess(netchan_t *chan, msg_t *msg)
{
    uint32_t raw, sequence;
    codol_fragments_t fragments;
    int result, header = chan->sock == NS_SERVER ? 6 : 4;
    MSG_BeginReading(msg);
    if (msg->cursize < header) return qfalse;
    raw = (uint32_t)MSG_ReadLong(msg);
    if (chan->sock == NS_SERVER) MSG_ReadShort(msg);
    sequence = raw & CODOL_SEQUENCE_MASK;
    if (raw & CODOL_ACK_BIT) return qfalse;
    if (sequence <= (uint32_t)chan->incomingSequence) return qfalse;
    if (!(raw & CODOL_FRAGMENT_BIT)) {
        if (raw != sequence) return qfalse;
        chan->dropped = sequence - (chan->incomingSequence + 1);
        chan->incomingSequence = sequence;
        return qtrue;
    }
    if (!chan->fragmentBuffer || chan->fragmentBufferSize <= (int)sizeof(fragments))
        return qfalse;
    /* Metadata uses caller-owned storage, preserving netchan_t's IW3 ABI. */
    memcpy(&fragments, chan->fragmentBuffer, sizeof(fragments));
    result = CODOL_ReadFragment(&fragments,
        chan->fragmentBuffer + sizeof(fragments),
        chan->fragmentBufferSize - sizeof(fragments), raw,
        msg->data + header, msg->cursize - header);
    if (result < 0) return qfalse;
    memcpy(chan->fragmentBuffer, &fragments, sizeof(fragments));
    if (result != CODOL_WIRE_COMPLETE) return qfalse;
    if (msg->maxsize < 4 || fragments.length > (unsigned)(msg->maxsize - 4))
        return qfalse;
    MSG_Init(msg, msg->data, msg->maxsize);
    MSG_WriteLong(msg, sequence);
    MSG_WriteData(msg, chan->fragmentBuffer + sizeof(fragments), fragments.length);
    msg->readcount = 4;
    msg->bit = 32;
    chan->fragmentSequence = sequence;
    chan->fragmentLength = 0;
    chan->dropped = sequence - (chan->incomingSequence + 1);
    chan->incomingSequence = sequence;
    return qtrue;
}

qboolean CODOL_NetchanTransmitNextFragment(netchan_t *chan)
{
    byte packet[MAX_PACKETLEN];
    size_t length, chunk;
    if (!chan->unsentFragments || chan->unsentFragmentStart < 0 ||
        chan->unsentLength <= chan->unsentFragmentStart) return qfalse;
    length = CODOL_WritePacket(packet, sizeof(packet), chan->outgoingSequence,
        chan->sock == NS_CLIENT ? chan->qport : -1, chan->unsentBuffer,
        chan->unsentLength, chan->unsentFragmentStart / CODOL_FRAGMENT_SIZE);
    if (!length || !NET_SendPacket(chan->sock, length, packet, &chan->remoteAddress))
        return qfalse;
    chunk = chan->unsentLength - chan->unsentFragmentStart;
    if (chunk > CODOL_FRAGMENT_SIZE) chunk = CODOL_FRAGMENT_SIZE;
    chan->unsentFragmentStart += chunk;
    if (chan->unsentFragmentStart == chan->unsentLength) {
        ++chan->outgoingSequence;
        chan->unsentFragments = qfalse;
    }
    return qtrue;
}

qboolean CODOL_NetchanTransmit(netchan_t *chan, int length, const byte *data)
{
    byte packet[MAX_PACKETLEN];
    size_t size;
    if (length < 0 || (!data && length) || length > chan->unsentBufferSize ||
        length > (int)CODOL_MAX_MESSAGE || chan->unsentFragments ||
        (unsigned)chan->outgoingSequence > CODOL_SEQUENCE_MASK) return qfalse;
    if (length >= (int)CODOL_FRAGMENT_SIZE) {
        if (!chan->unsentBuffer) return qfalse;
        chan->unsentFragmentStart = 0;
        chan->unsentFragments = qtrue;
        chan->unsentLength = length;
        memcpy(chan->unsentBuffer, data, length);
        return CODOL_NetchanTransmitNextFragment(chan);
    }
    size = CODOL_WritePacket(packet, sizeof(packet), chan->outgoingSequence,
        chan->sock == NS_CLIENT ? chan->qport : -1, data, length, 0);
    if (!size || !NET_SendPacket(chan->sock, size, packet, &chan->remoteAddress))
        return qfalse;
    ++chan->outgoingSequence;
    return qtrue;
}
qboolean CODOL_NetchanSubmit(netchan_t *chan, int length, const byte *data)
{
    qboolean sent;
    if (!chan || chan->unsentFragments) return qfalse;
    sent = CODOL_NetchanTransmit(chan, length, data);
    /* C1's message reassembler consumes a fragment set as one snapshot. Send
     * the complete set in this server frame, matching the reference server's
     * split_or_whole/send loop. Draining one fragment per 50 ms server frame
     * made every ordinary two-fragment snapshot arrive at 10 Hz and kept the
     * client's command clock another full snapshot behind, producing visible
     * prediction replay. A socket failure leaves the owned queue intact for
     * the engine's normal retry path. */
    while (sent && chan->unsentFragments)
        sent = CODOL_NetchanTransmitNextFragment(chan);
    return sent;
}
#endif
