#include "codol_transport.h"
#include "codol_platform.h"
#include "codol_session.h"
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET codol_socket_t;
#define CODOL_INVALID_SOCKET INVALID_SOCKET
#define CODOL_SOCKET_ERROR SOCKET_ERROR
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
typedef int codol_socket_t;
#define CODOL_INVALID_SOCKET (-1)
#define CODOL_SOCKET_ERROR (-1)
#endif

typedef struct {
    codol_socket_t sock;
    uint16_t       port;
    bool           initialized;
} codol_transport_ctx_t;

static codol_transport_ctx_t s_transport;
static codol_packet_sink_fn s_sink_fn = NULL;
static void *s_sink_ctx = NULL;

void codol_transport_set_packet_sink(codol_server_t *server,
                                     codol_packet_sink_fn fn, void *ctx)
{
    (void)server;
    s_sink_fn = fn;
    s_sink_ctx = ctx;
}

codol_result_t codol_transport_init(codol_server_t *server)
{
    if (!server) return CODOL_ERR_INVALID_ARG;

    memset(&s_transport, 0, sizeof(s_transport));
    s_transport.sock = CODOL_INVALID_SOCKET;
    s_transport.port = server->config.battle_port;

#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        CODOL_LOG_ERROR("WSAStartup failed");
        return CODOL_ERR_IO;
    }
#endif

    s_transport.sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s_transport.sock == CODOL_INVALID_SOCKET) {
        CODOL_LOG_ERROR("socket() failed");
        return CODOL_ERR_IO;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    if (server->config.bind_address[0]) {
#ifdef _WIN32
        if (InetPtonA(AF_INET, server->config.bind_address, &addr.sin_addr) != 1)
            addr.sin_addr.s_addr = INADDR_ANY;
#else
        if (inet_pton(AF_INET, server->config.bind_address, &addr.sin_addr) != 1)
            addr.sin_addr.s_addr = INADDR_ANY;
#endif
    } else {
        addr.sin_addr.s_addr = INADDR_ANY;
    }
    addr.sin_port = htons(s_transport.port);

    if (bind(s_transport.sock, (struct sockaddr *)&addr, sizeof(addr)) == CODOL_SOCKET_ERROR) {
        CODOL_LOG_ERROR("bind() failed on port %u", s_transport.port);
        return CODOL_ERR_IO;
    }

#ifdef _WIN32
    u_long nonblock = 1;
    ioctlsocket(s_transport.sock, FIONBIO, &nonblock);
#else
    int flags = fcntl(s_transport.sock, F_GETFL, 0);
    fcntl(s_transport.sock, F_SETFL, flags | O_NONBLOCK);
#endif

    s_transport.initialized = true;
    CODOL_LOG_INFO("transport initialized on UDP port %u", s_transport.port);
    return CODOL_OK;
}

void codol_transport_shutdown(codol_server_t *server)
{
    (void)server;
    if (s_transport.sock != CODOL_INVALID_SOCKET) {
#ifdef _WIN32
        closesocket(s_transport.sock);
        WSACleanup();
#else
        close(s_transport.sock);
#endif
        s_transport.sock = CODOL_INVALID_SOCKET;
    }
    s_transport.initialized = false;
}

codol_result_t codol_transport_send(codol_server_t *server, const codol_netadr_t *to,
                                     const uint8_t *data, size_t len)
{
    (void)server;
    if (!to || !data || len == 0 || !s_transport.initialized) return CODOL_ERR_INVALID_ARG;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    memcpy(&addr.sin_addr.s_addr, to->ip, 4);
    addr.sin_port = htons(to->port);

    int sent = sendto(s_transport.sock, (const char *)data, (int)len, 0,
                      (struct sockaddr *)&addr, sizeof(addr));
    if (sent == CODOL_SOCKET_ERROR) {
        return CODOL_ERR_IO;
    }
    return CODOL_OK;
}

codol_result_t codol_transport_recv(codol_server_t *server, codol_packet_t *packet)
{
    (void)server;
    if (!packet || !s_transport.initialized) return CODOL_ERR_INVALID_ARG;

    struct sockaddr_in from;
    socklen_t from_len = sizeof(from);
    int received = recvfrom(s_transport.sock, (char *)packet->data, (int)packet->len, 0,
                             (struct sockaddr *)&from, &from_len);
    if (received == CODOL_SOCKET_ERROR) {
#ifdef _WIN32
        int err = WSAGetLastError();
        if (err == WSAEWOULDBLOCK) return CODOL_ERR_IO;
#else
        if (errno == EAGAIN || errno == EWOULDBLOCK) return CODOL_ERR_IO;
#endif
        return CODOL_ERR_IO;
    }
    if (received <= 0) return CODOL_ERR_IO;

    packet->len = (size_t)received;
    packet->remote.type = CODOL_ADR_IPV4;
    memcpy(packet->remote.ip, &from.sin_addr.s_addr, 4);
    packet->remote.port = ntohs(from.sin_port);
    packet->recv_time_us = codol_platform_time_us();
    return CODOL_OK;
}

codol_result_t codol_transport_poll(codol_server_t *server, uint32_t budget_ms)
{
    if (!server) return CODOL_ERR_INVALID_ARG;
    (void)budget_ms;

    uint8_t buf[CODOL_MAX_PACKET_SIZE];
    codol_packet_t packet;
    packet.data = buf;
    packet.len = sizeof(buf);

    while (codol_transport_recv(server, &packet) == CODOL_OK) {
        if (s_sink_fn) {
            s_sink_fn(s_sink_ctx, &packet.remote, packet.data, packet.len);
            packet.len = sizeof(buf);
            continue;
        }
        codol_session_t *session = codol_session_find_by_adr(server, &packet.remote);
        if (!session) {
            session = codol_session_alloc(server, &packet.remote);
        }
        if (session) {
            codol_session_receive(server, session, packet.data, packet.len);
        }
        packet.len = sizeof(buf);
    }
    return CODOL_OK;
}

bool codol_netadr_equal(const codol_netadr_t *a, const codol_netadr_t *b)
{
    if (!a || !b) return false;
    if (a->type != b->type || a->port != b->port) return false;
    int len = (a->type == CODOL_ADR_IPV4) ? 4 : 16;
    return memcmp(a->ip, b->ip, len) == 0;
}

void codol_netadr_to_string(const codol_netadr_t *adr, char *buf, size_t buf_len)
{
    if (!adr || !buf || buf_len == 0) return;
    if (adr->type == CODOL_ADR_IPV4) {
        snprintf(buf, buf_len, "%u.%u.%u.%u:%u",
                 adr->ip[0], adr->ip[1], adr->ip[2], adr->ip[3], adr->port);
    } else {
        snprintf(buf, buf_len, "[ipv6]:%u", adr->port);
    }
}
