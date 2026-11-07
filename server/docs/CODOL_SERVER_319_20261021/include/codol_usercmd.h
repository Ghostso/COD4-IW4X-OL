#ifndef CODOL_USERCMD_H
#define CODOL_USERCMD_H
#include "codol_types.h"

#define CODOL_MAX_USERCMDS 32

#define CODOL_MAX_RELIABLE_TEXT 8
#define CODOL_RELIABLE_TEXT_LEN 128

typedef struct {
    codol_usercmd_t cmds[CODOL_MAX_USERCMDS];
    int             count;
    /* ★ 可靠命令段(opcode==2)。CODOL 客户端把背包/武器选择放在这里
     *   (如 "mr 1 1 custom2")，之前解析后直接丢弃 -> 服务端永远不知道玩家选了哪个背包。 */
    char            reliable[CODOL_MAX_RELIABLE_TEXT][CODOL_RELIABLE_TEXT_LEN];
    int             reliable_count;
} codol_usercmd_list_t;

#ifdef __cplusplus
extern "C" {
#endif

bool codol_usercmd_parse(const uint8_t *data, int len, uint32_t key,
                         const codol_usercmd_t *baseline,
                         codol_usercmd_list_t *out);

#ifdef __cplusplus
}
#endif
#endif
