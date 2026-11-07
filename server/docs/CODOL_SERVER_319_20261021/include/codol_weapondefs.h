#ifndef CODOL_WEAPONDEFS_H
#define CODOL_WEAPONDEFS_H
#include <stdbool.h>

#define CODOL_WEAPON_DAMAGE_TIERS 6
#define CODOL_HITLOC_COUNT 20

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
    float location_damage_multipliers[CODOL_HITLOC_COUNT];
    int damage_tiers[CODOL_WEAPON_DAMAGE_TIERS];
    float damage_ranges[CODOL_WEAPON_DAMAGE_TIERS];
} codol_weapondef_t;

/* 3.19 StringTable `hitloc_mapping`, entries 0..18. */
enum {
    CODOL_HITLOC_NONE = 0,
    CODOL_HITLOC_HELMET = 1,
    CODOL_HITLOC_HEAD = 2,
    CODOL_HITLOC_NECK = 3,
    CODOL_HITLOC_TORSO_UPPER = 4,
    CODOL_HITLOC_TORSO_LOWER = 5,
    CODOL_HITLOC_RIGHT_ARM_UPPER = 6,
    CODOL_HITLOC_LEFT_ARM_UPPER = 7,
    CODOL_HITLOC_RIGHT_ARM_LOWER = 8,
    CODOL_HITLOC_LEFT_ARM_LOWER = 9,
    CODOL_HITLOC_RIGHT_HAND = 10,
    CODOL_HITLOC_LEFT_HAND = 11,
    CODOL_HITLOC_RIGHT_LEG_UPPER = 12,
    CODOL_HITLOC_LEFT_LEG_UPPER = 13,
    CODOL_HITLOC_RIGHT_LEG_LOWER = 14,
    CODOL_HITLOC_LEFT_LEG_LOWER = 15,
    CODOL_HITLOC_RIGHT_FOOT = 16,
    CODOL_HITLOC_LEFT_FOOT = 17,
    CODOL_HITLOC_GUN = 18,
    CODOL_HITLOC_SHIELD = 19
};

extern const codol_weapondef_t codol_weapondefs_firingrange[];
extern const int codol_weapondefs_firingrange_count;
const codol_weapondef_t *codol_weapondef_find(const char *name);
int codol_weapondef_damage_at_distance(const codol_weapondef_t *def, float distance, bool player_damage);
int codol_weapondef_damage_for_hit(const codol_weapondef_t *def, float distance, bool player_damage, int hitloc);
#endif
