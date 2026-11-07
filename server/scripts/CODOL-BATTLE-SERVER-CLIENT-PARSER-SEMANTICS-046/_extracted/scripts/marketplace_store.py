# -*- coding: utf-8 -*-
"""CODOL 私服商城(marketplace)模块 —— 逐行移植自 C# 参考实现, 零第三方依赖。

参考源码(全部已实读):
  * MarketplaceStore.cs   (launcher_src/tools/firingrange-test/src/MarketplaceStore.cs)
  * PlayerProfile.cs      (同上目录, 取 Crc/Put/Tail/Decode/Apply/SecurePath/MarketplacePlayerData)
  * LocalPlayerAccount.cs (Read/Validate 依赖)
  * CodolLocalLobbyServer.cs:1333-1373 (商城分派/应答的实际调用点)

数据: SKU 目录来自启动器 exe 的嵌入资源 `marketplace-catalog.json`
      (本模块同目录下的 marketplace-catalog.json, 从 CODOL-Launcher-firingrange-v32.exe 反射提取)。
档案布局: 移植 Apply 所需的 `player-layout.json`(exe 资源) **已内嵌**为 LAYOUT,
      以免再落一个文件(本任务只允许新增 marketplace_store.py 与 marketplace-catalog.json)。

货币约定(照抄 CodolLocalLobbyServer.cs:1338/1357): service 80 -> currency 1(CP/CodPoints),
      service 93 -> currency 2(GP/Gold)。

自测: python marketplace_store.py   (用临时目录, 不碰真实数据)
"""
import base64
import datetime
import json
import os
import struct
import uuid

# ======================================================================
# 异常 —— 对应 C# System.IO.InvalidDataException
# ======================================================================
class InvalidDataError(Exception):
    """对应 C# InvalidDataException(商城校验失败统一抛这个)。"""


# ======================================================================
# 内嵌的玩家档案布局 —— 来自 exe 资源 player-layout.json
#   (实测 exe 内是 36 个 field、全部非 skipped, 与 secure.result 32983 字节吻合:
#    32803 + 36*5 = 32983。磁盘上 launcher_src 的那份只有 35 个字段、已过时, 不能用。)
# fields: (path, offset, type) —— 顺序即 Tail() 写出顺序。
# ======================================================================
LAYOUT_VERSION = 19
LAYOUT_SCHEMA_WORD = 2739108020
LAYOUT_RANK_VERSION = 4
LAYOUT_MAX_LEVEL = 70
LAYOUT_MAX_PRESTIGE = 4
LAYOUT_FIELDS = (
    ("accuracy", 12, "int32"),
    ("assists", 676, "int32"),
    ("bombDefuses", 680, "int32"),
    ("bombPlants", 684, "int32"),
    ("confirmed", 4820, "int32"),
    ("currentWinStreak", 4824, "int32"),
    ("deaths", 4828, "int32"),
    ("denied", 4832, "int32"),
    ("elo", 4836, "int32"),
    ("escapes", 4840, "int32"),
    ("experience", 4844, "int32"),
    ("headshots", 4848, "int32"),
    ("hits", 4852, "int32"),
    ("kdRatio", 4856, "int32"),
    ("killStreak", 4860, "int32"),
    ("kills", 4864, "float32"),
    ("losses", 4868, "int32"),
    ("objectives", 4872, "int32"),
    ("prestige", 4883, "int32"),
    ("rank", 4887, "int32"),
    ("rankVersion", 4891, "int32"),
    ("score", 4895, "int32"),
    ("scorePerMinute", 4899, "int32"),
    ("skill", 4903, "int32"),
    ("suicides", 4907, "int32"),
    ("survivalTopScoreEasy", 4911, "int32"),
    ("survivalTopScoreHard", 4915, "int32"),
    ("survivalTopScoreMedium", 4919, "int32"),
    ("ties", 4923, "int32"),
    ("timePlayed", 4927, "int32"),
    ("timePlayedOverAll", 4931, "int32"),
    ("timePlayedTotal", 4935, "int32"),
    ("totalShots", 4939, "int32"),
    ("winRatio", 4951, "int32"),
    ("winStreak", 4955, "int32"),
    ("wins", 4959, "float32"),
)

