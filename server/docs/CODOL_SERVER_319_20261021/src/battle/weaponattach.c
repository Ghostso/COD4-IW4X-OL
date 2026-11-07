#include "codol_weaponattach.h"
#include <string.h>
#include <math.h>
typedef struct { const char *name; int count; codol_weaponattach_entry_t entries[64]; } flat_attach_t;
static const flat_attach_t table[] = {
#include "codol_weaponattach_scalar_firingrange.inc"
};
const int codol_weaponattach_scalar_count = (int)(sizeof(table)/sizeof(table[0]));
const codol_weaponattach_t *codol_weaponattach_find(const char *name)
{
    static codol_weaponattach_t views[256];
    static const char *const names[] = {
#include "codol_weaponattach_names.inc"
    };
    int i;
    if (!name) return NULL;
    for (i=0;i<codol_weaponattach_scalar_count && i<256;i++) {
        if (!strcmp(names[i],name)) {
            views[i].name=names[i];
            views[i].count=table[i].count;
            views[i].entries=table[i].entries;
            return &views[i];
        }
    }
    return NULL;
}
static int i32v(uint32_t v) { int i; memcpy(&i,&v,4); return i; }
static float f32v(uint32_t v) { float f; memcpy(&f,&v,4); return f; }
static void scale_damage_field(codol_weapondef_t *def, int field, float scale)
{
    int i;
    if (field >= 0 && field < CODOL_WEAPON_DAMAGE_TIERS && def->damage_tiers[field] != 0)
        def->damage_tiers[field] = (int)floorf((float)def->damage_tiers[field] * scale + 0.5f);
    if (field == 0) def->damage = (int)floorf((float)def->damage * scale + 0.5f);
    if (field == 1) def->player_damage = (int)floorf((float)def->player_damage * scale + 0.5f);
    if (field == 2) def->min_damage = (int)floorf((float)def->min_damage * scale + 0.5f);
    if (field == 3) def->min_player_damage = (int)floorf((float)def->min_player_damage * scale + 0.5f);
}
bool codol_weaponattach_apply_ex(codol_weapondef_t *def, const codol_weaponattach_t *a,
                                codol_weaponattach_result_t *result)
{
    int i;
    if (!def || !a) return false;
    if (result) { result->applied=0; result->skipped=0; }
    for (i=0;i<a->count;i++) {
        const codol_weaponattach_entry_t *e=&a->entries[i];
        { int known=1; if ((e->type < 16 && e->type != 7 && e->type != 9) || e->type == 39) { if (result) result->skipped++; continue; }
        switch (e->field_offset) {
        case 0x978: def->move_speed_scale=f32v(e->value); break;
        case 0x97c: def->ads_move_speed_scale=f32v(e->value); break;
        case 0x980: def->sprint_duration_scale=f32v(e->value); break;
        case 0xe68: def->clip_size=i32v(e->value); break;
        case 0xe6c: /* source-only marker */ break;
        case 0xe70: def->fire_time_ms=i32v(e->value); break;
        case 0x85c: def->reload_ms=i32v(e->value); break;
        case 0x868: def->reload_empty_ms=i32v(e->value); break;
        case 0x870: def->reload_add_ms=i32v(e->value); break;
        case 0xd10: scale_damage_field(def, 0, f32v(e->value)); break;
        case 0xd14: scale_damage_field(def, 1, f32v(e->value)); break;
        case 0xd18: scale_damage_field(def, 2, f32v(e->value)); break;
        case 0xd1c: scale_damage_field(def, 3, f32v(e->value)); break;
        case 0xd28: def->max_damage_range=f32v(e->value); break;
        case 0xd30: def->min_damage_range=f32v(e->value); break;
        case 0xd4c: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;
        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;
        default: known=0; break;
        }
        if (known) { if (result) result->applied++; }
        else if (result) result->skipped++; }
    }
    return true;
}
bool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *a)
{
    codol_weaponattach_result_t r;
    return codol_weaponattach_apply_ex(def,a,&r);
}
