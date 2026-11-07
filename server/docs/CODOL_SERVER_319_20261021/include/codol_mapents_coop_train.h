#ifndef CODOL_MAPENTS_COOP_TRAIN_H
#define CODOL_MAPENTS_COOP_TRAIN_H
/* 由 tools/gen_mapents_inc.py 从 _map_extract/coop_train_entities.txt 生成。
 * 字段: kind(0=跳过 1=静态道具 2=actor) | origin x,y,z | yaw | classname | model | targetname */
#define CODOL_MAPENTS_COOP_TRAIN_COUNT 334
typedef struct {
    int         kind;
    float       x, y, z;
    float       yaw;
    const char *classname;
    const char *model;
    const char *targetname;
} codol_mapent_t;
extern const codol_mapent_t codol_mapents_coop_train[];
#endif /* CODOL_MAPENTS_COOP_TRAIN_H */
