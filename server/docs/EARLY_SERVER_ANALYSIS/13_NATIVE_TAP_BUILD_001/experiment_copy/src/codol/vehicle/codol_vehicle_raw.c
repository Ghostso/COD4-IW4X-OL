/* Shipped C1 raw vehicle data -> native settings. No RC gameplay registration.
 * Text semantics corroborated against OpenBLOPS bg_misctables.cpp and native
 * retained G_LoadVehicle. C1 binary offsets are deliberately not reused. */
#ifdef CODOL_SERVER
#include "codol_vehicle_raw.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <errno.h>
#include <float.h>

static int copy(char *to,size_t cap,const char *from)
{
    size_t size=strlen(from);if(size>=cap)return 0;
    memcpy(to,from,size+1);return 1;
}
const char *CODOL_GroundVehicleSourceValue(const codol_vehicle_raw_t *v,const char *key)
{
    unsigned i;if(!v||!key)return NULL;
    for(i=0;i<v->count;++i)if(!strcmp(v->fields[i].key,key))return v->fields[i].value;
    return NULL;
}
int CODOL_GroundVehicleSourceNumber(const codol_vehicle_raw_t *v,const char *key,float *out)
{
    const char *text=CODOL_GroundVehicleSourceValue(v,key);char *end;double value;
    if(!text||!*text||!out)return 0;
    errno=0;value=strtod(text,&end);
    if(errno==ERANGE||end==text||*end||!isfinite(value)||value>FLT_MAX||value< -FLT_MAX)return 0;
    *out=(float)value;return isfinite(*out);
}
static int boolean(const codol_vehicle_raw_t *v,const char *key,int *out)
{
    const char *s=CODOL_GroundVehicleSourceValue(v,key);
    if(!s||((strcmp(s,"0"))&&(strcmp(s,"1"))))return 0;
    *out=*s-'0';return 1;
}
static int axle(const codol_vehicle_raw_t *v,const char *key,codol_vehicle_axle_t *out)
{
    const char *s=CODOL_GroundVehicleSourceValue(v,key);if(!s)return 0;
    if(!strcmp(s,"front"))*out=CODOL_AXLE_FRONT;
    else if(!strcmp(s,"rear"))*out=CODOL_AXLE_REAR;
    else if(!strcmp(s,"all"))*out=CODOL_AXLE_ALL;
    else return 0;
    return 1;
}
typedef struct {const char *key;size_t offset;float scale;} number_field_t;
#define C(key,member,scale) {key,offsetof(codol_vehicle_raw_t,common.member),scale}
#define G(key,member) {key,offsetof(codol_vehicle_raw_t,ground.member),1.0f}
static const number_field_t numbers[]={
    C("topSpeed",top_speed,17.6f),C("accel",accel,17.6f),C("collisionSpeed",collision_speed,17.6f),
    C("engineSndSpeed",engine_snd_speed,17.6f),C("rotRate",rot_rate,1),C("rotAccel",rot_accel,1),
    C("collisionDamage",collision_damage,1),C("maxBodyPitch",max_body_pitch,1),C("maxBodyRoll",max_body_roll,1),
    C("texureScrollScale",tex_scroll_scale,1),C("suspensionTravel",suspension_travel,1),
    C("fakeBodyAccelPitch",fake_body_accel_pitch,1),C("fakeBodyAccelRoll",fake_body_accel_roll,1),
    C("fakeBodyVelPitch",fake_body_vel_pitch,1),C("fakeBodyVelRoll",fake_body_vel_roll,1),
    C("fakeBodySideVelPitch",fake_body_side_vel_pitch,1),C("fakeBodyPitchStrength",fake_body_pitch_strength,1),
    C("fakeBodyRollStrength",fake_body_roll_strength,1),C("fakeBodyPitchDampening",fake_body_pitch_dampening,1),
    C("fakeBodyRollDampening",fake_body_roll_dampening,1),
    C("turretHorizSpanLeft",turret_horiz_span_left,1),C("turretHorizSpanRight",turret_horiz_span_right,1),
    C("turretVertSpanUp",turret_vert_span_up,1),C("turretVertSpanDown",turret_vert_span_down,1),C("turretRotRate",turret_rot_rate,1),
    C("suspensionSoftCompression",suspension_soft_compression,1),C("suspensionHardCompression",suspension_hard_compression,1),
    C("collisionBlendSpeed",collision_blend_speed,1),C("speedSndBlendSpeed",speed_snd_blend_speed,1),
    C("surfaceSndBlendSpeed",surface_snd_blend_speed,1),C("slideVolume",slide_volume,1),
    C("slideBlendSpeed",slide_blend_speed,1),C("inAirPitch",in_air_pitch,1),
    G("wheelRadius",wheel_radius),G("suspensionTravelRear",suspension_travel_rear),
    G("suspensionStrengthFront",suspension_strength_front),G("suspensionStrengthRear",suspension_strength_rear),
    G("suspensionDampingFront",suspension_damping_front),G("suspensionDampingRear",suspension_damping_rear),
    G("maxSteeringAngle",max_steering_angle),G("steeringLerp",steering_lerp),
    G("minSteeringScale",min_steering_scale),G("minSteeringSpeed",min_steering_speed),
    G("frictionBraking",friction_braking),G("frictionCoasting",friction_coasting),G("frictionTopSpeed",friction_top_speed),
    G("frictionSide",friction_side),G("frictionSideRear",friction_side_rear),G("velocityDependentSlip",velocity_dependent_slip),
    G("rollStability",roll_stability),G("rollResistance",roll_resistance),G("pitchResistance",pitch_resistance),G("yawResistance",yaw_resistance),
    G("uprightStrengthPitch",upright_strength_pitch),G("uprightStrengthRoll",upright_strength_roll),G("targetAirPitch",target_air_pitch),
    G("airYawTorque",air_yaw_torque),G("airPitchTorque",air_pitch_torque),
    G("boostSpeedMultiplier",boost_speed_multiplier),G("boostAccelMultiplier",boost_accel_multiplier),
    G("boostDuration",boost_duration),G("boostRechargeTime",boost_recharge_time),
    G("thirdPersonCameraRange",camera_range),G("thirdPersonCameraHeight",camera_height),G("thirdPersonCameraHeightMin",camera_height_min),
    G("thirdPersonCameraPitch",camera_pitch),G("thirdPersonCameraPitchMin",camera_pitch_min),
    G("thirdPersonCameraMinPitchClamp",camera_min_pitch_clamp),G("thirdPersonCameraMaxPitchClamp",camera_max_pitch_clamp),
    G("thirdPersonCameraSpringDistance",camera_spring_distance),G("thirdPersonCameraSpringTime",camera_spring_time),
    G("thirdPersonCameraHandbrakeTurnRateInc",camera_handbrake_turn_rate),G("thirdPersonCameraFOV",camera_fov),
    G("maxVelocity",max_velocity_source),G("reverseSpeed",reverse_speed_source)
};
#undef C
#undef G
static int fill(codol_vehicle_raw_t *v,const char *name)
{
    const char *text;unsigned i;float number;
    static const struct {const char *key;size_t offset;} bools[]={
#define B(key,member) {key,offsetof(codol_vehicle_raw_t,member)}
        B("remoteControl",ground.remote_control),B("thirdPersonDriver",ground.third_person_driver),
        B("boostEnabled",ground.boost_enabled),B("handbrakeEnabled",ground.handbrake_enabled),
        B("physicsEnabled",common.physics_enabled),B("quadBarrel",common.quad_barrel),
        B("bulletDamage",common.bullet_damage),B("armorPiercingDamage",common.armor_piercing_damage),
        B("grenadeDamage",common.grenade_damage),B("projectileDamage",common.projectile_damage),
        B("projectileSplashDamage",common.projectile_splash_damage),B("heavyExplosiveDamage",common.heavy_explosive_damage)
#undef B
    };
    static const struct {const char *key;unsigned slot;} sounds[]={
        {"lowIdleSnd",CODOL_VEH_SND_IDLE_LOW},{"highIdleSnd",CODOL_VEH_SND_IDLE_HIGH},
        {"lowEngineSnd",CODOL_VEH_SND_ENGINE_LOW},{"highEngineSnd",CODOL_VEH_SND_ENGINE_HIGH},
        {"turretSpinSnd",CODOL_VEH_SND_TURRET_SPIN},{"turretStopSnd",CODOL_VEH_SND_TURRET_STOP},
        {"engineStartUpSnd",CODOL_VEH_SND_ENGINE_STARTUP},{"engineShutdownSnd",CODOL_VEH_SND_ENGINE_SHUTDOWN},
        {"engineIdleSnd",CODOL_VEH_SND_ENGINE_IDLE},{"engineSustainSnd",CODOL_VEH_SND_ENGINE_SUSTAIN},
        {"engineRampUpSnd",CODOL_VEH_SND_ENGINE_RAMP_UP},{"engineRampDownSnd",CODOL_VEH_SND_ENGINE_RAMP_DOWN},
        {"suspensionSoftSnd",CODOL_VEH_SND_SUSPENSION_SOFT},{"suspensionHardSnd",CODOL_VEH_SND_SUSPENSION_HARD},
        {"speedSnd",CODOL_VEH_SND_SPEED},{"collisionSnd",CODOL_VEH_SND_COLLISION}
    };
    text=CODOL_GroundVehicleSourceValue(v,"type");if(!text||strcmp(text,"4 wheel"))return 0;
    text=CODOL_GroundVehicleSourceValue(v,"baseAsset");if(text&&*text)return 0; /* inheritance not silently discarded */
    v->common.type=v->common.retained_type=0;
    if(!copy(v->common.name,sizeof(v->common.name),name))return 0;
    for(i=0;i<sizeof(numbers)/sizeof(*numbers);++i){
        if(!CODOL_GroundVehicleSourceNumber(v,numbers[i].key,&number))return 0;
        number*=numbers[i].scale;if(!isfinite(number))return 0;
        memcpy((char *)v+numbers[i].offset,&number,sizeof(number));
    }
    for(i=0;i<sizeof(bools)/sizeof(*bools);++i){int b;if(!boolean(v,bools[i].key,&b))return 0;memcpy((char *)v+bools[i].offset,&b,sizeof(b));}
    v->common.remote_control=v->ground.remote_control;
    v->common.extension[0]=(uint32_t)v->ground.remote_control;
    if(!axle(v,"steeringAxle",&v->ground.steering_axle)||!axle(v,"powerAxle",&v->ground.power_axle)||!axle(v,"brakingAxle",&v->ground.braking_axle))return 0;
    if(!CODOL_GroundVehicleSourceNumber(v,"health",&number)||number<1||number>2147483520.0f||number!=floorf(number))return 0;
    v->common.health=(int)number;v->common.suspension_travel_known=1;
#define STR(key,member) do {text=CODOL_GroundVehicleSourceValue(v,key);if(!text||!copy(v->common.member,sizeof(v->common.member),text))return 0;}while(0)
    STR("physicsPreset",physics_preset_name);STR("accelerationGraph",physics_profile);
    STR("useHintString",use_hint_string);STR("turretWeaponName",turret_weapon);
    STR("compassFriendlyIcon",compass_icon[0]);STR("compassEnemyIcon",compass_icon[1]);
    STR("surfaceSndPrefix",surface_snd_prefix);
#undef STR
    for(i=0;i<sizeof(sounds)/sizeof(*sounds);++i){text=CODOL_GroundVehicleSourceValue(v,sounds[i].key);if(!text||!copy(v->common.sounds[sounds[i].slot],64,text))return 0;}
    /* Preset remains an unresolved named dependency until a real physics
     * loader binds it; do not set physics_preset_resolved speculatively. */
    return v->ground.wheel_radius>0 && v->common.suspension_travel>=0 &&
        v->ground.suspension_travel_rear>=0 && v->ground.boost_duration>=0 &&
        v->ground.boost_recharge_time>=0 && v->ground.camera_fov>0 && v->ground.camera_fov<180;
}
int CODOL_ParseGroundVehicleFile(const char *name,const char *bytes,size_t size,codol_vehicle_raw_t *out)
{
    codol_vehicle_raw_t *v;size_t pos=12,start,length;unsigned i;int ok=0;
    if(!name||!*name||!bytes||!out||size<12||size>65536||memcmp(bytes,"VEHICLEFILE\\",12))return -1;
    if(size&&bytes[size-1]==0)--size;
    while(size&&(bytes[size-1]=='\r'||bytes[size-1]=='\n'))--size;
    v=calloc(1,sizeof(*v));if(!v)return -1;
    while(pos<size){
        codol_vehicle_raw_field_t *f;if(v->count==CODOL_VEHICLE_RAW_FIELDS)goto done;
        f=&v->fields[v->count];start=pos;
        while(pos<size&&bytes[pos]!='\\')++pos;
        length=pos-start;if(!length||length>=sizeof(f->key)||pos==size)goto done;
        for(i=0;i<length;++i)if((unsigned char)bytes[start+i]<33||(unsigned char)bytes[start+i]>126)goto done;
        memcpy(f->key,bytes+start,length);++pos;start=pos;
        while(pos<size&&bytes[pos]!='\\')++pos;
        length=pos-start;if(length>=sizeof(f->value))goto done;
        memcpy(f->value,bytes+start,length);
        for(i=0;i<v->count;++i)if(!strcmp(v->fields[i].key,f->key))goto done;
        for(i=0;i<length;++i)if((unsigned char)f->value[i]<32||(unsigned char)f->value[i]>126)goto done;
        ++v->count;if(pos<size)++pos;
    }
    if(!fill(v,name))goto done;
    v->decoded_domains=CODOL_GROUND_PHYSICS|CODOL_GROUND_CONTROL|
        CODOL_GROUND_CAMERA|CODOL_GROUND_SOURCE_TEXT;
    *out=*v;ok=1;
done:free(v);return ok?1:-1;
}
int CODOL_LoadGroundVehicleFile(const char *name,codol_vehicle_raw_t *out)
{
    char path[128];const codol_engine_rawfile_t *raw;int status;
    if(!name||!*name||!out||strchr(name,'/')||strchr(name,'\\')||strstr(name,".."))return -1;
    if(snprintf(path,sizeof(path),"vehicles/%s",name)>=(int)sizeof(path))return -1;
    status=CODOL_LoadEngineRawFile(path,&raw);if(status!=1)return status;
    if(!raw||!raw->buffer||raw->len<0)return -1;
    return CODOL_ParseGroundVehicleFile(name,raw->buffer,(size_t)raw->len,out);
}
#endif
