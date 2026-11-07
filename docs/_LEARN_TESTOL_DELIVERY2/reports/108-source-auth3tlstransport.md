# 学习报告 108（重开）— `Auth3TlsTransport.cpp`（311 行）+ `CodolClientPatches.hpp`（41 行）

**学习范围**：`Auth3TlsTransport.cpp`（12,771 B / 311 行）+ `CodolClientPatches.hpp`（2,094 B / 41 行）
**性质**：全实测（**两文件逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**证书必须用 SHA-1 签名**（CODOL 的旧验证器拒绝 SHA-256）②**`ALL:@SECLEVEL=0` + `TLS1_VERSION`** ③**证书的 `C=SE / O=Hedgehogscience`** ④**自签 RSA-2048 运行期生成** ⑤**`AUTH3_CAPTURE` 抓包日志**

---

## 一、★★★★★ **证书必须用 SHA-1 签名（一个决定性的兼容性事实）**

### 1.1 ★★★★★ 完整注释（第 96–98 行，逐字）

```cpp
// Match Ayria's 2019 IHTTPSServer exactly. CODOL's legacy verifier
// rejects the otherwise valid v3/SHA-256 certificate during Auth3.
requireOpenSsl(X509_sign(certificate, key, **EVP_sha1()**) > 0, "X509_sign");
```

★★★★★ **⇒ 三条精确事实：**
```
① ★★★ **必须"精确匹配 Ayria 2019 的 `IHTTPSServer`"**
        ↓
② ★★★★★ **CODOL 的旧验证器在 Auth3 期间会**拒绝**"otherwise valid 的 v3/SHA-256 证书"**
        ↓
③ ★★★ ⇒ 所以**必须用 `EVP_sha1()` 签名**
```

★★ **⇒ 这是**"现代安全实践（SHA-256）反而会失败"的精确案例**。**
**⇒ 与报告 105 的 `TypeI32` 警告同一性质（"不是外观差异"）。**

### ★★★★★ 与 `bundle\_ca.pem` / `_leaf2_chain.pem` 的对照

```
报告 084（交付包证书）：
  叶证书 SigAlg = **`sha256RSA`**
  CA  证书 SigAlg = **`sha256WithRSAEncryption`**
        ↓
★★★ 本报告（运行期自签）：
  **必须用 SHA-1**（`EVP_sha1()`）
        ↓
★★★★★ ⇒ **两套证书用不同的签名算法：**
   `bundle\` 里的（**fake_auth_tls.py 用**）⇒ **SHA-256**
   `Auth3TlsTransport` 运行期生成的 ⇒ **SHA-1**
        ↓
★★★ ⇒ 两条路径**不通用**（各自的验证器要求不同）
```

★ **⇒ 这解释了为什么交付包里既有一套 PEM 证书、又有一个运行期自签的实现** ——
**它们服务于两个不同的 TLS 端点。**

---

## 二、★★★★★ **`ALL:@SECLEVEL=0` + `TLS1_VERSION`**

### 2.1 ★★★★★ 完整 TLS 配置（第 138–146 行）

```cpp
context = SSL_CTX_new(**TLS_server_method()**);
...
SSL_CTX_set_security_level(context, **0**);                              // ★★ 安全级别 0
requireOpenSsl(SSL_CTX_set_min_proto_version(context, **TLS1_VERSION**) == 1,
    "SSL_CTX_set_min_proto_version");                                  // ★★ 最低 TLS 1.0
requireOpenSsl(SSL_CTX_set_cipher_list(context, "**ALL:@SECLEVEL=0**") == 1,
    "SSL_CTX_set_cipher_list");                                        // ★★★ 全部密码套件
```

### ★★★★★ 三个降级设置

| 设置 | 值 | 含义 |
|---|---|---|
| **安全级别** | ★★ **`0`** | **完全禁用安全级别检查** |
| **最低协议** | ★★ **`TLS1_VERSION`** | **允许 TLS 1.0**（2019 年的客户端） |
| **密码列表** | ★★★ **`"ALL:@SECLEVEL=0"`** | **所有套件 + 安全级别 0** |

★★★ **⇒ 与报告 044–046 的 `fake_auth_tls.py` 的 `ALL:@SECLEVEL=0` **完全一致** ✓**
**⇒ 且与报告 090 在插件字符串面发现的 `ALL:@SECLEVEL=0` **也是同一处** ✓**

### ★★★★★ 三处证据链闭合

```
报告 044–046（`fake_auth_tls.py`）⇒ 用 **`ALL:@SECLEVEL=0`**
报告 090（插件字符串面）           ⇒ 发现 **`ALL:@SECLEVEL=0`** 字面量
本报告（`Auth3TlsTransport.cpp`）  ⇒ 代码里 **`SSL_CTX_set_cipher_list(context, "ALL:@SECLEVEL=0")`**
        ↓
★★★★★ ⇒ **三处独立来源完全一致** ✓
```

