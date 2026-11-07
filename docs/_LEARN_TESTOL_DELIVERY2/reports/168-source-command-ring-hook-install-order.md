# 168 · 命令环读取、二进制子帧、钩子安装的校验顺序

## 一、范围

本报告学习 **2 处实现**：

- `ClientCommandTrace.cpp` 100–279 行
- `ClientRenderFrameHook.cpp` 480–640 行

## 二、命令环：`!` 记录不能按 NUL 截断

### 2.1 环寻址

```cpp
base = *(uint32*)(ModuleBase + 0x2F1C0C8) ^ 0xD362501F;
text = base + 524628 + ((sequence & 511) * 1024);
```

### 2.2 那次"85 条记录全变成一个字节"

```text
在第一次活体运行中测到：全部 85 条 '!' 记录都出来是【一个字节】，"!"，
因为子帧在偏移 1 处携带一个 NUL，而按 NUL 截断的读法就停在那里。
一半的流量——活体 configstring 更新与【两条】记分板记录——都塌成一行无法区分的东西。
record() 里的注释警告过完全一样的事，而 bug 在它所警告的代码的上游。
```

### 2.3 `!` 帧格式

```text
+0   '!'
+2   uint16 LENGTH
+4   payload，其首字节是 sub_614AC0 用来 switch 的内层动词
```

所以记录长度是 `4 + length`。

### 2.4 长度必须钳到槽位

```cpp
return std::string(text, std::min<std::size_t>(
    4u + length, CommandRingStride));
```

注释：

> **钳到槽位。**从一个本轮没被写过的槽里读出的长度是之前就在那里的东西，**而信任它就会走出环。**

### 2.5 文本记录按 NUL 截断但要加界

```cpp
const auto *end = (const char*)memchr(text, '\0', CommandRingStride);
return std::string(text, end ? (size_t)(end - text) : CommandRingStride);
```

注释：

> **以槽位为界，不以 NUL 为界。**一个从未被写过的槽保留着之前的东西，**而在它上面 `strlen` 会跑出环的末尾。**

两条规则的结合：**NUL 决定长度上限，槽位决定绝对上限**。

## 三、CSV 转义

```cpp
if (c == '"')  out += "\"\"";
else if ((unsigned char)c < 0x20) out += ' ';   // 换行会结束整行
else out += c;
```

注释：

> 一条可靠命令经常携带引号与逗号——`s ui_DMKillScore "50"` 两者都有——**而一个无法解析的追踪不是追踪。**

`< 0x20` 全变空格（不只是换行）——因为 CSV 里任何控制字符都是问题。

## 四、三类分派归属

```cpp
verb = text.front()
if (verb == '!')                          → dispatch = "sub_614AC0"，inner = text[4]
else if (verb=='d'||'k'||'x'||'t')        → dispatch = "sub_614C00"
else                                       → dispatch = "sub_613A40"
```

注释：

> `!` 记录是二进制子帧：`!` 然后 `+2` 的 uint16 长度、`+4` 的 payload，其首字节在 `sub_614AC0` 里选处理器。**只记录 `!` 会把 `% @ J K` —— 四个不同处理器，其中一个是记分板 —— 塌成一行无法区分的记录**，**那是一个发现被它自己的仪器删掉的形状。**

### 4.1 二进制用十六进制，文本用转义

> **二进制记录用十六进制，文本记录用转义。**`escape()` 把每个低于 0x20 的字节变成空格，对一个命令串里的杂散控制字符是对的，**而它会毁掉二进制载荷 —— 而二进制的那些正是我们离线无法解码的记录，所以它们正是这个东西存在的理由。**

## 五、每行 flush

```cpp
std::fprintf(Output, "%lu,%u,%c,%s,%s,%zu,\"%s\"\n", ...);
std::fflush(Output);
```

注释：

> **每行都 flush，故意的。**在约 2.4 条命令每秒下代价为零，**而替代方案已经让本项目赔掉过一次会话**：一个监视器的输出留在块缓冲里，**而它的日志 watching 的整轮都是 0 字节**。一个只有干净退出后才可读的追踪，对一个会崩的客户端没有用。

## 六、`dispatchHook`：先存再压

```asm
pushfd
pushad                  ; EAX 存活；PUSHAD 存而不清
push eax                ; 序列号，__cdecl 参数
call record
add esp, 4
popad
popfd
jmp [Trampoline]        ; 被偷的序言，然后回到 target+6
```

注释点明了一个容易搞错的地方：

