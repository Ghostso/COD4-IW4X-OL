/* Staged native RC rigid body. Requires reviewed ode-owned-world.patch. */
#include "codol_vehicle_ode.h"
#include "codol_physics_native.h"
#include "codol_vehicle_pulse.h"
#include "cm_local.h"
#include "entity.h"
#include "qcommon.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

extern "C" {
void Phys_Init(void);
void *CODOL_ODE_InitOwnedWorld(void *);
void CODOL_ODE_InitOwnedSpace(void *);
void CODOL_ODE_DestroyOwnedSpace(void *);
void dWorldDestroy(void *);
void *ODE_BodyGetFirstGeom(void *);
void CODOL_ODE_PostStepBody(void *);
void dBodyAddForceAtPos(void *,float,float,float,float,float,float);
void dBodyEnable(void *);
void Phys_ReduceContacts(void *,const void *,void *);
void *dGeomGetBody(void *);
void *dGeomGetBodyNext(void *);
int dAreConnectedExcluding(void *,void *,int);
int dBodyIsEnabled(void *);
void *Phys_GetWorldGeom(void);
void dSpaceCollide(void *,void *,void (*)(void *,void *,void *));
int dCollide(void *,void *,int,void *,int);
void *dJointCreateContact(void *,void *,const void *,const void *);
void dJointAttach(void *,void *,void *);
void dJointGroupEmpty(void *);
void CODOL_ODE_StepOwnedWorld(void *,float);
void dWorldSetGravity(void *,float,float,float);
void dWorldSetERP(void *,float);
void dWorldSetCFM(void *,float);
void dWorldSetContactMaxCorrectingVel(void *,float);
void dWorldSetContactSurfaceLayer(void *,float);
void dWorldSetQuickStepNumIterations(void *,int);
void *dBodyCreate(void *);
void dBodyDestroy(void *);
void dBodySetData(void *,void *);
void dBodySetPosition(void *,float,float,float);
void dBodySetRotation(void *,const float *);
void dBodySetLinearVel(void *,float,float,float);
void dBodySetAngularVel(void *,float,float,float);
const float *dBodyGetPosition(void *);
const float *dBodyGetRotation(void *);
const float *dBodyGetLinearVel(void *);
const float *dBodyGetAngularVel(void *);
void dMassSetParameters(float *,float,float,float,float,float,float,float,float,float,float);
void dBodySetMass(void *,const float *);
void dBodyGetMass(void *,float *);
void *dCreateBox(void *,void *,float,float,float);
void *Phys_CreateCylinderGeom(void *,void *,const void *);
void *Phys_CreateBrushGeom(void *,void *,BrushWrapper_t *,const float *);
void *dCreateGeomTransform(void *,void *);
void dGeomTransformSetGeom(void *,void *);
void ODE_GeomTransformSetRotation(void *,const float *,const float (*)[3]);
}
struct vehicle_pulse_context_t;
static int pulseForceAtPoint(vehicle_pulse_context_t *,codol_vehicle_ode_body_t *,const float *,const float *);
static int pulseCentralForce(vehicle_pulse_context_t *,codol_vehicle_ode_body_t *,const float *);
struct codol_vehicle_ode_world_s {
    void *world,*space,*contacts;
    int stepping;
    codol_vehicle_ode_body_t *bodies;
    vehicle_pulse_context_t *pulse;
    void *pulse_storage;
};
struct codol_vehicle_ode_body_s {
    codol_vehicle_ode_world_t *owner;
    codol_vehicle_ode_body_t *next;
    void *body;
    codol_native_physics_map_t geometry;
    unsigned entity,generation;
    float center[3],mass,bounce,friction;
    unsigned rotation_tick;
    /* Diagnostics: chassis contacts generated this pulse pass, first one reported. */
    unsigned frame_contacts;
    int contact_reported;
    /* Chassis contacts of the previous pulse pass: T5 _update_orientation_constraint
     * reads body->m_contact_count from the last solve (airborne test). */
    unsigned previous_contacts;
};
extern "C" int CODOL_VehicleODEOwnsBody(const codol_vehicle_ode_world_t *world,const codol_vehicle_ode_body_t *candidate) {
    if(!world||!candidate)return 0;
    for(const codol_vehicle_ode_body_t *b=world->bodies;b;b=b->next)if(b==candidate)return 1;
    return 0;
}
extern "C" unsigned CODOL_VehicleODEFrameContacts(const codol_vehicle_ode_body_t *body) {
    return body ? body->frame_contacts : 0;
}
extern "C" int CODOL_VehicleODEMass(const codol_vehicle_ode_body_t *body,float *mass) {
    if(!body||!mass||!body->owner||!CODOL_VehicleODEOwnsBody(body->owner,body)||
       !std::isfinite(body->mass)||body->mass<=0)return 0;
    *mass=body->mass;return 1;
}
extern "C" int CODOL_VehicleODECenterOfMass(const codol_vehicle_ode_body_t *body,float center[3]) {
    if(!body||!center||!body->owner||!CODOL_VehicleODEOwnsBody(body->owner,body))return 0;
    for(unsigned i=0;i<3;++i)if(!std::isfinite(body->center[i]))return 0;
    std::memcpy(center,body->center,sizeof(body->center));return 1;
}
static bool finite3(const float *v) {
    return v && std::isfinite(v[0]) && std::isfinite(v[1]) && std::isfinite(v[2]);
}
static bool rotation(const float a[3][3]) {
    if (!a) return false;
    for (int i=0;i<3;++i) {
        if (!finite3(a[i])) return false;
        for (int j=0;j<3;++j) {
            const float dot=a[i][0]*a[j][0]+a[i][1]*a[j][1]+a[i][2]*a[j][2];
            if (std::fabs(dot-(i==j ? 1.0f : 0.0f))>0.002f) return false;
        }
    }
    const float det=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-
        a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+
        a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
    return det>0.998f;
}
static bool massTensor(const PhysMass_t &m,float mass,float out[17]) {
    const double x=m.momentsOfInertia[0],y=m.momentsOfInertia[1],z=m.momentsOfInertia[2];
    const double xy=m.productsOfInertia[0],xz=m.productsOfInertia[1],yz=m.productsOfInertia[2];
    if (!std::isfinite(mass) || mass<=0 || !finite3(m.centerOfMass) ||
        !finite3(m.momentsOfInertia) || !finite3(m.productsOfInertia) || x<=0 ||
        x*y-xy*xy<=0 || x*y*z+2*xy*xz*yz-x*yz*yz-y*xz*xz-z*xy*xy<=0) return false;
    float v[6]={(float)(mass*x),(float)(mass*y),(float)(mass*z),
        (float)(mass*xy),(float)(mass*xz),(float)(mass*yz)};
    for (int i=0;i<6;++i) if (!std::isfinite(v[i])) return false;
    dMassSetParameters(out,mass,0,0,0,v[0],v[1],v[2],v[3],v[4],v[5]);
    return true;
}
extern "C" codol_vehicle_ode_world_t *CODOL_CreateVehicleODEWorld(void) {
    Phys_Init(); // Existing idempotent entry initializes shared body/geometry pools.
    codol_vehicle_ode_world_t *w=(codol_vehicle_ode_world_t *)std::calloc(1,sizeof(*w));
    if (!w) return NULL;
    // Sizes from retained dWorldCreate and dGetSimpleSpace, never C1 offsets.
    w->world=std::calloc(1,0x10110);
    w->space=std::calloc(1,0x64);
    w->contacts=std::calloc(1,4+4096*0xac);
    if (!w->world || !w->space || !w->contacts) {
        std::free(w->contacts); std::free(w->world); std::free(w->space); std::free(w); return NULL;
    }
    CODOL_ODE_InitOwnedWorld(w->world);
    CODOL_ODE_InitOwnedSpace(w->space);
    return w;
}
extern "C" void CODOL_DestroyVehicleODEBody(codol_vehicle_ode_body_t *b) {
    if (!b || (b->owner && b->owner->stepping)) return;
    if (b->owner) {
        dJointGroupEmpty(b->owner->contacts);
        codol_vehicle_ode_body_t **link=&b->owner->bodies;
        while (*link && *link!=b) link=&(*link)->next;
        if (*link==b) *link=b->next;
    }
    // ODE geoms retain brush pointers; destroy them before owned map storage.
    if (b->body) dBodyDestroy(b->body);
    CODOL_FreeNativePhysicsMap(&b->geometry);
    std::free(b);
}
extern "C" void CODOL_DestroyVehicleODEWorld(codol_vehicle_ode_world_t *w) {
    if (!w || w->stepping) return;
    while (w->bodies) CODOL_DestroyVehicleODEBody(w->bodies);
    // Non-deleting space destructor: caller storage is not an ODE pool geom.
    CODOL_ODE_DestroyOwnedSpace(w->space);
    dWorldDestroy(w->world);
    std::free(w->pulse_storage);std::free(w->contacts); std::free(w->space); std::free(w->world); std::free(w);
}
static bool addGeometry(codol_vehicle_ode_body_t *b,const PhysGeomInfo_t &g) {
    void *space=b->owner->space;
    if (g.brush) {
        // Both native Phys_ObjSetCollisionFromXModel and C1 brush constructor
        // consume map-local planes plus COM; no extra primitive transform.
        return Phys_CreateBrushGeom(space,b->body,g.brush,b->center)!=NULL;
    }
    if (!rotation(g.orientation) || !finite3(g.offset) || !finite3(g.halfLengths)) return false;
    void *child=NULL;
    if (g.type==1) {
        if (g.halfLengths[0]<=0 || g.halfLengths[1]<=0 || g.halfLengths[2]<=0) return false;
        child=dCreateBox(space,b->body,2*g.halfLengths[0],2*g.halfLengths[1],2*g.halfLengths[2]);
    } else if (g.type==4) {
        // Retained XModel cylinder path: axis0 -> ODE direction1,
        // radius=halfLengths.y, height=halfLengths.x (no extra doubling).
        struct { int direction; float radius,height; } cylinder={1,g.halfLengths[1],g.halfLengths[0]};
        if (cylinder.radius<=0 || cylinder.height<=0) return false;
        child=Phys_CreateCylinderGeom(space,b->body,&cylinder);
    } else return false;
    if (!child) return false;
    void *wrapper=dCreateGeomTransform(space,b->body);
    if (!wrapper) return false; // Child remains body-owned; rollback destroys it.
    dGeomTransformSetGeom(wrapper,child); // Removes child from actual owned space.
    float offset[3];
    for (int i=0;i<3;++i) offset[i]=g.offset[i]-b->center[i];
    ODE_GeomTransformSetRotation(wrapper,offset,g.orientation);
    return true;
}
extern "C" codol_vehicle_ode_body_t *CODOL_CreateVehicleODEBody(codol_vehicle_ode_world_t *w,
    const codol_vehicle_raw_t *def,const char *model,unsigned entity,unsigned generation,
    const float origin[3],const float axis[3][3],const float velocity[3],const float angular[3]) {
    if (!w || w->stepping || !def || !model || !*model || entity>=ENTITYNUM_MAX_NORMAL ||
        !(def->decoded_domains&CODOL_GROUND_PHYSICS) || !def->common.physics_enabled ||
        !def->common.physics_preset_resolved || !def->common.physics_preset[0] ||
        !finite3(origin) || !rotation(axis) || !finite3(velocity) || !finite3(angular) ||
        !std::isfinite(def->ground.roll_stability)) return NULL;
    for (codol_vehicle_ode_body_t *p=w->bodies;p;p=p->next)
        if (p->entity==entity) return NULL; // Must destroy stale generation explicitly.
    const PhysPreset *preset=NULL;
    codol_mounted_model_physics_t source={};
    codol_physics_map_t parsed={};
    if (CODOL_LoadEnginePhysicsPreset(def->common.physics_preset,&preset)!=1 || !preset ||
        !std::isfinite(preset->bounce) || !std::isfinite(preset->friction) ||
        CODOL_LoadMountedModelPhysics(model,1,&source)!=1 || !CODOL_ReadPhysicsMap(&source,&parsed)) return NULL;
    float tensor[17];
    codol_vehicle_ode_body_t *b=(codol_vehicle_ode_body_t *)std::calloc(1,sizeof(*b));
    if (!b) { CODOL_FreePhysicsMap(&parsed); return NULL; }
    const bool decoded=CODOL_BuildNativePhysicsMap(&parsed,&b->geometry)!=0;
    CODOL_FreePhysicsMap(&parsed);
    if (!decoded || !b->geometry.map.count || !massTensor(b->geometry.map.mass,preset->mass,tensor)) {
        CODOL_DestroyVehicleODEBody(b); return NULL;
    }
    b->owner=w; b->entity=entity; b->generation=generation;
    b->mass=preset->mass; b->bounce=preset->bounce; b->friction=preset->friction;
    std::memcpy(b->center,b->geometry.map.mass.centerOfMass,sizeof(b->center));
    // C1 65c671 ->659100 ->658be0: only COM.z gets 1-roll_stability.
    b->center[2]*=1.0f-def->ground.roll_stability;
    if (!finite3(b->center)) { CODOL_DestroyVehicleODEBody(b); return NULL; }
    b->body=dBodyCreate(w->world);
    if (!b->body) { CODOL_DestroyVehicleODEBody(b); return NULL; }
    dBodySetData(b->body,b);
    dBodySetMass(b->body,tensor);
    for (unsigned i=0;i<b->geometry.map.count;++i)
        if (!addGeometry(b,b->geometry.map.geoms[i])) { CODOL_DestroyVehicleODEBody(b); return NULL; }
    float position[3],matrix[12]={};
    for (int i=0;i<3;++i) {
        position[i]=origin[i];
        for (int j=0;j<3;++j) { position[i]+=axis[j][i]*b->center[j]; matrix[i*4+j]=axis[j][i]; }
    }
    if (!finite3(position)) { CODOL_DestroyVehicleODEBody(b); return NULL; }
    dBodySetRotation(b->body,matrix);
    dBodySetPosition(b->body,position[0],position[1],position[2]);
    dBodySetLinearVel(b->body,velocity[0],velocity[1],velocity[2]);
    dBodySetAngularVel(b->body,angular[0],angular[1],angular[2]);
    b->next=w->bodies; w->bodies=b;
    return b;
}
extern "C" int CODOL_ReadVehicleODEBody(const codol_vehicle_ode_body_t *b,unsigned entity,unsigned generation,
    float origin[3],float axis[3][3],float velocity[3],float angular[3]) {
    if (!b || !b->body || b->entity!=entity || b->generation!=generation ||
        !origin || !axis || !velocity || !angular) return 0;
    const float *p=dBodyGetPosition(b->body),*r=dBodyGetRotation(b->body);
    const float *v=dBodyGetLinearVel(b->body),*a=dBodyGetAngularVel(b->body);
    float result[3],rotationAxis[3][3];
    if (!finite3(p) || !finite3(v) || !finite3(a) || !r) return 0;
    for (int i=0;i<3;++i) {
        result[i]=p[i];
        for (int j=0;j<3;++j) { rotationAxis[j][i]=r[i*4+j]; result[i]-=r[i*4+j]*b->center[j]; }
    }
    if (!finite3(result) || !rotation(rotationAxis)) return 0;
    std::memcpy(origin,result,sizeof(result)); std::memcpy(axis,rotationAxis,sizeof(rotationAxis));
    std::memcpy(velocity,v,3*sizeof(float)); std::memcpy(angular,a,3*sizeof(float));
    return 1;
}

