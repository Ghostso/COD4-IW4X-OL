#include "codol_session.h"
#include "codol_platform.h"
#include "codol_wire_codec.h"
#include "codol_evidence_gate.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

codol_result_t codol_session_table_init(codol_server_t *server)
{
    if (!server) return CODOL_ERR_INVALID_ARG;
    for (int i = 0; i < CODOL_MAX_CLIENTS; i++) {
        server->sessions[i].slot = i;
        server->sessions[i].state = CODOL_SESSION_FREE;
        server->sessions[i].challenge = 0;
        server->sessions[i].session_token = 0;
        server->sessions[i].recv_buf = NULL;
        server->sessions[i].recv_buf_cap = 0;
        server->sessions[i].recv_buf_len = 0;
    }
    server->num_sessions = 0;
    return CODOL_OK;
}

codol_session_t *codol_session_find_by_adr(codol_server_t *server, const codol_netadr_t *adr)
{
    if (!server || !adr) return NULL;
    for (int i = 0; i < CODOL_MAX_CLIENTS; i++) {
        codol_session_t *s = &server->sessions[i];
        if (s->state != CODOL_SESSION_FREE && codol_netadr_equal(&s->remote, adr)) {
            return s;
        }
    }
    return NULL;
}

codol_session_t *codol_session_alloc(codol_server_t *server, const codol_netadr_t *adr)
{
    if (!server || !adr) return NULL;
    for (int i = 0; i < CODOL_MAX_CLIENTS; i++) {
        codol_session_t *s = &server->sessions[i];
        if (s->state == CODOL_SESSION_FREE) {
            memset(s, 0, sizeof(*s));
            s->slot = i;
            s->state = CODOL_SESSION_COOKIE;
            memcpy(&s->remote, adr, sizeof(*adr));
            s->challenge = (uint32_t)(codol_platform_time_us() & 0xFFFFFFFF);
            s->connect_time_us = codol_platform_time_us();
            s->last_packet_time_us = s->connect_time_us;
            server->num_sessions++;
            CODOL_LOG_INFO("session %d allocated for client", i);
            return s;
        }
    }
    CODOL_LOG_WARN("no free session slots");
    return NULL;
}

codol_result_t codol_session_transition(codol_server_t *server, codol_session_t *session,
                                         int new_state)
{
    if (!server || !session) return CODOL_ERR_INVALID_ARG;

    int old = session->state;

    if (old == CODOL_SESSION_FREE && new_state != CODOL_SESSION_COOKIE) {
        return CODOL_ERR_STATE;
    }
    if (old == CODOL_SESSION_COOKIE && new_state != CODOL_SESSION_HANDSHAKE) {
        return CODOL_ERR_STATE;
    }
    if (old == CODOL_SESSION_HANDSHAKE &&
        new_state != CODOL_SESSION_CONNECTED && new_state != CODOL_SESSION_DISCONNECTED) {
        return CODOL_ERR_STATE;
    }
    if (old == CODOL_SESSION_CONNECTED && new_state != CODOL_SESSION_PRIMING) {
        return CODOL_ERR_STATE;
    }
    if (old == CODOL_SESSION_PRIMING &&
        new_state != CODOL_SESSION_ACTIVE && new_state != CODOL_SESSION_DISCONNECTED) {
        return CODOL_ERR_STATE;
    }

    session->state = new_state;
    CODOL_LOG_INFO("session %d: %s -> %s", session->slot,
                   codol_session_state_name(old), codol_session_state_name(new_state));
    return CODOL_OK;
}

codol_result_t codol_session_receive(codol_server_t *server, codol_session_t *session,
                                      const uint8_t *data, size_t len)
{
    if (!server || !session || !data || len == 0) return CODOL_ERR_INVALID_ARG;

    session->last_packet_time_us = codol_platform_time_us();

    if (session->state == CODOL_SESSION_COOKIE) {
        return CODOL_OK;
    }

    codol_message_t message;
    codol_result_t result = codol_wire_decode(session, data, len, &message);
    if (result != CODOL_OK) {
        CODOL_LOG_WARN("session %d: wire decode failed (%d)", session->slot, result);
        return result;
    }

    return CODOL_OK;
}

void codol_session_close(codol_session_t *session, int reason)
{
    if (!session) return;
    CODOL_LOG_INFO("session %d closed, reason=%d", session->slot, reason);
    if (session->recv_buf) {
        free(session->recv_buf);
        session->recv_buf = NULL;
    }
    session->state = CODOL_SESSION_FREE;
}

void codol_session_check_timeouts(codol_server_t *server, uint64_t now_us)
{
    if (!server) return;
    uint64_t timeout_us = 30000000;
    for (int i = 0; i < CODOL_MAX_CLIENTS; i++) {
        codol_session_t *s = &server->sessions[i];
        if (s->state == CODOL_SESSION_FREE) continue;
        if (now_us - s->last_packet_time_us > timeout_us) {
            codol_session_close(s, CODOL_CLOSE_TIMEOUT);
            server->num_sessions--;
        }
    }
}

const char *codol_session_state_name(int state)
{
    switch (state) {
        case CODOL_SESSION_FREE:         return "FREE";
        case CODOL_SESSION_COOKIE:       return "COOKIE";
        case CODOL_SESSION_HANDSHAKE:    return "HANDSHAKE";
        case CODOL_SESSION_CONNECTED:    return "CONNECTED";
        case CODOL_SESSION_PRIMING:      return "PRIMING";
        case CODOL_SESSION_ACTIVE:       return "ACTIVE";
        case CODOL_SESSION_DISCONNECTED: return "DISCONNECTED";
        case CODOL_SESSION_ZOMBIE:       return "ZOMBIE";
        default:                         return "UNKNOWN";
    }
}

bool codol_session_is_active(const codol_session_t *session)
{
    return session && session->state == CODOL_SESSION_ACTIVE;
}
