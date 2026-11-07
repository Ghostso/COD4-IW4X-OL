/* Script-owned weapon HUD icon overrides and their publication.
 * See codol_hud_icon_overrides.h for the two-stage provenance, the publication
 * point and the lifetime. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_hud_icon_overrides.h"
#include "codol_playerstate_ext.h"
#include "sys_cod4defs.h"
#include <string.h>

/* Stage 1: the equivalent of IW4's client+0x3264 and C1's client+0x35ac. It is
 * script state of a client slot, not of a playerState, so it is keyed by client
 * number and is never reached by a playerState copy - which is exactly what
 * keeps a following spectator's own overrides intact. */
static uint16_t client_hud_icons[MAX_CLIENTS][CODOL_HUD_ICON_CLIENT_SLOTS];

int CODOL_SetClientHudIconOverride(unsigned client, unsigned slot, unsigned material)
{
    if (client >= MAX_CLIENTS || slot >= CODOL_HUD_ICON_CLIENT_SLOTS) return 0;
    /* The index is into the retained CS_MATERIALS range; 0 is "no override".
     * An index outside it is a producer that did not use G_MaterialIndex, and
     * the publication could not carry it. */
    if (material >= (unsigned)MAX_MATERIALS) return 0;
    client_hud_icons[client][slot] = (uint16_t)material;
    return 1;
}

unsigned CODOL_GetClientHudIconOverride(unsigned client, unsigned slot)
{
    if (client >= MAX_CLIENTS || slot >= CODOL_HUD_ICON_CLIENT_SLOTS) return 0;
    return client_hud_icons[client][slot];
}

void CODOL_PublishClientHudIconOverrides(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* IW4 0x005d80bc copies the whole array, unconditionally, every frame it
     * runs: the playerState half is a copy of the script half and nothing else
     * writes it, so there is no merge and no "changed" test here either. */
    CODOL_PlayerStateExtSetClientHudIcons(client, client_hud_icons[client]);
}

void CODOL_ResetClientHudIconOverrides(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    memset(client_hud_icons[client], 0, sizeof(client_hud_icons[client]));
}

void CODOL_ResetAllHudIconOverrides(void)
{
    memset(client_hud_icons, 0, sizeof(client_hud_icons));
}
