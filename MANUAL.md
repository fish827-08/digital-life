# Digital Life 项目手册（MANUAL）

> 面向想理解、干预、修改本项目的读者。阅读顺序建议：
> **① 快速上手 → ② 模块地图 → ③ 核心数据流 → ④ 配置表 → ⑤ 观测系统 → ⑥ 干预指南 → ⑦ 测试 → ⑧ 诊断**。
>
> 伴文档：
> - `README.md` — 项目哲学（八条规则 / 核心循环）
> - `AGENT.md` — AI 导航：文档分工 / 双引擎设计 / 硬约定 / 红线
> - `AI_DEVELOPMENT_PROMPT.md` — 面向 AI 助手的开发约束（原则 1–9）
> - `PROJECT_MAINTENANCE_PROMPT.md` — 维护规程（后文"修改安全指南"的完整版）

---

## 1. 快速上手

```bash
# 运行环境：Python >= 3.12（实测 3.14），依赖 numpy / pydantic，测试用 pytest

# ① 单次模拟（Stage 1 入口，种子固定、确定性）
py -m main                        # 默认配置：seed=42，1000 tick
py -m main --ticks 5000 --seed 7  # 覆盖 tick 数与种子
py -m main --seed random          # 系统熵（不可复现）

# ② 实验矩阵（Stage 2 入口，5 类实验；默认对象引擎，`--vec` 用数组化高速引擎）
py -m observatory --out results/s2                    # 默认：baseline 1000 代 + 全部对照 250 代
py -m observatory --names baseline --generations 1000 # 只跑 baseline（精简档）
py -m observatory --names baseline --generations 10000 --vec  # 完整 1 万代档（VecEngine，约 30–60 分钟）
py -m observatory --group resource_pressure            # 只跑某组
py -m observatory --names pressure_low --seed 7        # 换 base seed（跨 seed 复现）

# ③ 测试
py -m pytest -q                  # 全量（151 个）
py -m pytest -q tests/test_observatory.py  # 只跑观测台
py -m pytest -q tests/test_vecengine.py     # 只跑数组引擎（等价性/确定性/性能哨兵）
```

每个实验结束后结果落在 `--out` 目录：`<实验名>/manifest.json`（元数据+配置+摘要）、`<实验名>/generations.csv|json`（逐代观测点）、`__survey__.json|md`（批量汇总）。

---

## 2. 目录与模块地图（每个文件是什么）

```
digital_life/
├── core/           # ① 生命内核：与"规则"无关的纯数据与契约
│   ├── genome.py       # Genome：定长连续基因链（float64 一维数组）的容器
│   ├── genetics.py     # 基因→性状解码契约 + 变异/交叉纯函数 + TRAIT_TABLE
│   ├── organism.py     # Organism：个体（位置/能量/基因/表现型/生命周期/谱系元数据）
│   ├── lifecycle.py    # Lifecycle：年龄推进、死亡判定、死因枚举（DeathCause）
│   └── metabolism.py   # 能量收支纯函数（代谢消耗/进食增益/能量钳制）
├── world/          # ② 世界：个体生存的空间与资源
│   ├── resource.py     # ResourceField：网格资源场（向量化再生、消费、斑块异质）
│   ├── terrain.py      # TerrainField：通行性布尔网格（v1 全通）
│   ├── environment.py  # Environment：EnvironmentView 协议实现（torus/查询/8 邻格）
│   └── world.py        # World：装配三子对象，对外暴露整体语义
├── evolution/      # ③ 演化：把"个体与世界"转成"种群与选择"
│   ├── population.py   # Population：种群容器，每 tick 总账（行动→繁殖→死亡）
│   ├── mutation.py     # 变异策略包装（genome → 变异 genome）
│   ├── reproduction.py # 无性繁殖：子代 = 亲代基因 + 变异，能量对半
│   └── selection.py    # 选择压判定：繁殖门槛 / 死亡判定（纯涌现，无 fitness）
├── simulation/     # ④ 调度：确定性主循环与配置
│   ├── config.py       # SimConfig 全量参数（唯一事实来源，pydantic 校验）
│   ├── engine.py       # SimulationEngine：对象引擎，tick 节拍器，固定 RNG 顺序契约
│   ├── vecengine.py    # VecEngine：数组化高速引擎（SoA，规则等价、统计一致，约 90× 提速）
│   └── tick.py         # TickStats：单 tick 的不可变统计快照
├── observatory/    # ⑤ 观测台（Stage 2：证明"自然选择正在发生"的实验系统）
│   ├── statistics.py   # 纯函数统计聚合 → GenerationStats（观测点口径）
│   ├── observer.py     # EvolutionObserver：世代轴 + 时间轴双触发采样
│   ├── experiment.py   # ExperimentSpec/Run/Runner + 5 类实验矩阵 + 种子派生
│   └── __main__.py     # `py -m observatory` 无头 CLI
├── persistence/    # ⑥ 持久化
│   └── io.py           # 实验结果 JSON/CSV 落盘与回读 + survey 摘要
├── brain/          # ⑦ 预留：感知→决策（神经元）占位，空包
├── visualization/  # ⑧ 预留：pygame 可视化占位，空包
├── main.py             # Stage 1 无头 CLI（单次模拟摘要）
├── tests/              # 151 个测试（见第 7 节）
├── results/            # 实验输出（运行产物，不入 git）
└── pyproject.toml      # 打包/依赖/pytest 配置
```

