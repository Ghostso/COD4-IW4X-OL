# Predator linear flight integration

The shipped remote missile has projectileSpeed10 and timeToAccelerate0.
The retained rocket spawner therefore selects TR_LINEAR. MissileTrajectory
previously returned through BG_EvaluateTrajectory for that type before reaching
the explicitly enabled remote-flight controller. This explains a projectile
that exists but only travels at its very low asset launch speed.

The native dispatch now checks the remote controller after the launch-time and
rocket-handler guards, before the ordinary linear fallback. Uncontrolled
projectiles retain their existing evaluation. The C call's false-return path
reloads level.time before the generic evaluator; its return value cannot become
the evaluation timestamp.

Linear remote flight starts each step from the last traced currentOrigin and
anchors the new base at level.time. This avoids snapping to an old launch base
when controls are attached later and avoids client extrapolation adding all
elapsed launch time to an already advanced base. Unlink resumes linear travel
from the last current anchor. Existing non-linear remote behavior is unchanged.

Flight speed arithmetic remains the measured IW4 calculation with C1's
registered numeric settings1188/1189/1190. Steering uses recovered C1 control
bytes. This implements the missing server integration; it does not claim that
an identical speed consumer has been located in C1.exe. Asset values are intact.

Parent and secondary worker reviewed dispatch ABI, direct snapshot trajectory
publication and archived timestamp rebasing. Built and deployed SHA256
D2F7C46A32C6BC341107DC9E5147A6C3653D930D1B7837051312B4455C71B44F;
build log obj/build-predator-flight-20260915.log. Four-bot server launched.
No automated tests. Live missile movement/boost/impact remain unverified.
