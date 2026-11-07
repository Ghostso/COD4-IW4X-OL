# Remaining selected-class killstreak coverage

Read-only source/data audit. No builds, automated tests, process changes or
gameplay verification. A registered callback is not proof that every downstream
native facility or live reward works.

## Effective source and coverage

Selection originates in C1 playerdata class killstreak slots, decoded by
codol_script_profile_loadout.c and passed through _class.gsc::cac_getKillstreak.
Catalogue data comes from mp/coKillstreakStatsTable.csv; corresponding marketplace
type is kis. Inspected scripts/codol overrides first, then effective fallback
alpha0022/vendor/iw4/maps/mp/killstreaks under
`D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022`.

MP catalogue IDs1..43 contain43 rewards. Eighteen have initialization-reachable
callbacks: IDs1..17 plus19(sr71_mp). The dynamic autosentry registration resolves
level.sentryType["sentry_minigun"] to sentry(ID16); it is not missing. Mortar17
and SR71 have current native overrides. Other base callbacks reside in IW4
fallback modules. This is registration coverage only, not18 fully verified rewards.

Absent base callbacks:

| ID | Reward | Cost | Activation weapon |
|---|---|---|---|
|18|rcbomb_mp|3|rcbomb_mp|
|20|dogs_mp|11|dogs_mp|
|21|sam_turret|4|auto_tow_mp|
|22|airdrop_sam_turret|4|airdrop_sam_marker_mp|

All21 pro rewards(ID23..43) lack distinct callbacks: uav_pro,
counter_uav_pro, rcbomb_pro_mp, airdrop_pro, airdrop_mega_pro,
airdrop_sam_turret_pro, sam_turret_pro, airdrop_sentry_minigun_pro,
sentry_pro, mortar_pro_mp, precision_airstrike_pro, predator_missile_pro,
helicopter_pro, harrier_airstrike_pro, sr71_pro_mp, helicopter_flares_pro,
stealth_airstrike_pro, helicopter_minigun_pro, dogs_pro_mp, ac130_pro, emp_pro.
They are separate catalogue/activation identities; aliasing them to base rewards
would hide missing semantics. IDs44 onward are predominantly zombie rewards and
are outside this MP callback count.

Current initKillstreakData deliberately skips unregistered rewards, while
killstreakUsePressed still asserts that an earned reward has a callback. The
selected-class reader does not filter these identities. Thus choosing a catalogue
reward does not imply there is any activation path; the missing registration
also prevents normal activation-asset initialization for it.

## Highest-impact next implementation: RC-XD

rcbomb_mp is a distinct low-cost(3) selectable base reward, marketplace4018.
Its lifecycle is wholly missing, unlike a registered handler with one isolated
method gap. No live _rcbomb module or callback was found.

Fresh shipped-asset evidence from common_gametype_mp.ff:

- Type36 **rawfile** vehicles/rc_car_medium_mp at zone offset2f6b9f5 contains a
  complete VEHICLEFILE, not merely a model or the type41 binary VehicleDef.
- Named fields include type=4 wheel, remoteControl=1, thirdPersonDriver=1,
  health=10, topSpeed=38, accel=30, physicsEnabled=1,
  physicsPreset=t5_veh_rc_bomb_medium, wheelRadius=6, suspensionTravel=3,
  maxSteeringAngle=30, boostEnabled=1, boostSpeedMultiplier=2,
  boostAccelMultiplier=3, boostDuration=2, boostRechargeTime=60.
- The same record names drive/brake axles, suspension damping, slip/friction,
  airborne torque, camera fields, rcxd engine aliases and compass icon.
- Shipped RC deployment/remote/countdown sounds, controller animations and tread,
  disabled-spark and light effects exist. Their presence supports implementation;
  it does not establish vehicle simulation compatibility.

The current codol_vehicle_native.cpp loader converts type41. The retained parser
knows VEHICLEFILE but lacks these remote/boost fields; blindly feeding this record
through it loses meaningful C1 behavior. The named rawfile supplies concrete data
to extend native vehicle representation instead of guessing binary offsets.

Existing remote missile control is specifically insufficient: C1 evidence in
codol_remote_missile.c identifies50c870 as an ET_MISSILE-only consumer. Its native
helper also rejects nonmissile entities. A driveable RC car cannot be implemented
by adding its name to that callback or steering a script model.

