/* The actual native distance helper used by custom equipment and killstreak
 * splash. Live C1 hit callbacks and visibility are outside this fixture. */
#include "codol_radius_distance.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

static void near(float actual,float expected)
{ assert(fabsf(actual-expected)<0.0001f); }

int main(void)
{
    const float player_min[3]={-15.0f,-15.0f,0.0f};
    const float player_max[3]={15.0f,15.0f,72.0f};
    const float chest[3]={0.0f,0.0f,60.0f};
    const float side[3]={25.0f,0.0f,60.0f};
    const float corner[3]={18.0f,19.0f,60.0f};
    const float below[3]={0.0f,0.0f,-8.0f};

    /* A chest-height blast is inside a player's box even though its distance
     * to the player's feet is 60 units. A 40-unit radius must reach it. */
    near(CODOL_RadiusBoxDistance(chest,player_min,player_max),0.0f);
    assert(CODOL_RadiusBoxDistance(chest,player_min,player_max)<40.0f);
    near(CODOL_RadiusBoxDistance(side,player_min,player_max),10.0f);
    near(CODOL_RadiusBoxDistance(corner,player_min,player_max),5.0f);
    near(CODOL_RadiusBoxDistance(below,player_min,player_max),8.0f);
    puts("PASS: custom splash measures players from absolute bounds");
    return 0;
}
