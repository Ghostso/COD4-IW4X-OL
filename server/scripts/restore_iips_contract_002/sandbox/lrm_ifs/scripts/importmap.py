"""重建 .idata2 的「导入槽 RVA -> dll!name」映射（v2，已修正）。

结构（全部经字节级验证）：

  * IAT 槽数组位于 0xb02000，长度 0xc00（与 PE 数据目录 IAT 项一致），
    紧接其后 0xb02db8 起是同一序列的第二份拷贝（ILT/IAT 镜像）。
    每个 DLL 一块，块内以 NULL dword 结尾。
  * 具名条目的槽值 = 指向 `[u16 hint][asciz name]` 的 RVA，名字在 slot_value+2。
  * 序数条目 = 0x80000000 | ordinal。
  * 名字区从 0xb039b8 起，**每条目按 4 字节对齐**：
        step = (2 + len(name) + 1 + 3) & ~3
    这正是早期解析漂移、把 "CRYPT32.dll" 读成 "YPT32.dll" 的原因。
  * DLL 名串混排在函数名之间，DLL 出现顺序 == 槽块顺序，
    因此可用名字区顺序给槽块归属 DLL。
  * 出 0xb02c00 之后的「块」不是导入槽——那是把 IAT 当成无限表读越界了，
    会产生 rviceW / owWindow 这类**字符串中段截断**的假名字。

注意：PE 头里的 Import 目录指向 0x009f67b8（.data，仅 kernel32 + libcef，是幌子），
真正的导入表在 .idata2，且 IAT 数据目录被改写为指向它。
"""
import struct
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe import Image

IAT_RVA = 0xb02000
IAT_SIZE = 0xc00          # 来自 PE 数据目录
NAMES_RVA = 0xb039ba      # 名字区起点=首个 hint 字段（0xb039b8 是其前的 2 字节零)
IDATA2_END = 0xb07000

