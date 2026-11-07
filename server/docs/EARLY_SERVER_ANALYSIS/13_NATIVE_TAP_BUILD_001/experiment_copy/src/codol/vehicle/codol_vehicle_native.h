/* CoDOL native VehicleDef conversion: the serialized C1 type-41 definition
 * turned into the server's simulation representation.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_VEHICLE_NATIVE_H
#define CODOL_VEHICLE_NATIVE_H
#include "codol_assets.h"
/* server.h leaks a bare #pragma pack(1) into every translation unit that
 * includes it, so a CoDOL header whose structs are not wrapped gets a
 * different layout in those units than in the ones that define them. Wrap
 * the whole header, as codol_actors.h does. Verified with
 * obj/claude-workers/packcheck.py. */
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* Sound slots in codol_mounted_vehicle_t.sounds, which the archive loader
 * fills in C1 loader order (codol_asset_registry.c CODOL_LoadMountedVehicle:
 * header 0x1ac/0x1b0, then the fourteen sparse fields 0x1e0,0x1e4,0x1e8,0x1ec,
 * 0x1f4,0x1fc,0x200,0x204,0x208,0x210,0x218,0x220,0x228,0x230, then the
 * thirty-one contiguous slots at 0x23c). The names below are the measured
 * field identities of those offsets, not an assumed ordering: see the
 * evidence block in codol_vehicle_native.cpp. */
enum {
    CODOL_VEH_SND_TURRET_SPIN = 0,
    CODOL_VEH_SND_TURRET_STOP = 1,
    CODOL_VEH_SND_IDLE_LOW = 2,
    CODOL_VEH_SND_IDLE_HIGH = 3,
    CODOL_VEH_SND_ENGINE_LOW = 4,
    CODOL_VEH_SND_ENGINE_HIGH = 5,
    CODOL_VEH_SND_ENGINE_STARTUP = 6,
    CODOL_VEH_SND_ENGINE_SHUTDOWN = 7,
    CODOL_VEH_SND_ENGINE_IDLE = 8,
    CODOL_VEH_SND_ENGINE_SUSTAIN = 9,
    CODOL_VEH_SND_ENGINE_RAMP_UP = 10,
    CODOL_VEH_SND_ENGINE_RAMP_DOWN = 11,
    CODOL_VEH_SND_SUSPENSION_SOFT = 12,
    CODOL_VEH_SND_SUSPENSION_HARD = 13,
    CODOL_VEH_SND_COLLISION = 14,
    CODOL_VEH_SND_SPEED = 15,
    CODOL_VEH_SND_SURFACE_FIRST = 16,
    CODOL_VEH_SND_SURFACE_COUNT = 31,
    CODOL_VEH_SND_COUNT = 47
};
/* The six retained sndNames[] slots of vehicle_info_t, in record order
 * (_g_vehicles_mp.asm s_vehicleFields: lowIdleSnd, highIdleSnd, lowEngineSnd,
 * highEngineSnd, turretSpinSnd, turretStopSnd at 0xe4 + 0x40*i). */
enum {
    CODOL_VEH_RETAINED_SND_COUNT = 6
};
/* C1 keeps 0x4c bytes at 0x2c8..0x313. They are retained verbatim even
 * where a named attribute is also decoded. Consumers exist in C1
 * (0x4717ff reads +0x2f8, 0x471dcb reads +0x2d0/+0x2d4/+0x2d8) but their
 * field identities there are not measured. Header+2c8 is independently
 * identified as remote_control by the vehicle enter/exit branches below. */
enum { CODOL_VEH_EXTENSION_DWORDS = 19 };