/* Retained collision ABI: 0x30 bytes/point; the contact joint copies its first
 * 0x2c bytes. Final dCollide scratch/count storage is reserved after the array. */
struct vehicle_contact_geom_t {
    float position[4],normal[4],depth;
    void *first,*second;
    unsigned surface;
};
struct vehicle_contact_surface_t {
    unsigned mode;
    float friction,friction2,bounce,bounce_velocity,erp,cfm,motion1,motion2,slip1,slip2;
};
static_assert(sizeof(vehicle_contact_geom_t)==0x30,"retained x86 contact ABI");
static_assert(sizeof(vehicle_contact_surface_t)==0x2c,"retained contact surface ABI");
struct vehicle_collision_context_t {
    codol_vehicle_ode_world_t *owner;
    const codol_vehicle_ode_step_t *settings;
    bool failed;
};
static codol_vehicle_ode_body_t *findBody(codol_vehicle_ode_world_t *w,void *native) {
    for (codol_vehicle_ode_body_t *b=w->bodies;b;b=b->next) if (b->body==native) return b;
    return NULL;
}
static void ownedNearCallback(void *opaque,void *first,void *second) {
    vehicle_collision_context_t &c=*(vehicle_collision_context_t *)opaque;
    if (c.failed) return;
    void *a=dGeomGetBody(first),*b=dGeomGetBody(second);
    if (a==b) return;
    codol_vehicle_ode_body_t *ownerA=a ? findBody(c.owner,a) : NULL;
    codol_vehicle_ode_body_t *ownerB=b ? findBody(c.owner,b) : NULL;
    // Never treat another world's userdata as an owned RC record.
    if ((a && !ownerA) || (b && !ownerB)) { c.failed=true; return; }
    // Native Phys_NearCallback excludes bodies joined by a non-contact joint.
    // Contact joint type is 4 in this retained backend, not an imported enum.
    if (a && b && dAreConnectedExcluding(a,b,4)) return;
    struct ContactList { vehicle_contact_geom_t points[128]; unsigned count; };
    ContactList contacts={},reduced={};
    const int count=dCollide(first,second,128,&contacts,sizeof(contacts.points[0]));
    if (count<0 || count>128) { c.failed=true; return; }
    contacts.count=(unsigned)count;
    ContactList *manifold=&contacts;
    if (count>4) {
        // Native reduction receives a body only for a body/world pair. With
        // two dynamic bodies it receives NULL, avoiding a one-body-biased
        // manifold selection (Phys_NearCallback's edi selection).
        Phys_ReduceContacts(a && b ? NULL : a ? a : b,&contacts,&reduced);
        if (reduced.count>128) { c.failed=true; return; }
        manifold=&reduced;
    }
    // Native preset material combination from Phys_NearCallback. Solver/contact
    // dvars remain explicit inputs until the C1 world3 settings producer is wired.
    const float friction=((ownerA ? ownerA->friction : 0)+(ownerB ? ownerB->friction : 0))*c.settings->friction_scale;
    float bounce=1;
    if (ownerA && ownerA->bounce<bounce) bounce=ownerA->bounce;
    if (ownerB && ownerB->bounce<bounce) bounce=ownerB->bounce;
    if (!std::isfinite(friction) || friction<0 || !std::isfinite(bounce) || bounce<0) { c.failed=true; return; }
    vehicle_contact_surface_t surface={0x301c,friction,0,bounce,c.settings->bounce_velocity,
        c.settings->contact_erp,c.settings->contact_cfm,0,0,0,0};
    for (unsigned i=0;i<manifold->count;++i) {
        vehicle_contact_geom_t &g=manifold->points[i];
        if (!finite3(g.position) || !finite3(g.normal) || !std::isfinite(g.depth) || g.depth<0) {
            c.failed=true; return;
        }
        void *joint=dJointCreateContact(c.owner->world,c.owner->contacts,&surface,&g);
        if (!joint) { c.failed=true; return; }
        dJointAttach(joint,a,b);
    }
}
static bool validStep(const codol_vehicle_ode_step_t &p) {
    const float values[]={p.erp,p.cfm,p.max_correcting_velocity,p.surface_layer,
        p.contact_erp,p.contact_cfm,p.friction_scale,p.bounce_velocity,p.contact_max_bounce_velocity,
        p.max_angular_velocity,p.linear_drag,p.angular_drag};
    if (!finite3(p.gravity) || p.iterations<=0) return false;
    for (unsigned i=0;i<sizeof(values)/sizeof(values[0]);++i)
        if (!std::isfinite(values[i]) || values[i]<0) return false;
    return p.erp<=1 && p.contact_erp<=1;
}
extern "C" int CODOL_VehicleODEForceAtPoint(codol_vehicle_ode_body_t *b,const float force[3],const float point[3]) {
    if (!b || !b->body || !b->owner || !b->owner->stepping || !finite3(force) || !finite3(point)) return 0;
    if(b->owner->pulse)return pulseForceAtPoint(b->owner->pulse,b,force,point);
    if (force[0]!=0 || force[1]!=0 || force[2]!=0) dBodyEnable(b->body);
    dBodyAddForceAtPos(b->body,force[0],force[1],force[2],point[0],point[1],point[2]);
    return 1;
}
/* T5 rigid_body::add_force (NitrousVehicleController::UpdateJump): a pure
 * force through the body's centre of mass, no torque. Integrated by the pulse
 * pass as linear += seconds*force/mass, so a caller wanting a velocity impulse
 * dv passes mass*dv/seconds. */
