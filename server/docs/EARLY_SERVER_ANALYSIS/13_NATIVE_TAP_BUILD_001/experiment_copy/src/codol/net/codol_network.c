/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "server.h"
#include "sys_net.h"
#include "sys_main.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include "codol_network.h"
#include "codol_handshake.h"
#include "codol_admission.h"
#include "codol_atomic_file.h"
#include <stdio.h>
#include <string.h>
#define PEERS 64
#define DATAGRAM 65507
#pragma pack(push, 8)
typedef struct {
    netadr_t address;
    codol_handshake_t handshake;
    uint32_t touched;
    uint32_t send_reserved;
    int used;
    int rejected;       /* DATA records no key opened since the handshake */
} peer_t;
#pragma pack(pop)
static peer_t peers[PEERS];
static cvar_t *key_path, *session_id;
static char configured_path[1024], configured_id[17];
static int sessions_loaded;
static uint32_t sessions_saved_at;
static int session_write_warned;
/* C1 1.1.1.13 interoperability key used by alpha0022/dtls_crypto.py.  C1 has
 * intermittently derived a different DATA key from otherwise valid randomized
 * COOKIE_ACK public keys: the tag and live-observed lobby security key match,
 * but every record MAC fails from counter 1.  The reference scalar has been
 * exercised by the Python server and keeps ECDH_X reproducible across native
 * restarts, which also makes cached-association recovery deterministic. */
