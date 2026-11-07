#include "codol_weapondefs.h"
#include "codol_weaponattach.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    const codol_weapondef_t *m4 = codol_weapondef_find("m4a1tech_mp");
    const codol_weapondef_t *ak = codol_weapondef_find("ak47_mp");
    const codol_weapondef_t *mp5 = codol_weapondef_find("mp5k_mp");
    assert(m4 && ak && mp5);

    /* Zone-verified raw fields. */
    assert(m4->clip_size == 30 && m4->fire_time_ms == 71);
    assert(m4->damage == 33 && m4->reload_ms == 2029 && m4->reload_empty_ms == 2799);
    assert(m4->location_damage_multipliers[CODOL_HITLOC_HEAD] == 1.2f);
    assert(ak->clip_size == 30 && ak->fire_time_ms == 96 && ak->damage == 45);
    assert(mp5->clip_size == 30 && mp5->fire_time_ms == 74 && mp5->damage == 40);

    /* Six-tier zone-verified curves. */
    assert(m4->damage_tiers[0] == 33 && m4->damage_tiers[5] == 24);
    assert(m4->damage_ranges[0] == 500.0f && m4->damage_ranges[2] == 1800.0f);
    assert(ak->damage_tiers[0] == 45 && ak->damage_tiers[2] == 33);
    assert(ak->damage_ranges[0] == 1600.0f && ak->damage_ranges[2] == 2250.0f);
    assert(mp5->damage_tiers[0] == 40 && mp5->damage_tiers[5] == 18);

    /* Inside the first tier, and beyond the final range: the final sparse
     * non-zero damage tier is active. */
    assert(codol_weapondef_damage_at_distance(m4, 100.0f, true) == 33);
    assert(codol_weapondef_damage_at_distance(m4, 4000.0f, true) == 24);
    assert(codol_weapondef_damage_at_distance(ak, 1000.0f, true) == 45);
    assert(codol_weapondef_damage_at_distance(ak, 2250.0f, true) == 33);
    assert(codol_weapondef_damage_at_distance(mp5, 1600.0f, true) == 18);
    assert(codol_weapondef_damage_for_hit(m4, 100.0f, true, CODOL_HITLOC_HEAD) == 40);
    assert(codol_weapondef_damage_for_hit(ak, 100.0f, true, CODOL_HITLOC_HEAD) == 54);
    assert(codol_weapondef_damage_for_hit(mp5, 100.0f, true, CODOL_HITLOC_HEAD) == 44);

    {
        codol_weapondef_t d = *m4;
        const codol_weaponattach_t *hc = codol_weaponattach_find("highcal_base");
        const codol_weaponattach_t *fmj = codol_weaponattach_find("fmj_base");
        assert(hc && fmj);
        assert(codol_weaponattach_apply(&d, hc));
        assert(d.location_damage_multipliers[CODOL_HITLOC_HEAD] == 1.5f);
        d = *m4;
        assert(codol_weaponattach_apply(&d, fmj));
        assert(d.location_damage_multipliers[CODOL_HITLOC_HEAD] == 1.2f);
        {
            codol_weaponattach_result_t r;
            d = *m4;
            assert(codol_weaponattach_apply_ex(&d, hc, &r));
            assert(r.applied == 2 && r.skipped == 0);
        }
    }
    puts("test_weapondefs: all checks passed");
    return 0;
}
