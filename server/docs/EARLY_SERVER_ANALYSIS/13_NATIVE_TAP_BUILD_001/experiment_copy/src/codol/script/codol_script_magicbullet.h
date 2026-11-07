#ifndef CODOL_SCRIPT_MAGICBULLET_H
#define CODOL_SCRIPT_MAGICBULLET_H
#ifdef CODOL_SERVER

#ifdef __cplusplus
extern "C" {
#endif

/* IW4 0x497ed0: magicbullet(<weaponName>, <start>, <end>[, <attacker>]).
 * Function (not a method). See src/codol_script_magicbullet.c for the
 * traced contract and obj/claude-workers/magicbullet-r1-report.md for the
 * disassembly evidence. */
void CODOL_Scr_MagicBullet(void);
/* Native handle bridge for the shared projectile return path. */
struct gentity_s;
void CODOL_MagicBulletSetOwner(struct gentity_s *projectile, struct gentity_s *owner);

#ifdef __cplusplus
}
#endif

#endif
#endif
