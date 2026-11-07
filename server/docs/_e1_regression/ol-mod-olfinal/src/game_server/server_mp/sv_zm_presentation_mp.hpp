#pragma once
#include <array>
#include <cstdint>
#include <span>
#include <optional>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    // CODREF(actor_head_attachment): 0x530C90 selects real model aliases;
    // original recordings group intact body colors by round, not outfit.
    enum class SvZmBodyColor : std::uint8_t { Unspecified, Blue, Yellow, Orange, Base, Red };
    inline SvZmBodyColor SV_ZmRoundBodyColor(std::uint32_t round)
    {
        // 1625 labelled initial bodies in five original recordings: R1-4 blue,
        // R5-8 yellow, R9 orange. No same-life intact body color swaps observed.
        // OLMOD(zm-round-colors): R10+ holds the last evidenced color. Later
        // native bands are unknown; this is an explicit conservative fallback.
        return round <= 4 ? SvZmBodyColor::Blue :
            round <= 8 ? SvZmBodyColor::Yellow : SvZmBodyColor::Orange;
    }
    struct SvZmOutfit
    {
        std::uint16_t body{}, head{};
        // CODREF(actor_head_attachment): CODOL CG_UpdateAgentDObj 0x52FBE0
        // composes shared-bone parts (empty attachment tags). Original Factory
        // records pair torso_1 + head + lowclean, or body + behead.
        std::uint16_t torso{}, lower{}, behead{};
        std::uint8_t neckBone{255}, torsoBone{255};
        std::uint16_t rightArmOff{};
        std::uint8_t rightArmBone{255}, shockBone{255}, eyeBone{255};
        std::uint16_t leftArmOff{};
        std::uint8_t leftArmBone{255};
        SvZmBodyColor color{SvZmBodyColor::Unspecified};
        // OLMOD(zm-face-glow): optional resident FX; separate from Tesla shock.
        std::uint16_t eyeGlow{}, mouthGlow{};
        std::uint8_t eyeGlowBone{255}, mouthGlowBone{255};
    };
    inline SvZmOutfit SV_ZmChooseOutfit(std::span<const SvZmOutfit> outfits,
        std::uint32_t sequence, std::uint32_t round, SvZmOutfit fallback)
    {
        if (outfits.empty()) return fallback;
        // OLMOD(zm-round-colors): filter by resolved metadata, never alias/index
        // arithmetic. Missing families cannot couple clothing to color or attach
        // a head from another family. Clothing remains the accepted equal cycle.
        const auto choose = [&](SvZmBodyColor color) -> std::optional<SvZmOutfit> {
            std::uint32_t count{};
            for (const auto &o : outfits) if (o.color == color) ++count;
            if (!count) return std::nullopt;
            auto ticket = sequence % count;
            for (const auto &o : outfits)
                if (o.color == color && ticket-- == 0) return o;
            return std::nullopt;
        };
        if (const auto o = choose(SV_ZmRoundBodyColor(round))) return *o;
        // Missing phase assets keep a uniform resolved blue set. Unannotated
        // callers retain their old cycle; an empty set retains the caller pair.
        if (const auto o = choose(SvZmBodyColor::Blue)) return *o;
        if (const auto o = choose(SvZmBodyColor::Unspecified)) return *o;
        return fallback;
    }
    struct SvZmDeathFx
    {
        // Resolve native names per map, never use a recording's numeric IDs.
        std::uint16_t neck{}, torso{};
        // OLMOD(bo1_damage_profile): opt-in BO1 script policy, NOT CODOL retail odds.
        bool bo1Derived{};
        std::uint16_t shock{}, shockEyes{};
        std::vector<std::uint16_t> electricalWeapons, excludedWeapons;
        std::uint32_t randomSeed{1};
        // OLMOD(refined_fx): explicit preview; original CODOL selection odds unknown.
        bool refined{};
    };
    // BO1 packaged _zombiemode_spawner::zombie_should_gib/head_should_gib.
    // Callers must separately validate attacker, weapon, method and model state.
    inline bool SV_ZmBo1DamageThreshold(std::int32_t damage, std::int32_t before)
    {
        return damage>0 && before>0 && static_cast<std::int64_t>(damage)*10>=before;
    }
    inline bool SV_ZmBo1HeadThreshold(std::int32_t remaining, std::int32_t maximum)
    {
        return maximum>0 && static_cast<std::int64_t>(remaining)*10<=maximum;
    }
    struct SvZmDeathClip
    {
        std::uint16_t animation{};
        std::uint32_t milliseconds{};
        std::uint32_t weight{};
        // Optional original-demo loop/down pair; absent assets retain base clip.
        std::uint16_t loopAnimation{}, downAnimation{};
        std::uint32_t loopMilliseconds{}, downMilliseconds{};
        // Tesla animation family, not a claim that the kill was electrical.
        // Original recordings also use its base clips without body-shock events.
        bool electrical{};
    };
    // CODREF(actor_head_attachment): exact CODOL XModel classification and posed
    // 0x7825F0 replay distinguish right 6/8/10 and left 7/9/11. BO1 packaged
    // _zombiemode_spawner::zombie_gib maps upper/lower arm and hand to that side.
    // Thresholds and once-per-body ownership remain the BO1-derived profile.
    inline int SV_ZmArmSide(std::uint8_t location)
    {
        if(location==6 || location==8 || location==10)return 1;
        if(location==7 || location==9 || location==11)return -1;
        return 0;
    }
    inline bool SV_ZmHasDeathSequence(const SvZmDeathClip &c)
    {
        return c.loopAnimation>0 && c.loopAnimation<4096 &&
            c.downAnimation>0 && c.downAnimation<4096 &&
            c.loopMilliseconds>=100 && c.loopMilliseconds<=1500 &&
            c.downMilliseconds>=1000 && c.downMilliseconds<=6000;
    }
    struct SvZmDeathSpec
    {
        std::string_view name;
        std::uint32_t milliseconds, weight;
        bool electrical{};
    };
    // CODREF(xanim_shared_actor_blend): CODOL 0x786E70 advances rate * asset
    // frequency and clamps non-looping leaves. BO1 XAnimGetLength 0x7ED5C0,
    // Ghosts 0x14024F070 return asset duration. Original Factory commands include
    // both ordinary leaves and all five Tesla bases; see presentation research.
    // OLMOD(death_variety): rounded asset duration + 250ms settling allowance.
    // Weights within a damage class are reconstructed, not retail probabilities.
    // BO1's weapon path supports electrical sequence selection, not exclusive
    // ownership of these names in CODOL. Original CODOL base clips occur without
    // nearby shock events; loop/down + lightning remains separately gated.
    inline constexpr std::array<SvZmDeathSpec,7> SvZmDeathSpecs{{
        {"ai_zombie_death_v1",2250,5},
        {"ai_zombie_death_v2",2517,5},
        {"ai_zombie_tesla_death_a",4750,2,true},
        {"ai_zombie_tesla_death_b",4517,2,true},
        {"ai_zombie_tesla_death_c",4750,2,true},
        {"ai_zombie_tesla_death_d",4517,2,true},
        {"ai_zombie_tesla_death_e",3617,2,true},
    }};
    // OLMOD(death_variety): bounded deterministic weighted cycle for repeatable
    // playtests. No asset lookup or mutable RNG in the actor frame.
    inline SvZmDeathClip SV_ZmChooseDeath(std::span<const SvZmDeathClip> clips,
        std::uint32_t sequence, SvZmDeathClip fallback,
        std::optional<bool> electrical=std::nullopt, bool favorOrdinary=false)
    {
        // OLMOD(death_variety): head-intact ordinary deaths favor the two ordinary
        // leaves 4:1 over the previous mix (20% Tesla family with all assets).
        // This is presentation tuning, not a recovered CODOL probability.
        const auto weight=[&](const SvZmDeathClip &c) {
            return c.weight * (favorOrdinary && !electrical && !c.electrical ? 4u : 1u);
        };
        std::uint32_t total{};
        for (const auto &c:clips)
            if(!electrical || c.electrical==*electrical) total+=weight(c);
        if (!total) return fallback;
        // Filtering by explicit metadata survives missing assets and reordered clips.
        // Runtime always supplies the damage class; an empty class uses fallback.
        auto ticket=(static_cast<std::uint64_t>(sequence)*7u)%total;
        for (const auto &c:clips)
        {
            if(electrical && c.electrical!=*electrical)continue;
            if(ticket<weight(c))return c;
            ticket-=weight(c);
        }
        return fallback;
    }
    inline bool SV_ZmValidDeathClip(const SvZmDeathClip &c)
    {
        return c.animation>0 && c.animation<4096 && c.milliseconds>=1000 &&
            c.milliseconds<=6000 && c.weight>0 && c.weight<=10;
    }
}
