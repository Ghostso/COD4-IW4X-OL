/* CoDOL native VehicleDef conversion and installation.
 *
 * Source: CODOL_LoadMountedVehicle (codol_asset_registry.c), which walks the
 * complete serialized C1 type-41 asset: a 0x314-byte header followed by the
 * dependency stream, with strings at header 0/8/0xac, the physics preset at
 * 0xb0 and its profile string at 0xb4, a string at 0x190 and a type-28 weapon
 * at 0x194, two sounds at 0x1ac/0x1b0, two materials at 0x1d0/0x1d4, fourteen
 * sparse sounds (0x1e0,0x1e4,0x1e8,0x1ec,0x1f4,0x1fc,0x200,0x204,0x208,0x210,
 * 0x218,0x220,0x228,0x230), a string at 0x238 and thirty-one sounds at 0x23c.
 *
 * Field identities. The serialized header is the IW4 VehicleDef layout with
 * an eight-byte difference inside 0xb8..0x18f and 0x4c bytes appended past
 * IW4's end, which is why offsets are taken from the C1 asset and only the
 * regions corroborated below are converted:
 *   - 0x0 name and 0x8 useHintString: the loader's first two strings, and the
 *     IW4 header's first string pair (name, type, useHintString).
 *   - 0x80/0x84/0x88 killcamOffset: C1 0x46c158..0x46c176 loads exactly these
 *     three consecutive floats into three consecutive client globals
 *     (0xc8ba4/0xc8ba8/0xc8bac).
 *   - 0xa8..0xb4: physicsEnabled, physPresetName, physPreset, accelGraphName.
 *     The loader resolves an asset at 0xb0 whose name is the string at 0xac
 *     and a further string at 0xb4, which is the IW4 VehiclePhysDef prologue.
 *   - 0x190/0x194: a string immediately followed by a type-28 weapon asset,
 *     the IW4 turretWeaponName/turretWeapon pair; 0x198..0x1a8 are then the
 *     five turret span/rate floats and 0x1ac/0x1b0 the turret spin/stop
 *     sounds, which is exactly the sound pair the loader reads there.
 *   - 0x1d0/0x1d4: the two Material dependencies, IW4's compassFriendlyIcon
 *     and compassEnemyIcon (IW5 has four; C1 has two, like IW4).
 *   - 0x1e0.. : the sparse sound stream reproduces the IW4 sound/scalar
 *     interleave exactly. Every gap in the loader's offset list is an IW4
 *     scalar: 0x1f0 engineSndSpeed, 0x1f8 engineStartUpLength, 0x20c/0x214
 *     the ramp lengths, 0x21c/0x224 the suspension compressions, 0x22c
 *     collisionBlendSpeed, 0x234 speedSndBlendSpeed. C1 corroborates two of
 *     the sound slots directly: 0x67c9d5..0x67c9e5 selects +0x218 for event
 *     0x72 and +0x220 for event 0x73, the two EV_VEHICLE_SUSPENSION_* events.
 *   - 0x238 surfaceSndPrefix and 0x23c surfaceSnds[31], ending at 0x2b8;
 *     0x2b8/0x2bc/0x2c0/0x2c4 are then surfaceSndBlendSpeed, slideVolume,
 *     slideBlendSpeed and inAirPitch, the last four IW4 fields.
 *   - 0x2c8..0x313 is C1-only. It is retained verbatim (extension[]); C1 uses
 *     +0x2d0/+0x2d4/+0x2d8 (0x471dcb) and +0x2f8 (0x4717ff) as floats, but
 *     their identities are not measured and nothing is guessed for them.
 * The eight-byte difference lies between 0xb4 and 0x190, i.e. inside the
 * physics/boost/camera block. Only suspensionTravel at0x160 is converted
 * within that interval, based on the independent producer/consumer trace
 * recorded below; the remaining fields still need measured identities.
 *
 * Units. The asset stores speeds in inches/sec: the linker field types are
 * CSPFT_MPH_TO_INCHES_PER_SEC for topSpeed, accel and collisionSpeed, and the
 * retained text loader's own 17.6 multiply (_g_vehicles_mp.asm G_LoadVehicle,
 * on +0x6c/+0x70/+0x88/+0x26c) is that same conversion applied to mph text.
 * Converted values are therefore copied without scaling.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_vehicle_native.h"
#include "codol_vehicle_ground_runtime.h"
#include "codol_vehicle_raw.h"
#include "codol_vehicle_ground_binary.h"
#include "codol_vehicle_graph.h"
#include <memory>
#include <new>
#include "codol_vehicle_assets.h"
#include "codol_entitystate_ext.h"
#include "scr_vm_functions.h"
#include "g_scr_vehicle.h"
#include "g_shared.h"
#include "qcommon_io.h"
#include <stddef.h>
#include <string.h>

extern "C" int __cdecl G_SoundAliasIndex(const char *name);
extern "C" short s_numVehicleInfos;
extern "C" scr_vehicle_s s_vehicles[8];
static_assert(sizeof(scr_vehicle_s) == 0x354, "native vehicle instance stride changed");
static_assert(offsetof(scr_vehicle_s, entNum) == 0x1b8, "native vehicle entity moved");
static_assert(offsetof(scr_vehicle_s, infoIdx) == 0x1bc, "native vehicle definition moved");

/* The retained pool is a fixed 32 records of 0x270 bytes; G_LoadVehicle
 * appends at s_numVehicleInfos without bounding it, so installation bounds it
 * here instead. */
