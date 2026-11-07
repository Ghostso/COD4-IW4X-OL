#include "codol_radar_input.h"
#ifdef CODOL_SERVER
#include "codol_radar_types.h"
#endif
#include "sys_cod4defs.h"
#include <string.h>

/* C1 client field c3c1e0 is a generic integer at client+35a4. Keep the
 * integer for script reads; only the frame publisher converts it to a bool.
 * This is live gclient input, never part of a spectator/archive copy. */
static int radar_block_input[MAX_CLIENTS];

int CODOL_ClientRadarBlockInput(unsigned client)
{
    return client < MAX_CLIENTS ? radar_block_input[client] : 0;
}
void CODOL_SetClientRadarBlockInput(unsigned client, int value)
{
    if (client < MAX_CLIENTS) radar_block_input[client] = value;
}
void CODOL_ResetClientRadarInput(unsigned client)
{
    CODOL_SetClientRadarBlockInput(client, 0);
#ifdef CODOL_SERVER
    CODOL_ResetClientRadarTypes(client);
#endif
}
void CODOL_ResetAllRadarInput(void)
{
    memset(radar_block_input, 0, sizeof(radar_block_input));
#ifdef CODOL_SERVER
    CODOL_ResetAllRadarTypes();
#endif
}
