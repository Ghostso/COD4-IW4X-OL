# -*- coding: utf-8 -*-
"""从 exe 里提取的 codo.objects.SKUObj 字段表(2026-10-05, exe 0x6AF8D4 附近)。

这是**客户端自己**的 SKU 结构定义 —— 商城目录、购买校验都按它来。
我们之前用的 marketplace-catalog.json 是启动器内嵌的另一套, 字段对不上,
这就是"客户端发的 sku id 在目录里查无此物"的根因。

字段顺序(按 exe 里字符串表的出现次序, 即引擎注册顺序):
"""

SKU_OBJ_FIELDS = [
    "SKUs",                    # 可能是容器名
    "giftable",
    "isAvailableForSale",
    "currentSKUIndex",
    "skuTypes",
    "codo.objects.SKUObj",     # 类型名
    "productId",               # ★ 客户端购买帧里的 "sku" 就是这个
    "requirementLevel",
    "requirementPrestige",
    "requirementUnlockFlag",
    "stackable",
    "promoSkuId",
    "price",
    "currency",                # @SF_UI_CP / @SF_UI_GP / @SF_UI_HP / @SF_UI_EHP
    "startDate",
    "endDate",
    "ignoreEntitlement",
    "couponEnable",
    "originalPrice",
    "discountRate",
    "override_duration",
    "itemsList",
    "expireDateTime",
    "expiryDuration",
    "hasIdenticalDurations",
    "noExpiredItemInBundle",
    "specialPara",
    "salesNumber",
    "enableInTF141",
    "enableInSC",
    "equipLevel",
    "enableInZombie",
    "isBanned",
    "isBasePerk",
    "inInventoryButLocked",
    "inInventoryButExpired",
    "showBreadcrumb",
    "exclusiveProductID",
    "codo.objects.NotForSaleObj",
    "notForSaleObj",
    "legendDesc",
    "itemDependencies",
    "isEquippableBundle",
    "onboardCharacterID",
    "bHideFromMarket",
    "tagOrder",
]

# 货币枚举(对应 @SF_UI_* 标签)
CURRENCY = {"CP": 1, "GP": 2, "HP": 3, "EHP": 4}

# 客户端内置的仓库操作入口(exe 字符串表) —— 可用于直接加道具
INVENTORY_API = [
    "HackAddToInventory",
    "UpdateInventoryForItem",
    "IsInInventory",
    "IsLastTransactionComplete",
    "ClearLastTransactionComplete",
]

# 购买/市场的 UI 错误文案键
UI_ERRORS = [
    "@SF_UI_PURCHASE_SKUS_FAILED",
    "@SF_UI_PURCHASE_INSUFFICIENT_FUNDS",
    "@SF_UI_PURCHASE_INTERRUPTED",
    "@SF_UI_MARKETPLACE_RESOURCE_NOT_FOUND",
    "purchaseInterrupted",
    "cppShoppingCartFull",
]

# 购买链路相关函数(exe 字符串表)
PURCHASE_FUNCS = [
    "cppRequestUpdateMarketInventory",
    "cppRefreshShoppingCart",
    "cppOnPreviewListChanged",
    "cppOnMarketplaceUpdateStateChanged",
    "cppOnMarketplaceInMaintainStateChanged",
    "updateInventory",
    "purchase",
]
