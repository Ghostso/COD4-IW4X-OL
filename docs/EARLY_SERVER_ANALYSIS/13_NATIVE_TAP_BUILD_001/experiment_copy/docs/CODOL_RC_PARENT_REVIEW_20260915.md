# RC physics parent review in progress

Reviewed staged runtime ownership, construction/rollback, publication, and
ODE body/geometry lifetime against retained source. Retained dBodyDestroy
explicitly calls ODE_GeomDestruct for attached geometry; body destruction before
freeing copied brush data is supported.

Integration findings:

- Staged ground_binary.cpp was stale and removed decoded_domains. The worker
  confirmed this would reject valid configuration. Keep installed decoder and
  its conditional boost validation. Installed drive and graph already match.
- Staged CODOL_CreateVehicleODEBody rejects entity >=1024, although runtime
  and C1 publication accept the native 2046 normal-entity boundary. Requested
  correction or concrete downstream evidence before activation.

Full solver/native lifecycle review is unfinished. Timer flag notifications
without presentation consumers are not complete support. Original T5 reward
watcher/rules/FX/audio dependencies remain with the RC worker. No full RC
activation or gameplay claim follows from these findings.