> **EAX 存活；`PUSHAD` 存而不清。**

即 `pushad` **不改变** EAX，所以紧接着 `push eax` 压的仍是入口时的序列号。

顺序也是对的：`pushfd` 在 `pushad` **之前**，`popfd` 在 `popad` **之后**——严格后进先出。

## 七、安装顺序：先验字节，再取地址

### 7.1 环境开关的宽松解析

```cpp
size = GetEnvironmentVariableA("CODOL_IMAGE_UPLOAD_HOOK", ...);
enabled = size && value[0] != '0' && value[0] != 'n' &&
          value[0] != 'N' && value[0] != 'f' && value[0] != 'F';
```

**接受任何非 `0`/`n`/`N`/`f`/`F` 开头的值** —— 所以 `1`、`true`、`yes`、`on` 都开。

### 7.2 六项范围检查

```cpp
RenderFrameCallSiteRva + OriginalCall.size() > imageSize ||
RenderFrameTargetRva >= imageSize ||
ImageUploadRva       >= imageSize ||
FiberSlotRva         >= imageSize ||
LoadForRendererDvarRva >= imageSize ||
DBLinkXAssetEntryRva   >= imageSize
→ UnsupportedHost
```

**每一项都在写之前检查**，包括"站点 + 5 字节不越界"这种组合条件。

### 7.3 验字节在写指针**之前**

```cpp
auto *const site = module + RenderFrameCallSiteRva;
if (!std::equal(OriginalCall.begin(), OriginalCall.end(), site))
    return RenderFrameHookResult::UnexpectedBytes;

// 只有通过了才取这五个地址
RenderBegin = module + RenderFrameTargetRva;
Upload = ...; FiberSlot = ...; Link = ...; LoadForRendererDvar = ...;
```

注释：

> **写之前先校验。**一个字节不同的构建就是这些偏移不是从它推导出来的构建。

即：**如果字节不符，连函数指针都不建立** —— 后续代码不可能用上错误的地址。

### 7.4 rel32 的计算

```cpp
target  = (uintptr_t)&renderFrameHook;
next    = (uintptr_t)site + OriginalCall.size();    // = site + 5
relative = (int32)(target - next);
replacement = { 0xE8, <4 字节 relative> };
```

`next` 是"下一条指令"的地址，与 x86 `E9`/`E8` 的 rel32 语义一致。

### 7.5 保护恢复的错误被吞掉

```cpp
DWORD ignored{};
VirtualProtect(site, replacement.size(), oldProtection, &ignored);
```

**恢复保护失败不报错** —— 因为代码已经写进去了，此时失败只意味着"页仍然可写"，不影响功能。

### 7.6 队列的快速路径同样先查安装

```cpp
bool queueForgeImageUpload(unique_ptr<SvForgeGfxImage> image, const bool link)
{
    if (!Installed.load() || !image) return false;
    ...
}
```

与头文件里"向一个永远不会跑的钩子入队是静默挂起"对应。

## 八、`queueForgeChain` 的传递闭包

```text
1. hook 未装 → "the render-frame hook is not installed"
2. SV_LoadForgeBundle 失败 → 返回
3. cloneSource 为空 → "no clone source; a Material is cloned, never authored"
4. models：request.models 为空则全部，否则按名字筛
   models.empty() → "the request names no model in the bundle"
5. 对每个 model 的每个 material：
     去重后加入 materials，并（后续）把 material 的图片加入 images
```

注释：

> **这样解析意味着对一个模型的请求只发布那个模型需要的东西，别的一概不发。**

`cloneSource` 的那句错误信息值得记：**"a Material is cloned, never authored"** —— 这是把设计约束写进错误消息，比注释更难被忽略。

## 九、关键结论

1. **二进制记录不能用 NUL 定界**，也不能被文本转义处理——否则"四个不同处理器塌成一行"。
2. **长度字段必须钳到槽位**，因为它可能是上一轮残留。
3. **每行 flush**：崩溃的客户端需要已经落盘的追踪。
4. **`PUSHAD` 存而不清**，所以紧跟其后的 `push eax` 仍是入口值。
5. **验字节必须在建立函数指针之前**，否则错误地址已经就位。
6. **错误消息可以承载设计约束**（"a Material is cloned, never authored"）。

## 十、未闭合点

- `queueForgeChain` 640 行之后的 images 收集与入队未在本组。
- 三个探针（`installPlayerStateTrace` / `startFpsProbe`）的实现未在本组。