# ranks[i]["next"] —— 逐值照抄 exe 的 player-layout.json(70 行)。
# 注: 该布局里 ranks[i]["experience"] == ranks[i-1]["next"](第 0 行为全 0),
#     已逐行核对为真, 所以这里只存 next、experience 由推导得到(见 _rank_experience)。
LAYOUT_RANKS_NEXT = (
    [2000, 2500, 3000, 3500, 15000],
    [4000, 5000, 6000, 7000, 34200],
    [6000, 7500, 9000, 10500, 57900],
    [9000, 11250, 13500, 15750, 86300],
    [12000, 15000, 18000, 21000, 119700],
    [16000, 20000, 24000, 28000, 158300],
    [20000, 25000, 30000, 35000, 202400],
    [25000, 31250, 37500, 43750, 252200],
    [30000, 37500, 45000, 52500, 308000],
    [37400, 46750, 56100, 65450, 369900],
    [46000, 57500, 69000, 80500, 438100],
    [55750, 69687, 83625, 97562, 512700],
    [66700, 83375, 100050, 116725, 593800],
    [78900, 98625, 118350, 138075, 681500],
    [92350, 115437, 138525, 161612, 775700],
    [107050, 133812, 160575, 187337, 876700],
    [123050, 153812, 184575, 215337, 983700],
    [140400, 175500, 210600, 245700, 1096700],
    [159050, 198812, 238575, 278337, 1216700],
    [179050, 223812, 268575, 313337, 1342700],
    [200400, 250500, 300600, 350700, 1473700],
    [223150, 278937, 334725, 390512, 1610700],
    [247300, 309125, 370950, 432775, 1752700],
    [272900, 341125, 409350, 477575, 1900700],
    [299900, 374875, 449850, 524825, 2052700],
    [328400, 410500, 492600, 574700, 2209700],
    [358400, 448000, 537600, 627200, 2370700],
    [389900, 487375, 584850, 682325, 2535700],
    [422900, 528625, 634350, 740075, 2704700],
    [457750, 572187, 686625, 801062, 2877700],
    [494400, 618000, 741600, 865200, 3053700],
    [532900, 666125, 799350, 932575, 3232700],
    [573300, 716625, 859950, 1003275, 3414700],
    [615600, 769500, 923400, 1077300, 3598700],
    [659800, 824750, 989700, 1154650, 3784700],
    [706000, 882500, 1059000, 1235500, 3972700],
    [754150, 942687, 1131225, 1319762, 4162700],
    [804300, 1005375, 1206450, 1407525, 4354700],
    [856450, 1070562, 1284675, 1498787, 4547700],
    [910650, 1138312, 1365975, 1593637, 4742700],
    [966950, 1208687, 1450425, 1692162, 4938700],
    [1025350, 1281687, 1538025, 1794362, 5135700],
    [1085850, 1357312, 1628775, 1900237, 5333700],
    [1148450, 1435562, 1722675, 2009787, 5532700],
    [1213250, 1516562, 1819875, 2123187, 5732700],
    [1280250, 1600312, 1920375, 2240437, 5933700],
    [1349450, 1686812, 2024175, 2361537, 6135700],
    [1420900, 1776125, 2131350, 2486575, 6338700],
    [1494600, 1868250, 2241900, 2615550, 6542700],
    [1571050, 1963812, 2356575, 2749337, 6747700],
    [1650250, 2062812, 2475375, 2887937, 6953700],
    [1732250, 2165312, 2598375, 3031437, 7160700],
    [1817050, 2271312, 2725575, 3179837, 7369700],
    [1904700, 2380875, 2857050, 3333225, 7579700],
    [1995250, 2494062, 2992875, 3491687, 7791700],
    [2088700, 2610875, 3133050, 3655225, 8005700],
    [2185100, 2731375, 3277650, 3823925, 8221700],
    [2284500, 2855625, 3426750, 3997875, 8439700],
    [2386900, 2983625, 3580350, 4177075, 8659700],
    [2492300, 3115375, 3738450, 4361525, 8882700],
    [2600800, 3251000, 3901200, 4551400, 9108700],
    [2712400, 3390500, 4068600, 4746700, 9337700],
    [2827100, 3533875, 4240650, 4947425, 9569700],
    [2944950, 3681187, 4417425, 5153662, 9805700],
    [3065950, 3832437, 4598925, 5365412, 10045700],
    [3190200, 3987750, 4785300, 5582850, 10290700],
    [3317700, 4147125, 4976550, 5805975, 10540700],
    [3448450, 4310562, 5172675, 6034787, 10795700],
    [3582550, 4478187, 5373825, 6269462, 11056700],
    [3732550, 4665687, 5598825, 6531962, 11323700],
)


def _rank_experience(level, prestige):
    """ranks[level-1].experience[prestige] —— 见 LAYOUT_RANKS_NEXT 注释(推导)。"""
    if level <= 1:
        return 0
    return LAYOUT_RANKS_NEXT[level - 2][prestige]


def _layout_offset(name):
    """Field(name) —— 照抄 PlayerProfile.cs:49-52。"""
    for path, offset, _type in LAYOUT_FIELDS:
        if path == name:
            return offset
    raise InvalidDataError("安全档案布局里没有字段 %s" % name)


# ======================================================================
# 通用工具
# ======================================================================
def _u32_at(buf, off):
    """BitConverter.ToUInt32(buf, off)。"""
    return struct.unpack_from("<I", buf, off)[0]


def _i32_at(buf, off):
    return struct.unpack_from("<i", buf, off)[0]


def _put(data, offset, value):
    """照抄 PlayerProfile.cs:99-102 Put(小端 4 字节)。"""
    struct.pack_into("<I", data, offset, value & 0xFFFFFFFF)


def _u32(w, v):
    """照抄 MarketplaceStore.cs:94 U32: 写 tag 0x08 + u32。"""
    w += bytes([0x08]) + struct.pack("<I", v & 0xFFFFFFFF)
    return w