## Reference and concrete required work

Primary T5 script reference:
https://raw.githubusercontent.com/AtomicLizard99/Black-Ops-1-GSC-Raw-Dump/main/RawDump/common_mp.ff/maps/mp/_rcbomb.gsc

That reference validates placement, spawns a vehicle, establishes ownership/team,
hands the driver seat to the player, and handles detonation, timeout, destruction,
disconnect, team changes and scrambler stun. Its account-stat writes and T5
hardpoint framework need adaptation to existing C1 class/reward ownership rather
than wholesale import.

Concrete local native references: OpenBLOPS Game/Server/game/g_scr_vehicle.cpp
VEH_LinkPlayer around2035..2097 distinguishes remote control from physically
linking the player, assigns occupancy/owner/view state and emits enter_vehicle.
PlayerCmd_IsRemoteControlling in game_mp/g_client_script_cmd_mp.cpp:5229 reads
T5's remote flag. These identify lifecycle semantics; their offsets/flags are
not C1 layout proof.

Required native increments:

1. Parse and preserve named RC rawfile fields, then implement its real ground
   physics/accepted-command drive path, boost/brake state and captured client
   vehicle state. Trace C1 actual producer/consumer layout first.
2. Implement C1 remote vehicle enter/exit, camera/input ownership and cleanup.
   Registry inspection finds no active spawnvehicle/usevehicle/isremotecontrolling
   support; makevehicleunusable and setvehicleteam already exist. Verify each
   receiver and method instead of counting only new names.
3. Stage placement, actual vehicle deployment, damage/detonation/fuse, stun,
   owner interruption and reward-commit script lifecycle using shipped identities.
4. Add callback/init only when those native consumers are real. Validate base RC
   before independently implementing the pro variant.

SAM is another concrete missing low-cost reward, but needs an anti-air target
selection/lock/missile lifecycle, not an alias to the minigun sentry. Dogs requires
the actor/navigation/attack lifecycle. Pro UAV may be smaller than RC, but no
distinct pro behavior evidence was established by this bounded audit.

## RC raw-settings source increment

New codol_vehicle_raw.c/h now loads the mounted vehicles/<name> rawfile into
owned native data, independent of the type41 converter. The parser bounds input
and field count, retains every source pair, rejects duplicate keys/control bytes,
string truncation, nonfinite/invalid numbers and unsupported inheritance, and
leaves caller output unchanged on failure. It validates the four-wheel settings
actually supplied by this C1 asset rather than substituting a missile type.

Typed settings include remote control, driver camera, drive/brake/steering axles,
wheel/suspension, friction/stability/air torque and boost. Common fields reuse the
native vehicle definition, including damage switches, health, weapon, compass
and sound names. Four common speed/acceleration fields convert text mph by17.6
once, consistent with retained G_LoadVehicle and OpenBLOPS field type19. Distinct
physics maxVelocity/reverseSpeed remain explicit source-unit fields; no unproved
conversion or native consumer is claimed. Preset resolution remains false until
an actual physics loader binds the named dependency.

Plaintext C1 parser-name searches found no VEHICLEFILE/remoteControl string xrefs;
that absence does not establish unused data or a particular virtualized parser.
The source asset's named data and existing native reference consumers underpin
this loader, not an assumed C1 binary-layout correspondence.

Parent shared integration requested: retain optional raw settings alongside each
installed native record, fallback only when type41 is absent, expose typed ground
settings, and free/reset them with the current native vehicle lifecycle. No RC
callback, vehicle controls, physics preset binding or proxy movement is installed
by this loader. New files source-complete; no tests/builds by worker.

### Installed-record lifetime integration

`codol_vehicle_native.cpp` now tries mounted type41 first and falls back to the
raw loader only on the explicit absent result. A malformed present type41 remains
an error. Existing binary conversion, sound registration and turret registration
are unchanged. Raw parsing is staged in a unique owner: failure at any subsequent
installation step releases it without altering the installed record.

Successful installation retains optional raw settings beside the common record;
their common fields include the resolved sound and turret indices. The getter
`CODOL_NativeGroundVehicleDefinition` returns them only while the retained index,
count and name still match. Binary records return NULL. Replacement frees the
old raw allocation, and `CODOL_ResetNativeVehicles` frees all owned raw settings
before clearing bindings. Getter pointers cannot survive replacement or reset.
The public common-definition loader returns copied strings and no borrowed raw
pointer. Existing `CODOL_ResetVehicleAssets` calls the native reset.

