#include "codol_session.h"
#include "codol_platform.h"
#include "codol_transport.h"
#include "codol_world.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

int main(void)
{
    printf("=== test_session ===\n");

    codol_config_t config;
    memset(&config, 0, sizeof(config));
    config.battle_port = 28960;
    config.tick_rate_hz = 20;
    config.release_mode = false;

    codol_server_t *server = (codol_server_t *)calloc(1, sizeof(codol_server_t));
    assert(server != NULL);

    codol_result_t result = codol_platform_init(server, &config);
    assert(result == CODOL_OK);

    result = codol_session_table_init(server);
    assert(result == CODOL_OK);

    codol_netadr_t adr;
    memset(&adr, 0, sizeof(adr));
    adr.type = CODOL_ADR_IPV4;
    adr.ip[0] = 127; adr.ip[1] = 0; adr.ip[2] = 0; adr.ip[3] = 1;
    adr.port = 12345;

    codol_session_t *s = codol_session_alloc(server, &adr);
    assert(s != NULL);
    assert(s->state == CODOL_SESSION_COOKIE);
    assert(s->slot == 0);
    assert(server->num_sessions == 1);

    codol_session_t *found = codol_session_find_by_adr(server, &adr);
    assert(found == s);

    result = codol_session_transition(server, s, CODOL_SESSION_HANDSHAKE);
    assert(result == CODOL_OK);
    assert(s->state == CODOL_SESSION_HANDSHAKE);

    result = codol_session_transition(server, s, CODOL_SESSION_ACTIVE);
    assert(result != CODOL_OK);
    assert(s->state == CODOL_SESSION_HANDSHAKE);

    result = codol_session_transition(server, s, CODOL_SESSION_CONNECTED);
    assert(result == CODOL_OK);

    result = codol_session_transition(server, s, CODOL_SESSION_PRIMING);
    assert(result == CODOL_OK);

    result = codol_session_transition(server, s, CODOL_SESSION_ACTIVE);
    assert(result == CODOL_OK);
    assert(codol_session_is_active(s));

    codol_session_close(s, CODOL_CLOSE_NORMAL);
    assert(s->state == CODOL_SESSION_FREE);

    found = codol_session_find_by_adr(server, &adr);
    assert(found == NULL);

    free(server);
    printf("All session tests PASSED.\n");
    return 0;
}