★ **⇒ 且现在知道了**额外的两层**：`SSL_CTX_set_security_level(0)` + `TLS1_VERSION`。**

---

## 三、★★★★★ **证书的 `C=SE / O=Hedgehogscience`**

### 3.1 ★★★★★ 完整证书构造（第 60–101 行）

```cpp
X509 *makeCertificate(EVP_PKEY *key, const std::string_view hostname)
{
    X509 *certificate = X509_new();
    ...
    ASN1_INTEGER_set(X509_get_serialNumber(certificate), **1**);              // 序列号 = 1
    X509_gmtime_adj(X509_getm_notBefore(certificate), **0**);                 // notBefore = 现在
    X509_gmtime_adj(X509_getm_notAfter(certificate), **31536000L**);          // notAfter = +1 年
    X509_set_pubkey(certificate, key);

    auto *name = X509_get_subject_name(certificate);
    X509_NAME_add_entry_by_txt(name, "**C**",  MBSTRING_ASC, "**SE**", -1, -1, 0);
    X509_NAME_add_entry_by_txt(name, "**O**",  MBSTRING_ASC, "**Hedgehogscience**", -1, -1, 0);
    X509_NAME_add_entry_by_txt(name, "**CN**", MBSTRING_ASC, hostname.data(), hostname.size(), -1, 0);
    X509_set_issuer_name(certificate, name);                                  // ★ 自签（subject == issuer）
    X509_sign(certificate, key, EVP_sha1());
    return certificate;
}
```

### ★★★★★ 完整的证书字段

| 字段 | 值 |
|---|---|
| **序列号** | ★ **`1`** |
| **`notBefore`** | **现在**（`gmtime_adj(0)`） |
| **`notAfter`** | ★ **现在 + 31,536,000 秒 = +365 天** |
| **`C`（国家）** | ★★★ **`SE`**（瑞典） |
| **`O`（组织）** | ★★★ **`Hedgehogscience`** |
| **`CN`（通用名）** | ★★ **`hostname`**（构造时传入） |
| **`issuer`** | ★ **= `subject`**（**自签**） |
| **签名算法** | ★★★ **`SHA-1`** |

### ★★★★★ **`O = Hedgehogscience` 与报告 103 的彩蛋对应**

```
报告 103（`Auth3Protocol.cpp`）：
  `codoId = "**Hedgehogscience0**"`
        ↓
★★★ 本报告：证书的 **`O = Hedgehogscience`**
        ↓
★★★★★ ⇒ **同一个词根：`Hedgehogscience`**
   ⇒ 报告 103 的 `codoId` 是 "Hedgehogscience" + "0"
   ⇒ 本报告的 `O` 是 "Hedgehogscience"
```

★ **⇒ 这是**作者的个人标记**（贯穿两处）。**

### ★★★ `C=SE`（瑞典）的意义

★★ **⇒ 与 `Hedgehogscience` 一起 ⇒ 可能是**Ayria 作者的身份**（2019 年的 `IHTTPSServer`）。**
**⇒ 注释说"Match Ayria's 2019 IHTTPSServer **exactly**" ⇒ 这些字段值是从 Ayria 抄来的。**

### ★★★ RSA-2048 的生成（第 39–53 行）

```cpp
EVP_PKEY *makeKey()
{
    EVP_PKEY_CTX *context = EVP_PKEY_CTX_new_id(**EVP_PKEY_RSA**, nullptr);
    EVP_PKEY_keygen_init(context);
    EVP_PKEY_CTX_set_rsa_keygen_bits(context, **2048**);
    EVP_PKEY_keygen(context, &key);
    ...
}
```

★★ **⇒ **RSA-2048**（与报告 084 的 `_leaf2.key` 同位数）。**

★★★ **⇒ 且**每次启动都重新生成**（不是从文件加载）⇒ 与报告 104 的"自签证书是运行期 mint 的"**完全吻合** ✓**

---

## 四、★★★★★ **`AUTH3_CAPTURE` 抓包日志**

### 4.1 ★★★★★ 完整实现（第 236–242 行）

```cpp
const auto result = protocol.authenticate(body);
report("**AUTH3_CAPTURE request=**" + std::string(body));
report("**AUTH3_CAPTURE response=**" + result.json);
report(std::string("**Authenticated user **") + result.username + " (" +
    std::to_string(result.userId) + ") for title " + std::to_string(result.titleId) + '.');
queuePlaintext(Auth3Protocol::httpResponse(result.json));
```

### ★★★★★ 与报告 090 的插件字符串面**完全吻合**