This source increment enables data loading and lifetime management only. RC
controls, physical preset binding and reward registration remain absent; existing
binary VehicleDef behavior remains the preferred path. Source reviewed locally;
no worker build or automated tests run.

### Physics controller trace and isolated demands

C1 vehicle update678ed0 selects683e90 when vehicle+210 contains a physics
instance; otherwise it runs legacy678c60. The physical branch obtains the owner's
accepted command atclient33a8. Helper683b50 reads signed command bytes1a/1b.
Definition+2cc selects steering from driver yaw minus vehicle yaw (reversed when
backing), versus negative right-axis/127. Its raw-field name is not yet proven;
camLookEnabled was considered but is not established, and thirdPersonDriver is
another candidate. No native loader maps either candidate to this branch yet.

The new isolated `codol_vehicle_controls.cpp/.h` accepts this mode explicitly,
implements both measured steering demands, outward-only interpolation683a30
through618c10, and speed-dependent steering scale683fa9. It also implements
boost683cc0: definition2fc enabled,300 speed multiplier,304 acceleration,
308 duration,30c recharge, button400. Deadline is now plus duration+recharge in
milliseconds; boost ends deadline minus recharge. C1's constants were read as
-1000 atC842B8 and1000 atC842B0. This differs from T5 Nitrous boost-pool modes.
Definition310 gates handbrake button100000 and low-speed large-angle assist.

These are control demands, not movement: final C1 consumer65d0c0 applies them to
the physical instance. Physical mass/preset, wheel contact/collision integration,
handbrake speed-demand adjustment, and camera remain missing. No server frame
call site, reward callback or GSC activation was added. The new helper is a
source-complete isolated prerequisite; it is not counted as a working RC car.

### Native four-wheel motor/friction increment

Constructor caller67536b passes VehicleDef+a8 into65c180, which stores it at
physical instance+280. This corrects the earlier informal description of that
pointer as a separate physics preset: its +48/+4c/+50 are the definition's
frictionBraking/frictionCoasting/frictionTopSpeed at f0/f4/f8. The actual preset
pointer is +8 within this block (VehicleDef+b0). Caller675357..67536a separately
passes the per-definition acceleration record at2bbc170+index*148; physical
instance+284 stores that record. Its 32 graph knots begin+40, count is+140 and
maximum acceleration is+144.

`codol_vehicle_drive.cpp/.h` implements the ordinary four-wheel portion of
65d0c0: contact-relative forward velocity selects forward versus reverse motor
target; current/max speed selects the acceleration curve; graph acceleration
is converted by the measured17.600000381469727 factor and multiplied by slope,
boost and the physical instance mass scale. Uphill assistance is directional.
Over-speed demand uses maximum(braking friction, top-speed friction), while
coasting uses maximum(braking friction, coasting friction). Decreasing coasting
friction wakes the body. It also implements the measured handbrake speed-demand
adjustment683d00..683daa and graph interpolation618d80.

The APIs require actual physical inputs; they neither manufacture mass/contact
state nor update entity positions. Invalid graph coverage fails rather than
substituting a constant acceleration. The alternative physics flag10 controller
is outside this four-wheel API. No activation or frame consumer is wired yet:
the remaining work is physical body/preset initialization, wheel constraints,
contact integration, control/camera publication and reviewed reward lifecycle.
Source written and inspected, no worker compilation or automated tests.

### C1 remote vehicle ownership trace

Aligned C1 enter routine `679b80` obtains VehicleDef via vehicle+234 and the
definition table at2bbbe60. It checks definition+2c8 at679bf6,679c35,679c5f,
679d7b and679e20. Nonzero saves player viewangles14c/150/154 into
linkAngles1d4/1d8/1dc, skips physical linking through575630, adds otherFlags
(ps+10) bit400000, and preserves the body yaw from the saved link angle.
This independently identifies header+2c8 as remoteControl; native definitions
now decode `remote_control` from it, while raw definitions populate the same
field and extension[0] from their validated named boolean.

