# Synthetic 实验报告

本文档记录当前仓库中的 synthetic legalization 实验，用于对比 **Abacus**、**NGLIC** 与 **MyLegal** 在自造测试集上的合法化效果。

## 实验目的

实验目标是验证 MyLegal 是否能在 NGLIC 的基础上进一步降低 legalization 位移，并兼顾 HPWL Growth。MyLegal 的核心思路是：先获得 NGLIC 合法解，再在不破坏边界和 spacing 约束的前提下，将位移较大的 terminal 尽可能向原始 GP 坐标回拉。当前实现采用多步长候选搜索，会尝试直接对齐 GP 的 x/y 坐标、半程回拉，以及若干指数步长回拉；候选位置必须合法、降低单点位移，并且不能让当前 per-net HPWL 变差，然后再用 displacement + HPWL 的 weighted cost 选择候选。

本实验重点关注：

```text
Total Disp   总位移，所有 terminal 曼哈顿位移之和
Max Disp     最大位移，单个 terminal 的最大曼哈顿位移
HPWL Growth  合法化后 per-net bounding-box HPWL 总和相比 GP 的增长
```

其中 `Total Disp` 和 `Max Disp` 是主要观察指标，越小越好。`HPWL Growth` 作为辅助指标保留，用来观察 legalization 对线长质量的影响。当前 synthetic case 含有自造 `nets` 字段，因此 HPWL 按 per-net bounding-box HPWL 求和；如果 case 没有 `nets` 字段，代码会退回到全局 bounding-box proxy。

## 实验数据

实验数据位于：

```text
benchmark/synthetic/
```

当前正式实验只使用 3 个自造 case：

```text
large_sparse_300.json
large_medium_800.json
large_dense_1500.json
```

这三个 case 直接给出 terminal 的 GP 坐标，并额外提供自造 netlist，因此可以绕过完整的 ICCAD partition/place 流程，直接测试 legalization 算法及 HPWL 变化。

生成脚本：

```bash
cd src
python3 generate_synthetic_cases.py
```

## 实验命令

在项目根目录下执行：

```bash
cd src
python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus
```

如果需要 CSV 格式：

```bash
python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus --csv
```

本项目中，`Dplacer.abacus(...)` 作为 Abacus 方法使用；`NGLIC` 使用 Abacus 初始合法化加 UML post-optimization 的两阶段流程；`MyLegal` 在 NGLIC 合法解基础上执行 HPWL-aware 安全回拉优化。

## 实验结果

| Case | N | Abacus Total | NGLIC Total | MyLegal Total | NGLIC Total 降低 | MyLegal Total 降低 | Abacus Max | NGLIC Max | MyLegal Max | NGLIC Max 降低 | MyLegal Max 降低 | Abacus HPWL | NGLIC HPWL | MyLegal HPWL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| large_sparse_300 | 300 | 7295 | 4575 | 4563 | 37.29% | 37.45% | 81 | 61 | 61 | 24.69% | 24.69% | 1162 | 760 | 758 |
| large_medium_800 | 800 | 45965 | 25111 | 25084 | 45.37% | 45.43% | 329 | 93 | 77 | 71.73% | 76.60% | 13679 | 9346 | 9319 |
| large_dense_1500 | 1500 | 717330 | 312119 | 312104 | 56.49% | 56.49% | 1217 | 602 | 602 | 50.53% | 50.53% | 190766 | 202468 | 202461 |

## 结果分析

从实验结果看，NGLIC 相比 Abacus 已经显著降低了 `Total Disp` 和 `Max Disp`；MyLegal 在 NGLIC 基础上又进一步降低了总位移，并在部分 case 上继续降低最大位移。

在 `large_sparse_300` 上，MyLegal 将总位移从 NGLIC 的 4575 进一步降低到 4563，相比 Abacus 的总位移降低比例从 37.29% 提升到 37.45%。最大位移与 NGLIC 持平，为 61。

在 `large_medium_800` 上，MyLegal 将总位移从 NGLIC 的 25111 降低到 25084；最大位移从 93 降低到 77。相比 Abacus，MyLegal 的总位移降低 45.43%，最大位移降低 76.60%。

在 `large_dense_1500` 上，MyLegal 将总位移从 NGLIC 的 312119 降低到 312104。由于当前版本禁止接受 HPWL 变差候选，dense case 中可用移动更少，最大位移与 NGLIC 持平，为 602。

HPWL Growth 方面，MyLegal 的候选选择加入了硬约束：只接受不会让当前 per-net HPWL 变差的候选。因此三组 case 中 MyLegal 的 HPWL Growth 都不高于 NGLIC：`large_sparse_300` 从 760 降低到 758，`large_medium_800` 从 9346 降低到 9319，`large_dense_1500` 从 202468 降低到 202461。

## 实验结论

在自造 300/800/1500 规模测试集上，MyLegal 相比 Abacus 能显著降低 total displacement 和 maximum displacement；相比 NGLIC，MyLegal 也能在保持合法性的前提下进一步恢复一部分 GP 质量。

当前实验能够支持以下结论：

```text
MyLegal 在 NGLIC 合法解基础上执行 HPWL-aware 安全回拉优化，
能够在不恶化 per-net HPWL Growth 的前提下进一步降低 legalization 位移。
```
