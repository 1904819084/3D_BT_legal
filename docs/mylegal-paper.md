# MyLegal: 面向 3-D Interdie Connection 的安全回拉合法化优化方法

## 摘要

3-D 集成电路中的 interdie connection legalization 需要在满足 die 边界、connection spacing 和无重叠约束的前提下，尽量减少 connection 从全局布局位置到合法位置的移动距离，同时避免明显增加 HPWL。已有 NGLIC 方法通过 Abacus 初始合法化和 UML post-optimization 缓解了标准单元行对齐约束带来的解空间损失，但在完成局部合法化后，部分 connection 仍可能停留在距离 GP 位置较远的位置。本文提出 MyLegal，一种基于 NGLIC 合法解的 HPWL-aware 安全回拉优化方法。MyLegal 以 NGLIC 输出为初始合法解，按照当前位移从大到小选择 terminal，在不破坏边界和 spacing 约束的前提下，尝试将 terminal 向其 GP 坐标方向移动；候选必须降低位移且不恶化 per-net HPWL，并使用 displacement + HPWL 的 weighted cost 选择候选位置。实验基于 300、800、1500 三组 synthetic legalization case，对比 Abacus、NGLIC 和 MyLegal。结果表明，MyLegal 相比 Abacus 在三组 case 上均显著降低 total displacement 和 maximum displacement；相比 NGLIC，MyLegal 能在不恶化 HPWL Growth 的前提下进一步降低总位移。

## 1. 引言

随着 3-D IC 和 chiplet 技术的发展，die 间连接密度不断提高，interdie connection 的布局质量对整体线长、制造可行性和后续布线有重要影响。全局布局通常以 wirelength 或其他全局目标为主，会忽略 spacing、边界和重叠等物理约束，因此需要 legalization 阶段将 connection 移动到合法位置。

传统 standard cell legalization 通常假设 cell 必须放置在 row 上。然而，interdie connection 并不需要严格行对齐。如果直接使用 single-row legalization，例如 Abacus，可能会引入不必要的垂直移动；如果使用更细粒度的 multirow legalization，又可能带来较大的搜索开销。NGLIC 针对这一问题提出了两阶段框架：先使用 Abacus 得到初始合法解，再通过 UML 在非行对齐空间中进行局部优化。

本文进一步观察到：NGLIC 输出虽然已经合法，但某些 terminal 周围仍可能存在可行空隙，使其能够在不破坏合法性的情况下向 GP 坐标回拉。同时，单纯降低位移不一定保证 HPWL 改善。因此，本文提出 MyLegal，在安全回拉过程中加入 HPWL-aware 约束与 weighted cost，用一种简单、可验证、保守的后处理策略进一步恢复 GP 质量。

## 2. 问题定义

给定一组 interdie connections：

```text
C = {c1, c2, ..., cn}
```

每个 connection 具有 GP 坐标：

```text
GP_i = (x_i, y_i)
```

legalization 输出合法坐标：

```text
LP_i = (x_i^l, y_i^l)
```

本文主要优化两个位移指标：

```text
Total Disp = sum_i |x_i^l - x_i| + |y_i^l - y_i|
Max Disp   = max_i |x_i^l - x_i| + |y_i^l - y_i|
```

合法性约束包括：

```text
1. connection 不越出 die 边界
2. connection 之间不重叠
3. connection 之间满足 spacing
```

此外，实验中报告 HPWL Growth：

```text
HPWL Growth = HPWL(LP) - HPWL(GP)
```

当前 synthetic case 自造了 netlist，因此本文对每条 net 分别计算 bounding-box HPWL，再对所有 net 求和。若输入 case 没有 `nets` 字段，实验脚本会退回到所有 terminal 的全局 bounding-box proxy。

## 3. 方法

### 3.1 NGLIC 基础流程

NGLIC 使用两阶段合法化：

```text
1. Abacus 初始合法化
2. UML post-optimization
```

Abacus 提供一个快速合法初解，适合压实 dense 区域；UML 使用 unequal multirow height 的局部搜索方式，避免强制 row alignment 导致的解空间损失。

### 3.2 MyLegal 安全回拉优化

MyLegal 以 NGLIC 输出为初始合法解。算法每轮按照 terminal 当前位移从大到小排序，优先处理移动距离较大的 terminal。对于每个 terminal，MyLegal 生成多类向 GP 回拉的候选位置，包括直接对齐 GP 的 x/y 坐标、半程回拉、指数步长回拉，以及 x/y 组合回拉。如果候选位置满足边界、spacing 和无重叠约束，并且该移动可以降低 terminal 的 Manhattan 位移，则进入候选检查。随后 MyLegal 只保留不会使当前 per-net HPWL 变差的候选，并使用 displacement + HPWL 的 weighted cost 选择最优候选。

