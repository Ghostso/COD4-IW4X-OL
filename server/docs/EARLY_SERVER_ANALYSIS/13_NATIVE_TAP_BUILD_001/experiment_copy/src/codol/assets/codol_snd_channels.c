/* SPDX-License-Identifier: AGPL-3.0-or-later
 * CoDOL sound entity-channel table; see codol_snd_channels.h. */
#include "codol_snd_channels.h"
#include "codol_assets.h"
#include "q_shared.h"
#include "qcommon_io.h"
#include <string.h>

#define SND_CHANNEL_MAX 64u   /* channels.def header: "MAX number of channels: 64" */
#define SND_CHANNEL_NAME_MAX 64u /* C1 40ad79: names longer than 0x40 are rejected */

/* soundaliases/channels.def as shipped by CoDOL 1.1.1.13 (mounted copy at
 * bin/home/codol_rawfiles/soundaliases/channels.def; byte-identical to the
 * IW4 vendor file). Used only when no archive serves the def at first use. */
static const char *const shipped_channels[] = {
    "physics", "ambdist1", "ambdist2", "auto", "auto2", "autodog", "bulletimpact",
    "bulletwhizby", "explosiveimpact", "element", "auto2d", "vehicle", "vehiclelimited",
    "menu", "body", "body2d", "reload", "reload2d", "item", "effects1", "effects2",
    "weapon", "weapon2d", "nonshock", "voice", "local", "local2", "local3", "ambient",
    "hurt", "player1", "player2", "music", "musicnopause", "mission", "announcer",
    "shellshock"
};

static char channel_names[SND_CHANNEL_MAX][SND_CHANNEL_NAME_MAX + 1];
static int channel_count = -1;

/* Parses the def the way C1 40acc0.. does: each line is one channel, lines
 * starting with '#' are comments, the name is the text before the first ','
 * (trailing whitespace trimmed). Returns the number of channels parsed. */
static int parse_channels_def(const char *text, int length)
{
    int count = 0, i = 0;
    while (i < length && count < (int)SND_CHANNEL_MAX) {
        int start, end, name_end;
        while (i < length && (text[i] == ' ' || text[i] == '\t' || text[i] == '\r')) ++i;
        start = i;
        while (i < length && text[i] != '\n') ++i;
        end = i;
        if (i < length) ++i; /* consume '\n' */
        if (start == end || text[start] == '#') continue;
        name_end = start;
        while (name_end < end && text[name_end] != ',') ++name_end;
        while (name_end > start && (text[name_end - 1] == ' ' || text[name_end - 1] == '\t' || text[name_end - 1] == '\r')) --name_end;
        if (name_end == start) continue;
        if ((unsigned)(name_end - start) > SND_CHANNEL_NAME_MAX) {
            Com_PrintWarning(CON_CHANNEL_SYSTEM, "CoDOL snd channels: channel name longer than %u characters in soundaliases/channels.def, skipped\n", SND_CHANNEL_NAME_MAX);
            continue;
        }
        memcpy(channel_names[count], text + start, (size_t)(name_end - start));
        channel_names[count][name_end - start] = 0;
        ++count;
    }
    return count;
}

static void resolve_channels(void)
{
    const codol_engine_rawfile_t *raw = NULL;
    int count = 0;
    if (channel_count >= 0) return;
    if (CODOL_LoadEngineRawFile("soundaliases/channels.def", &raw) == 1 && raw && raw->buffer && raw->len > 0)
        count = parse_channels_def(raw->buffer, raw->len);
    if (count > 0) {
        Com_DPrintf(CON_CHANNEL_SYSTEM, "CoDOL snd channels: %d entity channels from soundaliases/channels.def\n", count);
    } else {
        unsigned i;
        count = (int)(sizeof(shipped_channels) / sizeof(*shipped_channels));
        for (i = 0; i < (unsigned)count; ++i)
            Q_strncpyz(channel_names[i], shipped_channels[i], sizeof(channel_names[i]));
        Com_DPrintf(CON_CHANNEL_SYSTEM, "CoDOL snd channels: soundaliases/channels.def not mounted, using the shipped %d-channel table\n", count);
    }
    channel_count = count;
}

int CODOL_SndEntChannelCount(void)
{
    resolve_channels();
    return channel_count;
}

const char *CODOL_SndEntChannelName(int index)
{
    resolve_channels();
    if (index < 0 || index >= channel_count) return "";
    return channel_names[index];
}
