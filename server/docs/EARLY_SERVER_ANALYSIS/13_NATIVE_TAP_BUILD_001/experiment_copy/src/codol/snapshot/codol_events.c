/* Native semantic ID translation; SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_events.h"
#include "codol_usercmd.h"
#include "bg.h"
#include "codol_weapon_state.h"
#include <string.h>
/* Keep independently produced internal events distinct from appended BGEvent
 * entries. The full-width queue preserves these IDs through snapshot mapping. */
_Static_assert(EV_STOP_FX_ON_TAG != CODOL_EV_EJECT_BRASS_SECONDARY,
               "stop-fx event collides with secondary brass");
_Static_assert(EV_STOP_FX_ON_TAG != CODOL_EV_WEAPON_SWITCH_STARTED,
               "stop-fx event collides with weapon switch");
_Static_assert(EV_PLAY_FX_ON_TAG_FOR_CLIENTS != CODOL_EV_DTP_LAND,
               "play-fx event collides with dive land");
_Static_assert(EV_PLAY_FX_ON_TAG_FOR_CLIENTS != CODOL_EV_MANTLE_START,
               "play-fx event collides with mantle start");
_Static_assert(EV_PLAY_FX_ON_TAG_FOR_CLIENTS != CODOL_EV_DTP_LAUNCH,
               "play-fx event collides with dive launch");
_Static_assert(CODOL_EV_STANCE_INVALID > EV_PLAY_FX_ON_TAG_FOR_CLIENTS &&
               CODOL_EV_STANCE_INVALID != CODOL_EV_DTP_LAUNCH,
               "stance-invalid event collides with a native event");
_Static_assert(CODOL_EV_SCOPE_ZOOM > CODOL_EV_OFFHAND_END_NOTIFY,
               "scope zoom event collides with another internal event");
_Static_assert(CODOL_EV_OFFHAND_END_NOTIFY > EV_PLAY_FX_ON_TAG_FOR_CLIENTS &&
               CODOL_EV_OFFHAND_END_NOTIFY > CODOL_EV_DTP_LAUNCH,
               "offhand end notify collides with another internal event");