```
报告 090（`Alwaysoffline.Localnet32` 的字符串面）：
  **`AUTH3_CAPTURE request=`** × 1
  **`AUTH3_CAPTURE response=`** × 1
  **`Authenticated user `** × 1
        ↓
★★★★★ 本报告：**三处字面量逐字相同** ✓
```

### ★★★ HTTP 解析的严格性（第 195–234 行）

```cpp
if (!requestLine.starts_with("**POST /auth/**"))
    throw std::runtime_error("unexpected Auth3 HTTP target");
...
if (converted.ec != std::errc{})
    throw std::runtime_error("invalid Auth3 Content-Length");
```

★★ **⇒ 只接受 **`POST /auth/...`**（路径前缀检查）。**
**⇒ 且 `Content-Length` 必须可解析。**

### ★★★ TLS 状态机的三个入口

```cpp
void reset()              // ★ 重建 SSL + BIO
void processTls()         // ★ 握手 + 读
void processHttp()        // ★ 解析 HTTP 并回复
```

★★★ **⇒ `processTls` 的三条错误分支：**
```
`SSL_ERROR_WANT_READ` / `SSL_ERROR_WANT_WRITE`  ⇒ **返回（等更多数据）**
`SSL_ERROR_ZERO_RETURN`                          ⇒ ★★ **`reset()`（对端关闭,准备新连接）**
其他                                              ⇒ **抛异常**
```

★★ **⇒ 第 2 条是**"close_notify 后重置"**的关键**（与报告 044 的"必须发 TLS close-notify"呼应）。**

---

## 五、★★★★ **`CodolClientPatches.hpp` 的 9 个导出**

### 5.1 ★★★ 完整清单

```cpp
bool patchCodolStartupBuffer(std::span<std::uint8_t> image);              // ★ 纯函数（测试用）
bool shouldRequestCodolInventory(kind, operation, succeeded, errorCode);  // ★ 纯判定
bool shouldInvalidateCodolCurrentCharacterCache(...);                     // ★ 纯判定
std::uint32_t requestCodolProfileReload(std::uint32_t profileKind);       // ★ 请求
bool getCodolProfileReloadStatus(kind, &gen, &state, &errorCode);         // ★ 查状态
std::uint32_t requestCodolInventoryRefresh();                             // ★ 请求
bool getCodolInventoryRefreshStatus(&gen, &state, &errorCode);            // ★ 查状态
bool installCodolStartupPatches();                                        // ★ 安装
bool installForcedRecordValidatorPatch();                                 // ★ 探针
void armForcedAllocationPatch();                                          // ★★ 武装
```

★★ **⇒ 实际是 **10 个**（含 `armForcedAllocationPatch`）。**

### ★★★ 两个"纯函数"的用途（逐字）

```cpp
// Exposed for deterministic tests. The runtime path validates the known
// CODOL image and protects every affected page before changing any bytes.
```

★★★ **⇒ `patchCodolStartupBuffer` 与两个 `should*` 是**为确定性测试暴露的纯函数**。**

★ **⇒ 而运行期路径**会校验镜像并保护页**,测试路径不会。**

### ★★★ 三对"请求/查状态"API

```
`requestCodolProfileReload(kind)`      ⇔ `getCodolProfileReloadStatus(...)`
`requestCodolInventoryRefresh()`       ⇔ `getCodolInventoryRefreshStatus(...)`
        ↓
★★★ ⇒ 与报告 082 的 `Alwaysoffline.Localnet32` 的 4 个导出**完全对应** ✓
   `CODOL_RequestProfileReload` / `CODOL_GetProfileReloadStatus`
   `CODOL_RequestInventoryRefresh` / `CODOL_GetInventoryRefreshStatus`
```

### ★★★ 三个 `RuntimeRequestState`（第 95–102 行）

```cpp
enum class RuntimeRequestState : std::uint32_t
{
    **idle = 1**,
    **queued = 2**,
    **inFlight = 3**,
    **succeeded = 4**,
    **failed = 5**,
};
```