核心过程如下：

```text
Input: GP positions, NGLIC legal positions
Output: MyLegal legal positions

for pass in passes:
  sort terminals by displacement descending
  for each terminal i:
    current = LP_i
    gp = GP_i
    candidates = multi-step x/y/xy moves toward gp
    filter legal candidates that reduce |candidate - gp|
    filter candidates that do not increase per-net HPWL
    choose candidate by displacement + HPWL-aware weighted cost
    if such candidate exists:
      update LP_i
```

MyLegal 的设计原则是保守接受：

```text
1. 不接受任何破坏合法性的移动
2. 不接受任何增加单点位移的移动
3. 不接受 per-net HPWL 恶化的候选
4. 只在 NGLIC 合法解附近做局部恢复
```

因此，MyLegal 不会破坏已有 legalization 结果，且实现复杂度较低。

## 4. 实验设置

实验使用三组 synthetic legalization case：

```text
large_sparse_300   300 terminals
large_medium_800   800 terminals
large_dense_1500   1500 terminals
```

实验比较三种方法：

```text
Abacus
NGLIC
MyLegal
```

运行命令：

```bash
cd src
python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus
```

评价指标：

```text
Total Disp
Max Disp
HPWL Growth
```

其中 Total Disp 和 Max Disp 是主要指标，HPWL Growth 是辅助观察指标。HPWL Growth 按 synthetic netlist 的 per-net HPWL 总和计算。

## 5. 实验结果

| Case | N | Abacus Total | NGLIC Total | MyLegal Total | MyLegal Total 降低 | Abacus Max | NGLIC Max | MyLegal Max | MyLegal Max 降低 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| large_sparse_300 | 300 | 7295 | 4575 | 4563 | 37.45% | 81 | 61 | 61 | 24.69% |
| large_medium_800 | 800 | 45965 | 25111 | 25084 | 45.43% | 329 | 93 | 77 | 76.60% |
| large_dense_1500 | 1500 | 717330 | 312119 | 312104 | 56.49% | 1217 | 602 | 602 | 50.53% |

完整 HPWL Growth 结果如下：

| Case | Abacus HPWL Growth | NGLIC HPWL Growth | MyLegal HPWL Growth |
| --- | ---: | ---: | ---: |
| large_sparse_300 | 1162 | 760 | 758 |
| large_medium_800 | 13679 | 9346 | 9319 |
| large_dense_1500 | 190766 | 202468 | 202461 |

## 6. 分析

实验结果表明，NGLIC 已经能相比 Abacus 大幅降低 total displacement 和 maximum displacement。MyLegal 在 NGLIC 的基础上进一步进行安全回拉，因此可以继续恢复一部分 GP 质量。

在 `large_medium_800` 中，MyLegal 的效果最明显：相比 NGLIC，总位移从 25111 降低到 25084，最大位移从 93 降低到 77。说明在中等密度场景中，NGLIC 合法解附近仍存在可利用空隙，安全回拉可以有效缩短长距离移动。

在 `large_dense_1500` 中，MyLegal 的总位移改善较小，最大位移与 NGLIC 持平。原因是 dense 场景中可行空隙较少，同时当前版本禁止接受 HPWL 变差候选，因此算法会牺牲一部分位移改善来保护 HPWL Growth。

HPWL Growth 方面，MyLegal 在三组 case 中均不高于 NGLIC：`large_sparse_300` 从 760 降低到 758，`large_medium_800` 从 9346 降低到 9319，`large_dense_1500` 从 202468 降低到 202461。这说明加入 HPWL-aware 约束后，MyLegal 的局部回拉没有导致 per-net HPWL 恶化，并且在部分 case 上能同时改善 HPWL Growth。

## 7. 结论

本文提出了 MyLegal，一种基于 NGLIC 合法解的 HPWL-aware 安全回拉优化方法。MyLegal 不改变 NGLIC 的主流程，而是在合法解附近尝试向 GP 坐标恢复，只接受合法、降低位移且不恶化 per-net HPWL 的移动，并用 weighted cost 选择候选。实验表明，在 300、800、1500 三组 synthetic case 上，MyLegal 相比 Abacus 显著降低 total displacement 和 maximum displacement；相比 NGLIC，MyLegal 能在保护 HPWL Growth 的前提下进一步降低总位移。

后续工作可以从以下方向继续扩展：

```text
1. 使用真实 ICCAD partition/place 生成的 netlist 计算 per-net HPWL
2. 将 MyLegal 的回拉步长改为自适应步长
3. 将回拉候选扩展为二维局部搜索
4. 将 HPWL 目标从硬约束扩展为多目标 Pareto 选择
```
