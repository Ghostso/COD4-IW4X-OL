#include "codol_pure.h"
#include <stddef.h>
#include <string.h>

static int number(const char **cursor, uint32_t *out)
{
    const char *p = *cursor;
    uint32_t value = 0, limit = 2147483647u;
    int negative = *p == '-';
    if (negative) { ++p; ++limit; }
    if (*p < '0' || *p > '9') return 0;
    do {
        unsigned digit = (unsigned)(*p++ - '0');
        if (value > (limit - digit) / 10u) return 0;
        value = value * 10u + digit;
    } while (*p >= '0' && *p <= '9');
    *cursor = p;
    *out = negative ? 0u - value : value;
    return 1;
}

int CODOL_VerifyPureChecksums(int argc, const char *const *argv,
                             const char *loaded_checksums, uint32_t feed)
{
    uint32_t client[CODOL_MAX_PURE_IWDS], server[CODOL_MAX_PURE_IWDS];
    uint32_t aggregate, claimed;
    int count, servers = 0, i, j;
    const char *p;
    if (!argv || !loaded_checksums || argc < 3 || argc > CODOL_MAX_PURE_IWDS + 3)
        return 0;
    for (i = 0; i < argc; ++i) if (!argv[i]) return 0;
    if (strcmp(argv[0], "cp") || strcmp(argv[1], "@")) return 0;
    count = argc - 3;
    aggregate = feed ^ (uint32_t)count;
    for (i = 0; i < count; ++i) {
        p = argv[i + 2];
        if (!number(&p, &client[i]) || *p) return 0;
        for (j = 0; j < i; ++j) if (client[i] == client[j]) return 0;
        aggregate ^= client[i];
    }
    p = argv[argc - 1];
    if (!number(&p, &claimed) || *p || claimed != aggregate) return 0;
    p = loaded_checksums;
    while (*p) {
        while (*p == ' ') ++p;
        if (!*p) break;
        if (servers == CODOL_MAX_PURE_IWDS || !number(&p, &server[servers++])) return 0;
        if (*p && *p != ' ') return 0;
    }
    for (i = 0; i < count; ++i) {
        for (j = 0; j < servers && client[i] != server[j]; ++j) {}
        if (j == servers) return 0;
    }
    return 1;
}

int CODOL_PureCommandFeed(int argc, const char *const *argv, uint32_t *feed)
{
    uint32_t value, claimed, x = 0;
    int count, i;
    const char *p;
    if (!argv || !feed || argc < 3 || argc > CODOL_MAX_PURE_IWDS + 3) return 0;
    for (i = 0; i < argc; ++i) if (!argv[i]) return 0;
    if (strcmp(argv[0], "cp") || strcmp(argv[1], "@")) return 0;
    count = argc - 3;
    for (i = 0; i < count; ++i) {
        p = argv[i + 2];
        if (!number(&p, &value) || *p) return 0;
        x ^= value;
    }
    p = argv[argc - 1];
    if (!number(&p, &claimed) || *p) return 0;
    *feed = claimed ^ (uint32_t)count ^ x;
    return 1;
}