The enter path sets reciprocal entity owner handles at entity+164, entity
eFlags bit100000, player eFlags (ps+ec) bit100000, viewlocked_entNum atps+1b0,
and vehicle type atps+1f8. These are separate from remote missile cameraEntNum
atps+54. Exit679e60 skips body relocation when the same definition flag is set;
67a133 clears the occupied eFlag,67a13d clears otherFlags mask01c00000,
67a153 sets viewlocked_entNum to7ff, and67a166 restores saved viewangles.

Client45fd37 tests otherFlags400000 then reads saved linkAngles1d4..1dc.
Shared movement412696..4126ae distinguishes occupied vehicles from remote
vehicles using eFlags100000 and otherFlags400000. These source instructions
establish separate remote vehicle state; no T5 bit or structure offset is reused.

Current native snapshot already publishes otherFlags and viewlocked_entNum.
`codol_player_links_wire.c` owns saved linkAngles and publishes them from captured
extension state; a remote vehicle producer must update that representation, not
write transient snapshot values which the link overlay would overwrite. A
captured vehicle-type field atps+1f8 is still needed. Native reciprocal handle,
driver lifetime/exit, camera and actual ground command consumers remain to be
implemented before registering RC activation. This increment changes metadata
only, with no new remote state activation or runtime behavior claim.

### Remote ownership source increment

New `codol_remote_vehicle.cpp/.h` implements enter/exit ownership primitives:
validate the native vehicle pool/definition, reject occupied or conflicting
links, save body angles, establish reciprocal EntHandles, set C1 remote/occupied
flags and view lock, and restore view angles on release. The caller must supply
actual driver/barrel transform angles; no fabricated camera offset is applied.
Driver and vehicle generations are retained independently and checked before
cleanup, so a reused entity slot cannot inherit control or be cleared as the old
vehicle. Pool pointers and retained definition identity are checked before use.

Existing player-link reset, disconnect and entity-free paths release ownership.
Publication validates the driver before capturing links. A narrow existing-link
setter seeds saved angles in the live source record, whose existing snapshot and
archive readers/writers already own all three angle words. Native vehicle type
is kept in the driver record: the measured C1 netfield table has no ps+1f8 entry,
so the previously proposed new vehicle-type netfield was rejected. No snapshot
format or archive layout change was needed.

This is a callable native ownership prerequisite, still without GSC registration
or RC callback. Ground driving, vehicle-specific camera/clamp behavior, input
consumption and enter/exit notifications remain separate activation prerequisites.
No new player is linked by this source increment alone. Source reviewed locally;
no worker build or automated tests run.

### RC acceleration graph dependency (staged source)

C1 673d67..673dab checks VehicleDef+a8 (physics enabled), formats
`vehicle/%s` using name+b4, and calls59db70 with80.0f fromC323B0.
59db70 calls58d610 with rawfile type36, expected magic GRAPH_FLOAT_FILE,
then59d910 parses declared count and pairs; maximum32, actual count must match.
The loader stores maximum_acceleration80 at graph+144. This is not the raw
vehicle's accel30 value.

Offline shipped common_gametype_mp confirms rawfile
vehicle/default_accel.graph at inflated offset2f6b1bd:
(0,.5525),(.2855,.6232),(.5886,.4802),(.8615,.2913),(1,0).
The RC VEHICLEFILE names default_accel.graph and t5_veh_rc_bomb_medium.
Staged codol_vehicle_graph.cpp/.h implements exact named mounted dependency,
magic/count/float parsing and owned graph output. It rejects malformed/truncated,
nonfinite, unordered or uncovered curves instead of fabricating acceleration.
No source activation, builds or automated tests.

Crucial integration gap found: shipped zone also contains type41
rc_car_medium_mp. Current load_native_definition returns on that record, never
retaining raw ground settings, so CODOL_NativeGroundVehicleDefinition returns
NULL even though the matching VEHICLEFILE exists. A working controller must
represent ground settings for binary definitions too; attaching a raw supplement
must preserve binary common fields and validate identity, or decode additional
binary fields after proving their semantics. No fallback was guessed here.


### RC binary-definition prerequisite integrated; wheel/contact continuation

The earlier type41 gap is now resolved natively. `codol_vehicle_ground_binary`
loads the authoritative type41 physics/control fields instead of returning a
record with no ground representation. `codol_vehicle_graph` loads the actual
named type36 graph. Both are integrated in `codol_vehicle_native.cpp`, owned by
the installed definition record and reset with that record. Parent reviewed and
built/deployed E53711871BB1637519AFE011F788B3C345C95F5C904EFD28FDD458B79EB6B4C3.
No RC reward callback, physical controller, or gameplay activation is claimed.

