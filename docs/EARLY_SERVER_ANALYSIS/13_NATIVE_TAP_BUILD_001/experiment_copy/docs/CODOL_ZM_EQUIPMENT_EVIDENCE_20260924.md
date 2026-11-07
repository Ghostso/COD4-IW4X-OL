# Zombies equipment evidence (2026-09-24)

Shared evidence for the zombies equipment, trap, perk-pop and power-up work.
Everything here was MEASURED from the shipped C1 1.1.1.13 zones or the live
server on 2026-09-24; nothing is inferred from IW4/T5 unless labelled.

## 1. The roster (mounted mp/cyborgclasstable.csv, dumped live)

Columns: 0 key | 1 code | 2 sex | 3 head | 4 portrait | 5 pistol | 6 unused |
7 lethal | 8 special | 9 trap | 10 perk pop a | 11 perk pop b. Cells carry
stray tabs/spaces; trim them.

| key | code | pistol | lethal | special | trap | perk pops |
|---|---|---|---|---|---|---|
| zm1 | lb | m1911_zm | semtex_grenade_zm | teleporter_zm | trap_shock_zm | perkpop_discount_zm, perkpop_electro_zm |
| zm2 | danby | m1911dw_zm | money_ball_zm | zombie_cymbal_monkey | trap_freeze_zm | perkpop_deadshot_zm, perkpop_additionalprimary_zm |
| zm3 | hh | m1911_zm | bouncingbetty_zm | zombie_black_hole_bomb | trap_fire_zm | perkpop_longersprint_zm, perkpop_scavenger_zm |
| zm4 | lg | m1911_zm | money_ball_zm | revive_knife_zm | trap_shrink_zm | perkpop_flakjacket_zm, perkpop_carpenter_zm |

`zm/maps/mp/gametypes/_zombiemode_equipment.gsc` gives this kit: pistol, then
`setOffhandEquipment( lethal, special, trap )`. C1 offhand buttons: slot 0
lethal = frag 0x4000, slot 1 = 0x8000, slot 2 = 0x10000
(`src/codol/weapon/codol_weapon_state.c` CODOL_OFFHAND_BUTTON_*).

Item modules hook in with
`maps\mp\gametypes\_zombiemode_equipment::register_equipment( weapon, ::cb )`;
`cb` runs as `<grenade> thread [[ cb ]]( <player>, <weapon> )` on the engine's
own `grenade_fire` for that weapon.

## 2. What C1 says each item does (localized_code_post_gfx_mp, GBK)

