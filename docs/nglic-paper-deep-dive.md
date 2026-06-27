# NGLIC 论文深度解读与复现指南

论文：NGLIC: A Nonaligned-Row Legalization Approach for 3-D Interdie Connection

## 1. 论文要解决什么问题

这篇论文研究 3-D IC 物理设计中的 interdie connection legalization。全局布局 GP 会把连接点放到理想位置，但它通常忽略物理约束，因此 connection 之间可能重叠，也可能违反 die 边界和 spacing 约束。Legalization 的任务是在修正这些非法位置的同时，尽量保持 GP 的质量。

传统 standard cell legalization 默认 cell 必须放在 row 上。interdie connection 不同，它不需要 row alignment。如果直接套用 standard cell 的单行或多行 legalization，会人为缩小可行解空间，导致 connection 被移动得更远。NGLIC 的核心价值就是在不强制行对齐的前提下，快速找到低位移的合法位置。

论文优化两个主要指标：

```text
total displacement = sum_i |x_i^legal - x_i^gp| + |y_i^legal - y_i^gp|
max displacement   = max_i |x_i^legal - x_i^gp| + |y_i^legal - y_i^gp|
```

实验还观察 legalization 后的 HPWL growth，因为 connection 偏离 GP 越大，通常越容易破坏线长质量。

## 2. 物理约束和建模

每个 connection 用左下角坐标表示：

```text
GP_i = (x_i, y_i)
LP_i = (x_i^legal, y_i^legal)
```

连接必须满足：

1. connection 之间不能重叠。
2. connection 之间要保留 spacing。
3. connection 与 die 边界之间也要保留 spacing。

论文采用 binding / unbinding spacing 的技巧。实现时可以先把 spacing 绑定进 connection 尺寸和 die 边界：

```text
virtual_width  = width + spacing
virtual_height = height + spacing
virtual_x      = original_x - ceil(spacing / 2)
virtual_y      = original_y - ceil(spacing / 2)
```

legalization 在 virtual geometry 上运行。最后输出时再加回 `ceil(spacing / 2)`，得到真实 connection 坐标。这能把 spacing 检查转化为普通矩形无重叠检查。

## 3. 为什么需要两阶段

论文比较了两类已有方法：

1. Single-row height legalization，例如 Abacus。
   它把 row height 设为 connection height，速度快，在 dense 区域更稳定，但在 sparse 区域会因为垂直步长太大而错过更近的位置。

2. Multirow height legalization，例如 MGL。
   它允许一个 cell 跨多行，理论上更接近 nonaligned placement，但如果 row height 取得很小，搜索空间会急剧膨胀。dense 区域尤其容易产生大量小 gap，使后插入的 connection 位移变大。

NGLIC 的判断是：dense 区域先用 single-row 方法快速压实，sparse 区域再用更灵活的 multirow 思想优化。因此框架分成两步：

```text
Initial legalization: 用 Abacus 或类似 single-row legalizer 得到一个合法初解
Post-optimization:   用 UML 在局部 sparse 区域继续降低 displacement
```

这也是复现时最重要的工程切分。先跑通一个可行初解，再实现 UML kernel，比一开始追求完整 NGLIC 更稳。

## 4. UML 的核心思想

UML 是 Unequal Multirow Height Legalization。它是 NGLIC 的关键贡献。

MGL 使用等高 row。如果想完全覆盖 nonaligned solution space，row height 理论上要接近 unit height，导致搜索非常慢。UML 换了一个角度：在 target connection 的 local region 中，用已有 local connections 的上下边界切分局部空间，形成 unequal-height local segments。

这样做的观察是：

如果 target connection 在某个垂直范围内上下移动，但它左右直接冲突的 connection 没变，那么水平推挤代价也不会变。也就是说，很多连续的垂直位置是冗余的。只需要考察由 local connection 边界诱导出来的关键位置。

局部流程可以理解为：

```text
给定 target connection t:
1. 以 GP 位置为中心取 local region
2. 找出 local region 内的 fixed / movable local connections
3. 用 local connection 的 y_low / y_high 切分 unequal local segments
4. 找连续 segment range，使总高度能够容纳 t
5. 在这些 range 中枚举 insertion intervals / insertion points
6. 对每个 insertion point 求最优 x
7. 选择 total displacement 最小的位置
```

