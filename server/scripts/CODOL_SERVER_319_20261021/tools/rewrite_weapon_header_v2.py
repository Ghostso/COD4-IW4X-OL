from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weapondefs.h')
s='''#ifndef CODOL_WEAPONDEFS_H
#define CODOL_WEAPONDEFS_H
#include <stdbool.h>

/* Values below are from the 3.19 firingrange raw assets.  The final loaded
 * WeaponDef layout is carried separately in common_mp_weapondefs_*.json. */
typedef struct {
    const char *name;
    int clip_size;
    int fire_time_ms;
    int reload_ms;
    int reload_empty_ms;
    int reload_add_ms;
    int damage;
    int player_damage;
    int min_damage;
    int min_player_damage;
    float max_damage_range;
    float min_damage_range;
    float move_speed_scale;
    float ads_move_speed_scale;
    float sprint_duration_scale;
    float location_damage_multipliers[20];
} codol_weapondef_t;

enum {
    CODOL_HITLOC_NONE = 0,
    CODOL_HITLOC_HELMET = 1,
    CODOL_HITLOC_HEAD = 2,
    CODOL_HITLOC_NECK = 3,
    CODOL_HITLOC_TORSO_UPPER = 4,
    CODOL_HITLOC_TORSO_LOWER = 5,
    CODOL_HITLOC_GUN = 18,
    CODOL_HITLOC_SHIELD = 19
};

extern const codol_weapondef_t codol_weapondefs_firingrange[];
extern const int codol_weapondefs_firingrange_count;
const codol_weapondef_t *codol_weapondef_find(const char *name);
int codol_weapondef_damage_at_distance(const codol_weapondef_t *def, float distance, bool player_damage);
int codol_weapondef_damage_for_hit(const codol_weapondef_t *def, float distance, bool player_damage, int hitloc);
#endif
'''
p.write_text(s,encoding='utf-8')
print('ok')