static const int retained_capacity = 32;
static_assert(sizeof(vehicle_info_t) == 0x270, "retained vehicle record stride changed");
static_assert(offsetof(vehicle_info_t, turretWeapon) == 0x90, "retained turret weapon moved");
static_assert(offsetof(vehicle_info_t, sndNames) == 0xe4, "retained sound names moved");
static_assert(offsetof(vehicle_info_t, sndIndices) == 0x264, "retained sound indices moved");
static_assert(offsetof(vehicle_info_t, engineSndSpeed) == 0x26c, "retained engine sound speed moved");

/* Serialized header offsets (see the evidence block above). */
#define VEH_H_TYPE 0x4
#define VEH_H_HEALTH 0xc
#define VEH_H_QUAD_BARREL 0x10
#define VEH_H_TEX_SCROLL_SCALE 0x14
#define VEH_H_TOP_SPEED 0x18
#define VEH_H_ACCEL 0x1c
#define VEH_H_ROT_RATE 0x20
#define VEH_H_ROT_ACCEL 0x24
#define VEH_H_MAX_BODY_PITCH 0x28
#define VEH_H_MAX_BODY_ROLL 0x2c
#define VEH_H_FAKE_BODY 0x30      /* nine floats */
#define VEH_H_BOAT_ROCKING 0x54   /* four floats */
#define VEH_H_BOAT_BOUNCING 0x64  /* five floats */
#define VEH_H_COLLISION_DAMAGE 0x78
#define VEH_H_COLLISION_SPEED 0x7c
#define VEH_H_KILLCAM_OFFSET 0x80
#define VEH_H_PLAYER_PROTECTED 0x8c
#define VEH_H_DAMAGE 0x90         /* six ints */
#define VEH_H_PHYSICS_ENABLED 0xa8
#define VEH_H_SUSPENSION_TRAVEL 0x160
#define VEH_H_TURRET_SPANS 0x198  /* four floats, then the rate */
#define VEH_H_TURRET_ROT_RATE 0x1a8
#define VEH_H_ENGINE_SND_SPEED 0x1f0
#define VEH_H_ENGINE_STARTUP_LENGTH 0x1f8
#define VEH_H_ENGINE_RAMP_UP_LENGTH 0x20c
#define VEH_H_ENGINE_RAMP_DOWN_LENGTH 0x214
#define VEH_H_SUSPENSION_SOFT_COMPRESSION 0x21c
#define VEH_H_SUSPENSION_HARD_COMPRESSION 0x224
#define VEH_H_COLLISION_BLEND_SPEED 0x22c
#define VEH_H_SPEED_SND_BLEND_SPEED 0x234
#define VEH_H_SURFACE_SND_BLEND_SPEED 0x2b8
#define VEH_H_SLIDE_VOLUME 0x2bc
#define VEH_H_SLIDE_BLEND_SPEED 0x2c0
#define VEH_H_IN_AIR_PITCH 0x2c4
#define VEH_H_EXTENSION 0x2c8
#define VEH_H_SIZE 0x314

