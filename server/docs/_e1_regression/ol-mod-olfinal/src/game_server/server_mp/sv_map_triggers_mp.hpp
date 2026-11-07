#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <span>
#include <string_view>
#include <utility>

namespace CodolGameServer
{
    // THE USABLE VOLUMES, READ OUT OF THE MAP RATHER THAN GUESSED.
    //
    // A brush trigger is `?N` -- a namespace of its own that
    // has nothing to do with the visible `*N` brush models, even though entityState
    // +0x09C stores the bare N for both (zm_factory_sh has a `*88` and a `?88`, and the
    // const baseline table stores 88 for each). `?N` is NOT in the clipmap's cmodel
    // array; it indexes `MapEnts.trigger`, which the map fastfile carries immediately
    // behind the entity string as TriggerModel / TriggerHull / TriggerSlab.
    //
    // So none of this can be reached through the collision bindings the way a door's
    // clipHandle is, and none of it needs to be: it is static map data, so it ships here
    // the same way the const baselines do. See re/demo-re/19-entity-numbering-and-triggers.md.
    //
    // Regenerate with:
    //   python Tools/gen-mapent-numbering.py out.exe <map>.ff <map>_const.ff \
    //       --cpp .../sv_map_triggers_mp.cpp
    // ONE HALF-SPACE PAIR CUTTING THE BOX. `TriggerSlab` in the map fastfile: a unit
    // normal, and the interval along it the volume occupies, both in the trigger's own
    // local frame. Every trigger_use in the four zm maps is exactly ONE hull, but many
    // are not axis-aligned. Campaign progression triggers can contain several hulls;
    // every hull has its own AABB and slab run below.
    struct SvTriggerSlab
    {
        std::array<float, 3> direction{};
        float midPoint{};
        float halfSize{};
    };

    struct SvTriggerHull
    {
        std::array<float, 3> midpoint{};
        std::array<float, 3> halfSize{};
        std::uint16_t slabFirst{};
        std::uint16_t slabCount{};
    };

    struct SvMapTrigger
    {
        // The `?N` from the entity string's `model` key. Stable, and the only identifier
        // a trigger has that is not a name.
        std::uint16_t triggerIndex{};
        // World position, straight off the entity's `origin` key.
        //
        // THE HULL IS ENTITY-LOCAL, which is the whole reason this pairing works: every
        // trigger_use hull midpoint in zm_factory_sh is within a unit of (0,0,0) --
        // median 0.5 -- so the origin below is where the box actually sits and halfSize
        // is how big it is.
        std::array<float, 3> origin{};
        std::array<float, 3> halfSize{};
        // HOW MUCH OF THE VOLUME halfSize ACTUALLY DESCRIBES. Carried so a caller can
        // tell a complete box from a partial one rather than treating the first hull as
        // the whole thing: 53 of zm_factory_sh's 54 trigger_use are one hull with no
        // slabs, and the 54th (`?77`, a zombie_door) has two slab planes cutting it.
        // A containment test that ignores these is CONSERVATIVE on hulls (it can only
        // miss volume) and OPTIMISTIC on slabs (it can only claim volume it should not).
        // SV_MapTriggerTouches evaluates slabs and refuses multi-hull records.
        std::uint16_t hullCount{};
        // Index into SvMapTriggerTable::hulls. halfSize above mirrors the first
        // hull for prompt prioritisation and existing diagnostics.
        std::uint16_t hullFirst{};
        // Index and count into the map's own flat slab array (SvMapTriggerTable::slabs).
        std::uint16_t slabFirst{};
        std::uint16_t slabCount{};
        // The `zombie_cost` key, 0 when the entity does not carry one.
        std::uint32_t cost{};
        std::string_view targetname;
        std::string_view noteworthy;
        // The map entity's `target` key. Door/debris trigger_use entities point this
        // at the brush/script-model group which retail opens when use is accepted.
        std::string_view target;
        // The authored progression flag. Factory's ordinary doors/debris use
        // enter_* values; those are the authoritative link from a purchased
        // doorway to the zone which becomes spawn-eligible.
        std::string_view scriptFlag;
    };

    struct SvMapTriggerTable
    {
        std::string_view mapName;
        std::span<const SvMapTrigger> triggers;
        std::span<const SvTriggerHull> hulls;
        // Every slab of every trigger on this map, flat; SvMapTrigger indexes into it.
        std::span<const SvTriggerSlab> slabs;
    };

