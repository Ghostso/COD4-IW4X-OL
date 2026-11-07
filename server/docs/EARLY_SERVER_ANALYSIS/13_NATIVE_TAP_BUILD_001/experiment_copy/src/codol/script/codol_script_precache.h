/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_PRECACHE_H
#define CODOL_SCRIPT_PRECACHE_H
#ifdef __cplusplus
extern "C" {
#endif
/* precacheItem(<weapon>): the retained IW3 precache, except that a weapon name
 * no mounted CoDOL zone defines is skipped with a developer trace instead of
 * ending the level. The IW4 gametype scripts enumerate IW4 weapon and
 * attachment-combination names from the stats table; CoDOL composes
 * attachments through its marketplace items, so those names are not assets. */
void CODOL_Scr_PrecacheItem(void);
#ifdef __cplusplus
}
#endif
#endif
