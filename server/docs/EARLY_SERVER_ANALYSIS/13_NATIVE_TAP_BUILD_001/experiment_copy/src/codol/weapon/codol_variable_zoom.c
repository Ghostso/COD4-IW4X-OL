/* CoDOL variable-zoom scope state: a port of C1 PM_UpdateVariableZoom.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * A variable-zoom scope (the scope_vzoom / thermal_*_vzoom attachments) steps
 * its zoom with the melee key while the player is aiming down it. C1 does that
 * inside pmove, so the server has to run the same step and publish the result;
 * the other half of the rule is the melee check refusing a scoped melee
 * (0x41c123..0x41c139), which lives in _bg_weapons.asm.
 *
 * C1.exe 1.1.1.13, called from PM_Weapon at 0x41dbfb, after the ADS lerp
 * 0x4185a0 and before PM_UpdateHoldBreath 0x4188b0. ESI = pmove, ECX = ps:
 *
 *   00418486  mov edx,[ecx+0x33c]            ps->weapon
 *   00418493  cmp dword [def+0x694],0 / je   no scope overlay: return
 *   004184a0  fldz / fcom [ecx+0x348]        return unless fWeaponPosFrac > 0
 *   004184b3  test byte [ecx+0x344],2        offhand viewmodel: weapon = ps+0x328
 *   004184c4  mov edi,[ecx+0x5c4]            level
 *   004184cd  (level+1) % 3                  next
 *   004184e2  fld [def(weapon)+next*4+0x944] zoom FOV of next; 0.0 -> next = 0
 *   004184f6  level == 0 && next == 0        single-level scope: return
 *   00418504  latch byte ps+0x5cc == 0 &&
 *   0041850c  cmd.serverTime - ps+0x5c8 > 40 &&
 *   0041851a  cmd.buttons & 4                -> level = next, latch = 1,
 *                                               time = serverTime, event 0xb8
 *   00418568  serverTime - time > 40 && !(buttons & 4) -> latch = 0, time = now
 *
 * Event 0xb8 is EV_SCOPE_ZOOM in C1's event-name table 0xCD81D8 (slot 184),
 * queued with a zero parameter. ps+0x5c4 (2 bits) and ps+0x5cc (1 bit) are
 * netfields; ps+0x5c8 is not, so the client replays every command from a
 * snapshot with time 0. The hint C1 draws for it, PLATFORM_HOLD_BREATH_ZOOM
 * bound to +melee (0x457800..0x4578dd), uses the same def+0x694 and
 * def+0x948 != 0 tests. */
#include "codol_variable_zoom.h"
#include <string.h>

#ifndef MAX_CLIENTS
#define MAX_CLIENTS 64
#endif

static codol_variable_zoom_t codol_variable_zoom_clients[MAX_CLIENTS];

int CODOL_VariableZoomStep(codol_variable_zoom_t *zoom, int scoped, float pos_frac,
                           const float fov[3], int32_t server_time, uint32_t buttons)
{
    int32_t next;
    if(!zoom || !fov || !scoped) return 0;
    /* fcom/test ah,5/jp: continue only when 0 < posFrac (NaN returns). */
    if(!(pos_frac > 0.0f)) return 0;
    next = (zoom->level + 1) % 3;
    /* Our level is only ever 0..2; C1 would index out of bounds otherwise. */
    if(next < 0) next = 0;
    /* fucompp/test ah,0x44/jp: only an exact 0.0 resets (NaN does not). */
    if(fov[next] == 0.0f) next = 0;
    if(zoom->level == 0 && next == 0) return 0;
    if(!zoom->latch && server_time - zoom->time > CODOL_VARIABLE_ZOOM_DEBOUNCE_MS &&
       (buttons & CODOL_VARIABLE_ZOOM_BUTTON)) {
        zoom->level = next;
        zoom->latch = 1;
        zoom->time = server_time;
        return 1;
    }
    if(server_time - zoom->time > CODOL_VARIABLE_ZOOM_DEBOUNCE_MS &&
       !(buttons & CODOL_VARIABLE_ZOOM_BUTTON)) {
        zoom->latch = 0;
        zoom->time = server_time;
    }
    return 0;
}

codol_variable_zoom_t *CODOL_VariableZoomClient(unsigned client)
{
    return client < MAX_CLIENTS ? &codol_variable_zoom_clients[client] : NULL;
}

void CODOL_VariableZoomResetClient(unsigned client)
{
    if(client < MAX_CLIENTS)
        memset(&codol_variable_zoom_clients[client], 0, sizeof codol_variable_zoom_clients[client]);
}

void CODOL_VariableZoomResetAll(void)
{
    memset(codol_variable_zoom_clients, 0, sizeof codol_variable_zoom_clients);
}

void CODOL_VariableZoomWire(int client, uint32_t *level, uint32_t *latch)
{
    const codol_variable_zoom_t *zoom =
        client >= 0 ? CODOL_VariableZoomClient((unsigned)client) : NULL;
    uint32_t l = 0, b = 0;
    if(zoom) {
        l = zoom->level >= 0 && zoom->level <= 3 ? (uint32_t)zoom->level : 0u;
        b = zoom->latch ? 1u : 0u;
    }
    if(level) *level = l;
    if(latch) *latch = b;
}
