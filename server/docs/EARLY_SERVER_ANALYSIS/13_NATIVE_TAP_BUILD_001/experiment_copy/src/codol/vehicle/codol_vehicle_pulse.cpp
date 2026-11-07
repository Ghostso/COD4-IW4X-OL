/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_vehicle_pulse.h"
#include <cmath>
#include <cstring>
namespace {
bool finite3(const float *v) {return v && std::isfinite(v[0]) && std::isfinite(v[1]) && std::isfinite(v[2]);}
float dot(const float *a,const float *b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
void cross(const float *a,const float *b,float *out) {
    out[0]=a[1]*b[2]-a[2]*b[1];out[1]=a[2]*b[0]-a[0]*b[2];out[2]=a[0]*b[1]-a[1]*b[0];
}
bool validBody(const codol_vehicle_pulse_body_t *b) {
    if(!b || !std::isfinite(b->inverse_mass) || b->inverse_mass<=0 ||
       !finite3(b->linear) || !finite3(b->angular) ||
       !finite3(b->delta_linear) || !finite3(b->delta_angular)) return false;
    for(int i=0;i<3;++i) if(!finite3(b->world_inverse_inertia[i])) return false;
    return true;
}
void inertia(const codol_vehicle_pulse_body_t *b,const float *v,float *out) {
    for(int i=0;i<3;++i) out[i]=dot(b->world_inverse_inertia[i],v);
}
float velocity(const codol_vehicle_pulse_row_t &r,bool change) {
    float first[3],second[3]={};
    cross(change?r.first->delta_angular:r.first->angular,r.lever_first,first);
    if(r.second) cross(change?r.second->delta_angular:r.second->angular,r.lever_second,second);
    for(int i=0;i<3;++i) {
        first[i]+=(change?r.first->delta_linear:r.first->linear)[i];
        if(r.second) second[i]+=(change?r.second->delta_linear:r.second->linear)[i];
        first[i]-=second[i];
    }
    return dot(r.direction,first);
}
float clamp(float x,float lo,float hi) {return x<lo?lo:x>hi?hi:x;}
bool apply(codol_vehicle_pulse_row_t &r,float delta) {
    float l1[3],a1[3],l2[3]={},a2[3]={};
    for(int i=0;i<3;++i) {
        l1[i]=r.first->delta_linear[i]+r.direction[i]*r.first->inverse_mass*delta;
        a1[i]=r.first->delta_angular[i]+r.application_first[i]*delta;
        if(r.second) {
            l2[i]=r.second->delta_linear[i]-r.direction[i]*r.second->inverse_mass*delta;
            a2[i]=r.second->delta_angular[i]-r.application_second[i]*delta;
        }
    }
    if(!finite3(l1)||!finite3(a1)||!finite3(l2)||!finite3(a2)) return false;
    std::memcpy(r.first->delta_linear,l1,sizeof(l1)); std::memcpy(r.first->delta_angular,a1,sizeof(a1));
    if(r.second) {std::memcpy(r.second->delta_linear,l2,sizeof(l2));std::memcpy(r.second->delta_angular,a2,sizeof(a2));}
    return true;
}
void error(float delta,float denominator,float *maximum) {
    float e=delta*denominator;e*=e;if(e>*maximum)*maximum=e;
}
}
int CODOL_PrepareVehiclePulse(codol_vehicle_pulse_row_t *out,
    codol_vehicle_pulse_body_t *a,codol_vehicle_pulse_body_t *b,
    const float direction[3],const float ra[3],const float rb[3],
    const float displacement[3],const codol_vehicle_constraint_row_t *limits) {
    if(!out||!validBody(a)||(b&&!validBody(b))||a==b||!finite3(direction)||
       !finite3(ra)||!finite3(rb)||!finite3(displacement)||!limits) return 0;
    const float values[]={limits->rhs,limits->cfm,limits->minimum,limits->maximum};
    for(unsigned i=0;i<4;++i) if(!std::isfinite(values[i]))return 0;
    if(limits->cfm<0||limits->minimum>limits->maximum||std::fabs(dot(direction,direction)-1)>0.001f)return 0;
    codol_vehicle_pulse_row_t r={};r.first=a;r.second=b;
    std::memcpy(r.direction,direction,12);std::memcpy(r.lever_first,ra,12);std::memcpy(r.lever_second,rb,12);
    float shifted[3],moment[3],projected[3];
    for(int i=0;i<3;++i)shifted[i]=ra[i]+displacement[i];
    cross(shifted,direction,moment);inertia(a,moment,r.application_first);
    cross(r.application_first,ra,projected);
    r.denominator=a->inverse_mass+dot(direction,projected);
    if(b) {cross(rb,direction,moment);inertia(b,moment,r.application_second);r.denominator+=b->inverse_mass+dot(moment,r.application_second);}
    /* T5 calc_abs uses physical mass. Wheel setup subsequently adds CFM;
     * CODOL_PrepareVehicleWheel owns that separate regularization. */
    r.cfm=limits->cfm;r.minimum=limits->minimum;r.maximum=limits->maximum;
    r.rhs=limits->rhs-velocity(r,false);
    if(!std::isfinite(r.rhs)||!std::isfinite(r.denominator)||r.denominator<=0.00001f||
       !finite3(r.application_first)||!finite3(r.application_second))return 0;
    *out=r;return 1;
}
int CODOL_WarmVehiclePulse(codol_vehicle_pulse_row_t *r,float force,float seconds) {
    if(!r||!std::isfinite(force)||!std::isfinite(seconds)||seconds<=0||r->impulse!=0)return 0;
    float value=force*seconds;if(!std::isfinite(value))return 0;
    value=clamp(value,r->minimum,r->maximum);
    if(!apply(*r,value))return 0;
    r->impulse=value;return 1;
}
int CODOL_RelaxVehiclePulse(codol_vehicle_pulse_row_t *r,float *maximum) {
    if(!r||!maximum||!std::isfinite(*maximum)||*maximum<0)return 0;
    float next=r->impulse-(velocity(*r,true)+r->cfm*r->impulse-r->rhs)/r->denominator;
    if(!std::isfinite(next))return 0;
    next=clamp(next,r->minimum,r->maximum);
    float delta=next-r->impulse;if(!apply(*r,delta))return 0;
    r->impulse=next;error(delta,r->denominator,maximum);return std::isfinite(*maximum);
}
int CODOL_RelaxVehicleWheel(codol_vehicle_pulse_row_t rows[3],
    const codol_vehicle_wheel_constraints_t *limits,float *maximum) {
    if(!rows||!limits||!maximum)return 0;
    float previousSide=rows[1].impulse,previousForward=rows[2].impulse,ignored=0;
    if(!CODOL_RelaxVehiclePulse(rows,maximum))return 0;
    if(limits->side_parent_ratio) {
        rows[1].maximum=std::fabs(rows[0].impulse)*limits->side_ratio;
        rows[1].minimum=-rows[1].maximum;
    }
    if(!CODOL_RelaxVehiclePulse(rows+1,limits->has_forward?&ignored:maximum))return 0;
    if(!limits->has_forward)return 1;
    if(!CODOL_RelaxVehiclePulse(rows+2,&ignored))return 0;
    float side,forward;int clamped;
    if(!CODOL_ClampVehicleWheelFriction(limits,rows[0].impulse,rows[1].impulse,rows[2].impulse,&side,&forward,&clamped))return 0;
    if(!apply(rows[1],side-rows[1].impulse)||!apply(rows[2],forward-rows[2].impulse))return 0;
    rows[1].impulse=side;rows[2].impulse=forward;
    error(side-previousSide,rows[1].denominator,maximum);error(forward-previousForward,rows[2].denominator,maximum);
    return std::isfinite(*maximum);
}

int CODOL_PrepareVehicleWheel(codol_vehicle_pulse_row_t out[3],
    codol_vehicle_pulse_body_t *a,codol_vehicle_pulse_body_t *b,
    const float axes[3][3],const float ra[3],const float rb[3],
    const float roll[3],const float pitch[3],const codol_vehicle_wheel_constraints_t *limits) {
    if(!out||!axes||!limits)return 0;
    codol_vehicle_pulse_row_t rows[3]={};
    if(!CODOL_PrepareVehiclePulse(rows,a,b,axes[0],ra,rb,roll,&limits->suspension)||
       !CODOL_PrepareVehiclePulse(rows+1,a,b,axes[1],ra,rb,roll,&limits->side))return 0;
    /* rbc_def_vehicle::calc_abs_and_setup: both spring and powered motor
     * explicitly add compliance to m_denom, after pulse_sum_normal::set. */
    rows[0].denominator+=rows[0].cfm;
    if(limits->has_forward) {
        if(!CODOL_PrepareVehiclePulse(rows+2,a,b,axes[2],ra,rb,pitch,&limits->forward))return 0;
        rows[2].denominator+=rows[2].cfm;
    }
    if(!std::isfinite(rows[0].denominator)||!std::isfinite(rows[2].denominator))return 0;
    std::memcpy(out,rows,sizeof(rows));return 1;
}
namespace {
float crossMass(const codol_vehicle_pulse_row_t &measure,const codol_vehicle_pulse_row_t &act) {
    float v[3],other[3]={};
    cross(act.application_first,measure.lever_first,v);
    if(measure.second)cross(act.application_second,measure.lever_second,other);
    for(int i=0;i<3;++i)v[i]+=other[i]+act.direction[i]*(measure.first->inverse_mass+
        (measure.second?measure.second->inverse_mass:0));
    return dot(measure.direction,v);
}
bool projectContact(float impulses[3],float friction) {
    if(!finite3(impulses))return false;
    if(impulses[0]>0)impulses[0]=0;
    const double lengthSquared=(double)impulses[1]*impulses[1]+(double)impulses[2]*impulses[2];
    const double limit=-(double)friction*impulses[0];
    if(lengthSquared>limit*limit) {
        const double scale=limit/std::sqrt(lengthSquared);
        impulses[1]=(float)(impulses[1]*scale);impulses[2]=(float)(impulses[2]*scale);
    }
    return finite3(impulses);
}
}
int CODOL_WarmVehicleWheel(codol_vehicle_pulse_row_t rows[3],
    const codol_vehicle_wheel_constraints_t *limits,const float force[3],float seconds) {
    if(!rows||!limits||!finite3(force)||!CODOL_WarmVehiclePulse(rows,force[0],seconds))return 0;
    if(limits->side_parent_ratio) {
        rows[1].maximum=-rows[0].impulse*limits->side_ratio;rows[1].minimum=-rows[1].maximum;
    }
    if(!CODOL_WarmVehiclePulse(rows+1,force[1],seconds))return 0;
    if(!limits->has_forward)return 1;
    if(!CODOL_WarmVehiclePulse(rows+2,force[2],seconds))return 0;
    float side,forward;int clamped;
    if(!CODOL_ClampVehicleWheelFriction(limits,rows[0].impulse,rows[1].impulse,rows[2].impulse,&side,&forward,&clamped)||
       !apply(rows[1],side-rows[1].impulse)||!apply(rows[2],forward-rows[2].impulse))return 0;
    rows[1].impulse=side;rows[2].impulse=forward;return 1;
}
int CODOL_PrepareVehicleContact(codol_vehicle_pulse_contact_t *out,
    codol_vehicle_pulse_body_t *a,codol_vehicle_pulse_body_t *b,
    const float axes[3][3],const float ra[3],const float rb[3],float penetration,
    float friction,float bounce,float maxBounce,float minimumBounceSquared,float seconds) {
    if(!out||!axes||!std::isfinite(penetration)||!std::isfinite(friction)||friction<0||
       !std::isfinite(bounce)||bounce<0||!std::isfinite(maxBounce)||maxBounce<0||
       !std::isfinite(minimumBounceSquared)||minimumBounceSquared<0||!std::isfinite(seconds)||seconds<=0)return 0;
    for(int i=0;i<3;++i)for(int j=i+1;j<3;++j)
        if(!finite3(axes[i])||!finite3(axes[j])||std::fabs(dot(axes[i],axes[j]))>0.001f)return 0;
    codol_vehicle_pulse_contact_t c={};c.friction=friction;
    const float zero[3]={};
    codol_vehicle_constraint_row_t limits={0,0,-10000000.0f,10000000.0f};
    for(int i=0;i<3;++i) {
        if(i==0)limits.maximum=0;else limits.maximum=10000000.0f;
        if(!CODOL_PrepareVehiclePulse(c.rows+i,a,b,axes[i],ra,rb,zero,&limits))return 0;
    }
    c.cross_normal_side=crossMass(c.rows[1],c.rows[0]);
    c.cross_normal_forward=crossMass(c.rows[2],c.rows[0]);
    const double side=c.rows[1].denominator,forward=c.rows[2].denominator;
    const double coupling=crossMass(c.rows[1],c.rows[2]);
    const double determinant=side*forward-coupling*coupling;
    if(!std::isfinite(determinant)||determinant<=0)return 0;
    c.inverse_side=(float)(forward/determinant);c.inverse_cross=(float)(-coupling/determinant);
    c.inverse_forward=(float)(side/determinant);
    /* T5 contact setup uses 50 in/s penetration correction, while wheel hard
     * stops use170. Positional correction is introduced only after pass one. */
    float bias=-penetration/(seconds>0.016666668f?seconds:0.016666668f);
    if(bias<0)bias*=0.3f;
    if(bias< -50.0f)bias=-50.0f;
    c.position_bias=bias<0?bias:0;
    if(bias>=0)for(int i=0;i<3;++i)c.rows[i].rhs+=bias;
    const float impact=velocity(c.rows[0],false);
    if(bounce>0.00001f&&maxBounce>0.00001f&&penetration>=0&&impact>0&&
       (double)impact*impact>minimumBounceSquared) {
        const float restitution=impact*bounce<maxBounce?impact*bounce:maxBounce;
        if(c.position_bias> -0.00001f)c.rows[0].rhs-=restitution;
        else if(c.position_bias> -restitution) {
            c.rows[0].rhs=-restitution-impact;c.position_bias=0;
        }
    }
    const float scalars[]={c.cross_normal_side,c.cross_normal_forward,c.inverse_side,c.inverse_cross,
        c.inverse_forward,c.position_bias,c.rows[0].rhs,c.rows[1].rhs,c.rows[2].rhs};
    for(unsigned i=0;i<sizeof(scalars)/sizeof(scalars[0]);++i)if(!std::isfinite(scalars[i]))return 0;
    *out=c;return 1;
}
int CODOL_WarmVehicleContact(codol_vehicle_pulse_contact_t *c,const float force[3],float seconds) {
    if(!c||!finite3(force)||!std::isfinite(seconds)||seconds<=0)return 0;
    float impulses[3];
    for(int i=0;i<3;++i) {if(c->rows[i].impulse!=0)return 0;impulses[i]=force[i]*seconds;}
    if(!projectContact(impulses,c->friction))return 0;
    for(int i=0;i<3;++i) {if(!apply(c->rows[i],impulses[i]))return 0;c->rows[i].impulse=impulses[i];}
    return 1;
}
int CODOL_RelaxVehicleContact(codol_vehicle_pulse_contact_t *c,float *maximum) {
    if(!c||!maximum||!std::isfinite(*maximum)||*maximum<0)return 0;
    float objective[3],old[3],next[3];
    for(int i=0;i<3;++i) {old[i]=c->rows[i].impulse;objective[i]=velocity(c->rows[i],true)-c->rows[i].rhs;}
    next[0]=old[0]-objective[0]/c->rows[0].denominator;if(next[0]>0)next[0]=0;
    const float deltaNormal=next[0]-old[0];
    objective[1]+=c->cross_normal_side*deltaNormal;objective[2]+=c->cross_normal_forward*deltaNormal;
    next[1]=old[1]-(c->inverse_side*objective[1]+c->inverse_cross*objective[2]);
    next[2]=old[2]-(c->inverse_cross*objective[1]+c->inverse_forward*objective[2]);
    if(!projectContact(next,c->friction))return 0;
    for(int i=0;i<3;++i) {
        const float delta=next[i]-old[i];if(!apply(c->rows[i],delta))return 0;
        c->rows[i].impulse=next[i];error(delta,c->rows[i].denominator,maximum);
    }
    return std::isfinite(*maximum);
}
