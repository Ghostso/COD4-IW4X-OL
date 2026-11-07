#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "cscr_variable.h"
#include <math.h>
#include <stdlib.h>

/* T5 642ea0 copies dense point arrays before creating the result array.
 * Report sparse indices as script errors instead of its debug assertion. */
static bool collision_points(float points[256][3], unsigned *count)
{
    unsigned object=Scr_GetObject(0);
    if(Scr_GetObjectType(object)!=VAR_ARRAY) {
        Scr_ParamError(0,"points must be an array"); return false;
    }
    *count=GetArraySize(object);
    if(*count>256) {
        Scr_ParamError(0,"at most 256 collision points are supported"); return false;
    }
    for(unsigned i=0;i<*count;++i) {
        unsigned child=FindArrayVariable(object,i);
        if(!child || GetValueType(child)!=VAR_VECTOR) {
            Scr_ParamError(0,"points must be a dense array of vectors"); return false;
        }
        const float *point=GetVariableValueAddress(child)->vectorValue;
        for(unsigned axis=0;axis<3;++axis) points[i][axis]=point[axis];
    }
    return true;
}

/* These T5 entry points explicitly test VAR_FLOAT before Scr_GetFloat;
 * integer arguments are not implicitly promoted by their contract. */
static bool collision_float(unsigned index,float *out)
{
    if(Scr_GetType(index)!=VAR_FLOAT) {
        Scr_ParamError(index,"parameter must be a floating point value"); return false;
    }
    *out=Scr_GetFloat(index); return true;
}

/* T5 4073b0 rounds the differences to float but accumulates their squares
 * in the x87 register. Keep that precision until the caller stores a float. */
static long double distance_squared(const float *a,const float *b)
{
    float x=b[0]-a[0],y=b[1]-a[1],z=b[2]-a[2];
    return ((long double)x*x+(long double)y*y)+(long double)z*z;
}

static float dot(const float *a,const float *b)
{
    return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2];
}

static void difference(const float *a,const float *b,float *out)
{
    for(unsigned axis=0;axis<3;++axis)out[axis]=a[axis]-b[axis];
}

/* T5 403250 leaves zero vectors zero. */
static void normalize(float *v)
{
    float length=sqrtf(dot(v,v));
    float inverse=1.0f/(length<=0.0f ? 1.0f:length);
    for(unsigned axis=0;axis<3;++axis)v[axis]*=inverse;
}

/* T5 65f8f0 compares only the score in component 1. Equal/unordered scores
 * compare equal; the reference does not promise a stable tie ordering. */
static int compare_spawn_score(const void *left,const void *right)
{
    const float *a=(const float *)left,*b=(const float *)right;
    if(a[1]>b[1])return 1;
    if(b[1]>a[1])return -1;
    return 0;
}

/* T5 65f800 sorts a copied dense vector array, preserving its input. */
extern "C" void CODOL_Scr_QSortScoredSpawnPointsAscending(void)
{
    float points[256][3]; unsigned count;
    if(!collision_points(points,&count))return;
    if(count)qsort(points,count,sizeof(points[0]),compare_spawn_score);
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        Scr_AddVector(points[i]); Scr_AddArray();
    }
}

/* T5 65dbf0: result = (strictly inside, squared distance, 0).
 * Negative radii retain the reference's squared-radius behavior. */
extern "C" void CODOL_Scr_CollisionTestPointsInSphere(void)
{
    float points[256][3],origin[3],radius;
    unsigned count;
    if(!collision_points(points,&count))return;
    Scr_GetVector(1,origin);
    if(!collision_float(2,&radius))return;
    float radius2=radius*radius;
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        float d2=(float)distance_squared(points[i],origin);
        float result[3]={radius2>d2 ? 1.0f:0.0f,d2,0.0f};
        Scr_AddVector(result); Scr_AddArray();
    }
}

/* T5 65dde0: origin, radius, height, direction. The center is constructed
 * with the original direction BEFORE normalizing it, as in 65dfce..65e025.
 * Successful results contain squared distance to origin and to the axis;
 * rejected points return (0,0,0). All three bounds are strict. */
extern "C" void CODOL_Scr_CollisionTestPointsInCylinder(void)
{
    float points[256][3],origin[3],direction[3],center[3],radius,height;
    unsigned count;
    if(!collision_points(points,&count))return;
    Scr_GetVector(1,origin);
    if(!collision_float(2,&radius) || !collision_float(3,&height))return;
    Scr_GetVector(4,direction);
    float half=0.5f*height,radius2=radius*radius,bound=radius+half;
    float bound2=bound*bound;
    for(unsigned axis=0;axis<3;++axis) center[axis]=origin[axis]+direction[axis]*half;
    normalize(direction);
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        float result[3]={0.0f,0.0f,0.0f};
        if((long double)bound2>distance_squared(points[i],center)) {
            float delta[3];
            for(unsigned axis=0;axis<3;++axis) delta[axis]=points[i][axis]-center[axis];
            float axial=fabsf(delta[0]*direction[0]+delta[1]*direction[1]+delta[2]*direction[2]);
            if(half>axial) {
                float d2=(float)distance_squared(points[i],center);
                float radial2=d2-axial*axial;
                if(radius2>radial2) {
                    result[0]=1.0f;
                    result[1]=(float)distance_squared(origin,points[i]);
                    result[2]=radial2;
                }
            }
        }
        Scr_AddVector(result); Scr_AddArray();
    }
}

/* T5 65e260 takes an additional radial vector. On a hit its third result
 * is the SQUARED PROJECTION onto that vector, not distance to the axis. */
