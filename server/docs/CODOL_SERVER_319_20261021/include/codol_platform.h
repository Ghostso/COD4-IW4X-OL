#ifndef CODOL_PLATFORM_H
#define CODOL_PLATFORM_H

#include "codol_types.h"

codol_result_t codol_platform_init(codol_server_t *server, const codol_config_t *config);
void           codol_platform_shutdown(codol_server_t *server);
uint64_t       codol_platform_time_ms(void);
uint64_t       codol_platform_time_us(void);
codol_result_t codol_platform_ensure_single_instance(const char *run_dir);
void           codol_platform_release_instance(const char *run_dir);

typedef void (*codol_log_fn)(int level, const char *fmt, ...);
void codol_platform_set_log_fn(codol_log_fn fn);

#define CODOL_LOG_INFO(...)  codol_platform_log(0, __VA_ARGS__)
#define CODOL_LOG_WARN(...)  codol_platform_log(1, __VA_ARGS__)
#define CODOL_LOG_ERROR(...) codol_platform_log(2, __VA_ARGS__)

void codol_platform_log(int level, const char *fmt, ...);

#endif /* CODOL_PLATFORM_H */
