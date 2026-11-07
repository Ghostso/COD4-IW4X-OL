#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <span>

namespace CodolGameServer
{
// CODREF(actor_traversal_adapter): CODOL 0x786E70 advances each leaf using
// its own asset frequency and clamps a nonlooping clip at its end. Exact
// v6/v7 durations and translations come from the hashed CODOL assets below.
// BO1 XAnimGetLength 0x7ED5C0, Ghosts 0x14024F070 and BO2 0x7B18D0 use
// frames/framerate; BO1 Actor_Negotiation_Think 0x910780 and BO2 0x895A80
// keep negotiation ownership until the animation script ends, then replan.
// This adapter is deliberately partial: it has no original CODOL script VM
// or animation-notify owner. Turn rate, alternation and settlement are OLMOD
// policies; see .agents/research/actor-traversal-20260917.md.

// OLMOD(window-action-handoff): qualified donor policy from the earlier
// Factory entry/traverse owner. BO1 CalcYaw separates desired/body angles;
// this 300 deg/s bound is reconstructed policy, NOT a recovered CODOL rate.
inline float SV_ZmTurnBody(float current,float desired,unsigned milliseconds)
{
    if (!std::isfinite(current) || !std::isfinite(desired)) return current;
    const auto turn=std::remainder(desired-current,360.0f);
    const auto limit=.3f*std::min(milliseconds,100u);
    return std::remainder(current+std::clamp(turn,-limit,limit),360.0f);
}
inline bool SV_ZmFacingReady(float current,float desired)
{
    return std::isfinite(current) && std::isfinite(desired) &&
        std::abs(std::remainder(desired-current,360.0f))<=.01f;
}
// Ground must be supplied by the existing native trace boundary. Keep the
// traversal pose until this bounded settlement finishes, as in the donor.
inline float SV_ZmSettleWindowHeight(float current,float ground,unsigned milliseconds)
{
    return current+std::clamp(ground-current,-.09f*milliseconds,.09f*milliseconds);
}
// OLMOD(window-root-motion): original CODOL asset-local translation, not a
// recovered AI controller. v6/v7 have no root rotation and zero local Z.
// Source: common_gametype_zm.ff SHA256
// 7f49272825482e466f2782910aa2ee97e4b777ad36a528d7d7be5ae30c06b7c0.
// Translation corpus SHA256 c6f361930ccb1e71e411524841f204555c9756e8368af5c31c3205c3d7ca57ea.
// Do not normalize endpoints to a pathnode or reuse one clip's clock for another.
struct SvZmWindowClip
{
    const char* name;
    unsigned frames;
    std::span<const unsigned> indices;
    std::span<const std::array<unsigned,3>> packed;
    std::array<float,3> scale;
    float duration() const { return static_cast<float>(frames)*1000.0f/30.0f; }
};
inline constexpr std::array<unsigned,3> SvZmWindowIndices0{0,31,34};
inline constexpr std::array<std::array<unsigned,3>,3> SvZmWindowPacked0{{
    {0,0,0},
    {65535,65535,0},
    {65535,65535,0},
}};
inline constexpr std::array<unsigned,31> SvZmWindowIndices1{0,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,25,26,27,28,29,30,31,32,33,36,37,38,39,40,42};
inline constexpr std::array<std::array<unsigned,3>,31> SvZmWindowPacked1{{
    {0,0,0},
    {10501,7916,0},
    {13962,10525,0},
    {17354,13082,0},
    {20646,15564,0},
    {23809,17949,0},
    {26813,20214,0},
    {29628,22335,0},
    {32224,24291,0},
    {34571,26062,0},
    {36638,27619,0},
    {38397,28946,0},
    {39817,30017,0},
    {40868,30809,0},
    {41520,31301,0},
    {41744,31468,0},
    {41745,31470,0},
    {41917,31715,0},
    {42367,32360,0},
    {43064,33359,0},
    {43978,34667,0},
    {45076,36239,0},
    {46327,38030,0},
    {47700,39997,0},
    {49165,42095,0},
    {53789,48716,0},
    {55436,51074,0},
    {57249,53670,0},
    {59197,56459,0},
    {61249,59398,0},
    {65535,65535,0},
}};
inline constexpr std::array<SvZmWindowClip,2> SvZmWindowClips{{
    {"ai_zombie_traverse_v6",34,SvZmWindowIndices0,SvZmWindowPacked0,{0.0016577187925577164f,8.650488598505035e-05f,0.0f}},
    {"ai_zombie_traverse_v7",42,SvZmWindowIndices1,SvZmWindowPacked1,{0.0010891646379604936f,4.7333505790447816e-05f,0.0f}},
}};
inline std::array<float,3> SV_ZmWindowRoot(unsigned variant, float elapsed)
{
    const auto& clip=SvZmWindowClips[std::min(variant,1u)];
    const auto frame=std::clamp(elapsed/clip.duration(),0.0f,1.0f)*clip.frames;
    unsigned high=1;
    while(high+1<clip.indices.size() && frame>clip.indices[high]) ++high;
    const auto low=high-1;
    const auto fraction=(frame-clip.indices[low])/(clip.indices[high]-clip.indices[low]);
    std::array<float,3> result{};
    for(unsigned axis=0;axis<3;++axis)
        result[axis]=(static_cast<float>(clip.packed[low][axis])+
            (static_cast<float>(clip.packed[high][axis])-clip.packed[low][axis])*fraction)*clip.scale[axis];
    return result;
}
inline std::array<float,3> SV_ZmWindowRootWorld(unsigned variant,float elapsed,
    const std::array<float,3>& origin,float yaw)
{
    const auto local=SV_ZmWindowRoot(variant,elapsed);
    const auto radians=yaw*3.14159265358979323846f/180.0f;
    return {origin[0]+local[0]*std::cos(radians)-local[1]*std::sin(radians),
        origin[1]+local[0]*std::sin(radians)+local[1]*std::cos(radians),origin[2]+local[2]};
}
}