/* Retained VehicleType order, _g_vehicles_mp.asm s_vehicleTypeNames:
 * "4 wheel", "tank", "plane", "boat", "artillery", "helicopter" (six names,
 * VEH_ParseSpecificField stores the index as a word at record+0x40). The
 * serialized enum shares that order and continues past it, so values above
 * the retained range have no retained equivalent and are not substituted. */
static const int retained_type_count = 6;

static uint32_t read_u32(const uint8_t *header, unsigned offset)
{
    const uint8_t *p = header + offset;
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}
static int read_i32(const uint8_t *header, unsigned offset)
{
    return (int)read_u32(header, offset);
}
static float read_f32(const uint8_t *header, unsigned offset)
{
    uint32_t bits = read_u32(header, offset);
    float value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}
static int copy_name(char *destination, size_t capacity, const char *source)
{
    if (!source) { destination[0] = 0; return 1; }
    const size_t length = strlen(source);
    if (length >= capacity) return 0;
    memcpy(destination, source, length + 1);
    return 1;
}

int CODOL_ConvertMountedVehicle(const codol_mounted_vehicle_t *source,
                                codol_vehicle_native_t *out)
{
    codol_vehicle_native_t result;
    const uint8_t *header;
    unsigned i;
    if (!source || !out || !source->asset.data || source->asset.size < VEH_H_SIZE) return -1;
    if (!source->name || !*source->name) return -1;
    memset(&result, 0, sizeof(result));
    header = source->asset.data;
    if (!copy_name(result.name, sizeof(result.name), source->name)) return -1;
    result.type = read_i32(header, VEH_H_TYPE);
    result.retained_type = result.type >= 0 && result.type < retained_type_count ?
        result.type : -1;
    if (!copy_name(result.use_hint_string, sizeof(result.use_hint_string),
        source->prefix_strings[0])) return -1;
    result.health = read_i32(header, VEH_H_HEALTH);
    result.quad_barrel = read_i32(header, VEH_H_QUAD_BARREL);
    result.player_protected = read_i32(header, VEH_H_PLAYER_PROTECTED);
    result.tex_scroll_scale = read_f32(header, VEH_H_TEX_SCROLL_SCALE);
    result.top_speed = read_f32(header, VEH_H_TOP_SPEED);
    result.accel = read_f32(header, VEH_H_ACCEL);
    result.rot_rate = read_f32(header, VEH_H_ROT_RATE);
    result.rot_accel = read_f32(header, VEH_H_ROT_ACCEL);
    result.max_body_pitch = read_f32(header, VEH_H_MAX_BODY_PITCH);
    result.max_body_roll = read_f32(header, VEH_H_MAX_BODY_ROLL);
    result.fake_body_accel_pitch = read_f32(header, VEH_H_FAKE_BODY);
    result.fake_body_accel_roll = read_f32(header, VEH_H_FAKE_BODY + 4);
    result.fake_body_vel_pitch = read_f32(header, VEH_H_FAKE_BODY + 8);
    result.fake_body_vel_roll = read_f32(header, VEH_H_FAKE_BODY + 0xc);
    result.fake_body_side_vel_pitch = read_f32(header, VEH_H_FAKE_BODY + 0x10);
    result.fake_body_pitch_strength = read_f32(header, VEH_H_FAKE_BODY + 0x14);
    result.fake_body_roll_strength = read_f32(header, VEH_H_FAKE_BODY + 0x18);
    result.fake_body_pitch_dampening = read_f32(header, VEH_H_FAKE_BODY + 0x1c);
    result.fake_body_roll_dampening = read_f32(header, VEH_H_FAKE_BODY + 0x20);
    result.boat_rocking_amplitude = read_f32(header, VEH_H_BOAT_ROCKING);
    result.boat_rocking_period = read_f32(header, VEH_H_BOAT_ROCKING + 4);
    result.boat_rocking_rotation_period = read_f32(header, VEH_H_BOAT_ROCKING + 8);
    result.boat_rocking_fadeout_speed = read_f32(header, VEH_H_BOAT_ROCKING + 0xc);
    result.boat_bouncing_min_force = read_f32(header, VEH_H_BOAT_BOUNCING);
    result.boat_bouncing_max_force = read_f32(header, VEH_H_BOAT_BOUNCING + 4);
    result.boat_bouncing_rate = read_f32(header, VEH_H_BOAT_BOUNCING + 8);
    result.boat_bouncing_fadein_speed = read_f32(header, VEH_H_BOAT_BOUNCING + 0xc);
    result.boat_bouncing_fadeout_steering_angle =
        read_f32(header, VEH_H_BOAT_BOUNCING + 0x10);
    result.collision_damage = read_f32(header, VEH_H_COLLISION_DAMAGE);
    result.collision_speed = read_f32(header, VEH_H_COLLISION_SPEED);
    for (i = 0; i < 3; ++i)
        result.killcam_offset[i] = read_f32(header, VEH_H_KILLCAM_OFFSET + 4 * i);
    result.bullet_damage = read_i32(header, VEH_H_DAMAGE);
    result.armor_piercing_damage = read_i32(header, VEH_H_DAMAGE + 4);
    result.grenade_damage = read_i32(header, VEH_H_DAMAGE + 8);
    result.projectile_damage = read_i32(header, VEH_H_DAMAGE + 0xc);
    result.projectile_splash_damage = read_i32(header, VEH_H_DAMAGE + 0x10);
    result.heavy_explosive_damage = read_i32(header, VEH_H_DAMAGE + 0x14);
    result.physics_enabled = read_i32(header, VEH_H_PHYSICS_ENABLED);
    /* C1 67b3a4..67b3b8 publishes this value *1000 to entity+7c;
     * 67d703..67d73f uses the decoded distance for wheel suspension traces.
     * Retained G_VehEntHandler_Think_200 publishes the named suspensionTravel
     * field in exactly those units. This offset is independently measured,
     * not inferred from the unresolved physics-block layout. */
    result.suspension_travel = read_f32(header, VEH_H_SUSPENSION_TRAVEL);
    result.suspension_travel_known = 1;
    if (!copy_name(result.physics_preset_name, sizeof(result.physics_preset_name),
        source->prefix_strings[1])) return -1;
    if (!copy_name(result.physics_preset, sizeof(result.physics_preset),
        source->physics_preset_name)) return -1;
    if (!copy_name(result.physics_profile, sizeof(result.physics_profile),
        source->physics_profile)) return -1;
    result.physics_preset_resolved = result.physics_preset[0] != 0;
    /* IW4 674bd2 registers the definition's own turret weapon at precache
     * time. Prefer the resolved type-28 dependency: an overridden or renamed
     * nested weapon is the definition the archive actually carries, and the
     * 0x190 string is only its serialized request. */
    if (source->weapon_name && *source->weapon_name) {
        if (!copy_name(result.turret_weapon, sizeof(result.turret_weapon), source->weapon_name)) return -1;
        result.turret_weapon_resolved = 1;
    } else {
        if (!copy_name(result.turret_weapon, sizeof(result.turret_weapon), source->string190)) return -1;
    }
    result.turret_horiz_span_left = read_f32(header, VEH_H_TURRET_SPANS);
    result.turret_horiz_span_right = read_f32(header, VEH_H_TURRET_SPANS + 4);
    result.turret_vert_span_up = read_f32(header, VEH_H_TURRET_SPANS + 8);
    result.turret_vert_span_down = read_f32(header, VEH_H_TURRET_SPANS + 0xc);
    result.turret_rot_rate = read_f32(header, VEH_H_TURRET_ROT_RATE);
    result.engine_snd_speed = read_f32(header, VEH_H_ENGINE_SND_SPEED);
    result.engine_startup_length = read_i32(header, VEH_H_ENGINE_STARTUP_LENGTH);
    result.engine_ramp_up_length = read_i32(header, VEH_H_ENGINE_RAMP_UP_LENGTH);
    result.engine_ramp_down_length = read_i32(header, VEH_H_ENGINE_RAMP_DOWN_LENGTH);
    result.suspension_soft_compression =
        read_f32(header, VEH_H_SUSPENSION_SOFT_COMPRESSION);
    result.suspension_hard_compression =
        read_f32(header, VEH_H_SUSPENSION_HARD_COMPRESSION);
    result.collision_blend_speed = read_f32(header, VEH_H_COLLISION_BLEND_SPEED);
    result.speed_snd_blend_speed = read_f32(header, VEH_H_SPEED_SND_BLEND_SPEED);
    result.surface_snd_blend_speed = read_f32(header, VEH_H_SURFACE_SND_BLEND_SPEED);
    result.slide_volume = read_f32(header, VEH_H_SLIDE_VOLUME);
    result.slide_blend_speed = read_f32(header, VEH_H_SLIDE_BLEND_SPEED);
    result.in_air_pitch = read_f32(header, VEH_H_IN_AIR_PITCH);
    if (!copy_name(result.surface_snd_prefix, sizeof(result.surface_snd_prefix),
        source->string238)) return -1;
    for (i = 0; i < 2; ++i)
        if (!copy_name(result.compass_icon[i], sizeof(result.compass_icon[i]),
            source->material_names[i])) return -1;
    for (i = 0; i < CODOL_VEH_SND_COUNT; ++i)
        if (!copy_name(result.sounds[i], sizeof(result.sounds[i]), source->sounds[i])) return -1;
    for (i = 0; i < CODOL_VEH_EXTENSION_DWORDS; ++i)
        result.extension[i] = read_u32(header, VEH_H_EXTENSION + 4 * i);
    result.remote_control = result.extension[0] != 0;
    *out = result;
    return 1;
}