    // THE DOOR-TO-ZONE LINK, KEPT BESIDE THE EXTRACTED TRIGGER IDENTITY.
    // Factory's ordinary doors publish enter_* script flags.  The two electric
    // doors are the one authored exception: retail opens both from the power
    // switch, neither carries a script_flag, and both lead into the map's
    // outside_south_zone player-volume union.  Returning an empty view means a
    // trigger changes no spawn-zone eligibility.
    [[nodiscard]] inline constexpr std::string_view SV_ZmZoneUnlockedByTrigger(
        const SvMapTrigger &trigger)
    {
        if (trigger.noteworthy == "factory_electric_door")
            return "outside_south_zone";

        constexpr std::pair<std::string_view, std::string_view> links[] = {
            { "enter_outside_west", "outside_west_zone" },
            { "enter_outside_east", "outside_east_zone" },
            { "enter_tp_south", "tp_south_zone" },
            { "enter_tp_east", "tp_east_zone" },
            { "enter_tp_west", "tp_west_zone" },
            { "enter_wnuen_building", "wnuen_zone" },
            { "enter_wnuen_loading_dock", "wnuen_bridge_zone" },
            { "enter_wuen_loading_dock", "wnuen_bridge_zone" },
            { "enter_warehouse_building", "warehouse_bottom_zone" },
            { "enter_warehouse_second_floor", "warehouse_top_zone" },
        };
        for (const auto &[scriptFlag, zone] : links)
            if (trigger.scriptFlag == scriptFlag)
                return zone;
        return {};
    }

    // Null when this build ships no extracted table for the map. Callers degrade to
    // "no usable prompts", never to a guess.
    [[nodiscard]] const SvMapTriggerTable *SV_MapTriggerTable(std::string_view mapName);

    [[nodiscard]] inline const SvMapTrigger *SV_FindMapTrigger(
        const SvMapTriggerTable *const table,
        const std::uint16_t triggerIndex)
    {
        if (!table)
            return nullptr;
        for (const auto &trigger : table->triggers)
        {
            if (trigger.triggerIndex == triggerIndex)
                return &trigger;
        }
        return nullptr;
    }

    // A HINT STRING IS NOT ALWAYS ONE KEY. Two separator bytes appear in the retail
    // captures' hint band, and both are part of the value the server writes:
    //
    //   0x14   the rest is ANOTHER LOCALIZATION KEY, used as an argument
    //          `ZOMBIE_TRADE_WEAPON\x14ZOMBIE_TESLA_GUN`
    //   0x15   the rest is a LITERAL, used as an argument
    //          `ZOMBIE_TELEPORT_TO_CORE\x151.5`
    //
    // and they compose, literal first:
    //   `ZOMBIE_PERK_JUGGERNAUT\x154\x14ZOMBIE_PERK_JUGGERNAUT_EXP`
    //
    // Write these with adjacent string literals, never as one `"...\x152..."` -- a hex
    // escape is greedy and would swallow the digit that follows it.
    inline constexpr char HintArgumentKey = '\x14';
    inline constexpr char HintArgumentLiteral = '\x15';

    // WHICH PROMPT A TRIGGER GETS. Matched on the map's own keys, first rule wins, and
    // a trigger no rule matches gets NO prompt rather than a generic one.
    struct SvTriggerHintRule
    {
        std::string_view targetname;   // exact match, or empty to ignore
        std::string_view noteworthy;   // exact match, or empty to ignore
        std::uint32_t cost{};          // exact match, or 0 to ignore
        std::string_view hintString;
    };

