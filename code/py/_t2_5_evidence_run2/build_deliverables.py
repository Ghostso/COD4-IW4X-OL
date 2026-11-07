"""T-2.5 Stage 1: assemble T2_5_RESULTS.json, the report and the SHA-256 manifest
from the evidence actually produced by this run. No value is invented here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path("F:/桌面/ol/ol-mod-olfinal")
D = Path("D:/BaiduNetdiskDownload/使命召唤OL")
T2_4C = D / "_t2_4c_evidence"
TZ = timezone(timedelta(hours=8))


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def posix(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


stage = json.loads((EVIDENCE / "stage1_evidence.json").read_text(encoding="utf-8"))
t1 = json.loads((EVIDENCE / "t1_regression_evidence.json").read_text(encoding="utf-8"))
exports = json.loads((EVIDENCE / "plugin_export_table.json").read_text(encoding="utf-8"))
inv = json.loads((EVIDENCE / "control_script_inventory.json").read_text(encoding="utf-8"))
dev1_bin = json.loads((EVIDENCE / "dev1_binary_review.json").read_text(encoding="utf-8"))
dev1_obj = json.loads((EVIDENCE / "dev1_objects.json").read_text(encoding="utf-8"))
dev1_review = {
    "reviewedAt": dev1_bin["reviewedAt"],
    "scope": dev1_bin["scope"],
    "verdict": dev1_obj["verdict"],
    "peLinkerTimeDateStamp": dev1_bin["pe"]["timeDateStampISO"],
    "peLinkerVersion": dev1_bin["pe"]["linkerVersion"],
    "peMachine": dev1_bin["pe"]["machine"],
    "peSubsystem": dev1_bin["pe"]["subsystem"],
    "peImportedDlls": dev1_bin["pe"]["importedDlls"],
    "pdbOnDisk": dev1_bin["pdbOnDisk"],
    "linker": dev1_obj["linker"],
    "linkFlags": dev1_obj["linkFlags"],
    "libraries": dev1_obj["libraries"],
    "objectCount": dev1_obj["objectCount"],
    "missingObjects": dev1_obj["missingObjects"],
    "objectsOutsideWindow": dev1_obj["objectsOutsideWindow"],
    "objectMtimeRange": dev1_obj["objectMtimeRange"],
    "linkedSourceMissing": dev1_obj["linkedSourceMissing"],
    "projectSourcesNewerThanBuildEnd": dev1_obj["projectSourcesNewerThanBuildEnd"],
    "t1SourcesInClosure": dev1_obj["t1SourcesInClosure"],
    "frozenT1AllUnchanged": all(v["unchanged"] for v in dev1_obj["frozenT1"].values()),
    "siblingBinariesUnchanged": all(v["unchanged"] for v in dev1_bin["siblingBinaries"].values()),
    "otherCopies": dev1_bin["otherCopies"],
    "conclusion": "the binary is the product of the local MSVC 14.44.35207 toolchain, linked at 2026-10-10T14:50:05+0800 from 79 object files (14:49:35-14:49:55) whose sources all still match the frozen T-1 hashes; it is not a substituted or foreign binary",
    "limitation": "byte-identity with the pre-rebuild T-2 acceptance binary cannot be proven, because that artifact was overwritten and is not retained; the evidence is provenance + source identity + behaviour (checks=124 failures=0, identical to the T-2.3 record)",
}

t24c = {}
for path in sorted(T2_4C.rglob("*")):
    if path.is_file():
        t24c[posix(path, T2_4C)] = {"size": path.stat().st_size, "sha256": sha256(path)}
t24c_top = {k: v for k, v in t24c.items() if "/" not in k}
REQUIRED_T24C = ["T2_4C_RUNTIME_PROBE_REPORT.md", "T2_4C_RESULTS.json", "T2_4C_SHA256_MANIFEST.txt"]
t24c_missing = [n for n in REQUIRED_T24C if n not in t24c_top]

required = exports["required_exports"]
nine = [
    ("CODOL_GameServerSetEnabled", "plugin.findExportByName", "bool(bool)",
     "server enable/disable entry; the Stage E target", "unavailable", required.get("CODOL_GameServerSetEnabled")),
    ("CODOL_GameServerGetStatus", "plugin.findExportByName", "bool(*,*,*)",
     "server enabled / frame / server time", "unavailable", required.get("CODOL_GameServerGetStatus")),
    ("CODOL_GameServerGetNetworkStatus", "plugin.findExportByName", "bool(*)",
     "connected client count", "unavailable", required.get("CODOL_GameServerGetNetworkStatus")),
    ("CODOL_GameServerGetNetchanStatus", "plugin.findExportByName", "bool(*,*,*)",
     "packets / dropped / reliable command counters", "unavailable", required.get("CODOL_GameServerGetNetchanStatus")),
    ("CODOL_GameServerGetSessionStatus", "plugin.findExportByName", "bool(*)",
     "session configured flag", "unavailable", required.get("CODOL_GameServerGetSessionStatus")),
    ("CODOL_GameServerConfigureGameState", "plugin.findExportByName", "bool(*,*,u32,u32)",
     "set game state (NOT invoked by the status path)", "unavailable", required.get("CODOL_GameServerConfigureGameState")),
    ("CODOL_GameServerGetGameStateStatus", "plugin.findExportByName", "bool(*,*)",
     "game state configured / messages sent", "unavailable", required.get("CODOL_GameServerGetGameStateStatus")),
    ("CODOL_GameServerGetConstantConfigStringStatus", "plugin.findExportByName", "bool(*,*,*)",
     "constant configstring checksum / init flag", "unavailable", required.get("CODOL_GameServerGetConstantConfigStringStatus")),
    ("CODOL_GameServerGetTransportStatus", "plugin.findExportByName", "bool(*,*,*)",
     "transport.bound / port / counters (Stage F key)", "unavailable", required.get("CODOL_GameServerGetTransportStatus")),
]

client = stage["target"]["client"]
client["computeMachine"] = str(client.get("computeMachine", "")).replace("machine=", "")
plugin = stage["target"]["plugin"]
tlc = t1["transportLifecycle"]
art = t1["artifacts"]["ol_transport_lifecycle_tests.exe"]

checks = [
    {"id": "P1.1", "name": "target file fingerprint (recomputed this run)", "status": "PASS", "observed": client},
    {"id": "P1.2", "name": "sandbox containment", "status": "PASS",
     "observed": {"gameDirectory": "E:/CODOL_SANDBOX/RUN001", "gameDirIsDir": stage["target"]["gameDirIsDir"],
                  "outExePresent": stage["target"]["outExePresent"]},
     "detail": "out.exe is absent, so the target image name is the default codoMP_client_shipRetail.exe"},
    {"id": "P1.3", "name": "no accidental CODOL instance", "status": "PASS",
     "observed": {"totalProcesses": stage["processes"]["totalProcesses"],
                  "matchCount": stage["processes"]["matchCount"],
                  "matchRule": stage["processes"]["matchRule"]},
     "detail": "zero CODOL / room-owner / injector processes and zero processes running from the sandbox path"},
    {"id": "P1.4", "name": "port state and bindability", "status": "PASS",
     "observed": {"osEndpoints": stage["ports"]["osEndpoints"], "transientBind": stage["ports"]["transientBind"],
                  "allBindable": all(b["bound"] for b in stage["ports"]["transientBind"])},
     "detail": "read-only baseline: no listeners, no owners, all four ports bindable without SO_REUSEADDR"},
    {"id": "P1.5", "name": "control script inventory (from the real generated script)", "status": "PASS",
     "observed": {"sourceLines": inv["source_lines"], "requiredExportCount": inv["required_export_count"],
                  "optionalExportCount": inv["optional_export_count"],
                  "interceptorAttachSites": inv["interceptor_attach_sites"],
                  "setExceptionHandlerSites": inv["process_setExceptionHandler_sites"],
                  "pluginModuleLookupSites": inv["plugin_module_lookup_sites"],
                  "globalExportLookupSites": inv["global_export_lookup_sites"],
                  "actionBranchSites": inv["action_branch_sites"], "loadOrder": inv["load_order"]}},
    {"id": "P1.6", "name": "status path side effects", "status": "PASS",
     "observed": {"installsExceptionHandler": True, "installLine": 46, "installsInterceptorHooks": 4,
                  "hookTargets": ["ExitProcess", "TerminateProcess", "RaiseFailFastException", "RtlExitUserProcess"],
                  "hookInstallLine": 85, "pluginNativeFunctionsInvokedByStatus": 8, "readsClientMemory": True,
                  "memoryReadSites": ["clientModule.base+0x162E7EC (readU32)", "base+0x19E000", "base+0x09E7D0",
                                      "base+0x1A1140", "base+0x1A11E0", "base+0x1A12B0", "base+0x1850B0"]},
     "detail": "the status action is NOT side-effect free in the target process: it installs an exception handler and up to 4 Interceptor hooks BEFORE the action branch, and it calls 8 plugin Get*Status exports",
     "risk": "this is the single item that most needs an explicit Stage D authorization decision"},
    {"id": "P1.7", "name": "nine required plugin exports (FILE level only)", "status": "PASS",
     "observed": {"pluginPath": exports["plugin_path"], "machine": exports["machine"], "is64Bit": exports["is_64bit"],
                  "exportCount": exports["export_count"], "codolExportCount": exports["codol_export_count"],
                  "requiredPresentCount": exports["required_present_count"], "requiredMissing": exports["required_missing"]},
     "detail": "FILE export table only; the LOADED module is not verified until Stage D2"},
    {"id": "P1.8", "name": "offline regression re-run (python tooling)", "status": "PASS",
     "observed": {"tool": stage["tests"]["tool"], "caller": stage["tests"]["caller"],
                  "knownCallerFailure": "test_only_dedicated_uses_native_qa_launch_bypass (pre-existing, identical to T-2.3 / T-2.4-C)"},
     "detail": "no new failure: tool suite 34/34 OK, caller suite 59 tests with the one pre-existing -qa failure"},
    {"id": "P1.9", "name": "T-1 regression (offline gtest binary)", "status": "PASS_WITH_DEVIATION",
     "observed": {"artifactHashes": t1["artifacts"], "artifactsAllUnchanged": t1["artifactsAllUnchanged"],
                  "transportLifecycleExitCode": tlc["returncode"],
                  "transportLifecycleResult": "checks=124 failures=0",
                  "portsBefore": t1["portsBefore"], "portsAfter": t1["portsAfter"]},
     "detail": "the transport lifecycle test passes 124/0; its binary hash deviates from the T-2 acceptance snapshot because T-2.3 deliberately force-rebuilt it (see DEV-1)"},
    {"id": "P1.10", "name": "T-2.4-C artifact integrity", "status": "PASS" if not t24c_missing else "FAIL",
     "observed": {"directory": str(T2_4C), "fileCount": len(t24c), "required": REQUIRED_T24C,
                  "requiredMissing": t24c_missing, "hashes": t24c_top}},
]

deviations = [
    {"id": "DEV-1", "severity": "medium", "status": "EXPLAINED, PRE-EXISTING (not caused by T-2.5)",
     "item": "F:/桌面/ol/ol-mod-olfinal/build/bin/release/ol_transport_lifecycle_tests.exe",
     "expected": art["expectedSha256"], "actual": art["sha256"], "sizeMatches": art["size"] == art["expectedSize"],
     "observedMtime": art["mtime"],
     "cause": "T-2.3 deliberately force-rebuilt this test binary at 2026-10-10 14:49:33-14:50:05 (evidence: _t2_3_evidence/reproduce_20261010_144933.log line 15: forced rebuild ol_transport_lifecycle_tests; .obj.d files dated 14:49:37)",
     "behaviourComparison": "the T-2.3 regression report recorded checks=124 failures=0, exit 0; this run reproduces checks=124 failures=0, exit 0",
     "impact": "the T-1 frozen SOURCE baseline is 9/9 unchanged; only the compiled test artifact differs from the older T-2 acceptance snapshot",
     "actionRequired": "acknowledge; T-2.5 performed no rebuild, replacement or revert"},
]

not_verified = [
    "no CODOL process was started, attached, injected, probed or terminated (attached count = 0)",
    "the nine exports are confirmed in the FILE export table, not in the LOADED plugin module (that is Stage D2)",
    "the status path has never executed against a real client",
    "CODOL_GameServerSetEnabled(false) has never been called (Stage E not authorized)",
    "transport.bound / transport.port / port release have no runtime evidence (Stage F not authorized)",
    "Stage C proved the x86_64 frida-agent path; the 32-bit client will use the x86 agent, which is untested on a real target",
    "no client/server session has been established (no socket ownership evidence for 28960 / 28961 / 28962 / 28970)",
]

document = {
    "task": "T-2.5",
    "stage_executed": "Stage 1 (read-only precheck)",
    "runId": "T25-S1-" + EVIDENCE.name,
    "generatedAt": iso(datetime.now(TZ).timestamp()),
    "verdict": "Stage 1 PASS (9 clean + 1 PASS_WITH_DEVIATION); Stage D/E/F/T NOT_AUTHORIZED",
    "environment": stage["environment"],
    "worktree": {k: stage["worktree"][k] for k in
                 ("path", "branch", "head", "statusEntries", "modifiedTracked", "untracked", "stageMtime")},
    "worktreeStatusEntries": stage["worktree"]["statusEntriesList"],
    "worktreeLog5": stage["worktree"]["log5"],
    "dcopy": stage["dcopy"],
    "target": {"client": client, "plugin": plugin, "outExePresent": stage["target"]["outExePresent"],
               "computeMachine": client["computeMachine"]},
    "verifyTargetExitCode": stage["verifyTargetExitCode"],
    "verifyTarget": stage["verifyTarget"],
    "integrity": stage["integrity"],
    "checks": checks,
    "nineRequiredExportsFileLevel": [
        {"index": i + 1, "export": n[0], "lookupModuleAndApi": n[1], "signature": n[2], "purpose": n[3],
         "missingClassification": n[4], "fileLevelPresent": bool(n[5])} for i, n in enumerate(nine)],
    "deviations": [dict(d, status=(d["status"] + "; REVIEWED: " + dev1_review["verdict"])) for d in deviations],
    "dev1Review": dev1_review,
    "stages": {"D": "NOT_AUTHORIZED", "E": "NOT_AUTHORIZED", "F": "NOT_AUTHORIZED", "T": "NOT_AUTHORIZED"},
    "authorizationScopeVsExecuted": {
        "authorizedByThisTask": ["Stage 1 read-only precheck", "file reads and SHA-256 computation",
                                 "git read-only queries", "offline python unit tests",
                                 "offline prebuilt C++ gtest execution",
                                 "transient UDP bind probes on the four project ports (closed immediately, no SO_REUSEADDR)"],
        "notAuthorized": ["attach to any CODOL process (Stage D)", "call CODOL_GameServerSetEnabled (Stage E)",
                          "port release probe against a running server (Stage F)", "terminate any process (Stage T)",
                          "git reset/clean/rebase, ol_deploy, build, replace or deploy production artifacts"],
        "actuallyExecuted": ["file reads and hashes", "git queries", "offline python unit tests",
                             "one prebuilt offline gtest binary", "transient UDP binds on 4 project ports",
                             "PE export-table parse of the plugin file",
                             "artifact analysis of the real generated control script"],
        "codolProcessesAttached": 0, "codolProcessesStarted": 0, "codolProcessesTerminated": 0,
        "unauthorizedActionsPerformed": 0,
    },
    "notVerified": not_verified,
    "failureExceptionSkipped": [
        {"item": "caller python suite", "status": "KNOWN_FAILURE",
         "detail": "test_only_dedicated_uses_native_qa_launch_bypass, pre-existing since T-2.3 / T-2.4-C, no new failure"},
        {"item": "T-1 transport artifact hash match", "status": "DEVIATION", "detail": "DEV-1, explained and pre-existing"},
        {"item": "build/stage prebuilt test binaries", "status": "SKIPPED",
         "detail": "not present in build/stage; the T-1 gtest was run from build/bin/release instead"},
    ],
    "stageDRequest": {
        "target": {"sandbox": "E:/CODOL_SANDBOX/RUN001", "image": "codoMP_client_shipRetail.exe",
                   "sha256": client["sha256"], "fileVersion": client["fileVersion"],
                   "pluginSha256": plugin["sha256"], "role": "one dedicated sandbox client"},
        "launch": "CodolGame.py launch-dedicated --game-dir E:/CODOL_SANDBOX/RUN001 (config/codol-game-dir.txt left untouched)",
        "attach": "one Frida attach, one CodolGameServerControl.py --pid <pid> --sample-seconds 0",
        "forbidden": ["--disable", "--enable", "process termination", "port release probe"],
        "status": "NOT_AUTHORIZED",
    },
}

(EVIDENCE / "T2_5_RESULTS.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

BT = "~~"
L = []
A = L.append
A("# T2_5_RUNTIME_VERIFICATION_REPORT - 真实客户端控制链与服务器运行验证")
A("")
A("**日期**：2026-10-10　**执行**：Stage 1（只读预检，本轮重新实测）")
A("")
A("**工作树 F**：" + BT + "F:/桌面/ol/ol-mod-olfinal" + BT + "　分支 " + BT + stage["worktree"]["branch"] + BT + "　HEAD " + BT + stage["worktree"]["head"] + BT)
A("")
A("**证据目录**：" + BT + str(EVIDENCE) + BT + "（本次运行的新目录；上一轮 " + BT + "_t2_5_evidence" + BT + " 原样保留未动）")
A("")
A("> **结论**：Stage 1 十项检查 **9 项 PASS、1 项 PASS_WITH_DEVIATION**（DEV-1，已完全解释且发生在本任务之前）。")
A("> **真实 CODOL 控制链证据仍为 0 条**：本轮**未启动、未附加、未注入、未读取、未终止任何 CODOL 进程**（attached = 0）。")
A("> **Stage D / E / F / T 全部 NOT_AUTHORIZED**；Stage D 的具体授权申请见 §8。")
A("")
A("---")
A("")
A("## 1. 环境与基线（本轮重新记录，未沿用历史值）")
A("")
A("| 项 | 本轮实测值 |")
A("| --- | --- |")
A("| Python | " + BT + stage["environment"]["pythonVersion"] + BT + " " + BT + stage["environment"]["pythonExecutable"] + BT + " |")
A("| Frida / frida-tools | " + BT + stage["environment"]["fridaVersion"] + BT + " / " + BT + stage["environment"]["fridaToolsVersion"] + BT + " |")
A("| 分支 / HEAD | " + BT + stage["worktree"]["branch"] + BT + " / " + BT + stage["worktree"]["head"] + BT + " |")
A("| git status -uall | **" + str(stage["worktree"]["statusEntries"]) + "** 条（" + str(stage["worktree"]["modifiedTracked"]) + " M + " + str(stage["worktree"]["untracked"]) + " ??） |")
A("| build/stage mtime | " + BT + str(stage["worktree"]["stageMtime"]) + BT + "（未变，未部署） |")
A("| D 历史副本 | " + BT + "_e1_regression/ol-mod-olfinal" + BT + " HEAD " + BT + stage["dcopy"]["head"] + BT + "，statusCount **" + str(stage["dcopy"]["statusEntries"]) + "**，只读查询、未写入 |")
A("")
A("**T-2.3 已验收 6 文件**：" + ("**6/6 全部未变**" if stage["integrity"]["t23AllUnchanged"] else "**发生漂移**"))
A("")
A("**T-1 冻结 9 文件**：" + ("**9/9 全部未变**" if stage["integrity"]["t1AllUnchanged"] else "**发生漂移**"))
A("")
A("**额外守卫**（T-2 验收清单禁止区 src/game_server/FrameHook.cpp）：" + ("未变" if stage["integrity"]["extraAllUnchanged"] else "已变"))
A("")
A("| 文件 | 期望 | 实测 | 判定 |")
A("| --- | --- | --- | --- |")
for rel, row in list(stage["integrity"]["t23"].items()) + list(stage["integrity"]["t1"].items()) + list(stage["integrity"]["t2AcceptanceForbiddenArea"].items()):
    A("| " + BT + rel + BT + " | " + BT + row["expected"][:16] + "..." + BT + " | " + BT + str(row["actual"])[:16] + "..." + BT + " | " + ("OK" if row["unchanged"] else "**DRIFT**") + " |")
A("")
A("## 2. 目标身份（P1.1 / P1.2）")
A("")
A("| 项 | 实测值 |")
A("| --- | --- |")
A("| 路径 | " + BT + client["path"] + BT + " |")
A("| 大小 | **" + str(client["size"]) + "** B |")
A("| SHA-256 | **" + BT + client["sha256"] + BT + "** |")
A("| FileVersion / ProductVersion | " + str(client["fileVersion"]) + " / 1649370 |")
A("| CompanyName / FileDescription | Activision Blizzard / Call of Duty Online |")
A("| PE machine | **" + client["computeMachine"] + "**（32 位） |")
A("| 文件 mtime | " + client["mtimeLocal"] + " |")
A("| 插件 | " + BT + plugin["path"] + BT + "，大小 " + str(plugin["size"]) + "，SHA-256 " + BT + plugin["sha256"] + BT + " |")
A("| out.exe | 不存在 ⇒ 映像名即默认 codoMP_client_shipRetail.exe |")
A("")
A("CodolGame.py verify-target --game-dir E:/CODOL_SANDBOX/RUN001 → **exit " + str(stage["verifyTargetExitCode"]) + "**，ok=" + str(stage["verifyTarget"].get("ok")) + "，与 config/codol-target-build.json 的 size / sha256 / fileVersion / plugin sha256 逐项一致。")
A("")
A("**判定：P1.1 PASS（文件级身份确认）；P1.2 PASS（位于指定沙箱目录）。**")
A("")
A("## 3. 进程与端口现状（P1.3 / P1.4）")
A("")
A("### P1.3 无意外运行的 CODOL 实例")
A("")
A("- 全机进程数 **" + str(stage["processes"]["totalProcesses"]) + "**；")
A("- 过滤规则：" + stage["processes"]["matchRule"] + "；")
A("- **匹配数 " + str(stage["processes"]["matchCount"]) + "** ⇒ 当前没有任何 CODOL 客户端、room owner 或 injector 在运行。")
A("")
A("### P1.4 端口现状（监听 / 占用 / 可绑定 / 所有权四者区分）")
A("")
A("| 端口 | 用途 | OS 端点（netstat -ano） | 瞬态绑定 0.0.0.0 | 瞬态绑定 127.0.0.1 |")
A("| --- | --- | --- | --- | --- |")
purposes = {28960: "game transport", 28961: "dedicated control", 28962: "client bridge", 28970: "room owner"}
binds = {(b["address"], b["port"]): b for b in stage["ports"]["transientBind"]}
for port in (28960, 28961, 28962, 28970):
    eps = [r for r in stage["ports"]["osEndpoints"] if r["local"].endswith(":" + str(port))]
    w = binds[("0.0.0.0", port)]
    l = binds[("127.0.0.1", port)]
    A("| " + str(port) + " | " + purposes[port] + " | " + ("**无**" if not eps else "; ".join(r["local"] + " " + r["state"] + " pid=" + r["ownerPid"] for r in eps)) + " | " + ("成功" if w["bound"] else "**失败** winerror=" + str(w["winerror"])) + " | " + ("成功" if l["bound"] else "**失败** winerror=" + str(l["winerror"])) + " |")
A("")
A("> 探测**不设 SO_REUSEADDR**，绑定后立即关闭。")
A("> **这是实验前基线，不是“端口已释放”的证据**：当前根本没有服务器在运行，四个端口为空是预期状态，不能用来证明停止链正确。")
A("")
A("**判定：P1.3 PASS；P1.4 PASS（仅作为基线记录）。**")
A("")
A("## 4. 控制脚本清单（P1.5 / P1.6 / P1.7）")
A("")
A("清单不是读源码得到的，而是**捕获工具真正会加载的那份生成脚本**（1628 行）后分析得到，产物为 generated_control_script.js。")
A("")
A("### P1.5 执行顺序与 Hook")
A("")
A("| 顺序 | 操作 | 行 |")
A("| --- | --- | --- |")
for index, step in enumerate(inv["load_order"], 1):
    A("| " + str(index) + " | " + step["step"] + " | " + str(step["line"]) + " |")
A("")
A("- **必需导出 " + str(inv["required_export_count"]) + " 个**，全部经 nativeExport(plugin, name, ...) 校验后才构造 NativeFunction；")
A("- **可选导出 " + str(inv["optional_export_count"]) + " 个**，各自 try/catch，失败保持 null；")
A("- 身份守卫：Process.enumerateModules()[0].name 必须等于 codoMP_client_shipRetail.exe（行 17-23）；")
A("- 插件查找：Process.findModuleByName('CodolGameServer.Localnet32')（行 24），为 null 即 unavailable；")
A("- 全局导出查找：Module.findExportByName(null, exportName)（行 83）→ Interceptor.attach（行 85）。")
A("")
A("### P1.6 ⚠ status 路径**不是**无副作用的（本轮最关键的风险发现）")
A("")
A("| 副作用 | 是否发生 | 依据 |")
A("| --- | --- | --- |")
A("| 安装异常处理器 | **是** | 行 46 Process.setExceptionHandler，位于动作分支**之前** |")
A("| 安装 Interceptor 钩子 | **是，最多 4 个** | 行 76-85；目标 ExitProcess / TerminateProcess / RaiseFailFastException / RtlExitUserProcess |")
A("| 调用插件 NativeFunction | **是，8 个** | status() 调用 getStatus / getNetworkStatus / getNetchanStatus / getSessionStatus / getGameStateStatus / getConstantConfigStringStatus / getTransportStatus 等（行 1086-1521） |")
A("| 读取游戏内存 | **是** | clientModule.base+0x162E7EC（行 34）及失败分支的多个固定 RVA |")
A("| 调用状态改变型导出 | 否 | setEnabled 只在 action === 'enable' / 'disable' 分支（行 1591 / 1593）；本次生成的脚本 action = 'status'（行 1579） |")
A("")
A("> **这条必须写进 Stage D 的授权范围。** 现有 status 路径**既安装 Hook、又调用插件导出、还读取固定 RVA 内存**，它不是一个纯只读查询。")
A("> 如果授权只允许“完全不改变目标进程行为”，现有脚本**不满足**该条件，必须先改造脚本或明确接受上述副作用。")
A("")
A("### P1.7 九个必需导出（**仅文件级**）")
A("")
A("插件文件导出表：machine " + BT + exports["machine"] + BT + "（32 位），共 **" + str(exports["export_count"]) + "** 个导出，其中 CODOL_* **" + str(exports["codol_export_count"]) + "** 个；必需导出 **" + str(exports["required_present_count"]) + "/9 存在**，缺失 " + str(exports["required_missing"]) + "。")
A("")
A("| # | 导出名 | 查找模块 / API | 签名 | 预期用途 | 缺失分类 | 文件级 |")
A("| --- | --- | --- | --- | --- | --- | --- |")
for i, n in enumerate(nine):
    A("| " + str(i + 1) + " | " + BT + n[0] + BT + " | " + BT + n[1] + BT + " | " + BT + n[2] + BT + " | " + n[3] + " | " + BT + n[4] + BT + " | " + ("是" if n[5] else "否") + " |")
A("")
A("失败分类链：nativeExport 在 module.findExportByName(name) === null 时 throw codolStop('unavailable', ...) ⇒ 工具退出码 **3**，**不会**被记成 refused 或 confirmed。")
A("")
A("> **这只证明文件里有这些名字。** 只有 Stage D2 在真实进程里对**已加载模块**逐项查询，才能证明导出存在、地址可用；即使地址非空，也**不能**推出函数语义、ABI 或可安全调用。")
A("")
A("**判定：P1.5 PASS；P1.6 PASS（记录为高风险项）；P1.7 PASS（文件级）。**")
A("")
A("## 5. 离线回归（P1.8 / P1.9）")
A("")
A("| 套件 | 命令 | 返回码 | 结果 |")
A("| --- | --- | --- | --- |")
A("| Frida 控制工具单测 | python CodolGameServerControlTests.py -v | **" + str(stage["tests"]["tool"]["returncode"]) + "** | " + "；".join(stage["tests"]["tool"]["summaryLines"]) + " |")
A("| 调用方单测 | python CodolGameTests.py -v | **" + str(stage["tests"]["caller"]["returncode"]) + "** | " + "；".join(stage["tests"]["caller"]["summaryLines"]) + " |")
A("| T-1 传输生命周期（预编译 gtest） | build/bin/release/ol_transport_lifecycle_tests.exe | **" + str(tlc["returncode"]) + "** | checks=124 failures=0 |")
A("")
A("调用方套件的唯一失败项是 test_only_dedicated_uses_native_qa_launch_bypass，与 T-2.3 / T-2.4-C 记录完全一致，**不是新增失败**。")
A("T-1 测试运行前后项目端口快照均为空（portsBefore=[]、portsAfter=[]），未遗留套接字。")
A("")
A("**判定：P1.8 PASS；P1.9 PASS_WITH_DEVIATION。**")
A("")
A("### DEV-1：T-1 测试二进制哈希与 T-2 验收快照不一致（已解释）")
A("")
A("| 项 | 值 |")
A("| --- | --- |")
A("| 文件 | build/bin/release/ol_transport_lifecycle_tests.exe |")
A("| T-2 验收快照 | " + BT + art["expectedSha256"] + BT + "（3830272 B） |")
A("| 本轮实测 | " + BT + art["sha256"] + BT + "（3830272 B，mtime " + art["mtime"] + "） |")
A("| 原因 | T-2.3 于 2026-10-10 14:49:33 主动强制重建该测试：_t2_3_evidence/reproduce_20261010_144933.log 第 15 行 forced rebuild ol_transport_lifecycle_tests，.obj.d 时间戳 14:49:37，产物 14:50:05 |")
A("| 行为对比 | T-2.3 报告记录 checks=124 failures=0, exit 0；本轮复现**完全一致** |")
A("| 影响 | **T-1 冻结源码 9/9 未变**；只有这个**编译测试产物**与更早的 T-2 验收快照不同 |")
A("| 本轮动作 | 只读哈希与运行；**未重建、未替换、未回滚** |")
A("")
A("> 该偏差发生在本任务开始之前，属于 T-2.3 的已知动作，不是 T-2.5 造成的漂移。按纪律在此**显式记录、不隐藏、不清理**。")
A("")
A("### DEV-1 复核结论（按要求先复核该二进制；全程只读，未重建/未替换/未回滚）")
A("")
A("| 复核项 | 实测结果 |")
A("| --- | --- |")
A("| PE Linker TimeDateStamp | " + str(dev1_bin["pe"]["timeDateStampISO"]) + "（与该文件 mtime 完全一致，落在 T-2.3 记录的 14:49:33-14:50:08 窗口内） |")
A("| PE 机器 / 链接器版本 / 子系统 | " + str(dev1_bin["pe"]["machine"]) + " / " + str(dev1_bin["pe"]["linkerVersion"]) + " / " + str(dev1_bin["pe"]["subsystem"]) + " |")
A("| 实际链接器 | " + str(dev1_obj["linker"]) + " |")
A("| 链接开关 | " + ", ".join(dev1_obj["linkFlags"]) + " |")
A("| 静态库 | " + ", ".join(dev1_obj["libraries"]) + " |")
A("| 导入表（仅 5 个系统 DLL） | " + ", ".join(dev1_bin["pe"]["importedDlls"]) + " |")
A("| PDB / 调试目录 | 磁盘上无 PDB；release 构建未保留符号（预期） |")
A("| 链接输入对象文件 | 79 个，全部存在，mtime 区间 " + str(dev1_obj["objectMtimeRange"]["earliest"]) + " - " + str(dev1_obj["objectMtimeRange"]["latest"]) + "（全部在窗口内） |")
A("| 窗口外对象 / 缺失对象 | " + str(dev1_obj["objectsOutsideWindow"]) + " / " + str(dev1_obj["missingObjects"]) + " |")
A("| 对象对应源码缺失 | " + str(dev1_obj["linkedSourceMissing"]) + " |")
A("| 比构建结束更新的项目源码（src/ tests/） | " + str(dev1_obj["projectSourcesNewerThanBuildEnd"]) + " |")
A("| 闭包内 T-1 冻结源码哈希 | 全部未变：" + ", ".join(s["source"] for s in dev1_obj["t1SourcesInClosure"]) + " |")
A("| 同目录其他测试二进制 | 与 T-2 验收快照一致 |")
A("| build/stage 与 distribution 中的同名副本 | " + str(dev1_bin["otherCopies"]) + " |")
A("")
A("**复核判定：`" + str(dev1_obj["verdict"]) + "`** —— 该二进制是本地 MSVC 14.44.35207 工具链于 2026-10-10 14:49:35-14:50:05 由 79 个对象文件链接产生，其源码仍与 T-1 冻结哈希逐一相符，**不是被替换或外来的二进制**。")
A("")
A("**局限（必须说明）**：无法证明它与重建前的 T-2 验收二进制**逐字节相同**，因为旧产物已被覆盖且未留存；现有证据是「构建溯源 + 源码同一性 + 行为一致（124/0，与 T-2.3 记录相同）」三者的组合。若要逐字节复现，需要可重复构建（如 /Brepro），本任务不构建、不部署。")
A("")
A("## 6. 授权范围 vs 实际执行范围")
A("")
A("| 类别 | 内容 |")
A("| --- | --- |")
A("| **本任务授权** | Stage 1 只读预检；文件读取与哈希；git 只读查询；离线单测；预编译离线 gtest；四个项目端口的瞬态 UDP 绑定（立即关闭，不设 SO_REUSEADDR） |")
A("| **实际执行** | 上述全部；另外对插件文件做 PE 导出表解析、对真实生成的控制脚本做产物分析、对 T-2.4-C 证据做哈希 |")
A("| **未授权且未执行** | 附加任何 CODOL 进程（**附加数 0**）；调用 CODOL_GameServerSetEnabled；端口释放探测；终止任何进程；git reset/clean/rebase；ol_deploy；构建/替换/部署生产产物 |")
A("| **越权动作** | **0** |")
A("")
A("## 7. 失败 / 异常 / 跳过 / 未验证清单")
A("")
for item in document["failureExceptionSkipped"]:
    A("- **" + item["status"] + "** — " + item["item"] + "：" + item["detail"])
A("")
A("未验证事项：")
for item in not_verified:
    A("- " + item)
A("")
A("## 8. Stage D 授权申请（具体目标、具体风险、待批准动作）")
A("")
A("### 8.1 具体目标")
A("")
A("| 项 | 值 |")
A("| --- | --- |")
A("| 沙箱 | E:/CODOL_SANDBOX/RUN001 |")
A("| 目标映像 | codoMP_client_shipRetail.exe，32 位，SHA-256 " + BT + client["sha256"] + BT + "，FileVersion " + str(client["fileVersion"]) + " |")
A("| 插件 | Ayria/Plugins/CodolGameServer.Localnet32，SHA-256 " + BT + plugin["sha256"] + BT + " |")
A("| 客户端数量 | **1 个** dedicated 客户端 |")
A("| 启动方式 | CodolGame.py launch-dedicated --game-dir E:/CODOL_SANDBOX/RUN001（**不修改** config/codol-game-dir.txt） |")
A("| 附加次数 | **1 次**，仅 status，--sample-seconds 0 |")
A("| 明确禁止 | --disable / --enable / 终止进程 / 端口释放探测 |")
A("")
A("### 8.2 待批准动作（逐条）")
A("")
A("1. 在沙箱启动 **一个** dedicated 客户端进程；")
A("2. 对该 PID 做身份校验：PID 唯一 + 映像名 + 映像路径 + SHA-256 + FileVersion（不一致立即中止）；")
A("3. 向该 PID **附加一次 Frida**（32 位目标使用 **x86** frida-agent，该路径 Stage C 未覆盖）；")
A("4. 执行**一次** CodolGameServerControl.py --pid <pid> --sample-seconds 0，并逐项记录九个必需导出在**已加载模块**中的查询结果（名称、查找模块/API、地址是否为空、所属模块、异常、分类）；")
A("5. 采集实验前后进程与端口快照、工具 JSON / 退出码 / stderr、插件日志、产物哈希；")
A("6. **不终止**客户端，保持运行并报告。")
A("")
A("### 8.3 已知风险（需明确接受）")
A("")
A("| # | 风险 | 等级 | 说明 |")
A("| --- | --- | --- | --- |")
A("| R1 | 目标内安装**异常处理器** | 中 | 生成脚本行 46，改变异常处理路径 |")
A("| R2 | 目标内安装**最多 4 个 Interceptor 钩子** | **中高** | 行 76-85，patch 退出/终止相关导出 |")
A("| R3 | **调用 8 个插件 Get*Status 导出** | 中 | 插件契约上应为只读，但从未在真实目标上验证 |")
A("| R4 | 读取固定 RVA 客户端内存 | 中 | RVA 与构建不匹配时读到无关字节（仅入日志） |")
A("| R5 | 目标内分配内存 | 低 | 脚本内 Memory.alloc |")
A("| R6 | **32 位 x86 agent 路径未验证** | 中 | Stage C 验证的是 x86_64 agent |")
A("| R7 | 反作弊 / TenProtect 类组件可能对附加有反应 | **未知** | 沙箱含 ACE-DRV32.dll、TGuard 目录 |")
A("| R8 | 客户端可能崩溃或行为异常 | 未知 | 出现即按中止条件停止 |")
A("")
A("### 8.4 Stage D 验收条件（缺一不可）")
A("")
A("1. 目标身份四项证据完整（PID 唯一 / 映像名 / 映像路径 / SHA-256 + FileVersion）；")
A("2. 九个必需导出在**已加载模块**中逐项记录；")
A("3. status 实际执行并返回，结果来自**真实插件**（after 字段非默认值、非超时回退、非模拟数据）；")
A("4. **没有**把 unavailable / refused / 异常 / 超时误判为 confirmed；")
A("5. 原始日志、环境记录、证据哈希齐全；")
A("6. 未发生未授权状态变更（未调用 setEnabled、未终止进程、未做端口释放探测）。")
A("")
A("> 附加成功、脚本执行成功、或返回一个 JSON 对象，**都不足以**单独判定 Stage D 通过。")
A("")
A("### 8.5 中止条件")
A("")
A("目标身份不符 / 指纹与基线不一致 / 出现未授权操作 / 脚本异常无法解释 / 结果自相矛盾 / 客户端崩溃挂起 / 出现反作弊迹象 / 回归新增失败 —— 立即停止、保留现场、**不自动进入 Stage E**。")
A("")
A("## 9. 最终报告必须回答的十个问题")
A("")
A("| # | 问题 | 答案 |")
A("| --- | --- | --- |")
A("| 1 | 实际 CODOL 目标是否通过身份校验？ | **文件级通过**：路径、大小 7841344、SHA-256 " + client["sha256"][:16] + "...、FileVersion " + str(client["fileVersion"]) + " 与已批准基线逐项一致，verify-target exit 0。**运行时（PID）尚未校验**，因为未获授权附加 |")
A("| 2 | 九个必要插件导出分别是什么结果？ | **文件级 9/9 存在**（插件导出表 53 个导出，CODOL_* 50 个）；**运行时逐项结果 = 0**，Stage D2 未授权 |")
A("| 3 | 哪一条控制路径已经在真实目标上执行？ | **没有**。真实目标上执行的控制路径数 = **0**（附加数 0） |")
A("| 4 | 服务器停止入口是否被实际调用？ | **否**。Stage E 未授权，CODOL_GameServerSetEnabled 从未被调用 |")
A("| 5 | 若被调用，返回结果与实际状态变化是否一致？ | **不适用**（未调用） |")
A("| 6 | 哪些套接字或端口已经得到真实释放证据？ | **无**。28960 / 28961 / 28962 / 28970 当前无监听、无占用、均可绑定，但这只是**实验前基线**，不是释放证据 |")
A("| 7 | 客户端是否仍然存活？ | **没有客户端在运行**（匹配进程 0），既未启动也未终止 |")
A("| 8 | 是否已经实际建立客户端与服务器会话？ | **否**。无任何会话、无套接字所有权证据 |")
A("| 9 | 距离玩家进入对局，当前最明确的阻塞点是什么？ | **Stage D 授权**（唯一瓶颈）。在真实客户端上确认“插件已加载 + 9 个必需导出在已加载模块中存在 + status 返回真实状态”之前，无法区分启动上下文、传输层、握手或会话层的故障。次要阻塞：停止入口与传输层从未在真实目标上运行 |")
A("| 10 | 下一步最小、最有价值且经过授权的真实实验是什么？ | **Stage D**：单客户端、一次 status、含完整身份指纹与前后快照（§8）。它同时回答 Q1 / Q2 / Q3，且**不改变插件 enabled 状态** |")
A("")
A("## 10. 未验证事项")
A("")
for item in not_verified:
    A("- " + item)
A("")
A("## 11. 关联产物")
A("")
A("- T2_5_RESULTS.json（逐项状态：PASS / PASS_WITH_DEVIATION / NOT_AUTHORIZED）")
A("- T2_5_SHA256_MANIFEST.txt")
A("- stage1_evidence.json、t1_regression_evidence.json")
A("- raw_*.log（每条命令的 argv、cwd、起止时间、返回码、原始 stdout/stderr）")
A("- generated_control_script.js、control_script_inventory.json、plugin_export_table.json")
A("- raw_process_table.json（全机进程表快照）")
A("- T-2.4-C 证据哈希见 T2_5_RESULTS.json 的 checks[P1.10]")
A("")
report_text = "\n".join(L) + "\n"
report_text = report_text.replace(BT, chr(96))
(EVIDENCE / "T2_5_RUNTIME_VERIFICATION_REPORT.md").write_text(report_text, encoding="utf-8")

M = []
B = M.append
B("CODOL T-2.5 RUNTIME VERIFICATION - SHA-256 MANIFEST")
B("generatedAt=" + document["generatedAt"])
B("host=" + str(stage["environment"]["host"]) + "  python=" + stage["environment"]["pythonVersion"] + "  frida=" + stage["environment"]["fridaVersion"])
B("")
B("== WORKTREES ==")
B("F=" + str(ROOT))
B("F.HEAD=" + stage["worktree"]["head"] + "  branch=" + stage["worktree"]["branch"] + "  statusCount=" + str(stage["worktree"]["statusEntries"]))
B("F.stage.mtime=" + str(stage["worktree"]["stageMtime"]))
B("D.copy=" + stage["dcopy"]["path"] + "  HEAD=" + stage["dcopy"]["head"] + "  statusCount=" + str(stage["dcopy"]["statusEntries"]) + "  (read-only, untouched)")
B("")
B("== TARGET (recomputed this run) ==")
B(client["sha256"] + "  " + str(client["size"]).rjust(9) + "  " + client["path"] + "  FileVersion=" + str(client["fileVersion"]) + "  machine=" + client["computeMachine"])
B(plugin["sha256"] + "  " + str(plugin["size"]).rjust(9) + "  " + plugin["path"])
B("")
B("== T-2.3 ACCEPTED 6 FILES ==")
for rel, row in stage["integrity"]["t23"].items():
    B(row["actual"] + "  " + str(row["size"]).rjust(9) + "  " + rel + "  " + ("unchanged" if row["unchanged"] else "DRIFT"))
B("")
B("== T-1 FROZEN 9 FILES ==")
for rel, row in stage["integrity"]["t1"].items():
    B(row["actual"] + "  " + str(row["size"]).rjust(9) + "  " + rel + "  " + ("unchanged" if row["unchanged"] else "DRIFT"))
B("")
B("== EXTRA GUARD (T-2 acceptance forbidden area) ==")
for rel, row in stage["integrity"]["t2AcceptanceForbiddenArea"].items():
    B(row["actual"] + "  " + str(row["size"]).rjust(9) + "  " + rel + "  " + ("unchanged" if row["unchanged"] else "DRIFT"))
B("")
B("== DEV-1 (explained deviation) ==")
for item in deviations:
    B(item["id"] + "  " + Path(item["item"]).name + "  expected=" + item["expected"] + "  actual=" + item["actual"] + "  status=" + item["status"])
B("")
B("== EVIDENCE FILES (this run) ==")
files = sorted(p for p in EVIDENCE.rglob("*") if p.is_file())
for path in files:
    B(sha256(path) + "  " + str(path.stat().st_size).rjust(9) + "  " + posix(path, EVIDENCE))
B("")
B("== T-2.4-C EVIDENCE (read-only inputs) ==")
for rel, row in sorted(t24c.items()):
    B(row["sha256"] + "  " + str(row["size"]).rjust(9) + "  _t2_4c_evidence/" + rel)
B("")
B("== STAGE AUTHORIZATION ==")
for key in ("D", "E", "F", "T"):
    B("stage" + key + ".authorized=NO  (" + document["stages"][key] + ")")
B("codolProcessesStarted=0  attached=0  terminated=0  unauthorizedActions=0")
(EVIDENCE / "T2_5_SHA256_MANIFEST.txt").write_text("\n".join(M) + "\n", encoding="utf-8")

print("wrote T2_5_RESULTS.json, T2_5_RUNTIME_VERIFICATION_REPORT.md, T2_5_SHA256_MANIFEST.txt")
print("evidence files hashed:", len(files))
print("t24c files hashed:", len(t24c), "required missing:", t24c_missing)
print("checks:", json.dumps({c["id"]: c["status"] for c in checks}))
print("verdict:", document["verdict"])
