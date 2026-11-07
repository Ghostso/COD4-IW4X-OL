# -*- coding: utf-8 -*-
"""生成"商城 SKU 页"应答 —— 让商城显示可买道具。

背景
----
客户端向 `80/70`、`80/107`、`80/119`、`80/173/174/232` 要商品目录, 我们一直回**空页**
-> `MarketScrollGrid` 拿到 null -> 抛 `TypeError #1009` -> 商城空白、
`SupplyDropView`(军火箱)页面栈不完整 -> 返回时旧页面叠在大厅上。

目录值官方那份在 `common_marketplace_lite`(层二加密, 静态无解, 运行时内存里也只
有点到过的少数几条)。**因此我们自己造**: 本地有 37,615 条 SKU
(`marketplace-catalog.json`), 配上从客户端内存里挖到的权威字段表
(`_sku_schema_as.py`, `SKUObj`), 就能编出客户端认的目录。

编码格式
--------
与其它对象一致 —— Demonware ByteBuffer 的"类型标签 + 值"(见 codol_crypto.Buf):
    0x01 BOOL / 0x03 U8 / 0x06 U16 / 0x07 I32 / 0x08 U32 / 0x09 I64 /
    0x0A U64 / 0x10 STRING(0 结尾) / 0x13 BLOB(0x08 + u32 len + data)
已由 `inventory_object` / `balance_object` 两个**实机可用**的对象逐字节验证。

★ 默认关闭: 只有存在 `marketplace-skus.on` 时才回真实 SKU 页。
  因为三方注释警告过"格式错的 SKU 页会让整个 marketplace 服务死掉",
  所以第一版只发**少量**条目(可用 `marketplace-skus-count.txt` 调),
  先确认客户端能渲染、不再抛 #1009。
"""
import os
import struct

import codol_crypto as cc

OUTDIR = os.path.dirname(os.path.abspath(__file__))

SKU_FLAG = os.path.join(OUTDIR, "marketplace-skus.on")
SKU_COUNT_FILE = os.path.join(OUTDIR, "marketplace-skus-count.txt")

# 客户端货币枚举(见 §4.0.1 exe 字符串表: @SF_UI_CP/GP/HP/EHP)
CUR_CP, CUR_GP, CUR_HP, CUR_EHP = 1, 2, 3, 4


def sku_page_enabled():
    return os.path.exists(SKU_FLAG)


def page_size(default=24):
    try:
        return max(1, min(2000, int(open(SKU_COUNT_FILE, encoding="ascii").read().strip())))
    except Exception:
        return default


def _sku_obj(sku, item=None):
    """编一条 SKU 对象(字段顺序照 `_sku_schema_as.SKU_AS_FIELDS`)。

    这里只写客户端渲染**必需**的那几个字段; 其余留默认(不写 tag 即视为缺省)。
    字段名 -> 我们的取值:
        name          = 道具名(没有就空串, 客户端会回退到 id)
        id            = SKU id(catalog.Id)
        productId     = 道具 item(catalog.Item)  ← 购买帧里发的就是这个
        price/originalPrice = catalog.Price
        currency      = catalog.Currency(1=CP, 2=GP)
        stackable     = catalog.Stackable
        purchasable   = True
        requirementLevel / requirementPrestige / requirementUnlockFlag = 0(无门槛)
        indexInProduct = 0
    """
    # ★★ 2026-10-06 哨兵探针验证过的**类型正确**编码:
    #   AS3 类型表: name=String(10) id=int(07) stackable/purchasable/...=Boolean(01)
    #   currency 与余额对象一致用 u8(03); 其余数值用 u32(08), 有符号门槛用 i32(07)。
    #   实测: 这个编码的哨兵值会出现在客户端堆里(被解析); 旧的"全 u32"方案
    #   会把整个 marketplace 服务打挂(codol_crypto.py:260 也证明客户端逐值查类型)。
    b = cc.Buf()
    b.string(sku.get("name", "") or "")
    b.i32(int(sku["id"]))                     # id: int (0x07)
    b.u32(int(sku.get("promoSkuId", 0)))      # promoSkuId (0x08)
    b.u32(0)                                  # cp (0x08)
    b.u32(0)                                  # cc (0x08)
    b.u32(int(sku.get("duration", 0)))        # duration (0x08)
    b.u8(0)                                   # extra u8 in CODOL bdMarketplaceSku! (0x03)
    b.bool_(bool(sku.get("stackable", False)))# stackable (0x01)
    b.u32(int(sku.get("productId", 0)))       # productId (0x08)
    b.i32(int(sku.get("requirementLevel", 0)))# requirementLevel (0x07)
    b.i32(int(sku.get("requirementPrestige", 0))) # requirementPrestige (0x07)
    b.u32(0)                                  # requirementUnlockFlag (0x08)
    b.bool_(True)                             # purchasable (0x01)
    b.u32(int(sku.get("originalPrice", 0)))   # originalPrice (0x08)
    b.u32(int(sku.get("price", 0)))           # price (0x08)
    b.u8(int(sku.get("currency", CUR_CP)))    # currency: u8 (0x03)
    b.bool_(False)                            # couponEnable (0x01)
    b.u32(0)                                  # extra u32 in CODOL bdMarketplaceSku! (0x08)
    b.bool_(False)                            # ignoreEntitlement (0x01)
    b.u32(0)                                  # indexInProduct (0x08)
    b.bool_(False)                            # ignoreDiscount (0x01)
    return b.data()


