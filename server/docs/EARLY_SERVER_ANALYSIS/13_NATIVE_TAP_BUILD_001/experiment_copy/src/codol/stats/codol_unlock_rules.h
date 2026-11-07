#ifndef CODOL_UNLOCK_RULES_H
#define CODOL_UNLOCK_RULES_H
/* Return 1 with a signed scalar value, or 0 if the profile field is unavailable.
 * group is experienceRank, titleUnlocked, iconUnlocked or challengeState.
 * experienceRank is the IW4 zero-based rank converted from total experience;
 * it must not be supplied directly from CoDOL's one-based stored rank. */
typedef int (*codol_unlock_read_t)(void *context,const char *group,const char *key,int *value);
/* Evaluate a found IW4 unlocktable row. Returns 1 with an unlocked result, or
 * 0 on invalid/unavailable required inputs, preserving output. An unavailable
 * title/icon override still permits a known true result from ordinary rules;
 * failed ordinary rules with that override unknown cannot establish false.
 * Missing-row behavior
 * belongs to the table lookup caller. No account identity or profile mapping
 * is inferred here. */
int CODOL_EvaluateUnlockRule(const char *item,const char *category,const char *rank,
    const char *requirements,codol_unlock_read_t read,void *context,int *unlocked);
#endif