int CODOL_EventParameterToWire(unsigned event,uint32_t parameter,uint32_t *out)
{
    if(!out) return -1;
    if(event==EV_MISSILE_REMOTE_BOOST) {
        /* IW4 5e8853..5e8863 emits EV_MISSILE_REMOTE_BOOST with zero;
         * C1 event-name table cd81d8 identifies its counterpart as105. */
        if(parameter) return -1;
        *out=0; return 1;
    }
    if(event >= EV_LANDING_PAIN_DEFAULT && event <= EV_LANDING_PAIN_PAINTEDMETAL) {
        /* PM_GroundTrace publishes damage percent plus C1 surface flag80.
         * C1 producer411498 sets it; server consumer50bc6e masks it before
         * damage. Preserve the flag for client presentation. */
        if((parameter & ~0xffu) || (parameter & 0x7fu) > 100) return -1;
        *out=parameter; return 1;
    }
    if(event >= EV_LANDING_DEFAULT && event <= EV_LANDING_PAINTEDMETAL) {
        /* Surface is encoded by the event ID. Native PM_GroundTrace_270
         * computes the landing intensity and caps it at24; _510 emits it.
         * C1 411303..411331 likewise stores intensity capped24 at[ebp-8],
         * then 4115da..4115e3 sends it with surface+121 via40ced0.
         * This range deliberately excludes painful landings, whose
         * parameter has separate damage/flag semantics in C1. */
        if(parameter > 24) return -1;
        *out=parameter; return 1;
    }
    switch(event) {
    case EV_NONE: *out=0; return 1;
    case EV_FOOTSTEP_SPRINT:
    case EV_FOOTSTEP_RUN:
    case EV_FOOTSTEP_WALK:
    case EV_FOOTSTEP_PRONE:
    case EV_JUMP:
        /* Retained PM_FootstepEvent passes (surfaceFlags >> 20) & 31.
         * C1 413268..41329c extracts the identical five bits and stores
         * them as the parameter; 411040 selects event116..119. CoDOL
         * collision materials preserve their source surfaceFlags in the
         * native loader, so this is an unchanged surface value, not an
         * asset index. Jump uses the same extraction (native bg_jump.cpp,
         * C1 4095d0), with ladder surface21; its parameter stores are
         * 4095df/40960a. Explicit ladder/fallback surfaces also fit here. */
        if(parameter > 31) return -1;
        *out=parameter; return 1;
    case EV_RELOAD:
    case EV_RELOAD_FROM_EMPTY:
    case EV_RELOAD_START:
    case EV_RECHAMBER_WEAPON:
        /* IW3 PM_AddEvent supplies zero. C1 emits zero at 419456
         * (reload/empty), 419623 (start), and 4190f9 (rechamber). */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_RELOAD_END:
        /* Native PM_Weapon tail-calls PM_AddEvent with event18.
         * C1 clears edx at41a48d and writes it as event21's parameter
         * at41a4f0; the other completion path writes literal zero41a670. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_RESET_ADS:
    case EV_RELOAD_START_NOTIFY:
        /* Retained PM_BeginWeaponReload emits native14/19 via PM_AddEvent.
         * C1 clears ecx at419574, then writes zero for ADS-reset17 at
         * 419598 and reload-start-notify22 at4195c5, with no intervening
         * call or ecx assignment on either path. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_RELOAD_ADDAMMO:
        /* Retained PM_ReloadClip emits PM_AddEvent(EV_RELOAD_ADDAMMO).
         * C1 PM_ReloadClip 41e5ba writes event23 and 41e5c5 writes zero
         * parameter (ebx cleared at41e5a1), regardless of selected hand.
         * Ammo amounts belong to the player-state arrays, not this event. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_NOAMMO:
    case EV_RAISE_WEAPON:
    case EV_FIRST_RAISE_WEAPON:
        /* Native PM_Weapon emits these with PM_AddEvent (zero parameter).
         * C1 no-ammo stores zero at419bce/41b742. Its common raise path
         * clears ecx at419efc and writes it to eventParms at419f10 before
         * selecting first-raise25 (419f1c) or ordinary-raise24 (419f3c).
         * Weapon identity is supplied separately by player-state fields. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_PUTAWAY_WEAPON:
    case EV_WEAPON_ALT:
        /* Retained PM_BeginWeaponChange emits native23/24 via PM_AddEvent.
         * C1 clears edi at41987a, then writes that zero parameter for
         * alternate27 at4198c0 or ordinary put-away26 at419903. The
         * preceding event28 carries the requested weapon separately;
         * its parameter must not be reused for these animation events. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_EJECT_BRASS:
    case CODOL_EV_EJECT_BRASS_SECONDARY:
        /* Retained PM_Weapon_ReloadDelayedAction emits native29 via
         * PM_AddEvent. C1 rechamber418fd3 and delayed-reload41a216 select
         * primary event35 (other hand38) then call40f360, whose parameter
         * store40f374 is always zero. Hand identity belongs to the event
         * ID and must not be encoded in this parameter. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_ITEM_PICKUP:
    case EV_AMMO_PICKUP:
        /* C1 Touch_Item52855e..52856c extracts item.index %700 into edi;
         * 528649..52864e passes it as G_AddEvent's parameter. The retained
         * Touch_Item_130 likewise carries its native weapon index. */
    case EV_PULLBACK_WEAPON:
    case CODOL_EV_WEAPON_SWITCH_STARTED:
    case EV_PREP_OFFHAND:
    case EV_USE_OFFHAND:
    case EV_SWITCH_OFFHAND:
    {
        /* C1 switch-start28 carries a weapon at 419888/41c239; the new
         * native event136 therefore needs the same asset-ID translation.
         * Native PM_Weapon publishes ps->weapon with event25. C1 loads
         * ps+33c at41b3ed and stores it as event29's parameter at41b401.
         * Offhand native32/33 carry ps.offHandIndex; native34 carries the
         * selected offhand. C1 prep loads328 at41c3b7 -> param41c497;
         * use loads328 at41c78b -> param41c794; switch selects weapon330/334
         * at41cb78/41cba2 -> param41cbfa, then stores328 at41cc13.
         * Its throwback path40 -> param41ca4d also stores328 at41ca6a.
         * Use the same mounted weapon-ID map as snapshots/user commands. */
        int weapon = CODOL_WeaponToWire(parameter);
        if(weapon < 0) return -1;
        *out=(uint32_t)weapon; return 1;
    }
    case EV_MELEE_SWIPE:
        /* Native PM_Weapon_2220 uses PM_AddEvent30. C1 melee-start
         * 41bd30 clears edi at41bf11; the animation-selection branches
         * retain that callee-saved zero through event47's store41c02c.
         * Melee timing and selected animation are separate state. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_FIRE_MELEE:
        /* Native PM_Weapon_2330 uses PM_AddEvent31. C1 melee-fire event48
         * writes literal zero at41bcfc; damage is a separate server action. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_FIRE_WEAPON:
    case EV_FIRE_WEAPON_LASTSHOT:
        /* Retained primary fire uses PM_AddEvent (zero parameter). C1's
         * fire producer 41b8b0 writes zero at 41b908; primary/last-shot
         * selection is carried by the event ID, not a weapon or hit ID. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_FIRE_WEAPON_MG42:
        /* Mounted-turret fire; C1 names this slot EV_FIRE_TURRET (55).
         * Unlike the hand-held fire events this one is an entity event and
         * it does carry a parameter: the firing entity's number. The
         * retained producer loads it as [ebx] - the first word of the
         * attacker gentity, i.e. attacker->s.number - at
         * turret_think_client_340 in _g_misc_mp.asm, and C1's own turret
         * shot builder loads the same word at 0x57af65 into the parameter
         * register before its inlined G_AddEvent writes event 0x37. The
         * wire field is 11 bits (codec -93), which is exactly
         * GENTITYNUM_BITS, so every legal entity number including
         * ENTITYNUM_NONE fits and nothing else is accepted. */
        if(parameter >= MAX_GENTITIES) return -1;
        *out=parameter; return 1;
    case EV_SOUND_ALIAS:
    case EV_SOUND_ALIAS_AS_MASTER:
        /* C1's play-sound-on-entity helper 0x5730c0 queues the event with
         * the registered sound-bank index as its parameter (0x573145 for a
         * player state, 0x573175 for an entity) and its duplicate scan
         * 0x57310f compares that same index. G_SoundAliasIndex truncates to
         * a byte, so 1..255 is the whole space; zero means no sound.
         * C1 has no native producer for the as-master event, whose index
         * meaning is taken from the retained producer pairing. */
        if(!parameter || parameter>255) return -1;
        *out=parameter; return 1;
    case EV_EARTHQUAKE:
    case EV_PHYS_EXPLOSION_SPHERE:
        /* C1 538a05/54556a keep eventParm zero; typed payload is es58..60. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_STOPSOUNDS:
        /* IW4 stopsounds 0x5ecbcf and C1 StopSounds 0x5361f9/0x53622d both
         * queue this event with a literal zero; the receiver stops every
         * sound it owns, so no index rides along. */
        if(parameter) return -1;
        *out=0; return 1;
    case CODOL_EV_DTP_LAND:
    case CODOL_EV_DTP_LAUNCH:
        /* C1 4089a0 remaps groundTrace.sflags through its 31-entry dive
         * material table; launch 409091 and land 408f92 publish 0..8. */
        if(parameter>8) return -1;
        *out=parameter; return 1;
    case CODOL_EV_MANTLE_START:
        /* C1 PM_StartMantle queues event183 with zero parameter. */
        if(parameter) return -1;
        *out=0; return 1;
    case CODOL_EV_STANCE_INVALID:
        /* C1 0x41463a: the stance reason enum, prone blocked. */
        if(parameter>3) return -1;
        *out=parameter; return 1;
    case CODOL_EV_SCOPE_ZOOM:
        /* C1 PM_UpdateVariableZoom 0x41853e stores a zero parameter. */
        if(parameter) return -1;
        *out=0; return 1;
    case CODOL_EV_OFFHAND_END_NOTIFY:
        /* C1 0x41c96a stores a zero parameter beside event 16. */
        if(parameter) return -1;
        *out=0; return 1;
    case EV_GRENADE_BOUNCE:
        /* Retained MissileImpact passes (surfaceFlags >> 20) & 31, the same
         * five surface bits the footstep events carry; CoDOL collision
         * materials keep their source surfaceFlags, so the value is unchanged.
         * C1's bounce (69) is the same lifecycle event (projectile_wire.md). */
        if(parameter > 31) return -1;
        *out=parameter; return 1;
    case EV_GRENADE_EXPLODE:
    case EV_ROCKET_EXPLODE:
    case EV_ROCKET_EXPLODE_NOMARKS:
    case EV_FLASHBANG_EXPLODE:
    case EV_CUSTOM_EXPLODE:
    case EV_CUSTOM_EXPLODE_NOMARKS:
    case EV_DUD_EXPLODE:
        /* Retained G_ExplodeMissile/MissileImpact pass DirToByte(dir), as
         * IW4's do; the byte is the explosion normal, not an asset index. */
        if(parameter > 255) return -1;
        *out=parameter; return 1;
    case EV_MELEE_HIT:
    case EV_MELEE_MISS:
    case EV_MELEE_BLOOD:
        /* Melee temp entities: the retained producer's parameter (surface or
         * direction byte) is passed through within the 11-bit field. */
        if(parameter > 2047) return -1;
        *out=parameter; return 1;
    case EV_BULLET_HIT:
    case EV_BULLET_HIT_CLIENT_SMALL:
    case EV_BULLET_HIT_CLIENT_LARGE:
        /* Bullet_ImpactEffect stores DirToByte(normal) in native eventParm
         * (+9c); surface type is a separate +84 word, alongside weapon+c4
         * and shooter+74. This parameter alone is not a complete impact
         * adapter. C1 packing and the other impact variants still need
         * verification before claiming full impact publication parity. */
        if(parameter > 2047) return -1;
        *out=parameter; return 1;
    case EV_STANCE_FORCE_STAND:
    case EV_STANCE_FORCE_CROUCH:
    case EV_STANCE_FORCE_PRONE:
        /* Retained PM_CheckDuck and C1 PM_UpdateStance (412954..412ed0):
         * 0=forced, 1=standing blocked, 2=crouching blocked, 3=prone blocked.
         * This is a reason enum, not an entity/weapon/sound index. */
        if(parameter>3) return -1;
        *out=parameter; return 1;
    default: return 0;
    }
}
int CODOL_ResolveEventParameters(const uint32_t events[4],const uint32_t parameters[4],uint32_t out[4])
{
    uint32_t result[4]; unsigned i;
    if(!events || !parameters || !out) return 0;
    for(i=0;i<4;++i)
        if(CODOL_EventParameterToWire(events[i],parameters[i],result+i)!=1) return 0;
    memcpy(out,result,sizeof(result)); return 1;
}
int CODOL_PlayerFireEventToWire(unsigned event,unsigned hand,unsigned last_shot)
{
    if(hand>1) return -1;
    switch(event) {
    case EV_FIRE_WEAPON:
    case EV_FIRE_WEAPON_LASTSHOT:
        return (int)((last_shot ? 44u : 43u) + 2u*hand);
    default: return CODOL_EventToWire(event);
    }
}
int CODOL_EventToWire(unsigned event)
{
    switch (event) {
#include "codol_event_map.inc"
    default: return -1;
    }
}
int CODOL_EntityTypeToWire(unsigned type)
{
    int event;
    /* Entity categories are native C1, including spawners and actors.
     * Event payload numbers still use their separately verified event map. */
    if (type < ET_EVENTS) return type;
    if (type > 255 || type == ET_MOVER) return -1;
    event = CODOL_EventToWire(type-ET_EVENTS);
    return event < 0 || event > 234 ? -1 : 21+event;
}