# ---- 序号表来源（2026-09-11 更正，**必须**保留这段由来）----
# 旧表（1:accept … 23:socket，10=inet_addr / 11=inet_ntoa / 12=ioctlsocket）
# **不是 ws2_32.dll 的表**，而是 wsock32.dll（Socket 1.1）的序数布局，被误用到
# ws2_32.dll 上。实测两者 1..23 逐字节相同，连 10/11/12 的错位都一致。
#   真 ws2_32.dll : 10=ioctlsocket  11=inet_addr  12=inet_ntoa
#   真 wsock32.dll: 10=inet_addr    11=inet_ntoa  12=ioctlsocket
# 另有一段**独立**错误：旧表 112..119 两个 DLL 都不匹配（真 112/113/114 =
# WSASetLastError/WSACancelBlockingCall/WSAIsBlocking 被放到旧表的 117/118/119，
# 而 112/113/114 被凭空填成 WSAIoctl/WSANtohl/WSANtohs）。
#
# 下表由 C:\Windows\SysWOW64\ws2_32.dll 的**真实导出地址表(EAT)** 程序化导出：
#   Base=1  NumberOfFunctions=500  NumberOfNames=180（最高具名序数 179；无 500/WEP）
# 判定「块 16 是 ws2_32.dll」不依赖本表：其序数集合是经典 ws2_32 集合，
# 且块内有 16 个**二进制自带**的具名条目（WSAIoctl/WSASocketW/getaddrinfo…）。
# 本表只影响**序数形式**的槽；具名槽（槽值高位为 0）直接用二进制里的名字。
WS2_32_ORD = {
    1: 'accept', 2: 'bind', 3: 'closesocket', 4: 'connect', 5: 'getpeername', 6: 'getsockname',
    7: 'getsockopt', 8: 'htonl', 9: 'htons', 10: 'ioctlsocket', 11: 'inet_addr', 12: 'inet_ntoa',
    13: 'listen', 14: 'ntohl', 15: 'ntohs', 16: 'recv', 17: 'recvfrom',
    18: 'select', 19: 'send', 20: 'sendto', 21: 'setsockopt', 22: 'shutdown', 23: 'socket',
    24: 'WSApSetPostRoutine', 25: 'FreeAddrInfoEx', 26: 'FreeAddrInfoExW', 27: 'FreeAddrInfoW',
    28: 'GetAddrInfoExA', 29: 'GetAddrInfoExCancel', 30: 'GetAddrInfoExOverlappedResult',
    31: 'GetAddrInfoExW', 32: 'GetAddrInfoW', 33: 'GetHostNameW', 34: 'GetNameInfoW',
    35: 'InetNtopW', 36: 'InetPtonW', 37: 'SetAddrInfoExA', 38: 'SetAddrInfoExW',
    39: 'WPUCompleteOverlappedRequest', 40: 'WPUGetProviderPathEx', 41: 'WSAAccept',
    42: 'WSAAddressToStringA', 43: 'WSAAddressToStringW', 44: 'WSAAdvertiseProvider',
    45: 'WSACloseEvent', 46: 'WSAConnect', 47: 'WSAConnectByList', 48: 'WSAConnectByNameA',
    49: 'WSAConnectByNameW', 50: 'WSACreateEvent', 51: 'gethostbyaddr', 52: 'gethostbyname',
    53: 'getprotobyname', 54: 'getprotobynumber', 55: 'getservbyname', 56: 'getservbyport',
    57: 'gethostname', 58: 'WSADuplicateSocketA', 59: 'WSADuplicateSocketW',
    60: 'WSAEnumNameSpaceProvidersA', 61: 'WSAEnumNameSpaceProvidersExA',
    62: 'WSAEnumNameSpaceProvidersExW', 63: 'WSAEnumNameSpaceProvidersW',
    64: 'WSAEnumNetworkEvents', 65: 'WSAEnumProtocolsA', 66: 'WSAEnumProtocolsW',
    67: 'WSAEventSelect', 68: 'WSAGetOverlappedResult', 69: 'WSAGetQOSByName',
    70: 'WSAGetServiceClassInfoA', 71: 'WSAGetServiceClassInfoW',
    72: 'WSAGetServiceClassNameByClassIdA', 73: 'WSAGetServiceClassNameByClassIdW',
    74: 'WSAHtonl', 75: 'WSAHtons', 76: 'WSAInstallServiceClassA',
    77: 'WSAInstallServiceClassW', 78: 'WSAIoctl', 79: 'WSAJoinLeaf',
    80: 'WSALookupServiceBeginA', 81: 'WSALookupServiceBeginW', 82: 'WSALookupServiceEnd',
    83: 'WSALookupServiceNextA', 84: 'WSALookupServiceNextW', 85: 'WSANSPIoctl',
    86: 'WSANtohl', 87: 'WSANtohs', 88: 'WSAPoll', 89: 'WSAProviderCompleteAsyncCall',
    90: 'WSAProviderConfigChange', 91: 'WSARecv', 92: 'WSARecvDisconnect', 93: 'WSARecvFrom',
    94: 'WSARemoveServiceClass', 95: 'WSAResetEvent', 96: 'WSASend', 97: 'WSASendDisconnect',
    98: 'WSASendMsg', 99: 'WSASendTo', 100: 'WSASetEvent', 101: 'WSAAsyncSelect',
    102: 'WSAAsyncGetHostByAddr', 103: 'WSAAsyncGetHostByName',
    104: 'WSAAsyncGetProtoByNumber', 105: 'WSAAsyncGetProtoByName',
    106: 'WSAAsyncGetServByPort', 107: 'WSAAsyncGetServByName', 108: 'WSACancelAsyncRequest',
    109: 'WSASetBlockingHook', 110: 'WSAUnhookBlockingHook', 111: 'WSAGetLastError',
    112: 'WSASetLastError', 113: 'WSACancelBlockingCall', 114: 'WSAIsBlocking',
    115: 'WSAStartup', 116: 'WSACleanup', 117: 'WSASetServiceA', 118: 'WSASetServiceW',
    119: 'WSASocketA', 120: 'WSASocketW', 121: 'WSAStringToAddressA',
    122: 'WSAStringToAddressW', 123: 'WSAUnadvertiseProvider', 124: 'WSAWaitForMultipleEvents',
    125: 'WSCDeinstallProvider', 126: 'WSCDeinstallProviderEx', 127: 'WSCEnableNSProvider',
    128: 'WSCEnumProtocols', 129: 'WSCEnumProtocolsEx', 130: 'WSCGetApplicationCategory',
    131: 'WSCGetApplicationCategoryEx', 132: 'WSCGetProviderInfo', 133: 'WSCGetProviderPath',
    134: 'WSCInstallNameSpace', 135: 'WSCInstallNameSpaceEx2', 136: 'WSCInstallNameSpaceEx',
    137: 'WSCInstallProvider', 138: 'WSCInstallProviderAndChains', 139: 'WSCInstallProviderEx',
    140: 'WSCSetApplicationCategory', 141: 'WSCSetApplicationCategoryEx',
    142: 'WSCSetProviderInfo', 143: 'WSCUnInstallNameSpace', 144: 'WSCUnInstallNameSpaceEx2',
    145: 'WSCUpdateProvider', 146: 'WSCUpdateProviderEx', 147: 'WSCWriteNameSpaceOrder',
    148: 'WSCWriteProviderOrder', 149: 'WSCWriteProviderOrderEx', 150: 'WahCloseApcHelper',
    151: '__WSAFDIsSet', 152: 'WahCloseHandleHelper', 153: 'WahCloseNotificationHandleHelper',
    154: 'WahCloseSocketHandle', 155: 'WahCloseThread', 156: 'WahCompleteRequest',
    157: 'WahCreateHandleContextTable', 158: 'WahCreateNotificationHandle',
    159: 'WahCreateSocketHandle', 160: 'WahDestroyHandleContextTable',
    161: 'WahDisableNonIFSHandleSupport', 162: 'WahEnableNonIFSHandleSupport',
    163: 'WahEnumerateHandleContexts', 164: 'WahInsertHandleContext',
    165: 'WahNotifyAllProcesses', 166: 'WahOpenApcHelper', 167: 'WahOpenCurrentThread',
    168: 'WahOpenHandleHelper', 169: 'WahOpenNotificationHandleHelper', 170: 'WahQueueUserApc',
    171: 'WahReferenceContextByHandle', 172: 'WahRemoveHandleContext',
    173: 'WahWaitForNotification', 174: 'WahWriteLSPEvent', 175: 'freeaddrinfo',
    176: 'getaddrinfo', 177: 'getnameinfo', 178: 'inet_ntop', 179: 'inet_pton',
}