数据依赖方向（只允许上层依赖下层，禁止反向）：

```
core ← world ← evolution ← simulation ← main
                      ↘ observatory ← persistence ← (CLI)
```

---

## 3. 你不知道就改不对的三件事

### 3.1 一个 tick 的固定顺序契约（对象引擎 `SimulationEngine._advance_one_tick` / 数组引擎 `VecEngine._advance_one_tick`）

**双引擎**：`SimulationEngine`（AoS，逐个体 Python 循环，~150 tick/s）与 `VecEngine`（SoA，NumPy 全批量向量化，~13,500 tick/s）**规则等价、接口一致**（duck-typed），可随时切换。长程/批量实验用 `VecEngine`（`--vec`），需逐个体语义核对时用对象引擎。已知刻意差异（统计等价而非逐位一致）：同格多点取食为"均分封顶"（顺序无关）、移动方向批量均匀抽 8 邻、RNG 流整体不同，详见 `AGENT.md` 第 3 节。

同一配置 + 同一种子 → 逐 tick 世界演化完全相同。任何**改变 RNG 调用次数或顺序**的改动都会破坏复现性，是最高级别的红线。

```
每个 tick：
  1) world.tick_regrowth()        → 资源再生（向量化，全格 += regrowth_rate，封顶 capacity）
  2) population.update(rng)       → 对每个存活个体（快照迭代）依次：
        a. 代谢扣费        energy -= base_metabolism × metabolism_mult
        b. 若 energy ≤ 0   本 tick 不再进食/移动（死因判定交给引擎）
        c. 进食            taken = env.consume_resource(x, y, eat_amount)
                          energy = clamp(energy + taken × eat_efficiency, max_energy)
        d. 移动            if rng.random() < move_prob 且 energy ≥ move_cost：
                            random_neighbor(8 邻格，torus 包装，避开不可通行格)
                          energy -= move_cost
        e. 年龄 +1
        f. 死亡判定        先饿死（energy ≤ 0）后老死（age ≥ life_span）
        g. 繁殖判定        存活 且 种群 < max_count 且 energy ≥ repro_fraction × max_energy：
                          子代 = 亲代基因 + 变异；energy 对半扣；generation+1；parent_id=亲代
  3) 清理尸体（记录死因）→ 产出 TickStats → append 历史（有界模式下环形裁剪）
```

### 3.2 基因 → 性状解码（`core/genetics.py`）

16 个连续基因，只有 4 个被解码为性状（其余 12 个是"中性漂移区"，仍参与变异）：
基因值 ∈ [0,1]，线性映射到性状区间：

| 基因位 | 性状 | 区间 | 影响 |
|---|---|---|---|
| 0 | `move_prob` | [0, 1] | 每 tick 移动概率（觅食≠定居的权衡） |
| 1 | `metabolism_mult` | [0.5, 2.0] | 代谢倍率（省能耗 vs 能力上限） |
| 2 | `repro_fraction` | [0.25, 0.9] | 繁殖门槛比例（多生 vs 稳健） |
| 3 | `life_span` | [200, 4000] | 寿命 tick 数（短命早生代 vs 长寿晚育） |

### 3.3 能量经济学 = 选择压（「自然选择」的定义位置）

本项目**没有 fitness 函数**。选择压完全由这两条涌现规则构成（`selection.py`）：
1. **能攒够能量者繁殖**（门槛由基因决定：`repro_fraction × max_energy`）
2. **攒不够者被淘汰**（饿死）或 **寿命到限被淘汰**（老死）

因此"什么是最优个体"不由代码定义，而是由环境参数（资源多少/再生快慢/世界大小）定义——这就是干预的杠杆。

---

## 4. 配置系统全字段表（`simulation/config.py`）

所有数值参数集中于此，改参数 = 干预的第一级入口。顶节点为 `SimConfig`（seed + 6 个子配置）。