| key | C1 text | English |
|---|---|---|
| `CHALLENGE_ZM_TRAPS` | 陷阱专家 | Trap expert |
| `CHALLENGE_ZM_TRAPS_DESC` | 打开&&1个陷阱 | Activate &&1 traps |
| `PERKS_PERKPOP_ZM` | 连续生存奖励 | Survival streak reward |
| `SF_UI_BOUNCINGBETTY_ZM_DESC` | 如有机械僵尸接近，跳雷会从地面飞起造成范围爆炸 | When a robot zombie comes near, the betty springs from the ground and explodes over an area. |
| `SF_UI_BOUNCINGBETTY_ZM_NAME` | 跳雷（僵尸围城模式） |  |
| `SF_UI_MONEY_KNIFE_ZM_DESC` | 升级版粘性手雷，可吸附在物体上且每炸死一个机械僵尸可额外获得100分 | Upgraded sticky grenade: sticks to objects, and every robot zombie it kills earns an extra 100 points. |
| `SF_UI_MONEY_KNIFE_ZM_NAME` | 金钱手雷（僵尸围城模式） | Money grenade (Zombies) |
| `SF_UI_PERKPOP_ADDITIONALPRIMARY_ZM_DESC` | 可多携带一把主武器 | Carry one more primary weapon. |
| `SF_UI_PERKPOP_ADDITIONALPRIMARY_ZM_NAME` | 双主武（僵尸围城模式） |  |
| `SF_UI_PERKPOP_ARMORVEST_ZM_DESC` | 短时间增加玩家血量 | Briefly raises the player's health. |
| `SF_UI_PERKPOP_ARMORVEST_ZM_NAME` | 重装汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_DEADSHOT_ZM_DESC` | 减小准心尺寸和狙击枪开镜时的摇晃 | Smaller crosshair and less sniper-scope sway. |
| `SF_UI_PERKPOP_DEADSHOT_ZM_NAME` | 精准汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_DISCOUNT` | 返还10%的购买金额 | Refunds 10% of purchase prices. |
| `SF_UI_PERKPOP_FASTRELOAD_ZM_DESC` | 短时间内提升换弹速度 | Briefly faster reloads. |
| `SF_UI_PERKPOP_FASTRELOAD_ZM_NAME` | 快手汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_FLAKJACKET_ZM_DESC` | 对爆炸和摔落伤害免疫，跳扑时会产生小范围爆炸 | Immune to explosive and fall damage; diving to prone causes a small explosion. |
| `SF_UI_PERKPOP_FLAKJACKET_ZM_NAME` | 防爆汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_LONGERSPRINT_ZM_DESC` | 短时间内提升冲刺持续时间 | Briefly longer sprint duration. |
| `SF_UI_PERKPOP_LONGERSPRINT_ZM_NAME` | 耐力汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_QUICKREVIVE_ZM_DESC` | 短时间内增加复活队友的速度 | Briefly faster teammate revives. |
| `SF_UI_PERKPOP_QUICKREVIVE_ZM_NAME` | 速救汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_ROF_ZM_DESC` | 短时间内增加射速 | Briefly higher rate of fire. |
| `SF_UI_PERKPOP_ROF_ZM_NAME` | 速射汽水（僵尸围城模式） |  |
| `SF_UI_PERKPOP_SCAVENGER` | 能从死亡的机械僵尸身上补充弹药 | Resupply ammo from dead robot zombies. |
| `SF_UI_PLACEABLE_PROXIMITY_ALARM_ZM_DESC` | 机械僵尸接近时发出警报 | Sounds an alarm when robot zombies approach. |
| `SF_UI_PLACEABLE_PROXIMITY_ALARM_ZM_NAME` | 警报器（僵尸围城模式） |  |
| `SF_UI_PLACEABLE_TELEPORTER_ZM_DESC` | 撕裂空间制造出一个裂口，籍由该裂口玩家会被随机传送至已探索过的区域 | Tears space open into a rift; a player who goes through it is teleported at random to an area already explored. |
| `SF_UI_PLACEABLE_TELEPORTER_ZM_NAME` | 随机传送门（僵尸围城模式） | Random teleporter (Zombies) |
| `SF_UI_PLACEABLE_TRAP_FIRE_ZM_DESC` | 在地上放置一个火焰陷阱。每烧死一个机械僵尸，陷阱持续时间增加2秒。 | Place a fire trap on the ground. Each robot zombie burned to death extends the trap by 2 seconds. |
| `SF_UI_PLACEABLE_TRAP_FIRE_ZM_NAME` | 火焰陷阱（僵尸围城模式） |  |
| `SF_UI_PLACEABLE_TRAP_FREEZE_ZM_DESC` | 在地上放置一个寒冰陷阱冰冻靠近的机械僵尸。 | Place an ice trap on the ground that freezes approaching robot zombies. |
| `SF_UI_PLACEABLE_TRAP_FREEZE_ZM_NAME` | 寒冰陷阱（僵尸围城模式） |  |
| `SF_UI_PLACEABLE_TRAP_SHOCK_ZM_DESC` | 在地上放置一个电击陷阱，电击陷阱可以和其他电击陷阱相互连接制造出更大的电网 | Place a shock trap on the ground; shock traps link with other shock traps into a larger electric grid. |
| `SF_UI_PLACEABLE_TRAP_SHOCK_ZM_NAME` | 电击陷阱（僵尸围城模式） |  |
| `SF_UI_PLACEABLE_TRAP_SHRINK_ZM_DESC` | 在地上放置一个侏儒陷阱，靠近的机械僵尸会被缩小成可被直接踢飞的机械侏儒 | Place a dwarf trap on the ground; approaching robot zombies shrink into robot dwarves that can be kicked away. |
| `SF_UI_PLACEABLE_TRAP_SHRINK_ZM_NAME` | 侏儒陷阱（僵尸围城模式） |  |
| `SF_UI_REVIVE_KNIFE_ZM_DESC` | 投掷类武器，可远距离救活被击倒的队友，并造成小范围伤害 | Thrown weapon: revives a downed teammate at range, and does small-area damage. |
| `SF_UI_REVIVE_KNIFE_ZM_NAME` | 救援飞刀（僵尸围城模式） | Rescue throwing knife (Zombies) |
| `SF_UI_SEMTEX_GRENADE_ZM_DESC` | 投掷后可吸附在物体上 | Sticks to objects when thrown. |
| `SF_UI_SEMTEX_GRENADE_ZM_NAME` | 粘性手雷（僵尸围城模式） |  |
| `SF_UI_ZOMBIE_BLACK_HOLE_BOMB_DESC` | 将机械僵尸吸入一个黑洞并把它们碾碎 | Pulls robot zombies into a black hole and crushes them. |
| `SF_UI_ZOMBIE_BLACK_HOLE_BOMB_NAME` | 黑洞手雷（僵尸围城模式） |  |
| `SF_UI_ZOMBIE_CYMBAL_MONKEY_DESC` | 吸引机械僵尸注意，数秒后爆炸 | Attracts robot zombies' attention, explodes after a few seconds. |
| `SF_UI_ZOMBIE_CYMBAL_MONKEY_NAME` | 猴子炸弹（僵尸围城模式） |  |

