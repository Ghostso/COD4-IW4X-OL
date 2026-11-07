/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PROFILE_PROGRESS_H
#define CODOL_PROFILE_PROGRESS_H
#include <stdint.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Server-side persistence for the IW4-only playerdata roots.
 *
 * The CoDOL client's own playerdata and playersecuredata definitions do not
 * declare the roots IW4's _rank.gsc and _missions.gsc write to (experience,
 * rank, prestige, challenge progress and so on), so those are served from a
 * per-client session store that is discarded on disconnect. Nothing on the
 * server may write the lobby's own credential or profile files, so this keeps
 * a separate store of its own under the server home directory, keyed by the
 * player's secure-profile uid.
 *
 * This is the server's record of progression, not the account's: it is never
 * uploaded and the client is not told about it. It exists so that rank and
 * challenge progress survive a disconnect, a map change and a server restart,
 * which is what the scripts assume when they read a value back. */

/* Read <fs_homepath>/codol_progress/<uid>.txt into the client's session store.
 * Missing file is success with nothing loaded. Returns the number of entries
 * restored, or -1 on a malformed file. */
int CODOL_LoadClientProgress(unsigned client, uint64_t uid);

/* Write the client's session store back. Returns the number of entries
 * written, or -1 if the file could not be produced. A store with no entries
 * writes nothing and removes no existing file. */
int CODOL_SaveClientProgress(unsigned client, uint64_t uid);

/* Save using the uid currently attached to the client, if any. Safe to call
 * for a slot with no profile: it does nothing. */
void CODOL_SaveClientProgressIfAttached(unsigned client);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