static int load_native_definition(const char *name, codol_vehicle_native_t *out,
                                 std::unique_ptr<codol_vehicle_raw_t> &raw)
{
    codol_mounted_vehicle_t mounted;
    int status;
    if (!name || !*name || !out) return -1;
    memset(&mounted, 0, sizeof(mounted));
    status = CODOL_LoadMountedVehicle(name, &mounted);
    if (status == 1) {
        status=CODOL_ConvertMountedVehicle(&mounted,out);
        if(status!=1)return status;
        if(out->type==0 && out->physics_enabled) {
            raw.reset(new (std::nothrow) codol_vehicle_raw_t);
            if(!raw)return -1;
            if(CODOL_DecodeGroundVehicleSettings(mounted.asset.data,mounted.asset.size,
                                                out,raw.get())!=1) {
                raw.reset();
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "VehicleDef '%s' has invalid C1 ground physics settings\n",name);
                return -1;
            }
        }
        return 1;
    }
    /* A malformed mounted VehicleDef must not be hidden by a text asset. */
    if (status != 0) return status;
    raw.reset(new (std::nothrow) codol_vehicle_raw_t);
    if (!raw) return -1;
    status = CODOL_LoadGroundVehicleFile(name, raw.get());
    if (status == 1) *out = raw->common;
    else raw.reset();
    return status;
}
int CODOL_LoadNativeVehicleDefinition(const char *name, codol_vehicle_native_t *out)
{
    std::unique_ptr<codol_vehicle_raw_t> raw;
    return load_native_definition(name, out, raw);
}