The perk pops are "survival streak rewards" (PERKS_PERKPOP_ZM) and have their
own rows in mp/coKillstreakStatsTable.csv: rows 59-68, cost column 4 = 3
(perkpop_pandora_zm = 6), activation weapon column 13 = the perkpop weapon,
icons in columns 15-17/20. The kis_* rows 44-58 have cost 0 and put their icon
in the crate column 16: drop power-ups (see
`zm/maps/mp/gametypes/_zombiemode_powerups.gsc`). Rows 54 sentry_zm and 55
rcbomb_zm name the multiplayer weapons killstreak_sentry_mp and rcbomb_mp.

## 3. Weapon data (codol_checkweapon on zm_prototype_sh)

type 1 = grenade, 2 = projectile; inventory 0 primary, 1 offhand, 2 item;
class 5 = grenade, 6 = rocket launcher; offhand class 1 frag, 2 smoke/tactical,
4 throwing knife, 5 betty.

| weapon | type/inv/class | offhand | clip/max | fire ms | world model |
|---|---|---|---|---|---|
| money_ball_zm | 1/1/5 | 1 | 2/2 | 360 | weapon_semtex_grenade |
| semtex_grenade_zm | 1/1/5 | 1 | 2/2 | 360 | weapon_semtex_grenade |
| bouncingbetty_zm | 1/1/5 | 5 | 3/3 | 800 | projectile_bouncing_betty_grenade |
| teleporter_zm | 1/1/5 | 2 | 2/2 | 699 | t5_tp_bomb_world |
| zombie_cymbal_monkey | 1/1/5 | 2 | 2/2 | 699 | viewmodel_zombie_cymbal_monkey |
| zombie_black_hole_bomb | 1/1/5 | 2 | 2/2 | 699 | t5_bh_bomb_world |
| revive_knife_zm | 1/1/5 | 4 | 2/2 | 550 | weapon_parabolic_knife |
| trap_shock_zm | 1/1/5 | 2 | 2/2 | 699 | t5_ts_bomb_world |
| trap_freeze_zm | 1/1/5 | 2 | 2/2 | 699 | t5_tz_bomb_world |
| trap_fire_zm | 1/1/5 | 2 | 2/2 | 699 | t5_tf_bomb_world |
| trap_shrink_zm | 1/1/5 | 2 | 2/2 | 699 | t5_tk_bomb_world |
| perkpop_*_zm | 1/2/5 | 0 | 1/1 | 2000 | zombie_3rd_perk_bottle_revive (view codo_perk_can_ads) |
| kis_*_zm | 1/2/5 | 0 | 1/1 | 100 | weapon_uav_control_unit |
| tesla_gun_zm | 2/0/6 | 0 | 3/18 | 1000 | weapon_usa_tesla |
| minigun_zm | 0/0/1 | 0 | 500/500 | 50 | t5_weapon_carry_minigun_world |

Full dump: `docs/zm_evidence/zm_items_weapons.txt`.

## 4. Relevant zombies-zone assets (docs/zone_assets/common_gametype_zm.txt)