def build_sku_page(entries, offset=0, limit=None):
    """把 catalog 条目编成"一页 SKU"对象列表。

    entries: [{"id","productId","price","currency","stackable","name"?}, ...]
    返回 byte[][] —— 交给 build_task_reply_objects 当 objects。
    """
    if limit is None:
        limit = page_size()
    sel = entries[offset:offset + limit]
    return [_sku_obj(e) for e in sel]


# ============================================================================
# ★ 2026-10-07: "按 item 分组、组内多档" 的编码路径。
#
# 依据: 运行时内存显示客户端目录模型是 `item -> SKU[]`
#       （同一 item 下挂 680/7天、2580/30天、10880/永久 等多个档），
#       与 AS 侧 itemData.skus/promoSkus/sortedSkus 一致。
#       见 HANDOFF §15 与 mkt_assets/item_sku_arrays.csv。
#
# 注意: 这条路径的**外层/字段序仍是待验证假设**（80/70 的真实线格式没有
#       第三方参考实现）。所以：
#         * 默认关；
#         * 打开后**只发 1 个 item**（marketplace-skus-count.txt 控制），
#           确认客户端不锁 UI、能出条目，再放量；
#         * 任何异常 -> 删 `marketplace-skus-itemgroup.on` 立即回退空页。
# ============================================================================
ITEMGROUP_FLAG = os.path.join(OUTDIR, "marketplace-skus-itemgroup.on")
ITEMSKU_CSV = os.path.join(OUTDIR, "mkt_assets", "item_sku_arrays.csv")

# ground-truth SKU（实测入库成功）—— 只信含这些的 item 组。
# ★ 只用**真正实测过**的 5 个；不要加 80 这类"数值常见"的当锚点，
#   否则会把 (80,99,240) 这种跨区巧合组也放进来。
_TRUSTED_SKUS = {37251, 31184, 37116, 16096, 31774}


def itemgroup_enabled():
    return os.path.exists(ITEMGROUP_FLAG)


def load_item_groups(trusted_only=True):
    """读 item_sku_arrays.csv -> {item: [ {id,productId,price,duration_days} ]}。

    trusted_only=True 时只保留"组里至少有一个 ground-truth SKU"的 item，
    避免把低 item 段的噪声组发出去。
    """
    import csv
    groups = {}
    if not os.path.exists(ITEMSKU_CSV):
        return groups
    raw = {}
    with open(ITEMSKU_CSV, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            it = int(r["item"])
            raw.setdefault(it, []).append({
                "id": int(r["sku"]),
                "productId": it,
                "price": int(r["price"]),
                "duration_days": int(r["days"]),
                "currency": CUR_GP,      # 由客户端帧决定, 有 lenient 兜底
                "stackable": False,
                "name": "",
            })
    if not trusted_only:
        return raw
    for it, tiers in raw.items():
        if not any(t["id"] in _TRUSTED_SKUS for t in tiers):
            continue
        # ★ 组内清洗: 同一 item 的 SKU 档位编号应当量级相近(如 31184/31759/39592)。
        #   像 item 122 里混进来的 `sku 80`(240 天租金) 明显是跨区对齐噪声 ——
        #   丢掉远小于组内最大编号的档。
        hi = max(t["id"] for t in tiers)
        keep = [t for t in tiers if t["id"] >= hi // 10]
        if keep:
            groups[it] = keep
    return groups


def build_item_sku_page(limit=None):
    """编"一页 item 分组 SKU"：每个 item 一个对象，对象内是该 item 的多档 SKU。

    返回 [(item, [sku_obj_bytes, ...]), ...]，调用方决定怎么装进应答。
    """
    groups = load_item_groups(trusted_only=True)
    if limit is None:
        limit = page_size()
    out = []
    for it in sorted(groups)[:limit]:
        objs = [_sku_obj(t) for t in groups[it]]
        out.append((it, objs))
    return out


def catalog_entries(limit=None, category=None, currency=None, min_price=0):
    """从本地 catalog 取条目(已去重: 同一 item 只留一条, 优先同货币)。

    这样"商城摆全量"时不会因为同一个 item 有多条 SKU 而重复铺满。
    """
    try:
        import marketplace_store as ms
        cat = ms.load_catalog()
    except Exception:
        return []
    seen = set()
    out = []
    for s in sorted(cat.values(), key=lambda x: int(x.Id)):
        if category is not None and int(s.Category) != int(category):
            continue
        if currency is not None and int(s.Currency) != int(currency):
            continue
        if int(s.Price) < int(min_price):
            continue
        key = int(s.Item)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": int(s.Id),
            "productId": int(s.Item),
            "price": int(s.Price),
            "currency": CUR_CP if int(s.Currency) == 1 else CUR_GP,
            "stackable": bool(s.Stackable),
            "duration": 0,
            "name": "",
            "category": int(s.Category),
        })
        if limit and len(out) >= limit:
            break
    return out
