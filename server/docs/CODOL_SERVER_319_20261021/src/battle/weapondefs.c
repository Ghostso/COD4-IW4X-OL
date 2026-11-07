#include "codol_weapondefs.h"
#include <math.h>
#include <string.h>

const codol_weapondef_t codol_weapondefs_firingrange[] = {
#include "codol_weapondefs_firingrange.inc"
};
const int codol_weapondefs_firingrange_count =
    (int)(sizeof(codol_weapondefs_firingrange) / sizeof(codol_weapondefs_firingrange[0]));

const codol_weapondef_t *codol_weapondef_find(const char *name)
{
    int i;
    if (!name) return NULL;
    for (i = 0; i < codol_weapondefs_firingrange_count; ++i)
        if (strcmp(codol_weapondefs_firingrange[i].name, name) == 0)
            return &codol_weapondefs_firingrange[i];
    return NULL;
}

/* CODOL stores a sparse six-tier table.  A zero damage tier means "same
 * damage as the previous active tier", not zero damage.  Zero ranges are
 * unused slots; the last positive range is the final cutoff. */
int codol_weapondef_damage_at_distance(const codol_weapondef_t *def,
                                       float distance, bool player_damage)
{
    int i, active = -1, last = -1;
    (void)player_damage;
    if (!def) return 0;
    for (i = 0; i < CODOL_WEAPON_DAMAGE_TIERS; ++i) {
        if (def->damage_tiers[i] != 0) active = i;
        if (def->damage_ranges[i] > 0.0f) last = i;
        if (def->damage_ranges[i] > 0.0f && distance <= def->damage_ranges[i]) {
            if (active >= 0) return def->damage_tiers[active];
            break;
        }
    }
    if (active >= 0) return def->damage_tiers[active];
    if (last >= 0) return def->damage_tiers[last];
    return def->damage;
}

int codol_weapondef_damage_for_hit(const codol_weapondef_t *def,
                                   float distance, bool player_damage, int hitloc)
{
    float multiplier;
    int base;
    if (!def || hitloc < 0 || hitloc >= CODOL_HITLOC_COUNT)
        return codol_weapondef_damage_at_distance(def, distance, player_damage);
    base = codol_weapondef_damage_at_distance(def, distance, player_damage);
    multiplier = def->location_damage_multipliers[hitloc];
    if (multiplier <= 0.0f) return base;
    return (int)floorf((float)base * multiplier + 0.5f);
}

