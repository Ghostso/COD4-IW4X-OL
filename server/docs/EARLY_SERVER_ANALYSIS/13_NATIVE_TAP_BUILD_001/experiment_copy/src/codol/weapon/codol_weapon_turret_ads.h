/* CoDOL mounted-turret aim-down-sight (zoom) transition.
 *
 * C1 gives a player linked to a turret / mounted MG its own ADS path that
 * never consults the weapon definition: it is reached before the
 * WeaponDef +0xbc8 (aimDownSight) gate in both BG_PlayerCanAds (0x00418140)
 * and PM_UpdateAimDownSightLerp (0x004185a0).  That matters because the only
 * mountable CoDOL weapon, turret_minigun_mp, ships with aimDownSight == 0, so
 * every def-driven ADS gate refuses it.
 *
 * Both halves are driven by C1 dvars, not by per-weapon data:
 *   "209"  bool,  default 1,                  flags 4 (DVAR_CHEAT), C1 0x150c5ac
 *          -> may a linked player aim down sight at all
 *   "210"  float, default 250, range [0,5000], flags 4 (DVAR_CHEAT), C1 0x1509e94
 *          -> the full 0 -> 1 transition time in milliseconds.  <= 0 snaps.
 */
#ifndef CODOL_WEAPON_TURRET_ADS_H
#define CODOL_WEAPON_TURRET_ADS_H
#ifdef CODOL_SERVER

struct playerState_s;

/* C1 BG_PlayerCanAds 0x0041817b..0x0041818c: while ps->eFlags carries
 * PLAYER_EFLAG_TURRET_MASK the answer is this dvar and nothing else. */
int CODOL_TurretAdsAllowed(void);

/* The transition time in milliseconds, or <= 0 when C1 snaps instead. */
float CODOL_TurretAdsTransitionMsec(void);

/* C1 PM_UpdateAimDownSightLerp 0x004185c2..0x0041863d and 0x00418642.
 * Owns the whole ADS frame for a linked/turret player: advances
 * ps->fWeaponPosFrac towards the PMF_ADS_BUTTON endpoint at 1/"210" per
 * millisecond, clamps to [0,1] and clears ps->adsDelayTime.
 *
 * Returns 1 when it owned the frame (the caller must return immediately) and
 * 0 when the player is not linked, leaving the playerstate untouched. */
int CODOL_TurretAdsLerp(struct playerState_s *ps, int msec);

#endif
#endif
