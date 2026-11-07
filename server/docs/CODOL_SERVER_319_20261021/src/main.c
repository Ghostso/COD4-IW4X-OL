#include "codol_types.h"
#include "codol_platform.h"
#include "codol_session.h"
#include "codol_world.h"
#include "codol_transport.h"
#include "codol_evidence_gate.h"
#include "codol_battle_service.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

static volatile int g_running = 1;

/* ---- 战斗服接线: UDP 包 -> battle 服务 ---- */
static codol_battle_service_t g_battle;

static int battle_sendto(void *ctx, const codol_netadr_t *to,
                         const uint8_t *data, int len)
{
    codol_server_t *srv = (codol_server_t *)ctx;
    return (codol_transport_send(srv, to, data, (size_t)len) == CODOL_OK) ? len : -1;
}

static void battle_sink(void *ctx, const codol_netadr_t *from,
                        const uint8_t *data, size_t len)
{
    (void)ctx;
    codol_battle_service_on_packet(&g_battle, from, data, (int)len);
}

static void signal_handler(int sig)
{
    (void)sig;
    g_running = 0;
}

static void print_usage(const char *prog)
{
    printf("CODOL 3.19 Battle Server (Stage 0 Skeleton)\n");
    printf("Usage: %s [options]\n", prog);
    printf("  --map <name>       Map to load (default: mp_firingrange)\n");
    printf("  --port <port>      Battle UDP port (default: 28960)\n");
    printf("  --bind <addr>      Battle UDP bind address (default: 0.0.0.0)\n");
    printf("  --tick <hz>        Server tick rate (default: 20)\n");
    printf("  --release          Enable release mode (evidence gate strict)\n");
    printf("  --help             Show this help\n");
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    codol_config_t config;
    memset(&config, 0, sizeof(config));
    config.battle_port = 28960;
    config.control_port = 3074;
    config.tick_rate_hz = CODOL_SERVER_TICK_HZ;
    config.snapshot_rate_hz = CODOL_SNAPSHOT_RATE_HZ;
    config.max_clients = CODOL_MAX_CLIENTS;
    config.release_mode = false;
    snprintf(config.bind_address, sizeof(config.bind_address), "0.0.0.0");

    const char *map_name = "mp_firingrange";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--map") == 0 && i + 1 < argc) {
            map_name = argv[++i];
        } else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            config.battle_port = (uint16_t)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--bind") == 0 && i + 1 < argc) {
            snprintf(config.bind_address, sizeof(config.bind_address), "%s", argv[++i]);
        } else if (strcmp(argv[i], "--tick") == 0 && i + 1 < argc) {
            config.tick_rate_hz = (uint32_t)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--release") == 0) {
            config.release_mode = true;
        } else if (strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        }
    }

    printf("=== CODOL 3.19 Battle Server (Stage 0) ===\n");
    printf("Target version: %s (build %s)\n", CODOL_TARGET_VERSION, CODOL_TARGET_BUILD);
    printf("Map: %s | Port: %u | Tick: %u Hz | Release: %s\n",
           map_name, config.battle_port, config.tick_rate_hz,
           config.release_mode ? "yes" : "no");

    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    codol_server_t *server = (codol_server_t *)calloc(1, sizeof(codol_server_t));
    if (!server) {
        fprintf(stderr, "Failed to allocate server\n");
        return 1;
    }

    if (codol_platform_init(server, &config) != CODOL_OK) {
        fprintf(stderr, "Failed to initialize platform\n");
        free(server);
        return 1;
    }

    if (codol_transport_init(server) != CODOL_OK) {
        fprintf(stderr, "Failed to initialize transport\n");
        free(server);
        return 1;
    }

    /* 战斗服: 接管 UDP 包(NAT / 握手 / 数据帧 / OOB) */
    codol_battle_service_init(&g_battle, server, battle_sendto);
    codol_transport_set_packet_sink(server, battle_sink, server);

    if (codol_session_table_init(server) != CODOL_OK) {
        fprintf(stderr, "Failed to initialize session table\n");
        free(server);
        return 1;
    }

    if (codol_world_init(&server->world, map_name) != CODOL_OK) {
        fprintf(stderr, "Failed to initialize world\n");
        free(server);
        return 1;
    }

    if (codol_world_load_assets(&server->world) != CODOL_OK) {
        fprintf(stderr, "Failed to load world assets\n");
        free(server);
        return 1;
    }

    /* ★★ 把 world 绑进战斗服(2026-10-25)。
     *   此前 **从未调用过** bind_world -> svc->world 恒为 NULL -> 实体层整条是死的:
     *     世界被创建、被加载、每 tick 被 step, 但**没有任何东西被生成进去**,
     *     战斗服也从不使用它。后果:
     *       · ensure_damage_target() 第一句 `if (!svc->world) return -1;` 直接返回
     *       · apply_test_hit() 同样第一句就 return  => HIT/DAMAGE 永远为 0
     *       · 世界里的玩家也没生成(codol_world_spawn_player 只被 bind_world 调用)
     *   绑上之后 svc->world 非空, 并在世界里生成玩家实体(client 0);
     *   Phase 7 那套真实 clipmap 碰撞也从这一刻起才真正被战斗服使用。
     *   注: 这一步只改服务端内部, 不改任何上行字节(快照仍按 omit 策略发送)。 */
    codol_battle_service_bind_world(&g_battle, &server->world, 0);

    /* ★★ 按地图实体表生成世界里的实体(2026-10-25)。
     *   上一步只生成了玩家; 这一步把地图上**实际存在**的东西摆出来:
     *   333 个静态道具(靶场的轮胎墙 mp_firingrange_tire_wall 之类)
     *   + 1 个 actor_ally_hero_quartermaster_so(这张图唯一的 actor)。
     *   表由 tools/gen_mapents_inc.py 从 _map_extract/coop_train_entities.txt 生成,
     *   是只读的地图数据, 不是手工编的常量。 */
    codol_world_spawn_map_entities(&server->world);

    printf("Server initialized. Entering main loop (Ctrl+C to stop)...\n");

    uint64_t tick_interval_us = 1000000ULL / config.tick_rate_hz;
    uint64_t last_tick = codol_platform_time_us();

    while (g_running) {
        uint64_t now = codol_platform_time_us();

        codol_transport_poll(server, 0);

        if (now - last_tick >= tick_interval_us) {
            codol_frame_t frame;
            codol_world_step(&server->world, NULL, 0, &frame);
            codol_session_check_timeouts(server, now);
            codol_battle_service_tick(&g_battle, now / 1000);
            last_tick = now;
        }

#ifdef _WIN32
        Sleep(1);
#else
        usleep(1000);
#endif
    }

    printf("\nShutting down...\n");
    codol_platform_shutdown(server);
    free(server);
    printf("Server stopped cleanly.\n");
    return 0;
}
