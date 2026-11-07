#ifndef CODOL_LOADOUT_FASTMAG_H
#define CODOL_LOADOUT_FASTMAG_H
#include "codol_script_profile_loadout.h"
/* Narrow existing-asset compatibility policy; does not change profile identity.
 * 1 selects an equivalent composition base, 0 not applicable, -1 incompatible
 * or unavailable source data. The output index changes only on success. */
int CODOL_EventFastMagCompositionBase(const codol_loadout_recipe_t *,unsigned *);
#endif
