local function entity_reference(entity_num)
    if entity_num == nil then
        return nil
    end
    return codol.entity(entity_num)
end

assert(codol.on("player_damage", function(player, event)
    local inflictor = entity_reference(event.inflictor_entity_num)
    local attacker = entity_reference(event.attacker_entity_num)
    local damage_target = player
    local damage = event.damage
    local builtin = "method:finishplayerdamage"
    local shared_target = nil

    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        -- TODO(CODOL): apply native no-protection and producer-specific
        -- exemptions once those damage flags and event classes are restored.
        local attacker_player = codol.player(event.attacker_entity_num)
        local same_team, team_error = codol.call(
            "method:issameteam", player, attacker_player)
        if team_error == nil and same_team then
            local mode = codol_friendly_fire_mode
            if mode == 0 then
                return
            elseif mode == 1 then
                damage_target = player
            elseif mode == 2 then
                damage_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            elseif mode == 3 then
                builtin = "method:finishsharedplayerdamage"
                shared_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            else
                print("player_damage deferred", "invalid friendly-fire mode", mode)
                return
            end
        end
    end

    local _, error_message, error_code
    if shared_target ~= nil then
        _, error_message, error_code = codol.call(
            builtin,
            damage_target,
            shared_target,
            inflictor,
            attacker,
            damage,
            event.damage_flags,
            event.method_of_death,
            event.weapon_asset_index,
            event.point,
            event.direction,
            event.hit_location,
            event.time_offset,
            event.bone_index)
    else
        _, error_message, error_code = codol.call(
            builtin,
            damage_target,
            inflictor,
            attacker,
            damage,
            event.damage_flags,
            event.method_of_death,
            event.weapon_asset_index,
            event.point,
            event.direction,
            event.hit_location,
            event.time_offset,
            event.bone_index)
    end
    if error_message ~= nil then
        -- TODO(CODOL): last stand and producer-specific protection branches
        -- remain fail-closed until their native state owners are restored.
        print("player_damage deferred", error_message, error_code)
    end
end))
