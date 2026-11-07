#include "codol_player_links_wire.h"
#include <assert.h>
#include <string.h>

static uint32_t player_word(const codol_player_fields_t *state, unsigned offset)
{
    unsigned i;
    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i)
        if(CODOL_PlayerField(i)->offset == offset) return state->field[i];
    assert(!"missing player field");
    return 0;
}

int main(void)
{
    codol_player_fields_t wire, before;
    codol_ps_links_t link;

    memset(&wire, 0, sizeof(wire));
    memset(&link, 0, sizeof(link));
    link.linkWeaponEntNum = ENTITYNUM_NONE;
    link.controlsEntNum = ENTITYNUM_NONE;
    assert(CODOL_OverlayPlayerLinks(&wire, &link));
    assert(player_word(&wire, 0x1ec) == ENTITYNUM_NONE);

    link.mode = 2;
    link.linkWeaponEntNum = 37;
    assert(CODOL_OverlayPlayerLinks(&wire, &link));
    assert(player_word(&wire, 0x1ec) == 37);

    before = wire;
    link.mode = 1;
    link.linkWeaponEntNum = 0;
    assert(!CODOL_OverlayPlayerLinks(&wire, &link));
    assert(!memcmp(&wire, &before, sizeof(wire)));
    return 0;
}
