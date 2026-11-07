#include "codol_types.h"
#include "codol_platform.h"
#include "codol_world.h"
#include "codol_evidence_gate.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/time.h>
#include <unistd.h>
#endif

static codol_log_fn s_log_fn = NULL;

void codol_platform_set_log_fn(codol_log_fn fn) { s_log_fn = fn; }

void codol_platform_log(int level, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    if (s_log_fn) {
        char buf[1024];
        vsnprintf(buf, sizeof(buf), fmt, ap);
        s_log_fn(level, "%s", buf);
    } else {
        vfprintf(level == 2 ? stderr : stdout, fmt, ap);
        fputc('\n', level == 2 ? stderr : stdout);
    }
    va_end(ap);
}

uint64_t codol_platform_time_ms(void)
{
#ifdef _WIN32
    return GetTickCount64();
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000 + (uint64_t)tv.tv_usec / 1000;
#endif
}

uint64_t codol_platform_time_us(void)
{
#ifdef _WIN32
    LARGE_INTEGER freq, count;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&count);
    return (uint64_t)(count.QuadPart * 1000000ULL / (uint64_t)freq.QuadPart);
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000 + (uint64_t)tv.tv_usec;
#endif
}

codol_result_t codol_platform_ensure_single_instance(const char *run_dir)
{
    if (!run_dir) return CODOL_ERR_INVALID_ARG;
    return CODOL_OK;
}

void codol_platform_release_instance(const char *run_dir)
{
    (void)run_dir;
}

codol_result_t codol_platform_init(codol_server_t *server, const codol_config_t *config)
{
    if (!server || !config) return CODOL_ERR_INVALID_ARG;
    memset(server, 0, sizeof(*server));
    memcpy(&server->config, config, sizeof(*config));
    server->running = false;
    server->tick_count = 0;
    codol_evidence_registry_init(&server->evidence_registry, config->release_mode);
    return CODOL_OK;
}

void codol_platform_shutdown(codol_server_t *server)
{
    if (!server) return;
    server->running = false;
    codol_world_shutdown(&server->world);
}