typedef struct {
    char name[64];
    /* Raw serialized VehicleType and the retained enum it maps onto.
     * retained_type is -1 when the source value has no retained equivalent. */
    int type;
    int retained_type;
    /* C1 679bf6/679d87 and 67a15d gate remote vehicle enter/exit on
     * VehicleDef+2c8; remote drivers keep their body unlinked. */
    int remote_control;
    char use_hint_string[64];
    int health;
    int quad_barrel;
    int player_protected;
    float tex_scroll_scale;
    /* Already inches/sec in the asset: the linker converts mph at build time
     * (CSPFT_MPH_TO_INCHES_PER_SEC), unlike the retained text loader which
     * multiplies by 17.6 after parsing. */
    float top_speed;
    float accel;
    float rot_rate;
    float rot_accel;
    float max_body_pitch;
    float max_body_roll;
    float fake_body_accel_pitch, fake_body_accel_roll;
    float fake_body_vel_pitch, fake_body_vel_roll, fake_body_side_vel_pitch;
    float fake_body_pitch_strength, fake_body_roll_strength;
    float fake_body_pitch_dampening, fake_body_roll_dampening;
    float boat_rocking_amplitude, boat_rocking_period;
    float boat_rocking_rotation_period, boat_rocking_fadeout_speed;
    float boat_bouncing_min_force, boat_bouncing_max_force, boat_bouncing_rate;
    float boat_bouncing_fadein_speed, boat_bouncing_fadeout_steering_angle;
    float collision_damage;
    float collision_speed;
    float killcam_offset[3];
    int bullet_damage, armor_piercing_damage, grenade_damage;
    int projectile_damage, projectile_splash_damage, heavy_explosive_damage;
    /* Physics block. physics_preset carries the name of the resolved type-0
     * dependency at header 0xb0 when present; physics_preset_name is the
     * serialized name field at 0xac and physics_profile the 0xb4 string. */
    int physics_enabled;
    char physics_preset[64];
    char physics_preset_name[64];
    char physics_profile[64];
    int physics_preset_resolved;
    /* Turret. turret_weapon is the resolved type-28 dependency name when the
     * definition carries one, otherwise the serialized 0x190 name string. */
    char turret_weapon[64];
    int turret_weapon_resolved;
    int turret_weapon_index;
    float turret_horiz_span_left, turret_horiz_span_right;
    float turret_vert_span_up, turret_vert_span_down;
    float turret_rot_rate;
    /* Sound scalars that sit in the gaps of the sparse sound stream. */
    float engine_snd_speed;
    int engine_startup_length, engine_ramp_up_length, engine_ramp_down_length;
    float suspension_soft_compression, suspension_hard_compression;
    float collision_blend_speed, speed_snd_blend_speed;
    float surface_snd_blend_speed, slide_volume, slide_blend_speed, in_air_pitch;
    char surface_snd_prefix[64];
    char compass_icon[2][64];
    char sounds[CODOL_VEH_SND_COUNT][64];
    unsigned char retained_sound_index[CODOL_VEH_RETAINED_SND_COUNT];
    uint32_t extension[CODOL_VEH_EXTENSION_DWORDS];
    /* Independently measured at C1 header+160 by the suspension producer
     * and wheel trace consumer, despite the surrounding unresolved layout. */
    int suspension_travel_known;
    float suspension_travel;
} codol_vehicle_native_t;

/* Pure conversion of an archive view produced by CODOL_LoadMountedVehicle.
 * Copies every string it keeps, so the result outlives the archive. Performs
 * no engine calls and registers nothing. Returns 1, or -1 on a malformed
 * source (short header, missing name, or a string that cannot fit the native
 * representation). References are never silently truncated. Output is
 * untouched on failure. */
int CODOL_ConvertMountedVehicle(const codol_mounted_vehicle_t *source,
                                codol_vehicle_native_t *out);
/* Load the named VehicleDef from the mounted archives and convert it. Only
 * when type41 is absent, load the shipped vehicles/<name> VEHICLEFILE rawfile.
 * 1 = converted, 0 = no such asset, -1 = present but unusable. */
int CODOL_LoadNativeVehicleDefinition(const char *name,
                                      codol_vehicle_native_t *out);
/* Install a converted definition as a retained simulation record
 * (s_vehicleInfos), registering its turret weapon and resolving its six
 * retained sound aliases. Returns the record index, or -1 when no VehicleDef
 * asset exists, the conversion failed, or the retained table is full. An
 * already-installed definition returns its existing record. */
int CODOL_InstallNativeVehicleRecord(const char *name);
/* Converted definition bound to a retained record index, or NULL. This is the
 * query seam for every attribute the retained vehicle_info_t cannot hold
 * (health, physics preset/profile, all 47 sounds, compass materials, the C1
 * extension block). */
const codol_vehicle_native_t *CODOL_NativeVehicleDefinition(int info_index);
/* Turret weapon index registered while installing the record, or 0. */
int CODOL_NativeVehicleTurretWeapon(int info_index);
/* Per-map lifecycle: drops every installed definition and frees owned raw
 * ground settings. Call wherever
 * s_numVehicleInfos is cleared (G_VehiclesInit) or vehicle slots are reset. */
void CODOL_ResetNativeVehicles(void);
struct gentity_s;
/* Successful native spawn producer; records the actual instance/definition
 * pair in the entity extension before snapshots can copy the entity. */
void CODOL_CaptureSpawnedVehicle(struct gentity_s *entity);
/* Helicopter spawn has an explicit player owner; ordinary vehicle spawn
 * records zero, matching C1's absent-owner initialization. */
void CODOL_CaptureVehicleSpawnClient(struct gentity_s *entity, const struct gentity_s *owner);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
