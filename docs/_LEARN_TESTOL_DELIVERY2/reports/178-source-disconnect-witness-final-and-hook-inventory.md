# 178 · 断开见证的收尾与错误信息的写法

## 一、范围

本报告学习 `DisconnectWitness.cpp` 518–539 行（**该文件在本组读取范围内完整**，539 行）。

## 二、最后两步

```cpp
AddVectoredExceptionHandler(1, &watchpointHandler);
armClsStateWatchpoint();
return DisconnectWitnessResult::Installed;
```

**先注册 VEH（first-chance），再武装断点** —— 顺序不可交换：如果先武装再注册，第一次触发时会没有处理器接住。

`AddVectoredExceptionHandler` 的返回值**被丢弃** —— 如果注册失败，断点仍会武装但没人处理，结果是 `EXCEPTION_SINGLE_STEP` 落到默认处理器上，**进程可能直接终止**。

这是一个可指出的缺口：**注册失败没有检查**。

## 三、`UnexpectedBytes` 的错误文本

```cpp
case DisconnectWitnessResult::UnexpectedBytes:
    return "UNEXPECTED BYTES -- 0x0077C343 is not this build's cls.state=0 "
           "write, nothing was written";
```

这段值得单独记：

- **给出具体地址** `0x0077C343`；
- **说明它本该是什么** "cls.state=0 write"；
- **说明后果** "nothing was written"。

即：**看到这行的人立刻知道 (a) 哪个站点、(b) 期望什么、(c) 系统处于什么状态**。

对比 `animtree` 的 `UnexpectedBytes` 只返回 `"UnexpectedBytes"` —— 无地址、无后果。

## 四、六个结果名的完整表

```text
NotRequested     "not requested"
Installed        "installed"
AlreadyInstalled "already installed"
UnexpectedBytes  "UNEXPECTED BYTES -- ... nothing was written"
UnsupportedHost  "unsupported host"
```

**五个枚举值里只有一个是完整句子**，那就是"最可能是真问题"的那个。

## 五、这一批客户端钩子文件的全貌

到此，`game_server` 根目录的客户端侧仪器已全部读完。分类汇总：

| 文件 | 性质 | 默认 |
|---|---|---|
| `FrameHook.cpp/.hpp` | `Com_Frame` 入口钩子 | 无条件安装 |
| `ClientRenderFrameHook.cpp/.hpp` | 渲染帧 call 尾跳 + Forge 上传链 | `CODOL_IMAGE_UPLOAD_HOOK=1` |
| `ClientAnimtreeHook.cpp/.hpp` | 六个站点（resolve/build/populate/alloc×5/apply） | `CODOL_ANIMTREE_RESOLVE_HOOK=1`，仪器另需 `CODOL_ANIMTREE_TRACE=1` |
| `ClientCommandTrace.cpp/.hpp` | 命令分派钩子 + playerstate 镜像线程 + fps 探针 | 由控制口按需调用 |
| `DisconnectWitness.cpp/.hpp` | 三个软件钩子 + 硬件写断点 | `OLMOD_DISCONNECT_WITNESS=1` |
| `ClientBatteryLookup.hpp` | 无钩子，纯 XOR 解引用 | 只读 |

**六个文件里有五个打了补丁**，唯一的只读一个是 `ClientBatteryLookup`。

### 5.1 窃取长度的完整清点

```text
Com_Frame         5    55 8B EC 56 57
渲染帧 call       5    E8 3D FF FF FF
animtree resolve  5    E8 60 FA 33 00
animtree build    5    E8 00 B0 03 00
animtree populate 5    E8 41 FE FF FF
animtree alloc×5  5    E8 <rel32>
animtree apply    5    E8 <rel32>
命令分派          6    55 8B EC 83 EC 08
Com_Error         5    E8 7B F9 FF FF
cls.state 写入   10    C7 05 B0 46 64 07 00 00 00 00
cs 校验器         6    55 8B EC 83 EC 10
```

**十一处里三处不是 5**，而三处的原因各不相同：

- **命令分派 6**：`sub esp, 8` 是三字节指令；
- **cls.state 10**：整条 `mov [imm32], imm32`；
- **cs 校验器 6**：`sub esp, 0x10` 是三字节指令。

**共同点**：`sub esp, N` 与 `mov [abs], imm` 都容易跨过五字节边界。

## 六、关键结论

1. **VEH 必须先注册再武装断点**，顺序不可交换。
2. **`AddVectoredExceptionHandler` 的返回值应该检查**（当前丢弃）。
3. **错误文本要包含地址、期望、后果三要素**——`UnexpectedBytes` 那句是全项目的范例。
4. **十一处补丁里三处不是五字节**，原因都是"目标指令跨越五字节边界"。
5. **六个客户端仪器文件里五个打补丁、一个纯只读**——而只读的那个正是最先该试的形态。

## 七、未闭合点

- `cls.state` 10 → 0 与 `com_errorCode = 2` 的来源仍未点名。
- `game_server` 根目录仍有未读文件（`NativeEntityStateBindings.cpp` 后段、`PlayerDataDef.cpp` 后段等）。
