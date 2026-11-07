#ifndef CODOL_CASELESS_H
#define CODOL_CASELESS_H
#include <stdio.h>
/* Open a loose file for reading, matching path components case-insensitively
 * when the exact spelling is absent. Windows (and C1) resolve every rawfile
 * name case-insensitively and the script tree mixes spellings
 * (mp/challengeTable.csv beside mp/challenges/challengetable_perk.csv, asked
 * for as ChallengeTable_Perk.csv), so a Linux server needs the same rule.
 * On Windows this is plain fopen. On a miss errno is ENOENT, as from fopen. */
FILE *CODOL_FOpenReadCaseless(const char *path);
#endif
