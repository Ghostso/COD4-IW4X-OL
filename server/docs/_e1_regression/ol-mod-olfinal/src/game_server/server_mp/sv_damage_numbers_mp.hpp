#pragma once

#include <algorithm>
#include <array>
#include <cstdint>

namespace CodolGameServer
{
    // CODREF(sv_write_snapshot_to_client): exact OLFinal out.exe
    // 0x67406E..0x674112 reads T15 as slot5, sequence4, style4, amount12,
    // entity11 into 32 six-byte records at ps+0x3752. This is a source
    // projection, deliberately outside the address-sensitive SvPlayerState.
    struct SvDamageNumber
    {
        std::uint8_t sequence{}, style{};
        std::uint16_t amount{}, entity{};
        bool operator==(const SvDamageNumber &) const = default;
    };
    using SvDamageNumberRing = std::array<SvDamageNumber, 32>;

    // OLMOD(reconstructed-zm-feedback): proposed presentation criteria, NOT a
    // recovered CODOL server predicate. Enabled only by explicit opt-in.
    struct SvZmFeedbackFacts
    {
        bool lethal{}, headRemoved{}, bodyPartRemoved{}, headlessDecay{}, melee{}, headHit{};
    };
    inline std::uint8_t SV_ReconstructedZmNumberStyle(const SvZmFeedbackFacts &f)
    {
        // CODREF(561F15): native fallback styles3/4 are orange. This producer's
        // head/decay rule is reconstructed. Original recordings show orange
        // without removal and white with removal; neither death nor limb loss
        // alone selects orange. No extra damage multiplier is applied here.
        return f.headHit || f.headlessDecay ? 3 : 0;
    }
    inline std::uint32_t SV_ReconstructedZmKillReward(const SvZmFeedbackFacts &f)
    {
        // CODREF(sv_write_snapshot_to_client): original Factory J profile patches
        // and blue HUD agree on 60 ordinary / 80 headshot-counted kill. This is
        // the entire finishing award, not a bonus on top of another ten points.
        // TODO(CODOL): recover all special-kill predicates. Melee100 is retained
        // reconstruction; the video90 observation is not a universal native rule.
        return !f.lethal ? 0u : f.melee ? 100u :
            (f.headHit && !f.headlessDecay) ? 80u : 60u;
    }
    // OLMOD(zm-score-owner): one admitted zombie damage transaction owns both
    // currencies. Native score and raw battery are independent counters.
    struct SvZmAward
    {
        std::uint32_t score{}, battery{};
        bool kill{}, headshot{};
        bool operator==(const SvZmAward &) const = default;
    };
    inline SvZmAward SV_ZmDamageAward(const SvZmFeedbackFacts &f)
    {
        // Original July31 Factory: nonlethal hits +10/+10, ordinary kill
        // +60/+30, headshot-counted kill +80/+40 (score/raw battery).
        // OLMOD(zm-score-unrecovered): nonlethal decay awards nothing; melee
        // battery50 is reconstruction pending an isolated original sample.
        if (!f.lethal) return f.headlessDecay ? SvZmAward{} : SvZmAward{10,10};
        const bool headshot=f.headHit && !f.headlessDecay && !f.melee;
        return {SV_ReconstructedZmKillReward(f),f.melee?50u:headshot?40u:30u,true,headshot};
    }
    struct SvZmAwardEvent
    {
        std::uint32_t clientNum{}, spawnSequence{};
        std::uint8_t spawnGeneration{};
        SvZmAward award;
        bool operator==(const SvZmAwardEvent &) const = default;
    };
    struct SvZmScoreFeedback
    {
        std::uint32_t clientNum{}, spawnSequence{};
        std::uint8_t spawnGeneration{};
        std::uint32_t value{}, startedAt{};
        bool active{};
    };
    inline void SV_AccumulateZmScore(SvZmScoreFeedback &state,
        std::uint32_t reward, std::uint32_t now)
    {
        if (!reward) return;
        // OLMOD(reconstructed-zm-score-window):1000ms fits9/9 original reward
        // bursts including two triple kills. Exact native boundary is unknown.
        if (!state.active || now < state.startedAt || now-state.startedAt > 1000)
            state.value=0;
        // Stay within exactly representable integer floats for the native Value HUD.
        state.value=std::min(16777215u,state.value+std::min(reward,16777215u));
        state.startedAt=now;state.active=true;
    }

    struct SvClientDamageNumbers
    {
        std::uint32_t clientNum{}, spawnSequence{};
        std::uint8_t spawnGeneration{};
        std::uint8_t cursor{};
        SvDamageNumberRing records{};
        bool operator==(const SvClientDamageNumbers &) const = default;
    };

    inline bool SV_AppendDamageNumber(SvClientDamageNumbers &state,
        std::uint32_t entity, std::uint32_t damage, std::uint8_t style = 0)
    {
        // OLMOD(damage-number-admission): reject invalid identities before
        // narrowing; saturation affects display only, never combat damage.
        if (entity >= 2047 || !damage || style > 15 || state.cursor >= 32)
            return false;
        auto &record = state.records[state.cursor];
        // CODREF(561776): zero is an inactive record, not a visible hit.
        // OLMOD(damage-number-producer): cycle 1..15 to preserve that contract;
        // the deleted native server's sequence-increment policy is unknown.
        record.sequence = static_cast<std::uint8_t>(record.sequence % 15u + 1u);
        record.style = style;
        record.amount = static_cast<std::uint16_t>(std::min(damage, 4095u));
        record.entity = static_cast<std::uint16_t>(entity);
        state.cursor = static_cast<std::uint8_t>((state.cursor + 1u) % 32u);
        return true;
    }

    inline bool SV_ValidDamageNumbers(const SvClientDamageNumbers &state)
    {
        return state.clientNum < 32 && state.cursor < 32 &&
            std::ranges::all_of(state.records, [](const auto &record) {
                return record.sequence <= 15 && record.style <= 15 &&
                    record.amount <= 4095 && record.entity < 2047 &&
                    (!record.sequence || record.amount != 0);
            });
    }

    template<class Writer>
    void SV_WriteDamageNumbers(Writer &message, const SvDamageNumberRing *current,
        const SvDamageNumberRing *baseline)
    {
        // CODREF(sv_write_snapshot_to_client): use the same acknowledged
        // immutable frame as the rest of playerstate, never the last packet sent.
        // No current owner leaves the baseline untouched; it cannot fabricate hits.
        if (current)
            for (unsigned slot = 0; slot < current->size(); ++slot)
            {
                const auto &record = (*current)[slot];
                if (record.sequence == (baseline ? (*baseline)[slot].sequence : 0))
                    continue;
                message.MSG_WriteBits(1, 1);
                message.MSG_WriteBits(slot, 5);
                message.MSG_WriteBits(record.sequence, 4);
                message.MSG_WriteBits(record.style, 4);
                message.MSG_WriteBits(record.amount, 12);
                message.MSG_WriteBits(record.entity, 11);
            }
        message.MSG_WriteBits(0, 1);
    }
}