extern "C" void CODOL_Scr_CollisionTestPointsInPill(void)
{
    float points[256][3],origin[3],direction[3],radial[3],center[3],end[3],radius,height;
    unsigned count;
    if(!collision_points(points,&count))return;
    Scr_GetVector(1,origin);
    if(!collision_float(2,&radius) || !collision_float(3,&height))return;
    Scr_GetVector(4,direction); Scr_GetVector(5,radial);
    float half=0.5f*height,radius2=radius*radius,bound=radius+half;
    float bound2=bound*bound;
    for(unsigned axis=0;axis<3;++axis) {
        center[axis]=origin[axis]+direction[axis]*half;
        end[axis]=origin[axis]+direction[axis]*height;
    }
    normalize(direction); normalize(radial);
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        bool inside=false;
        float result[3]={0.0f,0.0f,0.0f},delta[3];
        if((long double)bound2>distance_squared(points[i],center)) {
            if((long double)radius2>distance_squared(points[i],origin) ||
               (long double)radius2>distance_squared(points[i],end))inside=true;
            else {
                difference(points[i],center,delta);
                float axial=fabsf(dot(delta,direction));
                if(half>axial) {
                    float d2=(float)distance_squared(points[i],center);
                    inside=radius2>d2-axial*axial;
                }
            }
        }
        if(inside) {
            difference(points[i],origin,delta);
            float projection=dot(delta,radial);
            result[0]=1.0f;
            result[1]=(float)distance_squared(origin,points[i]);
            result[2]=projection*projection;
        }
        Scr_AddVector(result); Scr_AddArray();
    }
}

/* T5 65e8c0 constructs the apex and base edge from the original direction
 * vectors. Its angular test uses squared projections with a 1e-5 divisor
 * floor; preserve this for zero lengths and nonorthogonal input vectors. */
extern "C" void CODOL_Scr_CollisionTestPointsInCone(void)
{
    float points[256][3],origin[3],direction[3],radial[3],center[3],apex[3],edge[3];
    float back[3],edgeDelta[3],radius,height;
    unsigned count;
    if(!collision_points(points,&count))return;
    Scr_GetVector(1,origin);
    if(!collision_float(2,&radius) || !collision_float(3,&height))return;
    Scr_GetVector(4,direction); Scr_GetVector(5,radial);
    float half=0.5f*height,bound=radius+half,bound2=bound*bound;
    for(unsigned axis=0;axis<3;++axis) {
        center[axis]=origin[axis]+direction[axis]*half;
        apex[axis]=origin[axis]+direction[axis]*height;
        edge[axis]=origin[axis]+radial[axis]*radius;
    }
    normalize(direction); normalize(radial);
    difference(edge,apex,edgeDelta); difference(origin,apex,back);
    float edgeDot=dot(edgeDelta,back),edgeLength2=dot(edgeDelta,edgeDelta);
    float edgeDivisor=edgeLength2<=0.00001f ? 0.00001f:edgeLength2;
    float threshold=edgeDot*edgeDot/edgeDivisor;
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        float result[3]={0.0f,0.0f,0.0f},delta[3];
        if((long double)bound2>distance_squared(points[i],center)) {
            difference(points[i],center,delta);
            if(half>fabsf(dot(delta,direction))) {
                difference(points[i],apex,delta);
                float axial=dot(delta,back),length2=dot(delta,delta);
                float divisor=length2<=0.00001f ? 0.00001f:length2;
                if(axial*axial/divisor>threshold) {
                    difference(points[i],origin,delta);
                    float projection=dot(delta,radial);
                    result[0]=1.0f;
                    result[1]=(float)distance_squared(origin,points[i]);
                    result[2]=projection*projection;
                }
            }
        }
        Scr_AddVector(result); Scr_AddArray();
    }
}

/* T5 65f090: width follows forward, length follows up, depth follows their
 * cross product. Origin is the box center. Scaled basis vectors are
 * normalized independently; no orthogonalization is applied. */
extern "C" void CODOL_Scr_CollisionTestPointsInBox(void)
{
    float points[256][3],origin[3],dimensions[3],basis[3][3],axes[3][3];
    unsigned count;
    if(!collision_points(points,&count))return;
    Scr_GetVector(1,origin);
    for(unsigned i=0;i<3;++i)if(!collision_float(i+2,&dimensions[i]))return;
    Scr_GetVector(5,basis[0]); Scr_GetVector(6,basis[1]);
    basis[2][0]=basis[0][1]*basis[1][2]-basis[0][2]*basis[1][1];
    basis[2][1]=basis[0][2]*basis[1][0]-basis[0][0]*basis[1][2];
    basis[2][2]=basis[0][0]*basis[1][1]-basis[0][1]*basis[1][0];
    float minimum=dimensions[0]<=dimensions[1] ? dimensions[0]:dimensions[1];
    minimum=minimum<=dimensions[2] ? minimum:dimensions[2];
    float bound=((dimensions[0]+dimensions[1])+dimensions[2])-minimum;
    float bound2=bound*bound;
    for(unsigned i=0;i<3;++i) {
        float local[3]={0.0f,0.0f,0.0f}; local[i]=dimensions[i];
        for(unsigned axis=0;axis<3;++axis)
            axes[i][axis]=(local[0]*basis[0][axis]+local[1]*basis[1][axis])+local[2]*basis[2][axis];
        normalize(axes[i]);
    }
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i) {
        float result[3]={0.0f,0.0f,0.0f},delta[3];
        difference(points[i],origin,delta);
        float d2=dot(delta,delta);
        if(bound2>d2 &&
           dimensions[0]*0.5f>fabsf(dot(delta,axes[0])) &&
           dimensions[1]*0.5f>fabsf(dot(delta,axes[1])) &&
           dimensions[2]*0.5f>fabsf(dot(delta,axes[2]))) {
            result[0]=1.0f; result[1]=d2;
        }
        Scr_AddVector(result); Scr_AddArray();
    }
}
#endif
