# -*- coding: utf-8 -*-
"""跑完一局后自动判定：这次改动过没过（只读，不改东西）。

检查三件事：
  a. 大厅日志里有没有我们想看到的那条正向应答
     （item 分组 SKU 页 / PvE session / 靶场 session / game start）；
  b. 客户端 UIException 里对应的崩溃还在不在
     （商城空 MarketScrollGrid / 游玩清单 MatchMakingStripView /
       公告 FilterCategoryButton / 首页挑战 OnboardingChallenges）；
  c. 战斗服有没有收到包（可选，剧情/靶场用）。

用法：
    python -X utf8 check_run.py
    python -X utf8 check_run.py --log <别的日志> --tasks <别的 bin>
"""
import argparse
import base64
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

UI_MARKERS = {
    "MarketScrollGrid": "商城目录页(80/70) 仍空 -> MarketScrollGrid #1009",
    "SupplyDrop": "军火箱页面构造中断",
    "MatchMakingStripView": "游玩清单仍空 -> MatchMakingStripView #1009",
    "FilterCategoryButton": "公告 #1125 未消除",
    "MOTDNotificationsPopup": "公告弹层未消除",
    "OnboardingChallengesChecklist": "首页挑战 #1010 未消除",
}

# ★★ 2026-10-07 事故后新增的**有效判据**：
#   只统计 71/7 的 "异常有没有新增" 是**会骗人的** —— marketplace 解析失败时，
#   客户端是**整块停止工作**，反而不会抛 MarketScrollGrid/SupplyDrop。
#   真正要看的是"客户端还继续不继续要库存"：
#       marketplace 活着 -> 每局必然请求 80/203（库存）
#       marketplace 死了 -> 收到我们的 SKU 页后**再也不要 80/203**
#   这一条是本轮"仓库/大厅被锁"唯一能提前发现的信号。
MARKETPLACE_ALIVE_MARKER = "service=80 ver=0x03 task=203"

# ★★ 2026-10-07 第二个有效判据：**会话密钥选对了没有**。
#   实测症状：客户端重连时 nt10 会往 kdf_sessions.txt 追加新的一组密钥；
#   旧代码在"按 HMAC 试解都没命中"时回落到"猜的一组"硬解 →
#   解出 marker=0x4F / service=133 / declared=79273349 这种乱码 →
#   不回包 → 客户端超时重连 → 死循环 → ConnectionResetError(10054)。
#   修法：没通过 HMAC 就保留待解帧、不下结论。
#   健康的标志：`[keys] ★ 试解命中:` 出现，且首帧就是 hmac=OK marker=0x86。
KEY_PICK_OK_MARKER = "[keys] ★ 试解命中:"
HMAC_BAD_MARKER = "hmac=BAD"

POSITIVE_MARKERS = {
    "item 分组 SKU 页": "item 分组 SKU 页已下发",
    "PvE coop mission session 对象": "PvE session 已下发",
    "靶场 mission session 对象": "靶场 session 已下发",
    "game start": "已推 game start",
}


def read_text(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def scan_uiexceptions(tasks_path):
    """从 lobby_tasks.bin 里解 71/7 的 UIException 调用链。返回 (条数, [文本])。"""
    try:
        raw = open(tasks_path, "rb").read()
    except Exception:
        return 0, []
    off, n, texts = 0, 0, []
    while off + 6 <= len(raw):
        svc, task = raw[off], raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) != (71, 7):
            continue
        n += 1
        txt = pl.decode("latin1", "replace")
        for m in re.finditer(r"([A-Za-z0-9+/]{40,}={0,2})", txt):
            b = m.group(1)
            try:
                d = base64.b64decode(b + "=" * (-len(b) % 4)).decode(
                    "utf-8", "replace")
            except Exception:
                continue
            if "Error" in d:
                texts.append(d.strip())
    return n, texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.join(ROOT, "lobby_srv.log"))
    ap.add_argument("--tasks", default=os.path.join(ROOT, "lobby_tasks.bin"))
    ap.add_argument("--battle", default=os.path.join(ROOT, "battle_srv.log"))
    a = ap.parse_args()

    print("=" * 70)
    print("跑局结果自动判定")
    print("=" * 70)

    log = read_text(a.log)
    if not log:
        print("[!] 读不到 %s" % a.log)
    else:
        print("[大厅] %s (%d 字节)" % (os.path.basename(a.log), len(log)))
        for k, desc in POSITIVE_MARKERS.items():
            print("   %s %-30s %s" % ("OK " if k in log else "-- ", k, desc))

        # ★★ 最关键的一条：marketplace 子系统到底活着没有。
        #   收到 SKU 页后如果客户端**不再请求 80/203**，就是"仓库/大厅被锁"。
        mp_alive = MARKETPLACE_ALIVE_MARKER in log
        sent_sku = "item 分组 SKU 页" in log
        print("   %s %-30s %s"
              % ("OK " if mp_alive else "!! ", "80/203 库存请求",
                 "marketplace 子系统活着" if mp_alive
                 else "★ 没有任何 80/203 —— marketplace 很可能已经死了"))
        if sent_sku and not mp_alive:
            print("       ★★ 警告：我们发了 SKU 页，但客户端再也没要过库存")
            print("          ⇒ 这就是「仓库/大厅被锁」。立刻回滚：")
            print("          python -X utf8 enable_itemgroup_sku_test.py off")

        # ★★ 会话密钥选对了没有（见 KEY_PICK_OK_MARKER 注释）
        picked = KEY_PICK_OK_MARKER in log
        bad = log.count(HMAC_BAD_MARKER)
        print("   %s %-30s 试解命中=%s  hmac=BAD=%d"
              % ("OK " if (picked and bad == 0) else "!! ",
                 "会话密钥选取", "是" if picked else "否", bad))
        if bad:
            print("       ★★ 警告：出现 %d 条 hmac=BAD —— 密钥选错了。" % bad)
            print("          症状：满屏乱码 declared=79273349 / marker=0x4F，")
            print("                客户端超时重连 -> ConnectionResetError(10054)。")
            print("          检查 lobby_server.py 的 pick_keyset 回落分支：")
            print("          候选没过 HMAC 时必须 sec=None、保留 pending，绝不能硬解。")

    n, texts = scan_uiexceptions(a.tasks)
    print("[UI] 71/7 共 %d 条, 去重异常 %d 条" % (n, len(texts)))
    if not texts:
        print("   (无异常上报)")
    for k, desc in UI_MARKERS.items():
        hit = any(k in t for t in texts)
        print("   %s %-30s %s" % ("还在" if hit else "没了", k, desc))

    blog = read_text(a.battle)
    if blog:
        m = re.findall(r"收包=(\d+)", blog)
        last = int(m[-1]) if m else 0
        print("[战斗服] 最后一次统计 收包=%d" % last)

    print("-" * 70)
    print("判据提示：")
    print("  ★ 验商城改动必须**两条同时成立**，只看 UI 异常会被骗（2026-10-07 教训）：")
    print("    1) 本会话里出现过 80/203（库存请求）—— marketplace 还活着；")
    print("    2) 71/7 里没有新增 MarketScrollGrid / SupplyDrop。")
    print("    只有 (1) 成立，(2) 才有意义。")
    print("    若商城变灰/角色被锁：立刻 python -X utf8 enable_itemgroup_sku_test.py off")
    print("  ★ 会话密钥：出现 [keys] ★ 试解命中 + 首帧 hmac=OK marker=0x86 才算健康。")
    print("    出现 hmac=BAD（marker=0x4F / declared=79273349 这类乱码）")
    print("    会让客户端超时重连到 ConnectionResetError(10054)。")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
