#ifndef CODOL_SESSION_H
#define CODOL_SESSION_H

#include "codol_types.h"

#define CODOL_SESSION_FREE         0
#define CODOL_SESSION_COOKIE       1
#define CODOL_SESSION_HANDSHAKE    2
#define CODOL_SESSION_CONNECTED    3
#define CODOL_SESSION_PRIMING      4
#define CODOL_SESSION_ACTIVE       5
#define CODOL_SESSION_DISCONNECTED 6
#define CODOL_SESSION_ZOMBIE       7

#define CODOL_CLOSE_NORMAL          0
#define CODOL_CLOSE_TIMEOUT         1
#define CODOL_CLOSE_KICKED          2
#define CODOL_CLOSE_PROTOCOL_ERROR  3
#define CODOL_CLOSE_AUTH_FAILED     4
#define CODOL_CLOSE_SERVER_SHUTDOWN 5

codol_result_t codol_session_table_init(codol_server_t *server);
codol_session_t *codol_session_find_by_adr(codol_server_t *server, const codol_netadr_t *adr);
codol_session_t *codol_session_alloc(codol_server_t *server, const codol_netadr_t *adr);
codol_result_t codol_session_receive(codol_server_t *server, codol_session_t *session,
                                      const uint8_t *data, size_t len);
codol_result_t codol_session_transition(codol_server_t *server, codol_session_t *session,
                                         int new_state);
void           codol_session_close(codol_session_t *session, int reason);
void           codol_session_check_timeouts(codol_server_t *server, uint64_t now_us);

const char    *codol_session_state_name(int state);
bool           codol_session_is_active(const codol_session_t *session);

#endif /* CODOL_SESSION_H */