/* Installed definitions, indexed by retained record. A record only stays
 * bound while the retained pool still holds the same name: G_VehiclesInit(0)
 * clears s_numVehicleInfos per map, so a missed reset invalidates the binding
 * instead of aliasing another map's record. */
typedef struct {
    int used;
    int turret_weapon;
    codol_vehicle_raw_t *raw;
    int acceleration_known;
    codol_vehicle_acceleration_t acceleration;
    codol_vehicle_native_t definition;
} installed_vehicle_t;
static installed_vehicle_t installed[retained_capacity];

void CODOL_ResetNativeVehicles(void)
{
    CODOL_ResetGroundVehicleRuntime();
    for (int i = 0; i < retained_capacity; ++i) delete installed[i].raw;
    memset(installed, 0, sizeof(installed));
}
void CODOL_CaptureSpawnedVehicle(gentity_s *entity)
{
    if (!entity) return;
    entity->s.clientNum = 0;
    CODOL_EntityStateVehicleCaptured(&entity->s, 0, 0, 0);
    const uintptr_t base = (uintptr_t)s_vehicles;
    const uintptr_t address = (uintptr_t)entity->scr_vehicle;
    if (address < base || address - base >= sizeof(s_vehicles) ||
        (address - base) % sizeof(scr_vehicle_s) ||
        entity->scr_vehicle->entNum != entity->s.number ||
        (entity->s.eType != ET_HELICOPTER && entity->s.eType != ET_VEHICLE)) {
        Com_Error(ERR_DROP, "Invalid native vehicle instance at spawn");
        return;
    }
    const int slot = CODOL_BindVehicleInfoIndex(entity->scr_vehicle->infoIdx);
    if (slot <= 0) {
        Com_Error(ERR_DROP, "Unresolved native vehicle definition at spawn");
        return;
    }
    /* C1 spawn67a656..67a6bd packs slot<<4 | instance. The retained eight
     * fixed instances fit the C1 low-four-bit instance namespace. Capture
     * here, never reconstruct from live scr_vehicle state during a rewind. */
    CODOL_EntityStateVehicleCaptured(&entity->s,
        (unsigned)((address - base) / sizeof(scr_vehicle_s)), (unsigned)slot, 1);
    /* SpawnVehicle calls this after model/DObj and wheel tags exist. */
    if(CODOL_AttachSpawnedRCVehicle(entity)<0)
        Com_Error(ERR_DROP,"RC physics construction failed: check actual model wheel tags, preset, travel and sh1x tuning");
}
void CODOL_CaptureVehicleSpawnClient(gentity_s *entity, const gentity_s *owner)
{
    if (!entity) return;
    /* C1 67a6df..67a6ff copies the optional spawning player's ps.clientNum
     * to entity+74. Native helicopter code packs it into lerp.vehicle.team
     * alongside team bits; retain it independently for the CoDOL writer. */
    entity->s.clientNum = owner && owner->client ? owner->client->ps.clientNum : 0;
}
static int record_live(int info_index)
{
    if (info_index < 0 || info_index >= retained_capacity) return 0;
    if (info_index >= s_numVehicleInfos) return 0;
    if (!installed[info_index].used) return 0;
    return !Q_stricmp(s_vehicleInfos[info_index].name,
        installed[info_index].definition.name);
}
const codol_vehicle_native_t *CODOL_NativeVehicleDefinition(int info_index)
{
    return record_live(info_index) ? &installed[info_index].definition : NULL;
}
const codol_vehicle_raw_t *CODOL_NativeGroundVehicleDefinition(int info_index)
{
    return record_live(info_index) ? installed[info_index].raw : NULL;
}
const codol_vehicle_acceleration_t *CODOL_NativeVehicleAcceleration(int info_index)
{
    return record_live(info_index) && installed[info_index].acceleration_known ?
        &installed[info_index].acceleration : NULL;
}
int CODOL_NativeVehicleTurretWeapon(int info_index)
{
    return record_live(info_index) ? installed[info_index].turret_weapon : 0;
}