C1 camera evidence now distinguishes client work from server representation:
- `471d8a` extracts the vehicle instance index from centity+13c, low four bits;
  record `2bc2798 + instance*88`, definition index+4, pointer array2bc3018.
- `471dcb`: definition+2d0 range. `471ddb..471deb`: height+2d8 and minimum+2d4.
- `471f7c/471f8d`: lower/upper pitch clamps+2e4/+2e8.
- `472060..472185`: speed-dependent spring distance+2ec, time+2f0.
- `472245..47226b`: camera collision trace (except vehicle type5), mask280ea31.
- `47179e..471817`: occupied-vehicle eFlag100000, viewlocked entity+1b0,
  definition mode+2cc, and actual FOV+2f8.
C1 already computes this camera from the real linked vehicle. Server must publish
correct ownership/entity transform/definition and need not send an invented
camera origin or replace the client camera with a missile view. Fields+2dc/+2e0
and+2f4 have not been established as active consumers in these camera routines;
binary decoder still does not assert the CAMERA coverage bit.

Actual C1 physics constructor6752d0:
- At675371 it passes VehicleDef+a8 to65c180, which allocates a2a4-byte physical
  instance and creates one rigid body (658800). This is not six separate bodies.
- For each of six model wheel slots,6753b0 checks the resolved model bone index.
  674c20 obtains its actual local translation through572080;65c270 initializes
  a30-byte embedded wheel/contact record at instance+4 + index*30.
-65c270 seeds local origin, PRESENT flag1, heading(1,0,0), path ratio1 and motor ratio1,
  front/rear side friction from physics+54/+58, and radius from physics+b4.
-65c2e0 keeps PRESENT separate; assigns POWERED2, STEERING4, BRAKING8 by the
  binary axle enums. Auxiliary wheels4/5 always receive STEERING, but remain
  inactive unless their model tags were found. ALL power/brake includes them.
- Primary front/rear centers, signed wheelbase, half-track, and reciprocal actual
  powered wheel count are computed from those local translations.

`obj/rc-physics-stage/codol_vehicle_wheels.cpp/.h` now implements that verified
layout initialization with explicit missing-tag, nonfinite geometry, invalid
axle and zero-powered-wheel rejection. It is staged outside src; physics contact
forces, rigid body lifecycle, shared frame integration and RC GSC remain pending.
No arbitrary chassis bounds are used as wheel anchors. Four primary wheel tags
are required for this RC path; auxiliary tags are optional.