def _dumps(obj):
    """照抄 MarketplaceStore.cs:26 Encode(UTF8 无 BOM 的紧凑 JSON)。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _ci_get(d, name, default=None):
    """大小写不敏感取值(对应 JavaScriptSerializer 的字段匹配)。"""
    if name in d:
        return d[name]
    low = name.lower()
    for k, v in d.items():
        if isinstance(k, str) and k.lower() == low:
            return v
    return default


def _atomic(path, data):
    """照抄 MarketplaceStore.cs:20-25 Atomic(临时文件 + rename)。"""
    tmp = path + "." + uuid.uuid4().hex + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ======================================================================
# 路径
# ======================================================================
def _path_for(root):
    """照抄 MarketplaceStore.cs:19 PathFor。"""
    return os.path.join(root, "marketplace-inventory.json")


def pending_path(root):
    """照抄 MarketplaceStore.cs:31 marketplace.pending.json。"""
    return os.path.join(root, "marketplace.pending.json")


def secure_path(root):
    """照抄 PlayerProfile.cs:168-176 SecurePath。
    优先 player_profiles\\secure.result, 否则退回 profile_results\\secure.result。"""
    p = os.path.join(root, "player_profiles", "secure.result")
    if not os.path.exists(p):
        return os.path.join(root, "profile_results", "secure.result")
    return p


# ======================================================================
# SKU 目录
# ======================================================================
class Sku(object):
    """照抄 MarketplaceStore.cs:14 Sku。"""
    __slots__ = ("Id", "Item", "Currency", "Price", "Category",
                 "Stackable", "Grant", "SelectedDays")

    def __init__(self, Id, Item, Currency, Price, Category, Stackable, Grant, SelectedDays):
        self.Id = Id
        self.Item = Item
        self.Currency = Currency
        self.Price = Price
        self.Category = Category
        self.Stackable = Stackable
        self.Grant = Grant
        self.SelectedDays = SelectedDays

    def __repr__(self):
        return ("Sku(Id=%d, Item=%d, Currency=%d, Price=%d, Category=%d, "
                "Stackable=%s, Grant=%d, SelectedDays=%d)"
                % (self.Id, self.Item, self.Currency, self.Price, self.Category,
                   self.Stackable, self.Grant, self.SelectedDays))


_catalog = None  # 缓存, 对应 MarketplaceStore.cs:18 `catalog`


def catalog_path():
    """目录文件默认位置: 与模块同目录。"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "marketplace-catalog.json")


def load_catalog(path=None):
    """载入并缓存 SKU 目录(对应 MarketplaceStore.cs:49-58 Catalog)。

    返回 dict{uint Id: Sku}。字段名大小写不敏感(C# 用 JavaScriptSerializer)。
    """
    global _catalog
    if _catalog is not None and path is None:
        return _catalog
    with open(path or catalog_path(), "r", encoding="utf-8") as f:
        raw = json.load(f)
    table = {}
    for e in raw:
        sku = Sku(
            int(_ci_get(e, "Id", 0)),
            int(_ci_get(e, "Item", 0)),
            int(_ci_get(e, "Currency", 0)),
            int(_ci_get(e, "Price", 0)),
            int(_ci_get(e, "Category", 0)),
            bool(_ci_get(e, "Stackable", False)),
            int(_ci_get(e, "Grant", 1)),
            int(_ci_get(e, "SelectedDays", 0)),
        )
        table[sku.Id] = sku
    if path is None:
        _catalog = table
    return table


def get_sku(sku_id):
    """按 Id 取 Sku; 不存在返回 None(对应 Catalog().TryGetValue)。"""
    return load_catalog().get(int(sku_id))


# ======================================================================
# 玩家账户
# ======================================================================
ACCOUNT_BUILD = 1649370
INVENTORY_VERSION = 1


def _validate_account(account):
    """照抄 PlayerProfile.cs:64-83 Validate。"""
    name = _ci_get(account, "Name")
    if not name or name != name.strip() or len(name.encode("utf-8")) > 31:
        raise InvalidDataError("玩家名称需为 1-31 个 UTF-8 字节, 不能有首尾空格/引号/分号/反斜杠/加号。")
    for c in name:
        if ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F or c in "\";\\+":
            raise InvalidDataError("玩家名称含非法字符。")
    level = int(_ci_get(account, "Level", 0))
    prestige = int(_ci_get(account, "Prestige", 0))
    if level < 1 or level > LAYOUT_MAX_LEVEL or prestige < 0 or prestige > LAYOUT_MAX_PRESTIGE:
        raise InvalidDataError("等级或转生次数超出此客户端的范围。")
    exp = int(_ci_get(account, "Experience", 0))
    if exp < _rank_experience(level, prestige) or exp > LAYOUT_RANKS_NEXT[level - 1][prestige] - 1:
        raise InvalidDataError("经验值与所选等级不一致。")
    if int(_ci_get(account, "CodPoints", 0)) < 0 or int(_ci_get(account, "Gold", 0)) < 0:
        raise InvalidDataError("点券和金币必须为非负整数。")


