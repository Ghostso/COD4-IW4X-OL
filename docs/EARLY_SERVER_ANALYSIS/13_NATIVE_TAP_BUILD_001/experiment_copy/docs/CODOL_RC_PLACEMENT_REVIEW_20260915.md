# RC placement and spawn influence integration

Startup correction: first build0C895EDC rejected the spectator team during
getSpawnpoint_Final, which also selects a connecting spectator's position.
Parent corrected the query to accept spectators with zero combat influence;
the influence setter still requires a combat team. Rebuilt/deployed
8AAD9CB321B3F2737BC3D622220FA67A435FFC5B939DD78C62EBC193A2CC0217.
The earlier deployment was a startup regression, not a successful RC check.

Parent compared worker source directly with OpenBLOPS g_scr_main_mp.cpp:
Scr_PhysicsTrace7402 and Scr_BoundsWouldTelefrag6484, and
g_spawnsystem_mp.cpp InfluenceWeight1385/ComputeSphereInfluence1426.

Installed six-argument RC swept bounds trace with structured fraction, position,
entity, normal and surface result; explicit ignored entity and T5 mask categories.
Native C1 entity sentinels and surface bits are used. Existing two-argument IW4
physicstrace contract is unchanged. Native bounds occupancy query uses actual
player/actor entities and C1 dead/type values rather than T5 enum numbers.

Installed moving vehicle spawn influence with original sphere distance curves,
team exclusion, entity-generation cleanup and map reset. Both native-script
spawn selection paths consume its weight. Reward activation still must create
the influence; this increment alone does not activate the original RC reward.

Build obj/codol-rc-placement.exe passed without compiler warnings:
0C895EDCF92931A185170F4E464A5034B7CAFD3BF0C85A75A646387F750D978E.
Both native executable names deployed; native-only restart, four bots requested.
No automated tests or real RC placement/driving verification.

Further review confirmed current entity_seed lacks ET_VEHICLE/ET_HELICOPTER
arms despite existing overlay helpers. Worker owns restoring captured vehicle
publication together with recipient-specific model selection. Physics source
and successful build are not proof that an RC reaches the client.