# wsock32.dll（Socket 1.1）真实 EAT：Base=1  NumberOfFunctions=1142  NumberOfNames=75。
# **必须与 WS2_32_ORD 分开**：旧代码把同一张表套在两个 DLL 上，正是本文件这轮更正的起因。
# 注意 wsock32 在 117..150 段**没有具名导出**（116 直接跳到 151）。
# 本二进制里块 17 只导入序数 11 与 22（= inet_ntoa / shutdown），二者恰好与旧表相同，
# 所以旧表在此块上的输出**碰巧是对的**——但这属于巧合，不是设计。
WSOCK32_ORD = {
    1: 'accept', 2: 'bind', 3: 'closesocket', 4: 'connect', 5: 'getpeername', 6: 'getsockname',
    7: 'getsockopt', 8: 'htonl', 9: 'htons', 10: 'inet_addr', 11: 'inet_ntoa',
    12: 'ioctlsocket', 13: 'listen', 14: 'ntohl', 15: 'ntohs', 16: 'recv', 17: 'recvfrom',
    18: 'select', 19: 'send', 20: 'sendto', 21: 'setsockopt', 22: 'shutdown', 23: 'socket',
    24: 'MigrateWinsockConfiguration',
    51: 'gethostbyaddr', 52: 'gethostbyname', 53: 'getprotobyname', 54: 'getprotobynumber',
    55: 'getservbyname', 56: 'getservbyport', 57: 'gethostname',
    101: 'WSAAsyncSelect', 102: 'WSAAsyncGetHostByAddr', 103: 'WSAAsyncGetHostByName',
    104: 'WSAAsyncGetProtoByNumber', 105: 'WSAAsyncGetProtoByName',
    106: 'WSAAsyncGetServByPort', 107: 'WSAAsyncGetServByName', 108: 'WSACancelAsyncRequest',
    109: 'WSASetBlockingHook', 110: 'WSAUnhookBlockingHook', 111: 'WSAGetLastError',
    112: 'WSASetLastError', 113: 'WSACancelBlockingCall', 114: 'WSAIsBlocking',
    115: 'WSAStartup', 116: 'WSACleanup', 151: '__WSAFDIsSet', 500: 'WEP',
    1000: 'WSApSetPostRoutine', 1100: 'inet_network', 1101: 'getnetbyname', 1102: 'rcmd',
    1103: 'rexec', 1104: 'rresvport', 1105: 'sethostname', 1106: 'dn_expand',
    1107: 'WSARecvEx', 1108: 's_perror', 1109: 'GetAddressByNameA', 1110: 'GetAddressByNameW',
    1111: 'EnumProtocolsA', 1112: 'EnumProtocolsW', 1113: 'GetTypeByNameA',
    1114: 'GetTypeByNameW', 1115: 'GetNameByTypeA', 1116: 'GetNameByTypeW',
    1117: 'SetServiceA', 1118: 'SetServiceW', 1119: 'GetServiceA', 1120: 'GetServiceW',
    1130: 'NPLoadNameSpaces', 1140: 'TransmitFile', 1141: 'AcceptEx',
    1142: 'GetAcceptExSockaddrs',
}


