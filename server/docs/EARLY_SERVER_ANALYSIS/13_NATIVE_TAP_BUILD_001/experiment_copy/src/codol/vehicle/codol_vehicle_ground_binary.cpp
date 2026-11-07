/* C1 ground settings, not IW3 offsets. 67536b passes VehicleDef+a8 to the
 * physics constructor65c180. Motor65d0c0 uses block48/4c/50 (f0/f4/f8).
 * Steering683b50/683e90 uses164/168/16c/170 and mode2cc; boost683cc0 uses
 * 2fc..30c and handbrake683e90 uses310. The C1 RC binary and corresponding
 * shipped VEHICLEFILE corroborate the physical block field meanings, including
 * linker-converted resistance/torque values. IW4 OpenAssetTools VehiclePhysDef
 * and VehicleFields are an independent named schema lead, not offset proof.
 */
#ifdef CODOL_SERVER
#include "codol_vehicle_ground_binary.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
static unsigned word(const unsigned char *p,unsigned o)
{return (unsigned)p[o]|((unsigned)p[o+1]<<8)|((unsigned)p[o+2]<<16)|((unsigned)p[o+3]<<24);}
static float number(const unsigned char *p,unsigned o)
{unsigned b=word(p,o);float f;memcpy(&f,&b,4);return f;}
int CODOL_DecodeGroundVehicleSettings(const unsigned char *h,size_t size,
    const codol_vehicle_native_t *common,codol_vehicle_raw_t *out)
{
    if(!h || size<0x314 || !common || !out || common->type!=0 || !common->physics_enabled)return -1;
    codol_vehicle_raw_t *next=(codol_vehicle_raw_t *)calloc(1,sizeof(*next));
    if(!next)return -1;
    next->common=*common;
    next->decoded_domains=CODOL_GROUND_PHYSICS|CODOL_GROUND_CONTROL;
    codol_vehicle_ground_settings_t *g=&next->ground;
    struct field { unsigned source;size_t destination; };
#define F(offset,member) {offset,offsetof(codol_vehicle_ground_settings_t,member)}
    static const field fields[]={
        F(0xdc,suspension_travel_rear),F(0xe0,suspension_strength_front),F(0xe4,suspension_damping_front),
        F(0xe8,suspension_strength_rear),F(0xec,suspension_damping_rear),
        F(0xf0,friction_braking),F(0xf4,friction_coasting),F(0xf8,friction_top_speed),
        F(0xfc,friction_side),F(0x100,friction_side_rear),F(0x104,velocity_dependent_slip),
        F(0x108,roll_stability),F(0x120,target_air_pitch),F(0x15c,wheel_radius),
        F(0x164,max_steering_angle),F(0x168,steering_lerp),F(0x16c,min_steering_scale),
        F(0x170,min_steering_speed),F(0x300,boost_speed_multiplier),F(0x304,boost_accel_multiplier),
        F(0x308,boost_duration),F(0x30c,boost_recharge_time)
    };
#undef F
    int valid=1;
    for(unsigned i=0;i<sizeof(fields)/sizeof(*fields);++i){
        float value=number(h,fields[i].source);
        if(!isfinite(value)){valid=0;break;}
        memcpy((char *)g+fields[i].destination,&value,4);
    }
    /* Existing settings contract retains these particular source-unit values.
     * Undo the build-time unit conversion here; the physics adapter must apply
     * its own canonical unit conversion exactly once. */
    struct scaled {unsigned source;size_t destination;};
#define S(offset,member) {offset,offsetof(codol_vehicle_ground_settings_t,member)}
    static const scaled scales[]={S(0xc8,reverse_speed_source),S(0xcc,max_velocity_source),
        S(0x10c,roll_resistance),S(0x110,pitch_resistance),S(0x114,yaw_resistance),
        S(0x118,upright_strength_pitch),S(0x11c,upright_strength_roll),
        S(0x124,air_yaw_torque),S(0x128,air_pitch_torque)};
#undef S
    for(unsigned i=0;i<sizeof(scales)/sizeof(*scales);++i){
        float value=(float)((double)number(h,scales[i].source)/17.600000381469727);
        if(!isfinite(value)){valid=0;break;}
        memcpy((char *)g+scales[i].destination,&value,4);
    }
    unsigned steering=word(h,0xb8),power=word(h,0xbc),braking=word(h,0xc0);
    if(steering>2 || power>2 || braking>2 || word(h,0x2c8)>1 ||
       word(h,0x2cc)>1 || word(h,0x2fc)>1 || word(h,0x310)>1)valid=0;
    g->steering_axle=(codol_vehicle_axle_t)steering;g->power_axle=(codol_vehicle_axle_t)power;
    g->braking_axle=(codol_vehicle_axle_t)braking;
    g->remote_control=word(h,0x2c8);g->third_person_driver=word(h,0x2cc);
    g->boost_enabled=word(h,0x2fc);g->handbrake_enabled=word(h,0x310);
    /* Camera fields are deliberately not declared decoded here: their C1
     * consumer and field order still need verification before activation.
     * This decoder is a staged physical/control prerequisite only. */
    if(g->wheel_radius<=0 || (g->boost_enabled && g->boost_speed_multiplier<=0) ||
       g->boost_duration<0 || g->boost_recharge_time<0)valid=0;
    if(valid)*out=*next;
    free(next);return valid?1:-1;
}
#endif
