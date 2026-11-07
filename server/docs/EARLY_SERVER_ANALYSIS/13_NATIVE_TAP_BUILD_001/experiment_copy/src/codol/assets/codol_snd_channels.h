/* SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * CoDOL sound entity-channel table.
 *
 * C1 40acc0..40af26 builds its channel list from the rawfile
 * soundaliases/channels.def (one channel per non-comment line, name is the
 * first CSV field, at most 64 characters, at most 64 channels) and, for each
 * channel, registers the dvar "bg_shock_volume_<name>" as
 * Dvar_RegisterFloat(0.5, 0.0, 1.0, 0x10004, "") (40adbd..40adf1); the other
 * bg_shock_* dvars carry the same 0x10004 flags (40bc19..40bcaf), which the
 * retained port registers as CVAR_CHEAT (0x80). The retained
 * BG_RegisterShockVolumeDvars / BG_LoadShellShockDvars / BG_SaveShellShockDvars
 * (_bg_misc.asm) size their name list by SND_GetEntChannelCount() and name each
 * entry with SND_GetEntChannelName(i); the dedicated build stubbed those to 0 /
 * "server", so every bg_shock_volume_<channel> line of a mounted .shock file
 * was reported as an unknown cvar by Com_LoadDvarsFromBuffer (misc.c). */
#ifndef CODOL_SND_CHANNELS_H
#define CODOL_SND_CHANNELS_H
#ifdef __cplusplus
extern "C" {
#endif

/* Number of entity sound channels (C1 caps the def at 64). The table is
 * resolved on first use from the mounted soundaliases/channels.def and falls
 * back to the CoDOL 1.1.1.13 shipped list when no archive serves it. */
int CODOL_SndEntChannelCount(void);
/* Channel name for 0 <= index < CODOL_SndEntChannelCount(); "" otherwise. */
const char *CODOL_SndEntChannelName(int index);

#ifdef __cplusplus
}
#endif
#endif