```
fx	env/electrical/fx_elec_short_oneshot
fx	env/electrical/fx_elec_sparking_oneshot
fx	env/electrical/fx_elec_wire_spark_burst
fx	env/electrical/fx_elec_wire_spark_dl_oneshot
fx	env/fire/fx_fire_player_md
fx	env/fire/fx_fire_player_torso
fx	explosions/sentry_gun_explosion
fx	explosions/sentry_gun_explosion_instant
fx	fire/cigar_glow
fx	fire/fire_smoke_trail_m_invasion
fx	fire/firelp_med_pm
fx	impacts/fx_decal_scorch_fire_md
fx	impacts/fx_decal_scorch_fire_md_blue
fx	maps/zombie/fx_blackhole_zombie_breakup
fx	maps/zombie/fx_freeze_trap_active_loop
fx	maps/zombie/fx_portable_teleporter
fx	maps/zombie/fx_portable_teleporter_player
fx	maps/zombie/fx_zmb_blackhole_exit
fx	maps/zombie/fx_zmb_blackhole_flare_marker
fx	maps/zombie/fx_zmb_blackhole_implode
fx	maps/zombie/fx_zmb_blackhole_looping
fx	maps/zombie/fx_zmb_blackhole_trap_end
fx	maps/zombie/fx_zmb_blackhole_zombie_flare
fx	maps/zombie/fx_zmb_cola_revive_flicker
fx	maps/zombie/fx_zombie_dog_fire_trail
fx	maps/zombie/fx_zombie_fire_trap_med
fx	maps/zombie/fx_zombie_freeze_md
fx	maps/zombie/fx_zombie_freeze_torso
fx	maps/zombie/fx_zombie_monkey_light
fx	maps/zombie/fx_zombie_shrink_trap_looping
fx	maps/zombie/fx_zombie_tesla_bolt_secondary
fx	maps/zombie/fx_zombie_tesla_electric_bolt
fx	maps/zombie/fx_zombie_tesla_neck_spurt
fx	maps/zombie/fx_zombie_tesla_rail_view
fx	maps/zombie/fx_zombie_tesla_rail_view_ug
fx	maps/zombie/fx_zombie_tesla_shock
fx	maps/zombie/fx_zombie_tesla_shock_eyes
fx	maps/zombie/fx_zombie_tesla_shock_ground
fx	maps/zombie/fx_zombie_tesla_shock_secondary
fx	maps/zombie/fx_zombie_tesla_tube_view
fx	maps/zombie/fx_zombie_tesla_tube_view2
fx	maps/zombie/fx_zombie_tesla_tube_view2_ug
fx	maps/zombie/fx_zombie_tesla_tube_view3
fx	maps/zombie/fx_zombie_tesla_tube_view3_ug
fx	maps/zombie/fx_zombie_tesla_tube_view_ug
fx	maps/zombie/fx_zombie_tesla_ug_elec_bolt
fx	maps/zombie_temple/fx_ztem_monkey_shrink
fx	maps/zombie_temple/fx_ztem_zombie_mini_drown
fx	maps/zombie_temple/fx_ztem_zombie_mini_squish
fx	misc/fx_exp_raygun_fire_impact
fx	misc/fx_trail_raygun_fire_geotrail
fx	misc/fx_trail_raygun_fire_ring_emit
fx	misc/fx_zombie_cola_revive_on
fx	misc/light_moneyball_blink
fx	misc/light_moneyball_geotrail
fx	muzzleflashes/at4_flash_fire_child
fx	muzzleflashes/minigun_flash
fx	muzzleflashes/minigun_flash_tracer_view
fx	muzzleflashes/minigun_flash_view
fx	props/throwingknife_geotrail
fx	shellejects/sentry_turret_shell
fx	smoke/sentry_turret_overheat_smoke
fx	weapon/freeze_gun/fx_exp_freezegun_impact
fx	weapon/freeze_gun/fx_freezegun_crumple
fx	weapon/freeze_gun/fx_freezegun_crumple_ice
fx	weapon/freeze_gun/fx_freezegun_shatter
fx	weapon/freeze_gun/fx_freezegun_smoke_cloud
fx	weapon/freeze_gun/fx_trail_freezegun_blood_streak
fx	weapon/knife_ballistic/fx_trail_knife_ballistic
fx	weapon/muzzleflashes/fx_mini_cannon_flash_base1st
fx	weapon/muzzleflashes/fx_tesla_ug_view
fx	weapon/muzzleflashes/fx_tesla_ug_world
fx	weapon/muzzleflashes/fx_tesla_view
fx	weapon/muzzleflashes/fx_tesla_world
fx	weapon/quantum_bomb/area_effect
fx	weapon/quantum_bomb/fx_mystery_effect
fx	weapon/quantum_bomb/fx_player_position_effect
fx	weapon/quantum_bomb/fx_press
fx	weapon/quantum_bomb/fx_twist
fx	weapon/quantum_bomb/player_effect
fx	weapon/shellejects/fx_minigun
fx	weapon/shrink_ray/zombie_shrink
fx	weapon/shrink_ray/zombie_unshrink
fx	zombie/fire_head
sound	ac130_105mm_fire
sound	ac130_105mm_fire_npc
sound	ac130_105mm_fire_npc_sweet
sound	ac130_25mm_fire
sound	ac130_25mm_fire_npc
sound	ac130_40mm_fire
sound	ac130_40mm_fire_npc
sound	ai_zombie_quad_blackhole_crawl_fast_v1	~
sound	dst_electrical_large
sound	evt_electrical_surge
sound	evt_perk_bottle_open
sound	evt_perk_deny
sound	evt_perk_swallow
sound	evt_shrink
sound	evt_unshrink
sound	fly_bal_knife_load
sound	fly_bal_knife_load_npc
sound	fxt_fire_anim_flicker_1	~
sound	minigun_gatling_cooldown
sound	minigun_gatling_fire
sound	minigun_gatling_spin
sound	minigun_gatling_spindown1
sound	minigun_gatling_spindown2
sound	minigun_gatling_spindown3
sound	minigun_gatling_spindown4
sound	minigun_gatling_spinloop
sound	minigun_gatling_spinup1
sound	minigun_gatling_spinup2
sound	minigun_gatling_spinup3
sound	minigun_gatling_spinup4
sound	minigun_heli_gatling_cooldown
sound	minigun_heli_gatling_fire
sound	minigun_heli_gatling_spin
sound	minigun_heli_gatling_spindown1
sound	minigun_heli_gatling_spindown2
sound	minigun_heli_gatling_spindown3
sound	minigun_heli_gatling_spindown4
sound	minigun_heli_gatling_spinloop
sound	minigun_heli_gatling_spinup1
sound	minigun_heli_gatling_spinup2
sound	minigun_heli_gatling_spinup3
sound	minigun_heli_gatling_spinup4
sound	mus_fire_sale
sound	mus_perks_deadshot_jingle
sound	mus_perks_deadshot_sting
sound	mus_perks_doubletap_jingle
sound	mus_perks_doubletap_sting
sound	mus_perks_jugganog_jingle
sound	mus_perks_jugganog_sting
sound	mus_perks_mulekick_jingle
sound	mus_perks_mulekick_sting
sound	mus_perks_packa_jingle
sound	mus_perks_packa_sting
sound	mus_perks_phd_jingle
sound	mus_perks_phd_sting
sound	mus_perks_revive_jingle
sound	mus_perks_revive_sting
sound	mus_perks_speed_jingle
sound	mus_perks_speed_sting
sound	mus_perks_stamin_jingle
sound	mus_perks_stamin_sting
sound	projectile_hellfire_lod010	~
sound	remote_missile_fire
sound	remote_missile_fire_npc
sound	sentry_drop
sound	sentry_explode
```

