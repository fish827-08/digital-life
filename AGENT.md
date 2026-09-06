# AGENT.md — Digital Life 项目导航

> 面向 AI 代理与开发者的项目快速导航。本文件只回答"项目是什么、文档怎么分工、架构怎么组织、有什么硬约定"。
> 详细维护纪律见 `PROJECT_MAINTENANCE_PROMPT.md`；开发哲学与阶段定义见 `AI_DEVELOPMENT_PROMPT.md`；完整使用手册（模块地图/配置表/干预指南/测试/诊断）见 `MANUAL.md`。

## 0. 项目是什么

Artificial Life（人工生命）研究工程，不是游戏。核心闭环：

```
WORLD → SENSOR → BRAIN → ACTION → ENERGY → SURVIVAL → REPRODUCTION → MUTATION → NEW ORGANISM → WORLD
```

程序员只定义物理/能量/遗传/生命周期等**基础规则**；不定义"什么生命最优/谁该成为捕食者"。行为应由自然选择涌现。
**禁止**提前加入 LLM、人工 fitness、预设物种/语言类别。当前阶段：**Stage 2 — Evolution Observatory**（证明环境选择压引起可重复的跨世代统计变化）。

## 1. 文档分工（一个事实一个来源，避免重复）

| 文件 | 职责 | 更新时机 |
| --- | --- | --- |
| `AGENT.md`（本文件） | 目录导航、双引擎、硬约定、红线 | 架构/约定变化 |
| `MANUAL.md` | 完整使用手册：模块地图、配置表、干预指南、测试、诊断 | 功能/参数/命令变化 |
| `RESEARCH.md` | 研究记录：关键实验的 Observed/Expected、证据等级、毕业评估 | 每次影响进化结论的实验完成 | 
| `.ai/current-stage.md` | 当前 Stage 状态的唯一事实来源 | Stage 状态/毕业标准变化 |
| `AI_DEVELOPMENT_PROMPT.md` | 开发哲学、Stage 路线与验收标准 | 核心哲学或阶段定义变化 |
| `PROJECT_MAINTENANCE_PROMPT.md` | 维护纪律（一致性、实验诚实、Stage 评审） | 很少改，是守则 |
| `README.md` | 面向人类的项目哲学摘要 | 哲学描述变化 |
| 各模块 docstring + 测试 | 代码行为的事实来源 | 随代码一起 |

依赖方向：`core ← evolution / world ← simulation ← observatory`。观测层不引入"适应度"概念。模块逐文件说明见 `MANUAL.md` 第 2 节。

## 2. 双引擎设计（关键架构事实）

两套引擎规则等价、接口 duck-typed 对齐，可随时切换：

| | `SimulationEngine`（engine.py） | `VecEngine`（vecengine.py） |
| --- | --- | --- |
| 数据布局 | AoS：`dict[id → Organism]` 对象 | SoA：定长 NumPy 数组（x/y/energy/genes/age/generation/parent） |
| 每 tick | 逐个体 Python 循环 | 全批量向量化（代谢/进食/移动/衰老/死亡/繁殖） |
| 速度 | ~150 tick/s | ~13,500 tick/s（实测 ~90× 提速） |
| 用途 | 单步精确参照、行为语义基准 | 长程实验（万代/百万 tick）默认首选 |

**规则等价契约**（VecEngine 必须保持，改动前核对）：
1. 顺序契约：先 `world.tick_regrowth()` 资源再生，后种群行动
2. 个体行为链：代谢 → 进食（仅自己格）→ 概率移动 → 年龄推进；能量 ≤0 跳过进食/移动/年龄
3. 死亡：先饿死（energy≤0）后老死（age≥life_span；life_span=200+g3×3800）
4. 繁殖：存活且 energy ≥ (0.25+g2×0.65)×max_energy，种群 < max_count；子代能量对半、出生在亲代格、世代+1
5. 性状线性映射（TRAIT_TABLE）：move_prob=g0、代谢倍率=0.5+g1×1.5、repro=0.25+g2×0.65、life_span=200+g3×3800

**已知刻意差异**（统计等价而非逐位一致，测试覆盖）：
- 同格多点取食：VecEngine 用"均分封顶"（顺序无关），对象引擎是先到先得
- 移动方向：VecEngine 均匀抽 8 方向，对象引擎逐次抽 (dx,dy) 直到非零
- RNG 流整体不同（批量 vs 逐个体采样）→ 同种子不逐位复现，仅长期统计一致

## 3. 硬约定

- **引擎选择**：长程/批量实验用 `VecEngine`（`--vec`）；需逐 tick 逐个体语义核对时用 `SimulationEngine`
- **热路径**：不得在 `VecEngine._step_population` 内引入逐个体 Python 循环或对象创建；观测采样走 `population.organisms()`（自带重建，约每百 tick 一次）
- **随机性**：同种子必须逐 tick 可复现；不得引入时间/全局状态依赖
- **内存**：长程实验启用 `history_limit` 有界历史（默认 4,096），新增全量累积逻辑前检查 OOM 风险
- **实验落盘**：结果即时持久化（`run_plan(out_dir=...)` 每个实验完成后立即写盘），禁止仅内存累积

## 4. 红线（摘自维护守则）

- **不得伪造/美化实验结果**：Observed 与 Expected 必须区分；失败实验也是合法结果（如"高变异率→种群崩溃"是稳定性边界证据，不是删除理由）
- **测试不是用来退让的**：回归失败先判断是否真 bug；预期行为变化才改测试，且须同步改文档
- **Stage 不能因"代码写完"自动升级**：只有验收条件（可复现的跨世代统计变化）满足才可升级；升级须记录 Original/Reason/Evidence/New
- **文档跟随现实**：代码/测试/文档不一致时，先查实现与实验证据，再决定更新哪一侧；不要为迎合旧文档改代码
- **新增功能必须回答**：Why / Evidence / Stage / Impact / Reproducibility / Documentation / Testing，答不上来就不要加

常用命令、配置字段、测试矩阵与诊断请见 `MANUAL.md` 的快速上手与测试两节。