static const byte reference_private_key[28] = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28
};
static void erase(void *ptr, size_t n)
{ volatile byte *p = ptr; while(n--) *p++ = 0; }
static int save_sessions(void);
void CODOL_NetworkReset(void) { save_sessions(); erase(peers, sizeof(peers)); sessions_loaded = 0; }
void CODOL_NetworkInit(void)
{
    key_path = Cvar_RegisterString("codol_securityKeyPath", "", 0,
        "Native bdDTLS session-key file (exactly 16 bytes); empty enables plaintext diagnostics");
    session_id = Cvar_RegisterString("codol_securityId", "4600000000000000", 0,
        "Trusted lobby bdDTLS security ID as 16 hexadecimal digits");
    CODOL_AdmissionInit();
}
static int hex(unsigned char c)
{
    if(c >= '0' && c <= '9') return c - '0';
    if(c >= 'a' && c <= 'f') return c - 'a' + 10;
    if(c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static int configuration(byte id[8])
{
    size_t i;
    if (!key_path || !session_id) return 0;
    if (strcmp(configured_path, key_path->string) || strcmp(configured_id, session_id->string)) {
        CODOL_NetworkReset();
        if (strlen(key_path->string) >= sizeof(configured_path) || strlen(session_id->string) != 16) return -1;
        strcpy(configured_path, key_path->string); strcpy(configured_id, session_id->string);
    }
    if (!*configured_path) return 0;
    for(i = 0; i < 8; ++i) {
        int a = hex(configured_id[2*i]), b = hex(configured_id[2*i+1]);
        if(a < 0 || b < 0) return -1;
        id[i] = (a << 4) | b;
    }
    return 1;
}
static int read_key(byte out[16])
{
    byte data[17]; size_t n; FILE *file = fopen(configured_path, "rb"); int ok;
    if(!file) return 0;
    n = fread(data, 1, sizeof(data), file); ok = n == 16 && !ferror(file);
    fclose(file); if(ok) memcpy(out, data, 16); erase(data, sizeof(data)); return ok;
}
/* Every session key this source may hold: the lobby's admission roster (this
 * IP's entries first), then -- unless admission is required -- the single
 * securitykey.bin the lobby rewrites on each createSession. The roster keeps a
 * seat's recent keys, not only its newest (C1 dials with the first key its
 * bdSecurityKeyMap registered since its last game; see dw_game_admission.py),
 * so there is room for several seats' histories behind one address. */
#define CANDIDATES 64
static peer_t *find(netadr_t *address, uint32_t now, int allocate);
static size_t candidate_keys(const netadr_t *from, byte keys[CANDIDATES][16])
{
    size_t count = CODOL_AdmissionCandidates(from->ip, keys, CANDIDATES - 1);
    if(!CODOL_AdmissionRequired() && read_key(keys[count])) {
        size_t i;
        for(i = 0; i < count && memcmp(keys[i], keys[count], 16); ++i);
        if(i == count) ++count;
    }
    return count;
}
int CODOL_NetworkAdmission(const netadr_t *from, codol_admission_entry_t *out)
{
    peer_t *p;
    if(!from || !out || from->type != NA_IP) return 0;
    p = find((netadr_t *)from, Sys_Milliseconds(), 0);
    if(!p || !p->handshake.established || !p->handshake.data.active) return 0;
    return CODOL_AdmissionIdentify(from->ip, p->handshake.data.shared_x, p->handshake.data.key, out);
}
static int random_bytes(void *unused, unsigned char *out, size_t n)
{ (void)unused; return n <= 65535 && Sys_RandomBytes(out, (int)n) ? 0 : -1; }
static int same(const netadr_t *a, const netadr_t *b)
{ return a->type == NA_IP && b->type == NA_IP && a->port == b->port && !memcmp(a->ip, b->ip, 4); }
static peer_t *find(netadr_t *address, uint32_t now, int allocate)
{
    peer_t *free_slot = NULL, *oldest_idle = NULL;
    uint32_t oldest_age = 120000u;
    unsigned i;
    for(i = 0; i < PEERS; ++i) {
        peer_t *p = &peers[i];
        uint32_t age = (uint32_t)(now - p->touched);
        /* C1 can reuse its established association after a long lobby idle.
         * Only incomplete handshakes expire automatically; established peers
         * are recycled when a valid new INIT needs a full pool's idle slot. */
        if(p->used && !p->handshake.established && age > 10000u)
            erase(p, sizeof(*p));
        if(p->used && same(&p->address, address)) return p;
        if(!p->used && !free_slot) free_slot = p;
        if(allocate && p->used && p->handshake.established && age > oldest_age) {
            oldest_idle = p;
            oldest_age = age;
        }
    }
    return allocate ? (free_slot ? free_slot : oldest_idle) : NULL;
}
static void drop_previous(netadr_t *address)
{
    int i;
    if (!svs.clients || !sv_maxclients) return;
    for(i = 0; i < sv_maxclients->integer; ++i)
        if(svs.clients[i].state >= CS_CONNECTED && same(&svs.clients[i].netchan.remoteAddress, address))
            SV_DropClientNoNotify(&svs.clients[i], "EXE_DISCONNECTED");
}
/* Association persistence across server restarts. C1 caches its bdDTLS
 * association with the host (NAT traversal is cached, the association is
 * reused forever), so a restarted server that lost the state can never
 * decrypt the client again and the client dies of cl_timeout at every
 * attempt. alpha0022 game-server.py persists the same state
 * (session_resume.json / ecdh_x_cache.json): the shared X (only obtainable
 * from the client's COOKIE_ECHO), the derived key, both tags, and the record
 * counters. The send counter resumes with a margin (the client only requires
 * strictly newer records); the receive counter must be exact. Entries expire
 * after fifteen minutes, as the reference's CODOL_RESUME_TTL does. */
#define SESSION_FILE "codol_sessions.txt"
#define SESSION_TTL 900
#define SESSION_SEND_MARGIN 256u
static void hex_encode(char *out, const byte *in, size_t n)
{
    static const char digits[] = "0123456789abcdef"; size_t i;
    for(i = 0; i < n; ++i) { out[2*i] = digits[in[i] >> 4]; out[2*i+1] = digits[in[i] & 15]; }
    out[2*n] = 0;
}
static int hex_decode(byte *out, const char *in, size_t n)
{
    size_t i;
    for(i = 0; i < n; ++i) {
        int a = hex((unsigned char)in[2*i]), b = hex((unsigned char)in[2*i+1]);
        if(a < 0 || b < 0) return 0;
        out[i] = (byte)((a << 4) | b);
    }
    return 1;
}
static uint32_t next_reservation(uint32_t send_next)
{
    return send_next > UINT32_MAX - SESSION_SEND_MARGIN ? UINT32_MAX : send_next + SESSION_SEND_MARGIN;
}
static int save_sessions(void)
{
    char text[PEERS * 200], *at = text;
    uint32_t reserved[PEERS] = {0};
    unsigned i; int count = 0, length;
    time_t now = Com_GetRealtime();
    for(i = 0; i < PEERS; ++i) {
        const peer_t *p = &peers[i]; char x[57], key[49];
        if(!p->used || !p->handshake.established || !p->handshake.data.active || p->address.type != NA_IP) continue;
        reserved[i] = next_reservation(p->handshake.data.send_next);
        hex_encode(x, p->handshake.data.shared_x, 28); hex_encode(key, p->handshake.data.key, 24);
        at += sprintf(at, "%u.%u.%u.%u %u %s %s %u %u %u %u %u %ld\n",
            p->address.ip[0], p->address.ip[1], p->address.ip[2], p->address.ip[3], (unsigned)BigShort(p->address.port),
            x, key, (unsigned)p->handshake.data.local_tag, (unsigned)p->handshake.data.peer_tag,
            reserved[i], p->handshake.data.receive_high, p->handshake.data.receive_window, (long)now);
        ++count;
    }
    /* Before the saved file has been read (the startup configuration reset)
     * there is nothing to record, and writing would discard it. */
    if(!count && !sessions_loaded) return 1;
    length = (int)(at - text);
    if(!CODOL_AtomicWriteHomeFile(SESSION_FILE, text, (size_t)length)) {
        if(!session_write_warned) {
            session_write_warned = 1;
            Com_PrintWarning(CON_CHANNEL_NETWORK, "bdDTLS: could not save session counter reservations; gameplay sends paused\n");
        }
        return 0;
    }
    session_write_warned = 0;
    for(i = 0; i < PEERS; ++i) if(reserved[i]) peers[i].send_reserved = reserved[i];
    sessions_saved_at = Sys_Milliseconds();
    if(com_developer && com_developer->integer)
        Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: saved %d association(s) to %s\n", count, SESSION_FILE);
    return 1;
}
static void load_sessions(void)
{
    fileHandle_t file; long length; char *text, *line; int restored = 0;
    time_t now = Com_GetRealtime(); uint32_t ms = Sys_Milliseconds();
    sessions_loaded = 1;
    length = FS_SV_FOpenFileRead(SESSION_FILE, &file);
    /* An empty file still returns an open handle; leaving it open kept
     * Windows from replacing the file, so every save failed and gameplay
     * sends stayed paused ("waiting for connection"). */
    if(length <= 0 || !file) { if(file) FS_FCloseFile(file); return; }
    text = malloc((size_t)length + 1);
    if(!text) { FS_FCloseFile(file); return; }
    if(FS_Read(text, (int)length, file) != length) { free(text); FS_FCloseFile(file); return; }
    FS_FCloseFile(file); text[length] = 0;
    for(line = strtok(text, "\r\n"); line; line = strtok(NULL, "\r\n")) {
        unsigned ip[4], port, local_tag, peer_tag, send_next, receive_high, receive_window; long saved;
        char x[57], key[49]; peer_t *p; netadr_t address;
        if(sscanf(line, "%u.%u.%u.%u %u %56s %48s %u %u %u %u %u %ld", &ip[0], &ip[1], &ip[2], &ip[3], &port,
                  x, key, &local_tag, &peer_tag, &send_next, &receive_high, &receive_window, &saved) != 13) continue;
        if(strlen(x) != 56 || strlen(key) != 48 || now - saved > SESSION_TTL || ip[0] > 255 || ip[1] > 255 || ip[2] > 255 || ip[3] > 255 || port > 65535) continue;
        memset(&address, 0, sizeof(address)); address.type = NA_IP;
        address.ip[0] = (byte)ip[0]; address.ip[1] = (byte)ip[1]; address.ip[2] = (byte)ip[2]; address.ip[3] = (byte)ip[3];
        address.port = BigShort((unsigned short)port);
        p = find(&address, ms, 1);
        if(!p) continue;
        erase(p, sizeof(*p));
        if(!hex_decode(p->handshake.data.shared_x, x, 28) || !hex_decode(p->handshake.data.key, key, 24)) { erase(p, sizeof(*p)); continue; }
        p->handshake.data.local_tag = (uint16_t)local_tag; p->handshake.data.peer_tag = (uint16_t)peer_tag;
        /* Old files contain an actual counter; new files contain a reserved
         * high-water mark. Skipping another block is safe for both formats. */
        p->handshake.data.send_next = next_reservation(send_next);
        p->handshake.data.receive_high = receive_high; p->handshake.data.receive_window = receive_window;
        p->handshake.data.active = 1; p->handshake.data.received = 1;
        p->handshake.established = 1;
        p->used = 1; p->address = address; p->touched = ms;
        ++restored;
        if(com_developer && com_developer->integer)
            Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: restored association with %u.%u.%u.%u:%u (send counter %u, receive counter %u)\n",
                ip[0], ip[1], ip[2], ip[3], port, p->handshake.data.send_next, receive_high);
    }
    free(text);
    if(restored && com_developer && com_developer->integer)
        Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: %d association(s) resumed from %s\n", restored, SESSION_FILE);
}
void CODOL_NetworkSaveSessions(void) { save_sessions(); }
int CODOL_NetworkAuthenticated(netadr_t *address)
{
    byte id[8]; peer_t *p;
    if(configuration(id) != 1 || !address || address->type != NA_IP) return 0;
    p = find(address, Sys_Milliseconds(), 0);
    return p && p->handshake.established && p->handshake.data.received;
}
int CODOL_NetworkSend(netadr_t *to, const void *data, int n)
{
    byte id[8], wire[DATAGRAM]; size_t size;
    peer_t *p; int mode = configuration(id);
    /* Return-value contract with NET_SendPacket:
     *   >=0 -> we OWN this send (sealed record; the value is the send result)
     *   -1  -> NOT ours; NET_SendPacket falls through to plaintext Sys_SendPacket.
     *
     * The C1 bdDTLS association only ever carries the netchan gameplay stream to
     * a client we have completed a handshake with. Connectionless OOB traffic
     * (0xffffffff getinfo/getstatus/rcon "print"/challenge replies, bdNAT, a
     * bdQoS probe answer) is plaintext by definition and is addressed to senders
     * that have NO association -- the lobby's rcon dispatch from an ephemeral
     * 127.0.0.1 port, or a status/QoS probe. Sealing is impossible for those, so
     * they are not ours: hand them back to the plaintext path.
     *
     * Previously every un-associated destination returned 0 ("handled, drop"),
     * which silently swallowed EVERY OOB reply: the server executed an rcon
     * "status"/"getinfo" but the reply datagram never left the process and any
     * request/reply probe to the game port timed out. Falling through is safe --
     * a real gameplay client always has an established peer and still seals
     * below; an un-associated destination could not have received an encrypted
     * packet anyway, so at worst a datagram the client discards is emitted in
     * place of one that was already being lost. */
    if(mode <= 0 || !to || to->type != NA_IP || n < 0)
        return -1;
    p = find(to, Sys_Milliseconds(), 0);
    if(!p || !p->handshake.established)
        return -1;
    /* Persist a future counter before using any value from that range.
     * A process restart then resumes above every record this process sent,
     * independent of its packet rate between periodic session saves. */
    if(p->handshake.data.send_next >= p->send_reserved &&
       (!save_sessions() || p->handshake.data.send_next >= p->send_reserved))
        return 0;
    size = CODOL_AssociationSeal(&p->handshake.data, wire, sizeof(wire), data, (size_t)n);
    /* Only receive activity extends lifetime. Failed sends consume counters. */
    return size && Sys_SendPacket((int)size, wire, to);
}
int CODOL_NetworkReceive(netadr_t *from, const void *raw, int n)
{
    const byte *packet = raw;
    byte id[8], security[16] = {0}, private_key[28] = {0}, tag_bytes[2];
    byte keys[CANDIDATES][16];
    byte response[114], plain[DATAGRAM];
    uint16_t tag; uint32_t now; peer_t *p; int mode, result;
    size_t size; msg_t msg;
    int trace;
    /* bdQoSProbe request (C1 bdQoSProbe::sendRequest 0xa547a0): plaintext,
     * 18 bytes on the game socket: type 0x28, u64 client time, u32 probe id,
     * 4 bytes of secId, u8 last-retry flag. C1's QoSProbe_start (0x4dd2a0)
     * probes the connected server every 90 s; without an answer
     * bdQoSProbe::pump (0xa56568) logs "QoS failed to Public Addr", and
     * while the probe is pending bdNetImpl::receiveAll runs the shared socket
     * through bdConnectionStore::receiveAll (0xb0fe38), which can parse a
     * game datagram as bdPacket chunks ("unknown chunk type"). The answer is
     * C1's own bdQoSReplyPacket (deserialize 0xa5e7c0, reply type 0x29):
     * u8 type, u32 id, u64 time (both echoed), u8 enabled, u32 dataSize,
     * u32 0, f32 processing time, u8 hasData - 27 bytes with no data. C1
     * reports the round trip only to its Tencent TLOG (0x4dd900); nothing
     * gates play. No association is involved. */
    if(from && from->type == NA_IP && packet && n == 18 && packet[0] == 0x28) {
        /* Unauthenticated and plaintext, so it must not become a reflector:
         * one reply per address per 500 ms (C1 retries about once a second,
         * every 90 s) and at most 50 per second overall. */
        static uint32_t qos_addr[64], qos_addr_ms[64], qos_window_ms, qos_window_count;
        uint32_t now = (uint32_t)Sys_Milliseconds(), key;
        unsigned slot;
        byte reply[27] = {0x29};
        memcpy(&key, from->ip, 4);
        key ^= (uint32_t)from->port << 16;
        slot = (key ^ (key >> 11) ^ (key >> 22)) & 63;
        if(now - qos_window_ms >= 1000) { qos_window_ms = now; qos_window_count = 0; }
        if(qos_window_count >= 50 || (qos_addr[slot] == key && now - qos_addr_ms[slot] < 500))
            return 1;
        qos_window_count++;
        qos_addr[slot] = key;
        qos_addr_ms[slot] = now;
        memcpy(reply + 1, packet + 9, 4);
        memcpy(reply + 5, packet + 1, 8);
        reply[13] = 1;
        Sys_SendPacket((int)sizeof(reply), reply, from);
        if(com_developer && com_developer->integer)
            Com_DPrintf(CON_CHANNEL_NETWORK, "bdQoS: probe from %s -> reply\n", NET_AdrToString(from));
        return 1;
    }
    mode = configuration(id);
    if(!mode) return 0;
    trace = com_developer && com_developer->integer;
    if(mode < 0) {
        if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: invalid codol_securityKeyPath/codol_securityId configuration; packet dropped\n");
        return 1;
    }
    if(!from || from->type != NA_IP || !packet || n < 2 || n > DATAGRAM) return 1;
    /* bdNATTravClient INTRO REQ (type 13, 29 bytes: type, version 02 00, u32 id,
     * 10-byte MAC, two 6-byte addresses). C1's bdNATTravClient::receiveFrom
     * (0xa60560) waits for type 12 ("Received NAT Trav reply") before it
     * starts the bdDTLS INIT; otherwise the address fails with EXE_HOSTUNREACH.
     * The MAC is keyed with a client-local random key (init 0xa61400), so the
     * reply is the request echoed with the type flipped, which the client
     * verifies against its own inputs. No association is involved. */
    if(packet[0] == 13 && packet[1] == 2 && packet[2] == 0 && n == 29) {
        byte reply[29];
        memcpy(reply, packet, sizeof(reply)); reply[0] = 12;
        Sys_SendPacket((int)sizeof(reply), reply, from);
        if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: NAT-traversal INTRO REQ from %s -> reply\n", NET_AdrToString(from));
        return 1;
    }
    now = Sys_Milliseconds();
    if(!sessions_loaded) load_sessions();
    p = find(from, now, packet[0] == 1 && packet[1] == 2 && n == 16);
    if(!p) {
        if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: %s has no association slot (type %u, %d bytes); dropped\n", NET_AdrToString(from), packet[0], n);
        return 1;
    }
    if(packet[0] == 1 && packet[1] == 2 && n == 16) {
        int replacing;
        codol_handshake_t staged = {0};
        if(memcmp(packet + 8, id, 8)) {
            if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: INIT from %s carries security ID %02x%02x%02x%02x%02x%02x%02x%02x, configured %s; dropped\n",
                NET_AdrToString(from), packet[8], packet[9], packet[10], packet[11], packet[12], packet[13], packet[14], packet[15], configured_id);
            goto done;
        }
        if(!candidate_keys(from, keys)) {
            if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: INIT from %s but no session key is available (%s); dropped\n", NET_AdrToString(from),
                CODOL_AdmissionRequired() ? "no lobby admission" : "admission roster empty and session key file unreadable");
            goto done;
        }
        memcpy(private_key, reference_private_key, sizeof(private_key));
        if(random_bytes(NULL, tag_bytes, 2)) goto done;
        tag = (uint16_t)(tag_bytes[0] | (unsigned)tag_bytes[1] << 8);
        if(!tag) tag = 1;
        replacing = p->used && !same(&p->address, from);
        result = CODOL_HandshakeInit(replacing ? &staged : &p->handshake, response, packet, n, id, from->ip,
                    BigShort(from->port), tag, private_key, random_bytes, NULL);
        if(result && replacing) {
            erase(p, sizeof(*p));
            p->handshake = staged;
        }
        erase(&staged, sizeof(staged));
        if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: INIT from %s -> %s\n", NET_AdrToString(from), result == 1 ? "INIT_ACK (new)" : result ? "INIT_ACK (retransmit)" : "rejected");
        if(result) {
            if(result == 1) { drop_previous(from); p->rejected = 0; }
            p->used = 1; p->address = *from; p->touched = now;
            Sys_SendPacket(38, response, from);
        }
    } else if(packet[0] == 3 && packet[1] == 2 && n == 189) {
        if(!p->used || !candidate_keys(from, keys)) {
            if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: COOKIE_ECHO from %s %s; dropped\n", NET_AdrToString(from), p->used ? "with unreadable session key" : "without a pending INIT");
            goto done;
        }
        result = CODOL_HandshakeCookie(&p->handshake, response, packet, n, keys[0], random_bytes, NULL);
        if(trace) Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: COOKIE_ECHO from %s -> %s\n", NET_AdrToString(from), result ? "COOKIE_ACK, association established" : "rejected");
        if(result) { p->touched = now; Sys_SendPacket(114, response, from); save_sessions(); }
    } else if(packet[0] == 6 && packet[1] == 2 && p->used && p->handshake.established) {
        size_t have = candidate_keys(from, keys), k = 0;
        int have_key = have != 0, opened;
        const char *reason = NULL;
        /* A failed open leaves the association untouched, so each candidate may
         * be tried in turn; the one that authenticates becomes its key. */
        do opened = CODOL_AssociationOpenDetailed(&p->handshake.data, plain, sizeof(plain), &size,
                                packet, n, have ? keys[k] : NULL, &reason);
        while(!opened && ++k < have);
        if(opened) {
            p->touched = now; p->address = *from;
            if((uint32_t)(now - sessions_saved_at) > 5000u) save_sessions();
            if(size >= 4) { MSG_InitReadOnly(&msg, plain, (int)size); SV_PacketEvent(from, &msg); }
        } else {
            /* Said once per association even without developer: a client whose
             * records no roster key opens sits on "awaiting connection" until
             * EXE_ERR_SERVER_TIMEOUT and is otherwise invisible in the log. */
            if(!p->handshake.data.received && ++p->rejected == 10)
                Com_Printf(CON_CHANNEL_NETWORK, "CoDOL: %s: no admission key opens its records (%s); "
                    "its client dials with a key the lobby roster does not hold\n",
                    NET_AdrToString(from), reason ? reason : "?");
            if(trace)
                Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: DATA from %s rejected: %s (%d bytes, tag=%u expected=%u, counter=%u%s)\n", NET_AdrToString(from), reason, n,
                    (unsigned)packet[2] | (unsigned)packet[3] << 8,
                    p->handshake.data.local_tag,
                    (unsigned)packet[4] | (unsigned)packet[5] << 8,
                    have_key ? "" : ", no session key");
        }
    } else if(trace) {
        Com_DPrintf(CON_CHANNEL_NETWORK, "bdDTLS: %s sent type %u/%u (%d bytes) %s; dropped\n", NET_AdrToString(from), packet[0], packet[1], n,
            packet[0] == 6 ? "before its association was established" : "which is neither a handshake nor a DATA record");
    }
done:
    erase(security, sizeof(security)); erase(private_key, sizeof(private_key));
    erase(keys, sizeof(keys));
    return 1;
}
#endif