## 5. Testing without a C1 client

- `tools/codol_probe.ps1 -Port <p> -Name <n> -Scripts <rawfiles root>
  -Exe bin\codol_dedrun_worker.exe -Map zm_prototype_sh
  -Zone zm -Gametype zm -Boot 100 -Tail 20 -Commands ...` boots a private
  server, runs rcon commands (or `sleep <s>`) and copies the log out. Never
  use port 17733 (the live server).
- `set scr_codol_equiptest "addbots 2"` adds damage-proof test clients to a
  zombies match; `"<client> <slot> <weapon>"` arms the weapon in that offhand
  slot and presses its real button, so the engine throws it and raises
  `grenade_fire`; `"table <name>"` dumps a mounted table.
- Log with `codolPrintLn`. `println` is a developer builtin that the compiler
  drops, so it never reaches these logs.
- A script runtime error (undefined field, bad array index, a builtin that
  raises) SHUTS THE WHOLE SERVER DOWN. Guard every field read of an entity
  another thread can delete or clear; work from local copies.
- Static gate for the zombies chain (must print "every reachable script
  resolves"):
  `python tools/codol_script_resolve.py --root <rawfiles>/zm --root <rawfiles>
  --seed maps/mp/gametypes/zm.gsc --seed maps/mp/gametypes/_callbacksetup.gsc
  --seed maps/mp/zm_prototype_sh.gsc --only-seeds`
