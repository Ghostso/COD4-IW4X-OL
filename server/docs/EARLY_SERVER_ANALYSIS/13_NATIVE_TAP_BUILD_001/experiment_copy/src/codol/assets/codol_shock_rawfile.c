/* CoDOL shell-shock rawfile translation. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 ships shock/<name>.shock with its dvars named by registration number
 * (66 "blurred", 67 "0.4", ...) because the client's dvar names are stripped;
 * the bg_shock_volume_* entries keep their names. The retained
 * BG_LoadShellShock parses the IW3 bgShockDvarNames table by name, and that
 * table's order is C1's registration order, so id 66 + i is table entry i:
 *   66 screenType .. 73 viewKickFadeTime, 74 soundLoop, 75 soundLoopSilent,
 *   76 soundEnd, 77 soundEndAbort, 78 sound, 79 soundFadeInTime,
 *   80 soundFadeOutTime, 81 soundLoopFadeTime, 82 soundLoopEndDelay,
 *   83 soundRoomType, 84 soundDryLevel, 85 soundWetLevel, 86 soundModEndDelay,
 *   87 lookControl .. 91 lookControl_fadeTime, 92 movement.
 * The mounted default.shock confirms the assignment (66 "blurred",
 * 83 "underwater", 78 "1" for the sound flag). Lines that are not numbered
 * pass through unchanged. */
#include "codol_shock_rawfile.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static const char *const shock_names[] = {
    "bg_shock_screenType", "bg_shock_screenBlurBlendTime", "bg_shock_screenBlurBlendFadeTime",
    "bg_shock_screenFlashWhiteFadeTime", "bg_shock_screenFlashShotFadeTime", "bg_shock_viewKickPeriod",
    "bg_shock_viewKickRadius", "bg_shock_viewKickFadeTime", "bg_shock_soundLoop", "bg_shock_soundLoopSilent",
    "bg_shock_soundEnd", "bg_shock_soundEndAbort", "bg_shock_sound", "bg_shock_soundFadeInTime",
    "bg_shock_soundFadeOutTime", "bg_shock_soundLoopFadeTime", "bg_shock_soundLoopEndDelay",
    "bg_shock_soundRoomType", "bg_shock_soundDryLevel", "bg_shock_soundWetLevel", "bg_shock_soundModEndDelay",
    "bg_shock_lookControl", "bg_shock_lookControl_maxpitchspeed", "bg_shock_lookControl_maxyawspeed",
    "bg_shock_lookControl_mousesensitivityscale", "bg_shock_lookControl_fadeTime", "bg_shock_movement"
};
#define SHOCK_FIRST_ID 66u

int CODOL_TranslateShockText(const char *text, size_t length, char **out, size_t *out_length)
{
    size_t capacity, used = 0, i = 0;
    char *result;
    if (!text || !out || !out_length) return 0;
    capacity = length + 27 * 48 + 1;
    result = malloc(capacity);
    if (!result) return 0;
    while (i < length) {
        size_t line = i, digits = 0;
        unsigned id = 0;
        while (line < length && (text[line] == ' ' || text[line] == '\t')) ++line;
        while (line + digits < length && isdigit((unsigned char)text[line + digits]) && digits < 4) {
            id = id * 10 + (unsigned)(text[line + digits] - '0'); ++digits;
        }
        if (digits && line + digits < length && (text[line + digits] == ' ' || text[line + digits] == '\t') &&
            id >= SHOCK_FIRST_ID && id < SHOCK_FIRST_ID + sizeof(shock_names) / sizeof(*shock_names)) {
            const char *name = shock_names[id - SHOCK_FIRST_ID];
            size_t n = strlen(name);
            if (used + (line - i) + n >= capacity) { free(result); return 0; }
            memcpy(result + used, text + i, line - i); used += line - i;
            memcpy(result + used, name, n); used += n;
            i = line + digits;
        }
        while (i < length) {
            if (used + 1 >= capacity) { free(result); return 0; }
            result[used++] = text[i++];
            if (text[i - 1] == '\n') break;
        }
    }
    result[used] = 0;
    *out = result; *out_length = used;
    return 1;
}