    // EVERY STRING HERE IS RETAIL'S, not this project's wording.
    //
    // Four of them are pinned by the `ncs_hnt_localized_common_gametype_zm` block that
    // preloads the low end of the band, in the order the 7-31 capture publishes relative
    // indices 3, 4, 5 and 6 on a zombie_debris, four zombie_doors, the two trap triggers
    // and the use_elec_switch. The rest are the values retail's own server wrote into
    // that band during the five captures, paired to a trigger by the entity number the
    // hint named -- see re/demo-re/19-entity-numbering-and-triggers.md section 4.
    //
    // THE PERK LITERALS ARE STATE THIS SERVER DOES NOT HAVE. Pack-a-Punch appears with
    // 2, 3 AND 4 across the captures and quick revive with 2 and 3, so the number is a
    // runtime value -- a price or a tier -- not a constant of the machine. Each is
    // pinned here to the value retail was observed sending, lowest where more than one
    // was seen, and it will need to move when a battery economy exists.
    inline constexpr SvTriggerHintRule TriggerHintRules[] = {
        // Purchases. The cost is baked into retail's KEY, not passed as an argument,
        // and 1000 is the only door or debris cost the game ships a string for.
        { "zombie_door", "", 1000, "ZOMBIE_BUTTON_BUY_OPEN_DOOR_1000" },
        { "zombie_debris", "", 1000, "ZOMBIE_BUTTON_BUY_CLEAR_DEBRIS_1000" },
        // The two trap triggers. `auto407` is the map's own targetname for them and
        // both of factory's carry it; the capture hints both on relative index 5.
        { "auto407", "", 0, "ZOMBIE_BUTTON_BUY_TRAP" },
        { "use_elec_switch", "", 0, "ZOMBIE_ELECTRIC_SWITCH" },
        // The mystery box. Retail cycles this string as the offer changes -- trap
        // swaps, weapon trades, max ammo -- so the base offer is what goes here.
        { "treasure_chest_use", "", 0, "ZOMBIE_RANDOM_WEAPON_1000" },
        // The ammo crates, keyed on `script_noteworthy` ALONE because their targetname
        // is per-map boilerplate -- `pf734_auto1` on factory, `pf1904_auto1` on sumpf and
        // so on -- while every one of the 23 across the four maps carries
        // `ammobox_trigger`. An empty targetname in a rule means "any".
        //
        // The capture hints these on `ZOMBIE_CRATE_AMMO_REFILL_WW`, but the plain refill
        // is the general case and the WW one is the wonder-weapon variant of it, which
        // needs a weapon check this server cannot make yet.
        { "", "ammobox_trigger", 0, "ZOMBIE_CRATE_AMMO_REFILL" },
        // The perk machines, keyed on the machine's OWN `script_noteworthy`, which is
        // the specialty it dispenses. That pairing is measured, not assumed: entity 256
        // is `specialty_fastreload` and the capture hints it with FASTRELOAD, entity 263
        // is `specialty_armorvest` and is hinted with JUGGERNAUT.
        { "zombie_vending", "specialty_quickrevive", 0,
          "ZOMBIE_PERK_QUICKREVIVE\x15" "2\x14" "ZOMBIE_PERK_QUICKREVIVE_EXP" },
        { "zombie_vending", "specialty_fastreload", 0,
          "ZOMBIE_PERK_FASTRELOAD\x15" "3\x14" "ZOMBIE_PERK_FASTRELOAD_EXP" },
        { "zombie_vending", "specialty_armorvest", 0,
          "ZOMBIE_PERK_JUGGERNAUT\x15" "4\x14" "ZOMBIE_PERK_JUGGERNAUT_EXP" },
        { "zombie_vending", "specialty_rof", 0,
          "ZOMBIE_PERK_DOUBLETAP\x15" "2\x14" "ZOMBIE_PERK_DOUBLETAP_EXP" },
        { "zombie_vending_upgrade", "specialty_weapupgrade", 0,
          "ZOMBIE_PERK_PACKAPUNCH\x15" "2\x14" "ZOMBIE_PERK_PACKAPUNCH_EXP" },
        // The teleporter. INACTIVE is the honest base state: the pads do not work until
        // the power is on, and nothing in this server turns it on yet. Retail moves
        // these to POWER_UP_TPAD, LINK_TPAD, TELEPORT_COOLDOWN and TELEPORT_TO_CORE as
        // the sequence progresses -- all four strings are catalogued in
        // re/demo-re/hint-strings/ for when that sequence exists.
        { "trigger_teleport_core", "", 0, "ZOMBIE_LINK_TPAD" },
        { "trigger_teleport_pad_0", "", 0, "ZOMBIE_INACTIVE_TPAD" },
        { "trigger_teleport_pad_1", "", 0, "ZOMBIE_INACTIVE_TPAD" },
        { "trigger_teleport_pad_2", "", 0, "ZOMBIE_INACTIVE_TPAD" },
        // The intel pickups. Twelve of them, all one targetname, and the capture ships
        // this string in its gamestate rather than mid-match.
        { "intel_collectible", "", 0, "SCRIPT_INTELLIGENCE_PICKUP" },
    };

    // Null when nothing matches, which is the answer for factory's `auto408`/`auto409`
    // building triggers and its `trig_ee` -- none of which retail was ever seen hinting.
    [[nodiscard]] inline const SvTriggerHintRule *SV_TriggerHintRule(
        const SvMapTrigger &trigger)
    {
        for (const auto &rule : TriggerHintRules)
        {
            if (!rule.targetname.empty() &&
                rule.targetname != trigger.targetname)
            {
                continue;
            }
            if (!rule.noteworthy.empty() && rule.noteworthy != trigger.noteworthy)
                continue;
            if (rule.cost && rule.cost != trigger.cost)
                continue;
            return &rule;
        }
        return nullptr;
    }