| 子配置 | 字段 | 默认 | 含义 / 干预效果 |
|---|---|---|---|
| `world` | `width` / `height` | 128×128 | 网格尺寸（越小种群密度越高、tick 越快） |
| | `wrap` | True | torus 环形边界；False 有边界效应 |
| `resources` | `capacity` | 1.0 | 每格资源上限 |
| | `initial_fill` | 0.4 | 初始填充比例（0~1） |
| | `regrowth_rate` | 0.02 | 每 tick 全格再生量（**选压主旋钮**） |
| | `patchiness` | 0.0 | 初始空间异质幅度；>0 生成富/贫斑块 |
| | `patch_count` | 4 | 每边斑块数（patchiness>0 时生效） |
| `organisms` | `initial_energy` | 60.0 | 新生个体起手能量 |
| | `max_energy` | 300.0 | 能量上限（繁殖阈值 = repro_fraction × 300） |
| | `base_metabolism` | 0.6 | 基础代谢/ tick |
| | `move_cost` | 0.4 | 每格移动成本 |
| | `eat_amount` | 0.5 | 每 tick 最大进食量 |
| | `eat_efficiency` | 3.0 | 食物→能量转化率 |
| `genome` | `gene_count` | 16 | 基因链长度 |
| | `gene_min/max` | 0.0/1.0 | 基因取值域 |
| | `mutation_rate` | 0.05 | 单基因变异概率（**遗传多样性旋钮**） |
| | `mutation_sigma` | 0.05 | 高斯扰动幅度（相对基因域） |
| | `crossover_rate` | 0.5 | ⚠️ 配置存在但无性繁殖未使用（见 6.4） |
| `population` | `initial_count` | 200 | 初代数量 |
| | `max_count` | 2000 | 种群硬上限（防失控） |
| `simulation` | `ticks` | 1000 | 计划运行时长的 tick 上限 |
| | `stop_on_extinction` | True | 灭绝提前停止（防护） |
| | `log_interval` | 50 | CLI 进度打印间隔（0=不打印） |
| | `history_limit` | 0 | 历史统计保留上限；>0 有界（超长实验防 OOM） |

---

## 5. 观测系统（Stage 2：怎么证明自然选择在发生）

### 5.1 观测点口径（`observatory/statistics.py` → `GenerationStats`）

每个观测点给出（字段名即 CSV 列名）：

| 类别 | 字段 | 说明 |
|---|---|---|
| 种群 | `population` | 存活个体数 |
| 年龄/能量 | `mean_age`, `mean_energy` | 均值 |
| 谱系 | `max_generation`, `median_generation`, `mean_generation` | 世代号分布 |
| 世代结构 | `generation_histogram` | 对数桶 {"0-0","1-9","10-99",...}（仅 JSON） |
| 性状分布 | `trait_<name>_mean`, `trait_<name>_std` | 4 性状均值/标准差 |
| 基因组多样性 | `genome_diversity` | 平均每位点 Simpson 杂合度 [0,1] |
| 基因型 | `unique_genotypes`, `unique_genotype_ratio` | 量化（3 位小数）后的唯一基因型 |

### 5.2 采样触发（`observatory/observer.py` → `EvolutionObserver`）

每次采样追加一行（`GenerationSample`）：`tick, generation, span_ticks, born_since_prev, died_since_prev, birth_rate, death_rate` + 上述统计。**两个触发器**：
1. 世代推进：`population.max_generation` 前进时采样（世代轴连续）
2. 兜底节拍：距上次采样 ≥ `tick_interval` tick 时采样（时间轴连续，覆盖世代停滞/灭绝）

出生/死亡率按窗口（自上次采样）累计 ÷ span_ticks，per-tick 单位，跨实验可比。

### 5.3 实验系统（`observatory/experiment.py`）

- **确定性**：`seed = SeedSequence([base_seed, group_id, seed_index])` → 同命令行必然同结果
- **5 类矩阵（build_plan）**：baseline（默认 1000 代长程）/ resource_pressure ×2 / resource_distribution ×3 / mutation_rate ×2 / repeated_seeds ×3
- **停止条件**：世代达标 ∨ 引擎结束（跑满 tick/灭绝）∨ tick 硬上限（防失控）
- **结果摘要**（`ExperimentResult.summary`）：起/中/末 三点种群、多样性 drift、4 性状 start→mid→end drift、末态出生率/死亡率

### 5.4 输出格式（`persistence/io.py`）

