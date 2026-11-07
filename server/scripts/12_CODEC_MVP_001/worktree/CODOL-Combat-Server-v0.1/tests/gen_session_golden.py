# -*- coding: utf-8 -*-
"""会话描述符黄金向量的生成器（可重复构建的一部分）。

为什么需要它
------------
战斗服必须与大厅用**同一份** session 描述符字节：它是客户端"去哪台战斗服"的
唯一地址通道（21/5 findSessions），并且其中夹带的 16B securityKey 是 ECDH
派生的一半输入。字节错了客户端就是静默失败——没有报错，只有"连不上"。

因此本版把描述符字节固化成**黄金向量**，并从**已冻结的参考实现**
（REF_LOBBY_KIT/codol_crypto.py，其来源是 ol-mod MatchmakingService.cpp 与
三方 C# CodolLocalLobbyServer.cs）直接生成，避免任何手工转录错误。

用法
----
    python -X utf8 tests/gen_session_golden.py

输出: src/Codol/SessionGolden.cs（覆盖写）
参考实现位置由 REF_KIT 常量决定；默认指向工作区里的 REF_LOBBY_KIT。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REF_KIT = os.environ.get("CODOL_REF_KIT") or os.path.join(
    os.path.dirname(REPO), "REF_LOBBY_KIT")
OUT = os.path.join(REPO, "src", "Codol", "SessionGolden.cs")

if REF_KIT not in sys.path:
    sys.path.insert(0, REF_KIT)

import codol_crypto as cc  # noqa: E402


def cs_literal(hexstr, width=64):
    """把一段 hex 拆成若干行 C# 字符串字面量，用 + 连接（消除手抄错误）。"""
    parts = [hexstr[i:i + width] for i in range(0, len(hexstr), width)]
    lines = ['            "%s"' % p for p in parts]
    return " +\n".join(lines)


TEMPLATE = '''// CODOL Combat Server v0.1 -- 会话描述符黄金向量（自动生成，请勿手工编辑）
//
// 生成器: tests/gen_session_golden.py
// 字节来源: REF_LOBBY_KIT/codol_crypto.py（已冻结的参考实现）
//   CA_GOLDEN  = bd_common_addr((127,0,0,1), 28960)                 -> 37B
//   REC_GOLDEN = build_session_record(0x1122334455667788, ...)       -> 258B
//   FR_GOLDEN  = build_mission_session_object(True)                  -> 268B
//   NM_GOLDEN  = build_mission_session_object(False)                 -> 237B
// 上游迁移来源: ol-mod MatchmakingService.cpp:284-310 / :514-558 / :614-629
//               三方 C# CodolLocalLobbyServer.cs:420-488 BuildMissionSessionObject
namespace Codol.Combat.Codol
{
    internal static class SessionGolden
    {
        internal const string CA_GOLDEN =
%(ca)s;
        internal const string REC_GOLDEN =
%(rec)s;
        internal const string FR_GOLDEN =
%(fr)s;
        internal const string NM_GOLDEN =
%(nm)s;
    }
}
'''


def main():
    rec = cc.build_session_record(
        0x1122334455667788, (127, 0, 0, 1), 28960,
        game_type=0, max_players=18, current_players=1,
        map_name="mp_crash_tropical", security_key=bytes(range(16)))
    fr = cc.build_mission_session_object(True)
    nm = cc.build_mission_session_object(False)
    ca = cc.bd_common_addr((127, 0, 0, 1), 28960)

    for name, v, want in (("CA", ca, 37), ("REC", rec, 258),
                          ("FR", fr, 268), ("NM", nm, 237)):
        if len(v) != want:
            raise SystemExit("%s 长度 %d != 期望 %d（参考实现已变，需重新对齐）"
                             % (name, len(v), want))

    src = TEMPLATE % {
        "ca": cs_literal(ca.hex().upper()),
        "rec": cs_literal(rec.hex().upper()),
        "fr": cs_literal(fr.hex().upper()),
        "nm": cs_literal(nm.hex().upper()),
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(src)
    print("生成 %s" % OUT)
    for name, v in (("CA", ca), ("REC", rec), ("FR", fr), ("NM", nm)):
        print("  %-4s %3d 字节" % (name, len(v)))


if __name__ == "__main__":
    main()
