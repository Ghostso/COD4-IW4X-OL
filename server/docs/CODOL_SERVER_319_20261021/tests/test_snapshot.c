#include "codol_snapshot.h"
#include <stdio.h>
int main(void)
{
    codol_snap_equip_t eq; uint8_t out[512]; int n, i;
    codol_snap_equip_default(&eq);
    n = codol_snapshot_build(out, sizeof(out), 0, 1000, 1000, true,
                             48.0f, -572.0f, -116.0f,
                             0, 0, 0, 0.0f, 0.0f,
                             0.0f,   /* aim_fraction */
                             false,  /* aiming */
                             false,  /* omit_motion */
                             true,   /* on_ground */
                             0,      /* living_weapon_entity */
                             NULL, NULL,   /* baseline: all-zero for the entry frame */
                             &eq, NULL, 0);
    printf("len=%d\n", n);
    for (i = 0; i < n; i++) printf("%02X", out[i]);
    printf("\n");
    return n <= 0;
}