import re

# 名字区里混排着 DLL 名与函数名。**不要**靠逐条步进解析整块名字区去切分：
# 条目填充并不严格按 4 字节对齐（实测步进 16/20/20/22/26 不等），
# 一旦错位就会把 "EnumServicesStatusExA" 读成 "umServicesStatusExA"。
# 只需按地址顺序捞出 *.dll 串即可——它们恰好与槽块一一对应。
_DLL_RE = re.compile(rb'[A-Za-z0-9_.\-]{2,24}\.[Dd][Ll][Ll]\x00')


def parse_names(img, rva=NAMES_RVA, limit=0x2000):
    """顺序解析名字区，返回 [(rva, hint, name), ...]。
    仅作参考：填充不规则，长区间会漂移，别用它切分 DLL 边界。"""
    out = []
    while rva < IDATA2_END and len(out) < limit:
        o = img.foff(rva)
        if o is None:
            break
        hint = struct.unpack_from('<H', img.data, o)[0]
        s = img.cstr(rva + 2, 80)
        if not s or not all(c.isalnum() or c in '_@?.$' for c in s):
            break
        out.append((rva, hint, s))
        rva += (2 + len(s) + 1 + 3) & ~3
    return out


def dll_order(img, lo=IAT_RVA, hi=IDATA2_END):
    """名字区里所有 *.dll 串，按 RVA 升序 —— 这既是 DLL 顺序也是槽块顺序。"""
    start, end = img.foff(lo), img.foff(hi)
    buf = img.data[start:end]
    return [(img.voff(start + m.start()), m.group()[:-1].decode('latin1'))
            for m in _DLL_RE.finditer(buf)]


def groups(img):
    """[(dll_name, dll_name_rva), ...]，顺序即槽块顺序。"""
    return dll_order(img)


def slot_blocks(img):
    """按 NULL 分块读 IAT，**严格限制在数据目录给出的长度内**。"""
    blocks = []
    cur = []
    for rva in range(IAT_RVA, IAT_RVA + IAT_SIZE, 4):
        v = struct.unpack('<I', img.read(rva, 4))[0]
        if v == 0:
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append((rva, v))
    if cur:
        blocks.append(cur)
    return blocks


def _name_of(img, v, dll):
    """返回 (名字, 是否序数推导)。

    第二项=True 表示这个名字**不是二进制自带的**，而是我按「块归属哪个 DLL +
    序数 → 名字」推断出来的。调用点必须靠它区分「可信名字」与「表推名字」。
    具名条目（高位为 0）第二项恒为 False —— 名字直接读自 .idata2 名字区。
    """
    if v & 0x80000000:
        o = v & 0xffff
        d = dll.lower()
        # **先判 wsock32**：两个 DLL 的 1..23 段布局不同（10/11/12 完全错开），
        # 旧代码共用一张表正是这轮更正的起因。顺序写反会退回老毛病。
        if 'wsock32' in d:
            return WSOCK32_ORD.get(o) or ('ORD#%d' % o), True
        if 'ws2_32' in d:
            return WS2_32_ORD.get(o) or ('ORD#%d' % o), True
        return 'ORD#%d' % o, True
    return (img.cstr(v + 2, 96) or ('<bad 0x%08x>' % v)), False