★★★ **⇒ 5 个状态,**从 1 开始**（不是 0）⇒ 与报告 105 的 `StartupInventoryState`（从 0）**不同**。**
**⇒ 且与报告 104 的 `ResponseStatus`（`Accepted = 0`）**也不同**。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **证书必须 SHA-1 签名** | "Match Ayria's **2019 IHTTPSServer** exactly. CODOL's **legacy verifier rejects the otherwise valid v3/SHA-256 certificate** during Auth3" ⇒ 用 **`EVP_sha1()`** |
| 2 | ★★★★★ **与交付包证书的对照** | `bundle\` 的叶/CA 是 **`sha256RSA`**（报告 084）；运行期自签是 **SHA-1** ⇒ **两条路径不通用** |
| 3 | ★★★ **安全级别 0** | `SSL_CTX_set_security_level(context, **0**)` |
| 4 | ★★★ **最低 TLS 1.0** | `SSL_CTX_set_min_proto_version(context, **TLS1_VERSION**)` |
| 5 | ★★★★★ **密码列表** | **`"ALL:@SECLEVEL=0"`** ⇒ ✓ 与报告 044–046 与 090 **三处独立来源完全一致** |
| 6 | ★★★★★ **证书 `O`** | **`Hedgehogscience`** ⇒ ✓ 与报告 103 的 `codoId = "Hedgehogscience0"` **同一词根** |
| 7 | ★★★ 证书 `C` | **`SE`**（瑞典） |
| 8 | ★★ 证书 `CN` | `hostname`（构造时传入） |
| 9 | ★★★ 序列号 / 有效期 | 序列号 **`1`**；`notAfter` = 现在 + **31,536,000 秒（365 天）** |
| 10 | ★★★ 自签 | `X509_set_issuer_name(certificate, name)` ⇒ **issuer == subject** |
| 11 | ★★ 密钥 | **RSA-2048**,**每次启动重新生成**（不从文件加载） |
| 12 | ★★★★★ **`AUTH3_CAPTURE` 三字面量** | `AUTH3_CAPTURE request=` / `AUTH3_CAPTURE response=` / `Authenticated user ` ⇒ ✓ 与报告 090 **逐字相同** |
| 13 | ★★ HTTP 严格性 | 只接受 **`POST /auth/`** 前缀；`Content-Length` 必须可解析 |
| 14 | ★★★ TLS 三条错误分支 | `WANT_READ`/`WANT_WRITE` ⇒ 返回；**`ZERO_RETURN` ⇒ `reset()`**；其他 ⇒ 抛异常 |
| 15 | ★★★ `CodolClientPatches.hpp` 10 个导出 | 含 **`patchCodolStartupBuffer`**（纯函数）+ 两个 `should*`（纯判定）+ 两对请求/查状态 + `install*` + `arm*` |
| 16 | ★★ 纯函数的用途 | "Exposed for **deterministic tests**" ⇒ 运行期会校验镜像并保护页,测试路径不会 |
| 17 | ★★★ 与报告 082 吻合 | 4 个导出 `CODOL_Request/Get*` ⇔ 本文件的 `request*/get*` ✓ |
| 18 | ★★ `RuntimeRequestState` | **`idle=1` / `queued=2` / `inFlight=3` / `succeeded=4` / `failed=5`**（**从 1 开始**） |

---

## 七、结论

### 1. ★★★★★ **证书必须用 SHA-1 签名,因为 CODOL 的旧验证器拒绝 SHA-256**

```
"CODOL's **legacy verifier rejects the otherwise valid v3/SHA-256 certificate**
 during Auth3"
        ↓
★★★ ⇒ 必须"精确匹配 Ayria 2019 的 `IHTTPSServer`"
```

### 2. ★★★★★ **`ALL:@SECLEVEL=0` 在三个独立来源上完全一致**

★ **⇒ `fake_auth_tls.py` / 插件字符串面 / `Auth3TlsTransport.cpp`。**
**★ ⇒ 且本报告补充了另外两层：`set_security_level(0)` + `TLS1_VERSION`。**

### 3. ★★★★★ **`O = Hedgehogscience` 与报告 103 的彩蛋同源**

### 4. ★★★★★ **`AUTH3_CAPTURE` 三个日志字面量与插件字符串面逐字相同**

### 5. ★★★★ **两套证书并存,签名算法不同**

```
`bundle\` 的 PEM（`fake_auth_tls.py` 用）⇒ **SHA-256**
`Auth3TlsTransport` 运行期自签        ⇒ **SHA-1**
        ↓
★★★ ⇒ 服务于**两个不同的 TLS 端点**,互不通用
```

### 6. ★★★ **`ZERO_RETURN` ⇒ `reset()`**（对端关闭后准备新连接）

### 7. ★★★ **`CodolClientPatches.hpp` 暴露纯函数供确定性测试**

---

## 八、下一步

- 12 个 Service 实现：`MatchmakingService`（1,101 行）/ `MarketplaceService`（1,099 行）/ `StatsService`（875 行）/ `ClanService`（623 行）/ `LobbyProtocol`（807 行）/ `Unknown0BService`（669 行）/ `Profiles2Service`（630 行）/ `Storage2Service`（450 行）/ `InstantMessageService`（242 行）/ `Friends2Service`（325 行）/ `ContentUnlock2Service`（79 行）/ `TencentService`（94 行）/ `TitleUtilitiesService`（56 行）
- `ServiceRegistry` / `AckOnlyServices` / `CodolStartupTasks` / `RecoveredCatalog` / `LanDiscovery` / `SharedRoom*`