UML 只显式考虑水平移动。论文认为垂直移动可以通过两种方式等价获得：

1. 将布局旋转 90 度后，垂直移动变成水平移动。
2. 多轮 iterative insertion 中，前一轮插入造成的位置变化会在后一轮被重新优化。

因此实现中最重要的是把单次水平插入逻辑做正确。

## 5. 关键数据结构

建议复现时按下面的数据结构组织代码。

```text
Connection / Cell:
  id
  original x/y from GP
  current/legal x/y
  width, height
  placed flag

GlobalSegment:
  fixed-height horizontal strip
  x-sorted connection list

LocalRegion:
  lx, ly, hx, hy
  localCells
  localSegments_h

LocalSegment:
  line_l, line_u
  height
  x-sorted local cell index list

InsertionInterval:
  row index
  left endpoint
  right endpoint

InsertionPoint:
  continuous insertion intervals
  directly related connections
  best x/y
  cost
```

本仓库中大致对应：

```text
dp_data_horizon.py:
  Cell
  Segment
  LocalRegion
  LocalSegment
  LegalMoveInterval
  CriticalPoint
  Move

dplacer_horizon.py:
  Dplacer
  Dplacer.legalize(...)
  Dplacer.getOptimalX(...)
  Dplacer.abacus(...)

Legalization.py:
  Legalization
  spacing scaling
  demo entry
```

当前仓库是作者核心代码的精简版本。本项目中 `Dplacer.abacus(...)` 统一作为 Abacus 使用，`Dplacer.legalize(...)` 对应 NGLIC 的 post-optimization 流程。

## 6. Insertion point 怎么理解

在一个 local segment 中，相邻 connection 之间的可插入 gap 是 insertion interval。target connection 的高度可能跨多个 local segments，所以一个 insertion point 是多个连续 insertion intervals 的组合。

例如 target 高度是 40，local segments 高度分别是 10, 15, 15, 20，那么可行的 segment range 可能是：

```text
segments 0..2, total height = 40
segments 1..3, total height = 50
```

每个 range 再结合每一层的左右可插入区间，形成候选 insertion point。候选点要满足：

1. 垂直方向能容纳 target。
2. 水平方向存在共同可行 x。
3. 插入后局部 movable connections 可以通过水平移动消除冲突。

求最优 x 时，论文借用了 MGL 的 ACCURVE 思路：把 displacement cost 看作分段线性函数，用 critical points 找最小值。这个仓库中对应 `Dplacer.getOptimalX(...)`。

## 7. Pruning 为什么成立

UML 枚举的 insertion point 可能很多。论文提出 pruning：

如果两个 insertion points 的 directly related connections 完全相同，那么 target 插入后会推动同一组左右邻居。除 target 自身垂直位移外，其它 connection 的移动代价相同。因此只保留 target 自身 displacement 更小的 insertion point 即可。

换句话说，pruning 的 key 是：

```text
directly_related_connections -> best insertion point with minimal target displacement
```

这不会删除最优解，因为同一 key 下其它候选点的非 target 代价相同，而 target 代价更大。

复现时建议先关闭 pruning，确认合法性和 displacement，再打开 pruning 验证：

```text
pruning 前 total displacement == pruning 后 total displacement
pruning 后 insertion point 数量下降
```

## 8. 复现路线

建议分五步复现。

### Step 1: 跑通最小合法化

先不用 ICCAD benchmark，只用随机 connection。目标是：

```text
输入: die size, terminal size, spacing, GP coordinates
输出: legal coordinates
检查: 无越界, 无重叠, spacing 合法
```

本仓库中的 `smoke_test.py` 可用于这个目的；正式实验入口是 `run_synthetic_cases.py`。

### Step 2: 实现或替换 Initial Legalization

论文使用 Abacus。本项目中 `Dplacer.abacus(...)` 统一作为 Abacus 使用。

可选路线：

后续如果要进一步贴近论文环境，可以继续完善 Abacus 实现和 MGL 对照方法。

### Step 3: 单独验证 UML kernel

构造 5 到 20 个 connection 的小 case，手工画出 local region，检查：

```text
local segments 是否由 y 边界正确切分
segment index pairs 是否能覆盖所有可容纳 target 的连续 range
insertion intervals 是否正确
best x 是否合理
```