extern "C" int CODOL_VehicleODECentralForce(codol_vehicle_ode_body_t *b,const float force[3]) {
    if (!b || !b->body || !b->owner || !b->owner->stepping || !finite3(force)) return 0;
    if(b->owner->pulse)return pulseCentralForce(b->owner->pulse,b,force);
    const float *p=dBodyGetPosition(b->body);
    if (force[0]!=0 || force[1]!=0 || force[2]!=0) dBodyEnable(b->body);
    dBodyAddForceAtPos(b->body,force[0],force[1],force[2],p[0],p[1],p[2]);
    return 1;
}
extern "C" int CODOL_StepVehicleODEWorld(codol_vehicle_ode_world_t *w,float seconds,
    const codol_vehicle_ode_step_t *settings,codol_vehicle_ode_force_fn force,void *context) {
    if (!w || w->stepping || !settings || !force || !std::isfinite(seconds) || seconds<=0 || !validStep(*settings)) return 0;
    const float linear=1-settings->linear_drag*seconds,angular=1-settings->angular_drag*seconds;
    if (!std::isfinite(linear) || !std::isfinite(angular)) return 0;
    w->stepping=1;
    dJointGroupEmpty(w->contacts);
    vehicle_collision_context_t collision={w,settings,false};
    for (codol_vehicle_ode_body_t *b=w->bodies;b;b=b->next) {
        if (!force(b,seconds,context)) { collision.failed=true; break; }
    }
    if (!collision.failed) {
        dSpaceCollide(w->space,&collision,ownedNearCallback);
        // Use actual mounted clipmap collider, not a floor plane or trace proxy.
        void *worldGeom=Phys_GetWorldGeom();
        if (!worldGeom) collision.failed=true;
        for (codol_vehicle_ode_body_t *b=w->bodies;b && !collision.failed;b=b->next) {
            if (!dBodyIsEnabled(b->body)) continue;
            for (void *geom=ODE_BodyGetFirstGeom(b->body);geom && !collision.failed;geom=dGeomGetBodyNext(geom))
                ownedNearCallback(&collision,geom,worldGeom);
        }
    }
    if (!collision.failed) {
        dWorldSetGravity(w->world,settings->gravity[0],settings->gravity[1],settings->gravity[2]);
        dWorldSetERP(w->world,settings->erp); dWorldSetCFM(w->world,settings->cfm);
        dWorldSetContactMaxCorrectingVel(w->world,settings->max_correcting_velocity);
        dWorldSetContactSurfaceLayer(w->world,settings->surface_layer);
        dWorldSetQuickStepNumIterations(w->world,settings->iterations);
        CODOL_ODE_StepOwnedWorld(w->world,seconds);
    }
    // Actual native force reset and geometry invalidation, including aborted
    // force/contact preparation. No dangling contact joints across substeps.
    for (codol_vehicle_ode_body_t *b=w->bodies;b;b=b->next) {
        CODOL_ODE_PostStepBody(b->body);
        if (!collision.failed && dBodyIsEnabled(b->body)) {
            const float *v=dBodyGetLinearVel(b->body),*a=dBodyGetAngularVel(b->body);
            if (!finite3(v) || !finite3(a)) { collision.failed=true; continue; }
            float scaledV[3],scaledA[3];
            for (int i=0;i<3;++i) { scaledV[i]=v[i]*(linear>0 ? linear : 0); scaledA[i]=a[i]*(angular>0 ? angular : 0); }
            dBodySetLinearVel(b->body,scaledV[0],scaledV[1],scaledV[2]);
            dBodySetAngularVel(b->body,scaledA[0],scaledA[1],scaledA[2]);
        }
    }
    dJointGroupEmpty(w->contacts);
    w->stepping=0;
    return !collision.failed;
}

#include "codol_vehicle_pulse_world.inc"
#include "codol_vehicle_wheel_ray.inc"
