#ifndef CODOL_TRANSPORT_H
#define CODOL_TRANSPORT_H

#include "codol_types.h"

#define CODOL_ADR_LOOPBACK 0
#define CODOL_ADR_IPV4     1
#define CODOL_ADR_IPV6     2

codol_result_t codol_transport_init(codol_server_t *server);
void           codol_transport_shutdown(codol_server_t *server);
codol_result_t codol_transport_poll(codol_server_t *server, uint32_t budget_ms);
codol_result_t codol_transport_send(codol_server_t *server, const codol_netadr_t *to,
                                     const uint8_t *data, size_t len);
codol_result_t codol_transport_recv(codol_server_t *server, codol_packet_t *packet);

/* 收到 UDP 包时的回调(设了就由它接管, 不再走 session 默认处理) */
typedef void (*codol_packet_sink_fn)(void *ctx, const codol_netadr_t *from,
                                     const uint8_t *data, size_t len);
void codol_transport_set_packet_sink(codol_server_t *server,
                                     codol_packet_sink_fn fn, void *ctx);

bool codol_netadr_equal(const codol_netadr_t *a, const codol_netadr_t *b);
void codol_netadr_to_string(const codol_netadr_t *adr, char *buf, size_t buf_len);

#endif /* CODOL_TRANSPORT_H */
