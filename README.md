# 3D BT Legalization

本仓库用于阅读、复现和实验验证论文：

```text
NGLIC: A Nonaligned-Row Legalization Approach for 3-D Interdie Connection
```

当前实验重点是：使用自造 synthetic legalization 数据，对比 **Abacus**、**NGLIC** 与 **MyLegal** 在 `Total Disp`、`Max Disp` 和 `HPWL Growth` 上的表现。当前 synthetic case 带有自造 netlist，因此 HPWL 按 per-net bounding-box HPWL 求和；没有 `nets` 字段的 case 才会退回到全局 bounding-box proxy。

## 目录结构

```text
src/                 核心代码与实验脚本
docs/                论文解读与实验报告
benchmark/           ICCAD 原始 case 与自造 synthetic case
benchmark/synthetic/ 300/800/1500 三个自造实验数据
```

## 主要实验数据

正式对比实验只使用下面三个自造 case：

```text
benchmark/synthetic/large_sparse_300.json
benchmark/synthetic/large_medium_800.json
benchmark/synthetic/large_dense_1500.json
```

它们直接提供 terminal 的 GP 坐标，因此可以绕过完整的 ICCAD partition/place 流程，直接测试 legalization 效果。

## 怎么跑实验

### macOS / Linux

先进入项目根目录。下面以当前机器路径为例：

```bash
cd /Users/bytedance/Documents/trae_projects/boningTerminal
```

如需重新生成 300/800/1500 三个 synthetic case：

```bash
/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/generate_synthetic_cases.py
```

运行 Abacus vs NGLIC vs MyLegal 对比实验：

```bash
cd src
/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus
```

你会看到类似下面的结果表：

```text
case                        n   ab_total   ng_total   my_total     ng_imp     my_imp   ab_max   ng_max   my_max ng_max_imp my_max_imp    ab_hpwl    ng_hpwl    my_hpwl
large_dense_1500         1500     717330     312119     312104     56.49%     56.49%     1217      602      602     50.53%     50.53%     190766     202468     202461
large_medium_800          800      45965      25111      25084     45.37%     45.43%      329       93       77     71.73%     76.60%      13679       9346       9319
large_sparse_300          300       7295       4575       4563     37.29%     37.45%       81       61       61     24.69%     24.69%       1162        760        758
```

字段含义：

```text
ab_total    Abacus 的总位移
ng_total    NGLIC 的总位移
my_total    MyLegal 的总位移
ng_imp      NGLIC 相比 Abacus 的总位移降低比例
my_imp      MyLegal 相比 Abacus 的总位移降低比例
ab_max      Abacus 的最大单点位移
ng_max      NGLIC 的最大单点位移
my_max      MyLegal 的最大单点位移
ng_max_imp  NGLIC 相比 Abacus 的最大位移降低比例
my_max_imp  MyLegal 相比 Abacus 的最大位移降低比例
ab_hpwl     Abacus 的 HPWL Growth，当前 synthetic case 为 per-net HPWL 增量
ng_hpwl     NGLIC 的 HPWL Growth，当前 synthetic case 为 per-net HPWL 增量
my_hpwl     MyLegal 的 HPWL Growth，当前 synthetic case 为 per-net HPWL 增量
```

如果需要 CSV 格式，方便复制到表格或画图：

```bash
/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 run_synthetic_cases.py ../benchmark/synthetic/large_*.json --compare-abacus --csv
```

### Windows / PowerShell

假设你把项目放在：

```text
D:\3D_BT_legal
```

先进入项目目录：

```powershell
cd D:\3D_BT_legal
```

安装依赖：

```powershell
py -m pip install numpy
```

如果你的电脑没有 `py` 命令，就把下面命令里的 `py` 换成 `python`。

重新生成 300/800/1500 三个 synthetic case：

```powershell
py src\generate_synthetic_cases.py
```

运行 Abacus vs NGLIC vs MyLegal 对比实验。PowerShell 下建议显式写三个 case：

```powershell
cd src

py run_synthetic_cases.py `
  ..\benchmark\synthetic\large_sparse_300.json `
  ..\benchmark\synthetic\large_medium_800.json `
  ..\benchmark\synthetic\large_dense_1500.json `
  --compare-abacus
```

如果需要 CSV 格式：

```powershell
py run_synthetic_cases.py `
  ..\benchmark\synthetic\large_sparse_300.json `
  ..\benchmark\synthetic\large_medium_800.json `
  ..\benchmark\synthetic\large_dense_1500.json `
  --compare-abacus --csv
```

## 实验报告在哪里

当前固定 synthetic 实验报告在：

```text
docs/synthetic-experiment-results.md
```

MyLegal 论文草稿在：

```text
docs/mylegal-paper.md
```

论文深度解读和复现路线在：

```text
docs/nglic-paper-deep-dive.md
```

## 脚本说明

需要保留并主要使用的脚本：

```text
src/generate_synthetic_cases.py  生成 300/800/1500 synthetic case
src/run_synthetic_cases.py       跑 Abacus vs NGLIC vs MyLegal 对比实验
```

开发自测脚本：

```text
src/smoke_test.py                小规模 sanity check，不是正式实验入口
```

核心算法文件：

```text
src/Legalization.py
src/dplacer_horizon.py
src/dp_data_horizon.py
src/Die.py
src/Terminal.py
```

## 关于 ICCAD 原始 benchmark

`benchmark/case1.txt` 到 `benchmark/case4.txt` 来自 ICCAD 2022 CAD Contest Problem B。它们是原始网表/技术库输入，不是 NGLIC 直接需要的 interdie connection GP 坐标。

原论文中的实验数据是基于 ICCAD 原始 benchmark，经过 partition 后生成 interdie connections，再做 placement 和 legalization。当前仓库为了突出 legalization 对比效果，使用自造 synthetic case 进行 Abacus vs NGLIC vs MyLegal 对比实验。