    // Does a box at `origin` with these half-extents overlap this trigger?
    //
    // A BOX, NOT A POINT, and that is not a detail. The doors sit with their volume
    // centred on the doorway -- `?68` is centred at z=143 with a half-height of 56, so
    // it spans 87..199 -- while a player's origin is at their FEET. Testing the origin
    // as a point puts the answer on the boundary and makes the prompt flicker with the
    // floor height. The player's own standing box is 70 units tall and 30 wide
    // (`StandingPlayerTraceBounds`), so overlapping boxes is both what the engine does
    // for a touch and what makes a doorway usable when you are standing in it.
    //
    // WHAT THE DEMO COULD NOT SETTLE: whether retail tests the box, the point, or adds a
    // view check. The recording client's own entity is never sent to itself, so the only
    // position track available is the playerState origin, and that is client-predicted
    // and asserted in about 5% of snapshots -- far too coarse at walking speed to tell a
    // 30-unit box from a point. This is the engine-standard touch rule, chosen
    // deliberately and written down as a choice rather than a measurement.
    //
    // REFUSES WHAT IT CANNOT ANSWER. Slab planes are evaluated exactly. A trigger with
    // more than one hull still has only its first hull's extents in this table, so
    // answering "yes" would light a prompt or mission phase in space it does not occupy.
    [[nodiscard]] inline bool SV_MapTriggerTouches(
        const SvMapTriggerTable &table,
        const SvMapTrigger &trigger,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &boxMidpoint,
        const std::array<float, 3> &boxHalfSize)
    {
        if (!trigger.hullCount ||
            static_cast<std::size_t>(trigger.hullFirst) + trigger.hullCount >
                table.hulls.size())
        {
            return false;
        }
        for (std::size_t hullIndex = 0; hullIndex < trigger.hullCount;
             ++hullIndex)
        {
            const auto &hull = table.hulls[trigger.hullFirst + hullIndex];
            bool overlaps = true;
            for (std::size_t axis = 0; axis < 3; ++axis)
            {
                const auto centre = origin[axis] + boxMidpoint[axis];
                const auto hullCentre = trigger.origin[axis] + hull.midpoint[axis];
                if (std::fabs(centre - hullCentre) >
                    hull.halfSize[axis] + boxHalfSize[axis])
                {
                    overlaps = false;
                    break;
                }
            }
            if (!overlaps)
                continue;
            if (static_cast<std::size_t>(hull.slabFirst) + hull.slabCount >
                table.slabs.size())
            {
                return false;
            }
            // THE SLABS CUT THIS HULL'S BOX. Project the player AABB onto each
            // slab normal and widen by its support extent.
            for (std::size_t index = 0; index < hull.slabCount; ++index)
            {
                const auto &slab = table.slabs[hull.slabFirst + index];
                float projected = 0.0f;
                float support = 0.0f;
                for (std::size_t axis = 0; axis < 3; ++axis)
                {
                    projected += slab.direction[axis] *
                        (origin[axis] + boxMidpoint[axis] -
                            trigger.origin[axis]);
                    support +=
                        std::fabs(slab.direction[axis]) * boxHalfSize[axis];
                }
                if (std::fabs(projected - slab.midPoint) >
                    slab.halfSize + support)
                {
                    overlaps = false;
                    break;
                }
            }
            if (overlaps)
                return true;
        }
        return false;
    }

    // The PROMPTABLE trigger a box at `origin` is standing in, or null.
    //
    // Only triggers a hint rule matches are considered, so one with no prompt can never
    // shadow one that has a prompt by being tighter. When two promptable volumes
    // overlap -- and zm's do, a door and a debris purchase can share a doorway -- the
    // SMALLEST wins, because the tighter volume is the more specific thing the player
    // is standing at.
    [[nodiscard]] inline const SvMapTrigger *SV_PromptableTriggerAt(
        const SvMapTriggerTable *const table,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &boxMidpoint,
        const std::array<float, 3> &boxHalfSize,
        const SvTriggerHintRule **const outRule = nullptr)
    {
        if (outRule)
            *outRule = nullptr;
        if (!table)
            return nullptr;
        const SvMapTrigger *best = nullptr;
        const SvTriggerHintRule *bestRule = nullptr;
        float bestVolume = 0.0f;
        for (const auto &trigger : table->triggers)
        {
            const auto *const rule = SV_TriggerHintRule(trigger);
            if (!rule)
                continue;
            if (!SV_MapTriggerTouches(*table, trigger, origin, boxMidpoint,
                                      boxHalfSize))
            {
                continue;
            }
            const auto volume = trigger.halfSize[0] * trigger.halfSize[1] *
                trigger.halfSize[2];
            if (!best || volume < bestVolume)
            {
                best = &trigger;
                bestRule = rule;
                bestVolume = volume;
            }
        }
        if (outRule)
            *outRule = bestRule;
        return best;
    }
}