Independent named-schema leads (offsets were verified separately against C1):
[OpenAssetTools IW4 VehiclePhysDef](https://git.alterware.dev/zone/OpenAssetTools/raw/commit/c86139b0fa65078bc857f3ca39f65a0f8b881cf1/src/ZoneCommon/Game/IW4/IW4_Assets.h)
and [VehicleFields unit conversions](https://git.alterware.dev/zone/OpenAssetTools/src/commit/416823c6cd6a891574fb61939f2277222b5652c4/src/ObjCommon/Game/IW4/Vehicle/VehicleFields.h).
The latter marks resistance, upright and air torque source settings with the
same17.600000381469727 conversion confirmed in the shipped binary/raw pair.


### RC wheel steering constraints (staged, not activated)

`codol_vehicle_wheels` now also implements C1 ordinary wheel steering65ca00.
Its six wheel records preserve the verified actual fields: local origin+0,
flags+c, heading vector+10, path speed ratio+1c, final motor ratio+20,
side friction+24, reserved contact state+28, radius+2c. Earlier exploratory
planar-side-vector labels were corrected before any native integration.

For absolute steering<=.005, C1 restores heading(1,0,0) and both ratios1,
then returns before any brake-specific handling. Otherwise it computes the
instantaneous turning center from signed axle wheelbase and tan(steering),
normalizes each steerable wheel heading tangent to its own circle, and divides
powered-wheel path length by the reference-circle length. The final ordinary
motor ratio is normalized across participating powered wheels. Engaged handbrake
excludes front indices0/1 from ratio accumulation; final brake mode overrides
ratios rather than consuming this normalization. Actual constants are6 for
physical flag20,10 for automatic-turn flag40. Source addresses65cb3e..65ceb1.
The staged routine avoids unused zero/zero normalization when no rear wheel is
powered during a handbrake override, while preserving resulting valid outputs.

C1 control producer683ef0 stores automatic-turn braking at vehicle+22d;
683f0e merges that with raw command100000 into vehicle+22c.
65d43d..65d471 publishes these separately as physical instance20/40.
`codol_vehicle_controls.h/.cpp` now preserves `automatic_handbrake` in addition
to the existing merged `handbrake`, so a future native wheel consumer can use
both. No current frame consumer or gameplay activation changed.

Further exact producer boundary found while rereading683c50: with speed within
0..250 the automatic branch accepts steering==0 as well as >=10 or <=-10.
The equality reaches683c98 and683cb4, returning1. Previous helper omitted that
single zero boundary; corrected after parent released build hold. The separate automatic-brake representation was built by parent in0DF19B0EA9C86FC00FE8B4CCD86FDB70B4EA955E1A4966050E141E489CC2F476; the zero-boundary correction is newer source. The existing
handbrake+boost acceleration doubling is verified by683e60..683e89.

Remaining integration dependencies are real missing source, not placeholders:
actual model-local wheel extraction, owned rigid-body creation with C1 collision
geometry/preset mass, suspension/contact constraint assembly, chassis/world
collision response and lifecycle, native frame scheduling, physical transform
snapshot publication, and reviewed RC reward GSC. The staged steering routine
has no frame registration or substitute position integration.

### Owned RC body/world stage (2026-09-14, not deployed)

`obj/rc-physics-stage/codol_vehicle_ode.cpp/.h` now construct/destroy real retained ODE bodies from the named mounted vehicle preset and deep-owned XModel collision map. No bounds box fallback. The constructor validates positive-definite mass tensor, model axes, metadata and generation; it preserves actual preset mass/bounce/friction. Renderer origin is converted to/from the body's center of mass. C1 `65c671 -> 659100 -> 658be0` scales only COM.z by `1-roll_stability`; original inertia remains the source tensor times mass. Primitive geometry keeps local orientation/offset; brush geometry receives the owned map and adjusted COM, matching the retained XModel brush path. Cylinder argument ordering is explicitly taken from retained `Phys_ObjSetCollisionFromXModel` / `Phys_ObjAddGeomCylinderRotated`, rather than guessing from field names.

The staged `_ode.asm` patch adds three native entry points: shared existing world initialization on caller-owned `0x10110` bytes, and aliases to the exported simple-space constructor/non-deleting destructor on caller-owned `0x64` bytes. Existing dWorldCreate(index) keeps its old behavior. No fourth index is passed to retained arrays. This avoids relocating many unrelated fields inside `odeGlob` and `physGlob`; adding a fourth slot would require migrating all later constant offsets as well as every loop limit.

A concrete lifetime pitfall was addressed: `dGeomTransformSetGeom` unconditionally calls dSpaceRemove(child->space), and dSpaceRemove dereferences that space. Therefore children are first placed in the owned real space, then transferred to wrapper ownership. If wrapper allocation fails, the child remains body-owned and rollback destroys it. Body destruction runs before deep-owned brush storage release. World destruction runs after all body/geometry destruction. Owned space calls the non-deleting D1 destructor, never ODE_GeomDestruct or dSpaceDestroy, which assume pool storage.

**Solver/collision continuation, not an activated controller:** `dWorldQuickStep -> dxProcessIslands` takes an actual world pointer and does not index physGlob. However, `ODE_CollideSimpleSpaceWithGeomNoAABBTest` hardcodes Phys_NearCallback, whose context carries a PhysWorld index and whose material reads assume the retained body-userdata layout. `dxPostProcessIslands` also indexes physGlob, empties that world's joint group, clears forces, dirties geometry, and applies drag. The owned body record must not be sent to those callbacks. Next integration needs a real owned contact group/near callback using the same dCollide world geometry and actual C1 vehicle material/constraint parameters, plus correctly scheduled solver/post-step work. Current stage deliberately exposes no free-running step method: constructing a body does not claim collision, wheel suspension, or working RC-XD control. No tests/build/process changes were performed by this worker.

### Owned contacts and solver substep stage (2026-09-14)

The staged ODE adapter now owns a contact group (`4 + 4096*0xac` bytes, derived from retained dGetContactJointGroup/dJointCreateContact). It calls the real `dCollide` against the mounted clipmap world geom and between bodies in its owned simple space. Callback ownership is resolved against the actual native body pointers in the owned list, never by interpreting arbitrary body userdata. Manifolds over four points pass through the existing native Phys_ReduceContacts; its source accesses ContactList/math/debug state, not retained body-userdata fields. Native contact geometry is 48 bytes; contact-joint creation copies 44 geometry bytes plus a separate 44-byte surface record. The four-argument dJointCreateContact ABI is explicit.

The staged step requires an actual caller force/constraint producer and explicit solver/contact settings. It does not register itself or pick a new server timestep. Preset friction/bounce combination currently follows retained Phys_NearCallback; **C1 world3 setting/material equivalence is not yet established**, so these are an adapter boundary, not claimed final C1 tuning. Wheel spring/damping/contact forces and torque constraints still need their actual C1 producer. Every solver advance includes real static and interbody collision preparation; allocation/validation failure aborts before advancement and clears prepared joints/forces. Reentrant creation/destruction is rejected while stepping.

The assembly patch now additionally exports a pointer-based substep entry (stores actual dt at native world+50 then calls dxProcessIslands) and post-step body work (clear native force/torque accumulators and dirty every attached geom). Existing ODE_BodyGetFirstGeom is reused. Native linear/angular drag behavior is applied using explicit input coefficients; the owned group is emptied after the substep. No PhysWorld index is synthesized, and no existing indexed callback or postprocessor receives the owned body layout. Source remains staged only, with no build/test/process changes.

### Parent contact review (2026-09-15)
Reviewed retained Phys_NearCallback and transform/body destruction against the staged adapter. Corrected two omissions: connected dynamic bodies are filtered through dAreConnectedExcluding with native contact type 4; contact reduction receives NULL for two dynamic bodies, and the sole body for a body/world pair. The retained callback explicitly selects those cases before Phys_ReduceContacts. Transform child transfer removes both space and body linkage, so the owned body geometry traversal does not double-collide wrapped children. Stage remains inactive pending C1 wheel/settings integration; no server restart justified by these staging-only edits.


### T5 wheel row and traction projection stage (2026-09-15)

New `obj/rc-physics-stage/codol_vehicle_constraints.cpp/.h` implement reviewed OpenBLOPS algorithms from `Engine/Core/tl/physics/rbc_def_vehicle.cpp` and `Engine/Physics/physics/phys_constraint_solver_multithreaded.cpp`. These functions are staged, unregistered and unbuilt; they do not make RC playable.

Spring row uses CFM=1/(k*dt²+d*dt), rhs=-positionError*(k*dt²)*CFM/dt, accumulated impulse[-1e7,0]. The zero active-factor branch retains a side-friction row limited by the suspension parent's impulse, with no forward motor row. Braking supplies symmetric impulse bounds ±brakingFactor*dt. Powered motion supplies angular target*wheelRadius as row RHS, inverse drive compliance from accelerationFactor*turningRatio*dt/radius², and target-direction-dependent impulse limits. Inputs are actual contact/controller outputs, not authored-value guesses or free-standing acceleration forces.

The friction projection follows pulse_sum_wheel::clamp_pulse_sum_pulse_chain: side and forward impulses share a load-dependent ellipse; each axis is capped by the same side-friction maximum, and both impulses scale together. Zero contact load and the source small-denominator branches are preserved. Independent friction clamping would not be equivalent. This is real coefficient/projection logic awaiting its native Jacobian/solver consumer, not a registered placeholder.

T5 Phys_RunToTime (`phys_main.cpp3695+`) supplies a changed-clock interval clamped to1..100ms, then UpdateRigidBody takes body snapshots, updates vehicle prologs, advances phys_sys, and updates vehicle epilogs. The staged scheduling arithmetic preserves that order's interval without starting another timer or running a catch-up loop. C1 world3 dvar/default equivalence is still not established: no retained ODE ERP/CFM/iteration defaults were silently adopted.

Remaining concrete integration: actual model-tag wheel anchors and contact normals; T5 displaced lever-arm Jacobians (roll/pitch stability differs from a single ODE contact point); custom coupled row integration with chassis collision islands; real solver settings producer; frame/controller/camera and reward lifecycle. Existing ODE near callback/group corrections remain intact. No source under src, active GSC, process, or archive was changed by this stage.