def build(img=None, verbose=False):
    """返回 {slot_rva: 'dll!api'}"""
    if img is None:
        img = Image()
    gs = [n for _, n in groups(img)]
    bl = slot_blocks(img)
    slots = {}
    if verbose:
        print('DLL 串 %d 个 / 槽块 %d 个' % (len(gs), len(bl)))

    # 一一对应（实测 21/21，且每块首槽都是该 DLL 的标志性导出）。
    #
    # 警告：DLL 前缀是**按块顺序推断**的，只对「具名条目」可靠。
    # 块内若全是序数条目（槽值高位为 1），名字区里没有该 DLL 的字符串可验证，
    # 块序号一旦错开一格，前缀就会整体张冠李戴——而序数本身仍会被"成功"解析，
    # 于是产生**看起来完全合理、实际错误**的映射。
    # 实例：0xb027f4/f8/fc 曾被读成 WS2_32 的 ioctlsocket/htons/htonl，
    # 实为 OLEAUT32 的 VariantChangeType/VariantClear/VariantInit
    # （调用点 0x238899 压了 4 个参数含 VARTYPE=9，见 docs/protocol.md §2c）。
    #
    # ---- 标记位置（2026-09-11 更正）----
    # 旧做法把 '?' 加在 **DLL 侧**（'WSOCK32.dll?!shutdown'），有两个毛病：
    #   1) 粒度是「整块」：块 16 有 16 个具名 + 56 个序数，却因不是全序数块而
    #      **完全不带标记** —— 56 个表推名字伪装成可信，正是 inet_addr 误标能
    #      长期不被发现的原因。
    #   2) 消费者脚本普遍按 `lab.split('!')[0].lstrip('?')` 比 DLL 名，
    #      `.lstrip` 只吃**前导** '?'，后缀 '?' 去不掉 ⇒ 块 17 的调用点被**静默漏掉**。
    # 现改为加在 **名字侧**（'WS2_32.dll!?socket'）：逐槽标记，且现有
    # `.lstrip('?')`（netcallers.py:189/:342）天然能吃。DLL 侧不再加后缀。
    for i, b in enumerate(bl):
        dll = gs[i] if i < len(gs) else '<unknown-%d>' % i
        for rva, v in b:
            nm, ord_derived = _name_of(img, v, dll)
            slots[rva] = '%s!%s%s' % (dll, '?' if ord_derived else '', nm)
    if verbose:
        for i, b in enumerate(bl):
            dll = gs[i] if i < len(gs) else '<unknown-%d>' % i
            print('  [%2d] 0x%06x %3d 槽  %-16s 首=%s' % (
                i, b[0][0], len(b), dll, slots[b[0][0]]))
    return slots


def find_descriptors(img):
    """(保留) 标准 IMAGE_IMPORT_DESCRIPTOR 扫描——本 DLL 上**不适用**：
    真导入表在 .idata2 且没有走描述符数组，此函数恒返回空。"""
    return []


def xrefs(img, slots):
    """全 .text 扫 `FF 15 <abs32>`（call dword ptr [abs]），返回 {slot_rva: [call点RVA]}"""
    import collections
    sec = [s for s in img.sections if s['name'] == '.text'][0]
    start, end = sec['raw'], sec['raw'] + sec['rawsize']
    out = collections.defaultdict(list)
    i = img.data.find(b'\xff\x15', start, end)
    while i >= 0:
        tgt = struct.unpack_from('<I', img.data, i + 2)[0] - 0x10000000
        if tgt in slots:
            out[tgt].append(img.voff(i))
        i = img.data.find(b'\xff\x15', i + 1, end)
    return out


if __name__ == '__main__':
    im = Image()
    sl = build(im, verbose=True)
    print()
    print('槽总数：%d' % len(sl))
    xr = xrefs(im, sl)
    print('有调用的槽：%d   call 点合计：%d' % (len(xr), sum(len(v) for v in xr.values())))
    print()
    print('=== 网络 API 实际调用点 ===')
    KEY = ('socket', 'connect', 'send', 'recv', 'bind', 'listen', 'accept',
           'select', 'closesocket', 'hton', 'ntoh', 'inet_', 'getaddrinfo',
           'getnameinfo', 'freeaddrinfo', 'setsockopt', 'getsockopt',
           'shutdown', 'WSA', 'gethost')
    for rva in sorted(xr):
        lab = sl[rva]
        if any(k in lab for k in KEY):
            pts = ', '.join('0x%06x' % p for p in xr[rva][:8])
            print('  %-34s slot 0x%06x  %2d x   %s' % (lab, rva, len(xr[rva]), pts))
