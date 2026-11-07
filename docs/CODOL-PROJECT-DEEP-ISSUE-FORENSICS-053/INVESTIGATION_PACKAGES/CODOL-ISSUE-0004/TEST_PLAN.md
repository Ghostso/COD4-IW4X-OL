# 验证实验 B4

## 步骤
1. 建一个干净目录：cmake -S . -B build_clean -G "Visual Studio 17 2022" -A x64
2. cmake --build build_clean --config Debug
3. 比较 codol_battle_server.exe 哈希

## 通过判据
哈希与 275B165F… 一致 ⇒ 可复现

## 失败判据
不一致 ⇒ 当前源码≠线上二进制（重大）

## 成本
离线 10 分钟
