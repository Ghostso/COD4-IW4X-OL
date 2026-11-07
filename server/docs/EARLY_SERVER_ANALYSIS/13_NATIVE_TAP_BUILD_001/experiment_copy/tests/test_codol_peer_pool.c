/* Exercise the real native peer-slot selection without starting the server.
 * Unreferenced transport functions are discarded by section GC.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_network.c"
#include <assert.h>
#include <stdio.h>

static netadr_t address(unsigned port)
{
    netadr_t a = {0};
    a.type = NA_IP;
    a.ip[0] = 203; a.ip[1] = 0; a.ip[2] = 113; a.ip[3] = 7;
    a.port = (unsigned short)port;
    return a;
}

int main(void)
{
    netadr_t a = address(1), other = address(100);
    peer_t *p;
    unsigned i;

    p = find(&a, 1000, 1);
    assert(p == &peers[0]);
    p->used = 1; p->address = a; p->handshake.established = 1; p->touched = 1000;
    /* The client can return from the lobby without another INIT. Its DATA
     * must still find this association after two minutes of silence. */
    assert(find(&a, 122001, 0) == p);
    assert(find(&other, 122001, 1) == &peers[1]);

    memset(peers, 0, sizeof(peers));
    for (i = 0; i < PEERS; ++i) {
        peers[i].used = 1;
        peers[i].address = address(i + 1);
        peers[i].handshake.established = 1;
        peers[i].touched = 1000 + i;
    }
    peers[1].touched = 250000; /* A currently active match stays allocated. */
    other = address(100);
    assert(find(&other, 250000, 0) == NULL);
    assert(find(&other, 250000, 1) == &peers[0]);
    /* Selection alone must not evict a peer before INIT validation. */
    assert(peers[0].used && peers[0].address.port == 1);
    assert(find(&peers[1].address, 250000, 0) == &peers[1]);

    for (i = 0; i < PEERS; ++i) peers[i].touched = 250000;
    assert(find(&other, 250001, 1) == NULL);

    memset(peers, 0, sizeof(peers));
    p = &peers[0]; p->used = 1; p->address = a; p->touched = 1000;
    assert(find(&other, 12001, 1) == p);
    assert(!p->used); /* Pending handshakes still expire after ten seconds. */
    puts("CoDOL idle association retention and peer-slot selection passed");
    return 0;
}