/* Fill the retained simulation record. Everything the retained layout can
 * hold is written; the two IW3-only booleans (steerWheels at 0x44, texScroll
 * at 0x48) have no converted source and stay
 * zeroed rather than receiving an invented value. */
static void apply_retained(const codol_vehicle_native_t *definition,
                           vehicle_info_t *info)
{
    static const int retained_sound[CODOL_VEH_RETAINED_SND_COUNT] = {
        CODOL_VEH_SND_IDLE_LOW, CODOL_VEH_SND_IDLE_HIGH,
        CODOL_VEH_SND_ENGINE_LOW, CODOL_VEH_SND_ENGINE_HIGH,
        CODOL_VEH_SND_TURRET_SPIN, CODOL_VEH_SND_TURRET_STOP
    };
    int i;
    memset(info, 0, sizeof(*info));
    copy_name(info->name, sizeof(info->name), definition->name);
    info->type = (uint16_t)definition->retained_type;
    info->quadBarrel = definition->quad_barrel;
    info->bulletDamage = definition->bullet_damage;
    info->armorPiercingDamage = definition->armor_piercing_damage;
    info->grenadeDamage = definition->grenade_damage;
    info->projectileDamage = definition->projectile_damage;
    info->projectileSplashDamage = definition->projectile_splash_damage;
    info->heavyExplosiveDamage = definition->heavy_explosive_damage;
    info->texScrollScale = definition->tex_scroll_scale;
    info->maxSpeed = definition->top_speed;
    info->accel = definition->accel;
    info->rotRate = definition->rot_rate;
    info->rotAccel = definition->rot_accel;
    info->maxBodyPitch = definition->max_body_pitch;
    info->maxBodyRoll = definition->max_body_roll;
    info->collisionDamage = definition->collision_damage;
    info->collisionSpeed = definition->collision_speed;
    info->suspensionTravel = definition->suspension_travel;
    copy_name(info->turretWeapon, sizeof(info->turretWeapon), definition->turret_weapon);
    info->turretHorizSpanLeft = definition->turret_horiz_span_left;
    info->turretHorizSpanRight = definition->turret_horiz_span_right;
    info->turretVertSpanUp = definition->turret_vert_span_up;
    info->turretVertSpanDown = definition->turret_vert_span_down;
    info->turretRotRate = definition->turret_rot_rate;
    info->engineSndSpeed = definition->engine_snd_speed;
    for (i = 0; i < CODOL_VEH_RETAINED_SND_COUNT; ++i)
        copy_name(info->sndNames[i], sizeof(info->sndNames[i]),
            definition->sounds[retained_sound[i]]);
}
static int find_retained(const char *name)
{
    int index;
    for (index = 0; index < retained_capacity && index < s_numVehicleInfos; ++index)
        if (!Q_stricmp(s_vehicleInfos[index].name, name)) return index;
    return -1;
}
int CODOL_InstallNativeVehicleRecord(const char *name)
{
    std::unique_ptr<codol_vehicle_raw_t> raw;
    codol_vehicle_native_t definition;
    vehicle_info_t staged_info;
    codol_vehicle_acceleration_t acceleration={};
    int acceleration_known=0;
    vehicle_info_t *info = &staged_info;
    int index, i, status;
    if (!name || !*name) return -1;
    index = find_retained(name);
    if (index >= 0 && record_live(index)) return index;
    status = load_native_definition(name, &definition, raw);
    if (status != 1) {
        if (status < 0)
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "VehicleDef '%s' is present but could not be converted\n", name);
        return -1;
    }
    /* Preserve the converted source, but do not install an unrelated
     * simulation type. Additional C1 types need native movement consumers. */
    if (definition.retained_type < 0) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "VehicleDef '%s' type %d has no native simulation implementation\n",
            name, definition.type);
        return -1;
    }
    if (index < 0) {
        if (s_numVehicleInfos < 0 || s_numVehicleInfos >= retained_capacity) {
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "Vehicle definition records are full, cannot install '%s'\n", name);
            return -1;
        }
        index = s_numVehicleInfos;
    }
    /* Build locally. A failed sound/weapon registration must not overwrite
     * a live record or make a partly installed definition visible. */
    apply_retained(&definition, info);
    /* Resolve the six retained aliases exactly where G_LoadVehicle does:
     * a populated name becomes a sound-alias index byte, an empty slot stays
     * zero (_g_vehicles_mp.asm G_LoadVehicle_20/_40). */
    for (i = 0; i < CODOL_VEH_RETAINED_SND_COUNT; ++i) {
        int resolved = 0;
        if (info->sndNames[i][0]) {
            resolved = G_SoundAliasIndex(info->sndNames[i]);
            if (resolved <= 0 || resolved > 255) {
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "VehicleDef '%s' sound '%s' could not be registered\n",
                    name, info->sndNames[i]);
                return -1;
            }
        }
        info->sndIndices[i] = (char)resolved;
        definition.retained_sound_index[i] = resolved;
    }
    /* IW4 674bd2..674be7 registers the turret weapon while the definition is
     * loaded, so its configstring exists before any vehicle uses it. */
    definition.turret_weapon_index = definition.turret_weapon[0] ?
        G_GetWeaponIndexForName(definition.turret_weapon) : 0;
    if (definition.turret_weapon[0] && definition.turret_weapon_index <= 0) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "VehicleDef '%s' weapon '%s' could not be registered\n",
            name, definition.turret_weapon);
        return -1;
    }
    if(raw && definition.physics_enabled) {
        acceleration_known=CODOL_LoadVehicleAccelerationGraph(raw.get(),&acceleration)==1;
        if(!acceleration_known)
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "VehicleDef '%s': acceleration graph '%s' unavailable; physical driving cannot activate\n",
                name,definition.physics_profile);
    }
    s_vehicleInfos[index] = staged_info;
    if (raw) raw->common = definition;
    delete installed[index].raw;
    installed[index].raw = raw.release();
    installed[index].acceleration=acceleration;
    installed[index].acceleration_known=acceleration_known;
    installed[index].turret_weapon = definition.turret_weapon_index;
    installed[index].definition = definition;
    installed[index].used = 1;
    if (index >= s_numVehicleInfos) s_numVehicleInfos = (short)(index + 1);
    return index;
}
#endif