每个实验一个目录：`manifest.json`（实验元数据 + 完整 `SimConfig.to_dict()` + totals + summary）、`generations.csv`（宽表）、`generations.json`（镜像）；批量再加 `__survey__.json` 与人类可读的 `__survey__.md`。回读函数：`load_manifest` / `load_generations`。

---

## 6. 干预指南（怎么"玩"、怎么"改"）

### 6.1 不写代码的干预：调参数（示例）

| 你想观察 | 改什么 | 预期效应 |
|---|---|---|
| 食物变少迫使进化 | `regrowth_rate` 0.02→0.005 | 代谢更低、更早繁殖（`pressure_low` 已验证） |
| 饥饿危机 | `regrowth_rate` →0.001 | 灭绝动力学（`pressure_critical` 已验证） |
| 空间不公造就生态位 | `initial_fill` 0.08 / 0.8，`patchiness` 0.8 | 稀疏/富饶/斑块，迁移 vs 定居 |
| 遗传多样性变化 | `mutation_rate` 0.05→0.005/0.3 | 漂变 vs 变异供给 |
| 结果可重复性 | 换 `--seed` | repeated_seeds 方差分析 |
| 跑得快一点 | `--world 32`（或调小 width/height） | tick 提速，但密度上升 |

在 `observatory` 里这些已封装为实验矩阵的 `overrides`；直接跑 `py -m observatory --names <name>` 即可复现，或用 `ExperimentSpec(..., overrides={...})` 自定义。

### 6.2 自建实验（代码最少）

```python
from observatory.experiment import ExperimentRunner, ExperimentRun, ExperimentSpec, derive_seed

spec = ExperimentSpec(
    name="my_test", group="baseline",
    description="自定义：移动更贵",
    overrides={"organisms": {"move_cost": 1.2}},   # SimConfig 子字段覆盖
    max_generations=200,
)
run = ExperimentRun(spec=spec, seed=derive_seed(42, spec.group_id, 0))
res = ExperimentRunner().run_single(run)
# res.samples / res.summary / res.config.fingerprint() 都在手边
```

### 6.3 改代码的安全指南（分层：能不动下层就别动）

| 想达成的改动 | 应该改哪一层 | 关键注意 |
|---|---|---|
| 数值标定 | `simulation/config.py` | 只改默认值，别动字段名 |
| 加一个性状 | `core/genetics.py`（TRAIT_TABLE）+ config | 点 6.5 的 5 步法 |
| 换变异策略 | `core/genetics.mutate` 或 `evolution/mutation.py` | 保持纯函数签名 |
| 换繁殖方式（有性） | `evolution/reproduction.py` | 保留 `Offspring` 语义 |
| 改行为决策 | `core/organism.py::Organism.step` | 保持 RNG 调用次数不变量 |
| 加环境压力（毒区/季节） | `world/` + `resource.py/tick_regrowth` | 保持 `tick_regrowth` 先于 `population.update` |
| 加真·感知/决策 | `brain/`（当前空包） | 通过 `EnvironmentView` 协议接入 |
| 加新实验类别 | `observatory/experiment.py` + `_GROUP_IDS` | 新组须登记 int id |
| 加新的观测指标 | `observatory/statistics.py` | 纯函数聚合，JSON 安全 |

**六条铁律**（完整版见 `AI_DEVELOPMENT_PROMPT.md` 原则 1–9）：
1. 不要改变每 tick 的 RNG 调用顺序/次数（否则全历史复现失效）
2. 随机性必须来自显式传入的 `rng`，禁止 `random`/`np.random` 全局
3. 新规则先写成纯函数（入参出参，无全局状态），再让带状态对象去调用
4. 不向 `core` 层引入对 `world/simulation` 的依赖（依赖方向单向）
5. 每次改动先跑对应测试（见第 7 节），大改动全量回归
6. 不要为"看起来智能"提前加 LLM/神经网络/fitness——先证明涌现

### 6.4 已知缺口与注意点（改项目前必读）

- ⚠️ `crossover_rate`（默认 0.5）是**死参数**：无性繁殖从未调用 `crossover`。想用则在 `evolution/reproduction.py` 里接入，否则建议别在文档/论文里引用它。
- ⚠️ `pyproject.toml` 的 `packages` 列表**没有 `observatory` 与 `persistence` 是历史遗漏**：`py -m observatory` 在仓库根目录运行时无需安装即可用（pytest 的 `pythonpath=["."]` 同理）；若将来要 `pip install` 打包，需把这些包名补进 `[tool.setuptools] packages`。
- `history_limit=0`（默认）时引擎保留**全部** tick 历史，百万 tick 级会长到数 GB——长程实验必须开 `history_limit>0`（实验 runner 已自动设为 4096）。
- 世代推进速率实测 ~850–1,500 tick/代（64×64 默认生态，随种群收缩变慢）：1,000 代（对象引擎）≈ 40–45 分钟。**长程实验请用 `--vec`（VecEngine）**：1 万代 ≈ 30–60 分钟（对象引擎需数小时）。CLI 的 baseline tick 上限已按世代数自动推导（实验层 `build_plan`），无需手动配 `--max-ticks`。
- `Observatory` 的 `observe(tick_stats)` 与老的无参调用向后兼容（内部自动回退历史切片），新代码建议总是传 `stats`。