def read_account(root):
    """照抄 LocalPlayerAccount.cs:27-42 Read + MarketplaceStore.Recover。
    返回归一化后的 dict(保留原键), 文件不存在返回 None。"""
    recover(root)
    path = os.path.join(root, "player-account.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        account = json.load(f)
    if account is None or int(_ci_get(account, "FormatVersion", 0)) != 1 \
            or int(_ci_get(account, "Build", 0)) != ACCOUNT_BUILD:
        raise InvalidDataError("玩家档案配置版本不匹配。")
    _validate_account(account)
    return account


def write_account(root, account):
    """原子写回 player-account.json(私有辅助, 供主程序保存档案用)。"""
    _atomic(os.path.join(root, "player-account.json"), _dumps(account))


# ======================================================================
# 库存 / 事务日志
# ======================================================================
def _new_inventory(owner):
    """照抄 MarketplaceStore.cs:15 Inventory 的默认值。"""
    return {"Version": INVENTORY_VERSION, "Build": ACCOUNT_BUILD,
            "Owner": int(owner), "Items": {}, "Transactions": []}


def _norm_inventory(state, owner):
    """把 JSON 读回来的 dict 归一化成 PascalCase 形态(大小写不敏感)。"""
    out = {
        "Version": int(_ci_get(state, "Version", 0)),
        "Build": int(_ci_get(state, "Build", 0)),
        "Owner": int(_ci_get(state, "Owner", 0)),
        "Items": _ci_get(state, "Items"),
        "Transactions": _ci_get(state, "Transactions"),
    }
    if out["Items"] is None:
        out["Items"] = {}
    if out["Transactions"] is None:
        out["Transactions"] = []
    return out


def recover(root):
    """照抄 MarketplaceStore.cs:27-41 Recover(前滚恢复事务日志)。"""
    path = pending_path(root)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        journal = json.load(f)
    if journal is None or int(_ci_get(journal, "Version", 0)) != 1:
        raise InvalidDataError("Invalid marketplace recovery journal")
    _atomic(secure_path(root), base64.b64decode(_ci_get(journal, "Secure")))
    _atomic(os.path.join(root, "player-account.json"),
            base64.b64decode(_ci_get(journal, "Account")))
    _atomic(_path_for(root), base64.b64decode(_ci_get(journal, "Inventory")))
    os.remove(path)


def read_inventory(root, owner):
    """照抄 MarketplaceStore.cs:42-48 Read。返回归一化 Inventory dict。

    owner 不匹配/版本不匹配/结构损坏 -> InvalidDataError。
    """
    recover(root)
    path = _path_for(root)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            state = _norm_inventory(json.load(f), owner)
    else:
        state = _new_inventory(owner)
    if (state["Version"] != INVENTORY_VERSION or state["Build"] != ACCOUNT_BUILD
            or state["Owner"] != int(owner)
            or state["Items"] is None or state["Transactions"] is None):
        raise InvalidDataError("Invalid marketplace inventory owner/version")
    return state


def write_inventory(root, owner, state):
    """原子写 inventory(对应 Atomic(PathFor(root), Encode(state)))。
    写前校验 Owner/Version, 避免把别人的库存写坏。"""
    state = _norm_inventory(state, owner)
    if state["Version"] != INVENTORY_VERSION or state["Build"] != ACCOUNT_BUILD \
            or state["Owner"] != int(owner):
        raise InvalidDataError("Invalid marketplace inventory owner/version")
    _atomic(_path_for(root), _dumps(state))


# ======================================================================
# 购买
# ======================================================================
def purchase(root, owner, transaction, currency, skus, quantities):
    """照抄 MarketplaceStore.cs:59-89 Purchase。成功返回 0(事务已提交)。

    校验顺序与错误语义完全照抄:
      1. 同 transaction 已存在 -> 直接返回 0(幂等, 不扣款);
      2. SKU 数量 1..16、与 quantity 等长、无重复;
      3. 账户必须可读;
      4. 每个 SKU: 必须存在 / Currency 必须匹配 / quantity 1..1000 /
         非 Stackable 必须 quantity==1;
      5. Category 必须 0..7, 且 Category==7 时必须是 Stackable;
      6. Stackable 累加 price*qty 并加 Grant*qty; 非 Stackable 且未拥有才算 price、置 1;
      7. charge > 余额 -> "Insufficient balance"。
    提交方式: 写 marketplace.pending.json 事务日志 -> Recover(前滚)。
    """
    state = read_inventory(root, owner)
    if transaction in state["Transactions"]:
        return 0
    skus = list(skus)
    quantities = list(quantities)
    if len(skus) == 0 or len(skus) > 16 or len(skus) != len(quantities) \
            or len(set(skus)) != len(skus):
        raise InvalidDataError("Invalid SKU count")
    account = read_account(root)
    if account is None:
        raise InvalidDataError("Account unavailable")
    catalog = load_catalog()
    charge = 0
    for i, sku_id in enumerate(skus):
        sku = catalog.get(sku_id)
        qty = quantities[i]
        if sku is None or sku.Currency != currency or qty == 0 or qty > 1000 \
                or (not sku.Stackable and qty != 1):
            raise InvalidDataError("Unsupported SKU/currency/quantity")
        # 只处理已确认"永久拥有"语义的装备类别。
        if sku.Category < 0 or sku.Category > 7 or (sku.Category == 7 and not sku.Stackable):
            raise InvalidDataError("Unconfirmed quantity/bundle item")
        key = str(sku.Item)
        owned = int(state["Items"].get(key, 0))
        if sku.Stackable:
            charge += sku.Price * qty
            newv = owned + sku.Grant * qty
            if newv > 0xFFFFFFFF:   # C# checked((uint)) 溢出
                raise InvalidDataError("Inventory quantity overflow")
            state["Items"][key] = newv
        elif owned == 0:
            charge += sku.Price
            state["Items"][key] = 1
    balance = int(_ci_get(account, "CodPoints", 0)) if currency == 1 \
        else int(_ci_get(account, "Gold", 0))
    if charge > balance:
        raise InvalidDataError("Insufficient balance")
    if currency == 1:
        account["CodPoints"] = balance - charge
    else:
        account["Gold"] = balance - charge
    account["SavedUtc"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f") + "0Z"     # 近似 C# DateTime.UtcNow.ToString("o")
    state["Transactions"].append(transaction)
    journal = {
        "Version": 1,
        "Account": base64.b64encode(_dumps(account)).decode("ascii"),
        "Secure": base64.b64encode(
            apply_to_secure(open(secure_path(root), "rb").read(), account)).decode("ascii"),
        "Inventory": base64.b64encode(_dumps(state)).decode("ascii"),
    }
    _atomic(pending_path(root), _dumps(journal))
    recover(root)
    return 0


# ======================================================================
# 应答对象
# ======================================================================
def inventory_object(owner, item, quantity):
    """照抄 MarketplaceStore.cs:113-124 InventoryObject(逐字节)。共 62 字节。

    结构:
      10            u64 owner            16 "cod"\\0
      08 item      08 quantity          08 0        (无过期)
      19           08 0(blob 长度本身也是个带 tag 的 u32)
      08 FFFFFFFF  09 <i64 long.MaxValue>
      06 <u16 0>   08 FFFFFFFF           08 0
    """
    w = bytearray()
    w += bytes([0x0A]) + struct.pack("<Q", int(owner) & 0xFFFFFFFFFFFFFFFF)
    w += bytes([0x10]) + b"cod" + bytes([0x00])
    w = _u32(w, item)
    w = _u32(w, quantity)
    w = _u32(w, 0)                     # no expiration
    w += bytes([0x13])
    w = _u32(w, 0)                     # blob length is itself a typed UInt32
    w = _u32(w, 0xFFFFFFFF)
    w += bytes([0x09]) + struct.pack("<q", 0x7FFFFFFFFFFFFFFF)   # long.MaxValue
    w += bytes([0x06]) + struct.pack("<H", 0)
    w = _u32(w, 0xFFFFFFFF)
    w = _u32(w, 0)
    return bytes(w)


def inventory_results(root, owner):
    """照抄 MarketplaceStore.cs:90-93 InventoryResults: 按 item 数值升序的对象列表。"""
    state = read_inventory(root, owner)
    keys = sorted(state["Items"].keys(), key=lambda k: int(k))
    return [inventory_object(owner, int(k), int(state["Items"][k])) for k in keys]


def balance_object(root, currency):
    """照抄 MarketplaceStore.cs:95-103 BalanceObject: 03 <currency> 08 <u32 值>。"""
    account = read_account(root)
    if account is None:
        raise InvalidDataError("Account unavailable")
    val = int(_ci_get(account, "CodPoints", 0)) if currency == 1 \
        else int(_ci_get(account, "Gold", 0))
    return bytes([0x03, currency & 0xFF]) + _u32(bytearray(), val)


# 照抄 MarketplaceStore.cs:107 的 58 字节购买参数模板。
PARSE_EXPECTED = [
    16, 0, 8, 1, 0, 0, 0, 8, 0, 0, 0, 0, 8, 1, 0, 0, 0, 8, 1, 0, 0, 0, 1, 0,
    8, 1, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 16, 0, 8, 0, 0, 0, 0, 8, 0, 0,
    0, 0, 3, 0, 8, 0, 0, 0, 0, 0,
]


def parse_purchase(frame, declared, currency):
    """照抄 MarketplaceStore.cs:104-112 ParsePurchase(逐字节)。

    frame    = 客户端任务帧解出的**整段明文**(u32 declared 在偏移 0, payload 从偏移 8 起)。
    declared = frame[0:4] 的 u32。
    currency = 1(CP/80) 或 2(GP/93)。

    返回 (sku, quantity)。不匹配 -> InvalidDataError("Unsupported purchase parameters")。
    """
    expected = list(PARSE_EXPECTED)
    expected[53] = 1 if currency == 1 else 0
    if declared - 3 != len(expected):
        raise InvalidDataError("Unsupported purchase parameters")
    if len(frame) < 8 + len(expected):
        raise InvalidDataError("Unsupported purchase parameters")
    for i in range(len(expected)):
        if (i < 8 or i > 11) and (i < 18 or i > 21):
            if frame[8 + i] != expected[i]:
                raise InvalidDataError("Unsupported purchase parameters")
    sku = _u32_at(frame, 16)
    quantity = _u32_at(frame, 26)
    return sku, quantity


def marketplace_player_data(root, owner):
    """照抄 PlayerProfile.cs:318-345 MarketplacePlayerData。账户缺失时返回 None。

    结构:
      AccountId(10 u64 owner, 16 "cod"\\0)
      08 2 (钱包个数)
      for b in 1..2: 03 b 08 <u32 余额>
      08 <u32 库存对象个数>
      for item in inventory: item[14:]     (内嵌库存省略 AccountId 前缀 14 字节)
      08 0
    """
    account = read_account(root)
    if account is None:
        return None
    w = bytearray()
    w += bytes([0x0A]) + struct.pack("<Q", int(owner) & 0xFFFFFFFFFFFFFFFF)
    w += bytes([0x10]) + b"cod" + bytes([0x00])
    w = _u32(w, 2)
    for b in (1, 2):
        w += bytes([0x03, b])
        v = int(_ci_get(account, "CodPoints", 0)) if b == 1 \
            else int(_ci_get(account, "Gold", 0))
        w = _u32(w, v)
    inv = inventory_results(root, owner)
    w = _u32(w, len(inv))
    for item in inv:
        w += item[14:]
    w = _u32(w, 0)
    return bytes(w)


# ======================================================================
# secure 档案(8/2)—— Decode / Apply
# ======================================================================
def _crc(buf, begin, count):
    """照抄 PlayerProfile.cs:85-97 Crc(标准 CRC-32/ISO-HDLC, 反射多项式 0xEDB88320)。"""
    num = 0xFFFFFFFF
    for i in range(begin, begin + count):
        num ^= buf[i]
        for _ in range(8):
            num = (num >> 1) ^ (0xEDB88320 if (num & 1) else 0)
    return (~num) & 0xFFFFFFFF


def _tail(blob):
    """照抄 PlayerProfile.cs:104-132 Tail: 每个非 skipped 字段 = 1 字节类型 tag + 值。

    这里用的 exe 布局没有 skipped 字段, 但保留该分支以对齐 C#。
    """
    out = bytearray()
    for _path, offset, ftype in LAYOUT_FIELDS:
        if ftype == "skipped":
            continue
        out += bytes([13 if ftype == "float32" else 7])
        if ftype in ("int32", "float32"):
            out += blob[offset:offset + 4]
        elif ftype == "int32_from_byte":
            out += struct.pack("<i", blob[offset])
        elif ftype == "int32_from_int16":
            out += struct.pack("<i", struct.unpack_from("<h", blob, offset)[0])
        else:
            raise InvalidDataError("未知的安全档案字段类型。")
    return bytes(out)


def _decode_secure(response):
    """照抄 PlayerProfile.cs:134-148 Decode。返回 32768 字节的数组。"""
    count = len([f for f in LAYOUT_FIELDS if f[2] != "skipped"])
    if (len(response) != 32803 + count * 5 or response[0] != 10
            or response[9] != 8 or response[14] != 8 or response[19] != 8
            or response[24] != 8 or response[29] != 19 or response[30] != 8
            or _u32_at(response, 15) != 0 or _u32_at(response, 20) != 1
            or _u32_at(response, 31) != 32768):
        raise InvalidDataError("安全档案响应格式错误, 未修改原文件。")
    arr = bytearray(response[35:35 + 32768])
    crc = _crc(arr, 4, 32768 - 4)
    if (_i32_at(arr, 4) != LAYOUT_VERSION or _u32_at(arr, 8) != LAYOUT_SCHEMA_WORD
            or _u32_at(arr, 0) != crc or _u32_at(response, 25) != crc
            or _tail(arr) != bytes(response[32803:])):
        raise InvalidDataError("安全档案结构、校验值或附加字段不一致, 未修改原文件。")
    return arr


def apply_to_secure(secure_bytes, account):
    """照抄 PlayerProfile.cs:150-166 Apply: 把 Level/Experience/Prestige 写进 secure 档案。

    ★ 依赖的 player-layout.json 已内嵌为 LAYOUT_*(见文件头), 因此本函数无需外部布局文件。
    """
    _validate_account(account)
    arr = _decode_secure(secure_bytes)
    _put(arr, _layout_offset("rank"), int(_ci_get(account, "Level", 0)))
    _put(arr, _layout_offset("experience"), int(_ci_get(account, "Experience", 0)))
    _put(arr, _layout_offset("prestige"), int(_ci_get(account, "Prestige", 0)))
    _put(arr, _layout_offset("rankVersion"), LAYOUT_RANK_VERSION)
    crc = _crc(arr, 4, len(arr) - 4)
    _put(arr, 0, crc)
    out = bytearray(secure_bytes)
    _put(out, 25, crc)
    out[35:35 + len(arr)] = arr
    tail = _tail(arr)
    out[35 + len(arr):35 + len(arr) + len(tail)] = tail
    return bytes(out)


def load_secure(root):
    """读 root 下的 secure 档案原始字节(对应 PlayerProfile.SecurePath + ReadAllBytes)。"""
    with open(secure_path(root), "rb") as f:
        return f.read()


# ======================================================================
# 自测(临时目录)
# ======================================================================
if __name__ == "__main__":
    import shutil
    import tempfile

    def fake_secure(level, exp, prestige):
        """构造一份能被 Decode 接受的合法 secure 档案(用于自测)。"""
        arr = bytearray(32768)
        struct.pack_into("<i", arr, 4, LAYOUT_VERSION)
        struct.pack_into("<I", arr, 8, LAYOUT_SCHEMA_WORD)
        _put(arr, _layout_offset("rank"), level)
        _put(arr, _layout_offset("experience"), exp)
        _put(arr, _layout_offset("prestige"), prestige)
        _put(arr, _layout_offset("rankVersion"), LAYOUT_RANK_VERSION)
        crc = _crc(arr, 4, len(arr) - 4)
        _put(arr, 0, crc)
        tail = _tail(arr)
        resp = bytearray(32803 + len(tail))
        resp[0] = 10
        resp[9] = 8
        resp[14] = 8
        struct.pack_into("<I", resp, 15, 0)
        resp[19] = 8
        struct.pack_into("<I", resp, 20, 1)
        resp[24] = 8
        struct.pack_into("<I", resp, 25, crc)
        resp[29] = 19
        resp[30] = 8
        struct.pack_into("<I", resp, 31, 32768)
        resp[35:35 + 32768] = arr
        resp[32803:32803 + len(tail)] = tail
        return bytes(resp)

    print("=" * 68)
    print("[1] 目录加载")
    cat = load_catalog()
    print("    条目数 =", len(cat))
    for i in (1, 2, 3):
        print("    ", cat[i])
    assert len(cat) > 0, "目录为空"

    tmp = tempfile.mkdtemp(prefix="mkstore-selftest-")
    try:
        owner = 16701785630074219790
        account = {"FormatVersion": 1, "Build": 1649370, "Name": "TestClient",
                   "Level": 70, "Experience": 11056700, "Prestige": 4,
                   "CodPoints": 100000000, "Gold": 100000000,
                   "SavedUtc": "2026-09-30T13:30:48.6770580Z"}
        os.makedirs(os.path.join(tmp, "player_profiles"), exist_ok=True)
        with open(os.path.join(tmp, "player-account.json"), "w", encoding="utf-8") as f:
            json.dump(account, f, ensure_ascii=False)
        with open(os.path.join(tmp, "player_profiles", "secure.result"), "wb") as f:
            f.write(fake_secure(70, 11056700, 4))

        print("=" * 68)
        print("[2] apply_to_secure / _decode_secure 往返")
        sec = load_secure(tmp)
        print("    合成 secure 长度 =", len(sec), "(应 32983)")
        assert len(sec) == 32983
        for lv, ex, pr in ((1, 0, 0), (70, 11056700, 4), (30, 634350, 2)):
            a = dict(account, Level=lv, Experience=ex, Prestige=pr)
            out = apply_to_secure(sec, a)
            arr = _decode_secure(out)
            ok = (_i32_at(arr, _layout_offset("rank")) == lv
                  and _i32_at(arr, _layout_offset("experience")) == ex
                  and _i32_at(arr, _layout_offset("prestige")) == pr)
            print("    Lv=%-3d Exp=%-9d Prestige=%d -> rank/exp/prestige 写回 %s"
                  % (lv, ex, pr, "OK" if ok else "!! 失败"))
            assert ok
        # 只读验证真实档案(exe 布局是否匹配现场 secure.result)
        real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "player_profiles", "secure.result")
        if os.path.exists(real):
            raw = open(real, "rb").read()
            arr = _decode_secure(raw)
            print("    真实 secure.result: %d 字节, Decode OK(布局匹配), "
                  "rank=%d experience=%d prestige=%d"
                  % (len(raw), _i32_at(arr, _layout_offset("rank")),
                     _i32_at(arr, _layout_offset("experience")),
                     _i32_at(arr, _layout_offset("prestige"))))

        print("=" * 68)
        print("[3] purchase + 幂等")
        # 选一个 currency=1、Category 0..7、非 Stackable、非 cat7 的 SKU
        pick = None
        for sid in sorted(cat):
            s = cat[sid]
            if s.Currency == 1 and 0 <= s.Category <= 6 and not s.Stackable and s.Price > 0:
                pick = s
                break
        stack = None
        for sid in sorted(cat):
            s = cat[sid]
            if s.Currency == 1 and s.Stackable and 0 <= s.Category <= 7 and s.Grant > 0:
                stack = s
                break
        print("    非 Stackable 测试 SKU:", pick)
        cp0 = account["CodPoints"]
        st = read_inventory(tmp, owner)
        assert st["Items"] == {} and st["Transactions"] == []
        r = purchase(tmp, owner, "tx-1", 1, [pick.Id], [1])
        st = read_inventory(tmp, owner)
        a = read_account(tmp)
        print("    purchase 返回 =", r)
        print("    CodPoints %d -> %d (扣 %d, 期望 %d)"
              % (cp0, a["CodPoints"], cp0 - a["CodPoints"], pick.Price))
        print("    Items =", st["Items"], " Transactions =", st["Transactions"])
        assert r == 0
        assert a["CodPoints"] == cp0 - pick.Price
        assert st["Items"][str(pick.Item)] == 1
        assert st["Transactions"] == ["tx-1"]
        cp1 = a["CodPoints"]
        r2 = purchase(tmp, owner, "tx-1", 1, [pick.Id], [1])   # 幂等
        a2 = read_account(tmp)
        print("    重复同 transaction 返回 =", r2, " CodPoints 保持 =", a2["CodPoints"])
        assert r2 == 0 and a2["CodPoints"] == cp1
        # Stackable + quantity>1 分支
        if stack is not None:
            print("    Stackable 测试 SKU:", stack)
            before = read_account(tmp)["CodPoints"]
            purchase(tmp, owner, "tx-2", 1, [stack.Id], [3])
            after = read_account(tmp)["CodPoints"]
            st2 = read_inventory(tmp, owner)
            print("    quantity=3 -> 扣 %d (期望 %d), Items[%s]=%d (期望 %d)"
                  % (before - after, stack.Price * 3, stack.Item,
                     st2["Items"][str(stack.Item)], stack.Grant * 3))
            assert before - after == stack.Price * 3
            assert st2["Items"][str(stack.Item)] == stack.Grant * 3

        print("=" * 68)
        print("[4] parse_purchase")
        payload = bytearray(PARSE_EXPECTED)
        payload[53] = 1                                  # currency=1(CP/80)
        struct.pack_into("<I", payload, 8, pick.Id)      # frame[16]
        struct.pack_into("<I", payload, 18, 2)           # frame[26]
        frame = struct.pack("<I", 61) + bytes([0x86, 0x50, 0x03, 0x62]) + bytes(payload)
        print("    frame 长度 =", len(frame), " declared =", _u32_at(frame, 0))
        sku, qty = parse_purchase(frame, _u32_at(frame, 0), 1)
        print("    解出 sku = %d (期望 %d), quantity = %d (期望 2)" % (sku, pick.Id, qty))
        assert sku == pick.Id and qty == 2
        bad = bytearray(frame)
        bad[8 + 3] = 0xFF                                # 破坏一个受检字节(i=3)
        try:
            parse_purchase(bytes(bad), _u32_at(bad, 0), 1)
            print("    !! 篡改后未抛异常")
            raise SystemExit(1)
        except InvalidDataError as e:
            print("    篡改 1 字节 -> 抛异常:", e)

        print("=" * 68)
        print("[5] inventory_object / balance_object 逐字段核对")
        iob = inventory_object(owner, pick.Item, 1)
        print("    inventory_object(%d, %d, 1) = %d 字节" % (owner, pick.Item, len(iob)))
        print("      hex =", iob.hex(" "))
        assert len(iob) == 62
        assert iob[0] == 0x0A and struct.unpack_from("<Q", iob, 1)[0] == owner and iob[9] == 0x10
        assert iob[10:13] == b"cod" and iob[13] == 0x00
        assert iob[14] == 0x08 and _u32_at(iob, 15) == pick.Item      # item
        assert iob[19] == 0x08 and _u32_at(iob, 20) == 1              # quantity
        assert iob[24] == 0x08 and _u32_at(iob, 25) == 0             # no expiration
        assert iob[29] == 0x13 and iob[30] == 0x08 and _u32_at(iob, 31) == 0
        assert iob[35] == 0x08 and _u32_at(iob, 36) == 0xFFFFFFFF
        assert iob[40] == 0x09 and struct.unpack_from("<q", iob, 41)[0] == 0x7FFFFFFFFFFFFFFF
        assert iob[49] == 0x06 and struct.unpack_from("<H", iob, 50)[0] == 0
        assert iob[52] == 0x08 and _u32_at(iob, 53) == 0xFFFFFFFF
        assert iob[57] == 0x08 and _u32_at(iob, 58) == 0
        print("      字段核对: OK (10/u64 owner/16 'cod'/08 item/08 qty/08 0/"
              "13+08 blob-len 0/08 FFFFFFFF/09 i64 Max/06 u16 0/08 FFFFFFFF/08 0)")
        bal = balance_object(tmp, 1)
        cp = read_account(tmp)["CodPoints"]
        print("    balance_object(1) =", bal.hex(" "), " 值 =", _u32_at(bal, 3),
              " 账户 CodPoints =", cp)
        assert bal == bytes([3, 1, 8]) + struct.pack("<I", cp)
        bal2 = balance_object(tmp, 2)
        print("    balance_object(2) =", bal2.hex(" "), " 值 =", _u32_at(bal2, 3))

        print("=" * 68)
        print("[6] inventory_results / marketplace_player_data")
        objs = inventory_results(tmp, owner)
        print("    inventory_results 条数 =", len(objs), " 每条长度 =",
              [len(o) for o in objs])
        mpd = marketplace_player_data(tmp, owner)
        print("    marketplace_player_data = %d 字节" % len(mpd))
        print("      hex =", mpd.hex(" "))
        assert mpd[0] == 0x0A and mpd[9] == 0x10 and mpd[10:13] == b"cod"
        print("    自测全部通过")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