不要一开始就上大 benchmark，否则问题很难定位。

### Step 4: 加 iterative post-optimization

论文中 post-optimization 有多轮：

```text
for iter in max_iter:
  collect all connections into buffer
  for each target:
    if GP position is legal, move back toward GP
    else if UML finds better legal position, update
  if no improvement, stop or expand local region
```

这里要特别注意顺序效应。UML 是 sequential insertion，后处理 connection 会受前面结果影响。

### Step 5: 跑 benchmark 和 ablation

论文使用 ICCAD 2022 Problem B 数据，作者自己根据 partition 方法生成了三类密度：

```text
RND: high density
FM:  medium density
KHP: low density
```

这里要特别注意：公开 contest case 并不是 NGLIC 可以直接读取的 connection GP 数据。论文实验部分明确说明，contest 只提供 standard cell library 和 netlist，interdie connections 是在 netlist partition 之后生成的。作者为了更关注 legalization 结果，使用 RND、FM、KHP 三种 partition 方法生成不同密度的 connection datasets，再用 DreamPlace 产生 connection GP HPWL。因此，复现论文数值需要补齐 partition + placement + terminal generation 流程，或者拿到作者生成后的 connection 数据。

复现实验至少应报告：

```text
total displacement
max displacement
HPWL growth
runtime
insertion points before / after pruning
```

## 9. 容易踩坑的地方

1. spacing 绑定和解绑不一致。
   如果验证时用真实 size，但算法里用 virtual size，很容易误判 overlap。建议所有 legalization 内部统一 virtual geometry。

2. row index 边界。
   `floor((y - yl) / row_height)` 在 connection 正好压边界时容易出 off-by-one。代码里通常要用 `h - 1` 或 epsilon 处理上边界。

3. fixed local connection。
   只要 connection 部分进入 local region，就不能被移动。否则局部优化会破坏 region 外部已合法结果。

4. insertion point 枚举爆炸。
   先做小 case，再加 pruning。不要一开始就调大 local region。

5. Abacus 与 NGLIC 的输入必须完全一致。
   只有同一组 GP 坐标、terminal size、spacing 和 die size 下的对比才有意义。

6. 顺序依赖。
   sequential insertion 的连接顺序会影响结果。论文没有完全解决最优顺序问题，并在结论中把它列为未来工作。

## 10. 当前仓库状态建议

当前仓库已经能运行：

```bash
python3 Legalization.py
python3 smoke_test.py
python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus
```

后续建议增加：

```text
README.md: 说明环境、运行命令、当前和论文差异
tests/:    固定小 case 的单元测试
data/:     小型 synthetic benchmarks
scripts/:  benchmark runner 和 metrics reporter
```

如果要以论文复现为目标，下一阶段最值得做的是把 `Dplacer.legalize(...)` 里的 UML 流程拆成几个可测试函数：

```text
build_local_region
build_unequal_segments
generate_segment_pairs
enumerate_insertion_points
prune_insertion_points
choose_best_insertion
```

这样每一步都可以用小 case 校验，复现会快很多。

## 11. Abacus 对比与论文数值复现边界

论文 Table II 的比较对象包括 Abacus、MGL4、MGL8、UML 和 NGLIC，并报告 `Total Disp`、`Max Disp`、`HPWL Growth`。其中 Abacus 是 single-row height legalization 对照方法，NGLIC 是 Abacus initial legalization 加 UML post-optimization 的两阶段流程。

当前仓库可以做同字段的小规模对比：

```bash
cd src
python3 run_synthetic_cases.py ../benchmark/synthetic/*.json --compare-abacus
```

但这还不等于复现论文 Table II 的数值，原因有两个：

1. 论文实验的 RND/FM/KHP connection datasets 是基于 ICCAD 2022 netlist 经过 partition 生成的，不是公开 contest case 原文件。
2. 当前仓库的 `abacus` 模式在本项目中统一作为 Abacus 使用。

要获得和论文一致的实验数据，需要补齐：

```text
ICCAD netlist -> partition(RND/FM/KHP) -> interdie connection generation
             -> DreamPlace GP for connection positions
             -> Abacus / MGL / UML / NGLIC legalization comparison
```

如果拿不到作者生成后的 connection GP 坐标，则可复现的是“同流程、同指标、同趋势”，而不是逐项数值完全一致。
