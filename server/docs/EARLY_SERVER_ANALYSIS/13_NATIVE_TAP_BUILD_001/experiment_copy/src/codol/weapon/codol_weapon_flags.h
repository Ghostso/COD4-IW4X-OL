#ifndef CODOL_WEAPON_FLAGS_H
#define CODOL_WEAPON_FLAGS_H
/* Extension to retained native weapFlags. Outside IW3's original 9-bit wire
 * mask; only the CoDOL semantic serializer may publish this state. */
#define CODOL_WEAP_OFFHAND_DISABLED 0x1000u
#define CODOL_WEAP_SWITCH_DISABLED 0x800u
/* Server-private usability state; IW4 stores this in gclient flags. It is
 * deliberately not translated to a CoDOL player-state weapon flag. */
#define CODOL_USE_DISABLED 0x2000u
/* player_recoilScaleOn/Off. Unlike the bits above this one is not an invention:
 * IW4 (0x5dd34e/0x5dd3b0) and C1 (0x0051982f/0x005198da) set and clear exactly
 * 0x400 in their own weapon-flags word, and both engines' BG_WeaponFireRecoil
 * (IW4 0x4a60d5, C1 0x004222bf) tests it before scaling the recoil. The bit is
 * unused by the retained IW3 assembly and outside its 9-bit weapFlags netfield,
 * so it carries the same meaning here and is published unchanged to C1's
 * playerState field 0x344. */
#define CODOL_WEAP_RECOIL_SCALE 0x400u
/* The three per-button offhand restrictions C1 tests beside the three selected
 * slots: PM_Weapon_CheckForOffHand refuses a button whose bit is set in the
 * playerState weapon-flags word at 0x41cb52, 0x41cb70 and 0x41cb96, and the
 * pmove clears the third at 0x41a0c0. They are a different group from the
 * frag/tactical/special restrictions helper 0x41c5a0 reads (0x20000/0x40000/
 * 0x80000), which CODOL_OverlayEngineOffhandControl already owns. Like those,
 * these bits sit outside IW3's nine-bit weapFlags netfield and publish
 * unchanged to C1's playerState 0x344. No producer sets them yet; the consumer
 * is the selector in src/codol_weapon_state.c. */
#define CODOL_WEAP_OFFHAND_FRAG_DISABLED 0x4000u
#define CODOL_WEAP_OFFHAND_SPECIAL_DISABLED 0x8000u
#define CODOL_WEAP_OFFHAND_EQUIPMENT_DISABLED 0x10000u
/* disableWeaponPickup / enableWeaponPickup: IW4 PWF_DISABLE_WEAPON_PICKUP and
 * C1 0x5145c3/0x5145dc use 0x100000 in their own word; the CG pickup hint
 * 0x481105..0x48113b tests the same bit, so it publishes unchanged to 0x344
 * and Touch_Item refuses weapon pickups while it is set. */
#define CODOL_WEAP_PICKUP_DISABLED 0x100000u
/* C1 PM 0x41979a: set while the weapon being raised has def+0x340 == 3 (riot
 * shield), cleared at 0x4197a6/0x41db67. Wire bit is C1 0x1000 (IW4
 * PWF_SWITCHING_TO_RIOTSHIELD); the native word already uses 0x1000 for the
 * offhand disable, so it lives at 0x200000 here and is translated on publish. */
#define CODOL_WEAP_RIOTSHIELD_NEXT 0x200000u
/* The retained fresh trigger-pull latch (_bg_weapons.asm PM_Weapon_360 sets
 * it, PM_Weapon_1830 reads it, PM_Weapon_1900 consumes it on the first shot).
 * codol_engine_state.c publishes it as C1's own per-hand fresh-pull bit at
 * ps+0x27c, NOT as C1's ps+0x344 bit 0x100 -- C1 uses that bit in its weapon
 * flags word for the armed barrel of a double-barrel weapon (0x41ae4e read,
 * 0x41bad9/0x41bae5 write), which this engine keeps in the hand bundle
 * instead. The two meanings collide on the same bit number, so anything that
 * touches it has to say which one it means. */
#define CODOL_WEAP_FRESH_PULL 0x100u
#endif
