RESTORE_IIPS_REGRESSION_STATUS = LOCAL_RM_PROXY_ONLY
IIPS_LOAD_STAGE = LEVEL_1
ENVIRONMENT_DRIFT = YES
LOCAL_RM_BASELINE = STABLE
ENGINE_BRIDGE_RESULTS_VALID = NO

This is a NEW regression specific to the patched proxy DLL (iips_patched_proxy.dll) in the sandbox environment.
# RESTORE-IIPS-REGRESSION-001 Final Report

## Executive Summary

**Conclusion**: The "加载 iips.dll 失败" error is a **NEW regression specific to the patched proxy DLL (iips_patched_proxy.dll)**, NOT present in the original iips.dll or the runtime-injection Local RM approach. This is a **LEVEL_1 (LoadLibrary) failure** that did not exist in the stable baseline.

```
RESTORE_IIPS_REGRESSION_STATUS = LOCAL_RM_PROXY_ONLY
IIPS_LOAD_STAGE = LEVEL_1
ENVIRONMENT_DRIFT = YES
LOCAL_RM_BASELINE = STABLE
ENGINE_BRIDGE_RESULTS_VALID = NO
```

---

## 1. File Hashes (Current Environment)

| File | Path | SHA256 | Size |
|------|------|--------|------|
| codoMP_client_shipRetail.exe | COD OL\ | 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537 | 7,841,344 |
| iips.dll (original) | COD OL\IIPS\ | 72ddb9d15626b5a0a001347da141fb944a9f862db713e01c06a964ec8dc35348 | 347,704 |
| iips.dll (patched proxy) | EB1_SANDBOX\IIPS\ | 2ed4782491592ec837df12e8a48d8f763de417a18e466e68de5b171e59fcb4c2 | 380,928 |
| IFS2.dll | COD OL\IIPS\ / EB1_SANDBOX\IIPS\ | 5b0324e0b2ba3545a6c02626287d4fbc6a3116594744f4647333982d85508421 | 601,656 |
| codoMP_client_shipRetailBase.dll | COD OL\ | ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20 | 60,327,992 |
| BugTrace.dll | COD OL\ | 1fdb07e47c0bad6024309d6dcdda0eed3b1a87bcac61b57dc0ef750cb2225646 | 1,029,624 |
| TenProxy.dll | COD OL\ | a5ee7ede762c473f58a87b214213097f6dda8950ac537b0a959389aef31348cb | 167,592 |

**Key Finding**: Two different iips.dll binaries exist:
- **Original**: 347,704 bytes, hash `72ddb9d1...` (in COD OL\IIPS\)
- **Patched Proxy**: 380,928 bytes, hash `2ed47824...` (in EB1_SANDBOX\IIPS\, also saved as `iips_patched_proxy.dll.keep`)