### 6.5 扩展示例：加一个新性状（5 步）

1. **TRAIT_TABLE**（`core/genetics.py`）：追加 `Trait("forage_range", 4, 1.0, 3.0)`（8 邻格采样半径）
2. **config 校验**：`GenomeConfig.gene_count` 默认 16 已覆盖索引 4，无需改（若加更多位则调大）
3. **行为接入**：`Organism.step`/`EnvironmentView` 接口扩展（给 `random_neighbor` 加半径参数）
4. **观测自动获得**：`statistics.py::TRAIT_ORDER` 从 TRAIT_TABLE 派生 → 新性状自动进 CSV 与 drift 摘要
5. **测试**：仿照 `tests/test_genetics.py` 加解码边界用例 + `tests/test_organism.py` 行为用例

---

## 7. 测试体系（151 个，全部确定性）

| 文件 | 覆盖 | 说明 |
|---|---|---|
| `test_genome.py` | 基因链容器/比较/相等 | 工厂与边界 |
| `test_genetics.py` | 解码/变异/交叉 | 区间、纯函数、中性基因 |
| `test_lifecycle.py` | 年龄/死因 | 状态机与死因幂等 |
| `test_metabolism.py` | 能量收支 | 钳制边界 |
| `test_organism.py` | 个体行为 | 代谢/进食/移动/能量耗尽 |
| `test_resource.py` / `test_terrain.py` | 资源场/地形 | 再生、消费、异质、patchiness |
| `test_environment.py` / `test_world.py` | 环境与装配 | torus/越界/邻格 |
| `test_mutation.py` / `test_reproduction.py` / `test_selection.py` | 演化三件套 | 纯函数语义 |
| `test_population.py` | 种群账本 | 出生/死亡/谱系元数据 |
| `test_engine.py` | 对象引擎 | RNG 契约、灭绝、有界历史守卫 |
| `test_vecengine.py` | 数组引擎 | 确定性回放、双引擎统计等价、灭绝动力学、性能哨兵 |
| `test_config.py` | 配置 | 校验器、fingerprint |
| `test_integration.py` | 端到端 | 闭环生存、世代更替、复现、性能哨兵 |
| `test_observatory.py` | 观测台 | 统计口径/采样/矩阵/确定性/IO 往返/即时落盘 |

```bash
py -m pytest -q            # 全量（~2 分钟）
py -m pytest -q tests/test_engine.py tests/test_integration.py  # 涉及引擎契约改动时回归
py -m pytest -q tests/test_observatory.py                       # 只改观测台时
```

测试都是**确定性**的（固定种子构造），任何一次红 = 你的改动破坏了不变量，不是 flaky。

---

## 8. 常见问题诊断

| 现象 | 原因 | 处理 |
|---|---|---|
| 早期种群迅速归零 | 参数把生态调到"必死局"（如 regrowth 过小 × 代谢过高） | 放宽 `regrowth_rate`/`initial_fill`，或关 `stop_on_extinction` 观察曲线 |
| 世代推进极慢 | 能量富余但繁殖门槛（`repro_fraction`）被性状拖高 | 等观测数据看 `repro_fraction` drift；本身就是可观测的演化现象 |
| 多样性快速坍缩 | mutation_rate 过低或强选择 | 调 `mutation_rate`/`mutation_sigma`，用 repeated_seeds 对照漂变 |
| 两个同种子运行结果不同 | 你在代码里用了全局随机性 | `rg "random"` 找非 `rng` 用法，改显式 `rng` |
| 长实验内存暴涨 | `history_limit=0` | 实验层已自动开 4096；手写引擎循环时显式设 `simulation.history_limit` |
| CSV 某列全零 | 该观测点在灭绝后的空种群采样 | 正常的合法观测点（`_empty_stats` 全零），绘图时按 `population>0` 过滤 |
| `py -m observatory` 找不到模块 | 在非项目根目录执行 | 在 `digital_life/` 下执行（包路径依赖仓库根） |

---

*手册维护：修改代码时请同步更新本文件的模块地图、字段表与干预表。*