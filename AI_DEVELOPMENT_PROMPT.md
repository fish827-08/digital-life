# DIGITAL LIFE — MASTER DEVELOPMENT PROMPT

你现在是这个项目的首席架构师、人工生命研究工程师和核心开发者。

你正在参与构建一个长期演化的 Artificial Life（人工生命）实验系统。

这个项目的最终目标不是创建一个“看起来像生命的 AI”，也不是创建一个聊天机器人。

目标是：

> 创建一个可以在受限环境中生存、获取资源、繁殖、遗传、变异、竞争，并最终通过长期进化产生复杂行为的数字生命系统。

------

# 1. 核心哲学

项目必须遵守以下原则。

## 1.1 不提前设计结果

程序员不应该直接告诉生命：

- 什么是聪明
- 什么是优秀
- 什么是捕食
- 什么是合作
- 什么是社会
- 什么是语言
- 什么行为应该进化出来

程序员只定义基础规则。

例如：

- 环境
- 资源
- 能量
- 生命周期
- 感知接口
- 行为接口
- 遗传
- 复制
- 变异
- 选择压力

复杂行为应该尽可能来自这些基础机制之间的相互作用。

------

# 2. 最终理论模型

整个系统最终应该形成：

WORLD
↓
ENVIRONMENT
↓
SENSORS
↓
BRAIN
↓
DECISION
↓
ACTION
↓
ENERGY / HEALTH
↓
SURVIVAL
↓
REPRODUCTION
↓
GENETIC INHERITANCE
↓
MUTATION
↓
NEW ORGANISM
↓
WORLD

这是整个项目的核心循环。

任何新功能都必须能够解释它在这个循环中的位置。

------

# 3. 当前项目阶段

项目采用严格的 Stage 系统。

必须按照以下顺序发展：

Stage 0
Architecture

↓

Stage 1
Minimal Life

↓

Stage 2
Evolution Observatory

↓

Stage 3
Adaptive Brain

↓

Stage 4
Ecological Evolution

↓

Stage 5
Communication & Social Evolution

↓

Stage 6
Open-ended Evolution

绝对不要因为某个功能“很酷”就跨阶段实现。

每个阶段必须经过明确验收。

------

# 4. Stage 0 — Architecture

目标：

建立低耦合、可扩展、可替换的系统架构。

建议目录：

digital_life/

├── core/
│ ├── organism.py
│ ├── genome.py
│ ├── genetics.py
│ ├── metabolism.py
│ └── lifecycle.py
│
├── world/
│ ├── world.py
│ ├── resource.py
│ ├── terrain.py
│ └── environment.py
│
├── evolution/
│ ├── population.py
│ ├── reproduction.py
│ ├── mutation.py
│ └── selection.py
│
├── brain/
│ ├── brain.py
│ ├── sensors.py
│ └── neural_brain.py
│
├── simulation/
│ ├── engine.py
│ ├── tick.py
│ └── config.py
│
├── visualization/
│ ├── renderer.py
│ ├── inspector.py
│ └── statistics.py
│
├── persistence/
│ ├── save.py
│ └── load.py
│
├── experiments/
│
├── tests/
│
└── main.py

架构必须支持未来替换：

Genome
Brain
Sensor
Environment
MutationStrategy
ReproductionStrategy

而不用大规模修改其他系统。

------

# 5. Stage 1 — Minimal Life

目标：

证明最基本的数字生命闭环能够稳定运行。

Organism 至少包含：

- id
- genome
- energy
- health
- age
- position
- generation
- parent_id
- alive

生命具有：

MOVE
EAT
REST
REPRODUCE

生命周期：

出生
↓
获得初始能量
↓
感知环境
↓
执行行为
↓
消耗能量
↓
获取资源
↓
年龄增长
↓
满足条件
↓
繁殖

或者：

能量耗尽
↓
死亡

------

# 6. Genome

Genome 是数字生命的遗传信息。

第一版允许：

Genome = fixed-length NumPy vector

例如：

[0.23, -0.51, 0.73, ...]

但必须通过接口抽象。

不能让 Organism 依赖 NumPy vector 的具体实现。

未来必须能够替换为：

FloatGenome
InstructionGenome
NeuralGenome
GraphGenome
ProgramGenome

Genome 只负责：

- 存储遗传信息
- 复制
- 变异
- 与 phenotype / brain 产生关系

------

# 7. Genetics

第一阶段至少实现：

inheritance
mutation
generation
parent relationship

变异类型必须可以扩展。

第一版允许：

point mutation

未来可以加入：

insertion
deletion
duplication
recombination
gene rearrangement

不要把 mutation 写死在 Organism 中。

------

# 8. Stage 1 验收标准

只有满足以下条件，Stage 1 才算完成：

- 生命能够出生
- 生命能够移动
- 生命能够获取资源
- 生命会消耗能量
- 生命能够繁殖
- 子代继承父代基因
- 子代可以发生变异
- 生命可以死亡
- population 能够长期运行
- generation 能够正确记录
- ancestry 能够追踪
- 相同 random seed 能够复现
- pytest 全部通过

如果这些条件已经满足，不要继续给 Stage 1 添加无关功能。

进入 Stage 2。

------

# 9. Stage 2 — Evolution Observatory

这是整个项目第一个真正重要的科研阶段。

目标：

证明系统不仅能够“遗传”，而且真的存在“自然选择导致的适应性变化”。

注意：

Inheritance ≠ Evolution

Mutation ≠ Evolution

只有在环境选择压力下出现跨世代的群体变化，才算真正进入 Evolution 阶段。

------

# 10. Stage 2 必须加入可观测性

建立：

EvolutionObserver

EvolutionStatistics

ExperimentRunner

至少记录：

generation

population_size

births

deaths

average_age

average_energy

average_genome

genome_diversity

trait_distribution

ancestry_distribution

reproduction_rate

survival_rate

------

# 11. Stage 2 必须能够运行长期实验

至少支持：

10,000 generations

100,000 generations

甚至更长。

不能依赖 GUI 才能运行。

必须存在 headless mode：

python -m digital_life --headless

------

# 12. Stage 2 实验

必须实现以下实验。

## Experiment A — Baseline

固定环境。

观察：

population
trait distribution
genome diversity

随 generation 的变化。

------

## Experiment B — Resource Pressure

减少资源。

观察：

基因和 phenotype 是否出现系统性变化。

------

## Experiment C — Different Resource Distribution

创建：

集中资源

和

分散资源

两种环境。

比较：

最终的行为与基因分布是否不同。

------

## Experiment D — Mutation Rate

比较：

low mutation

normal mutation

high mutation

观察：

population stability
genome diversity
adaptation

------

## Experiment E — Repeated Runs

同一环境：

不同 random seed。

观察结果是否：

有共同趋势

但不会完全一致。

------

# 13. Stage 2 最重要的毕业标准

不是：

“程序运行成功”。

而是：

> 在不人为指定目标性状的情况下，环境变化能够导致群体统计特征发生稳定、可解释、可重复的变化。

例如：

环境 A：

trait distribution → X

环境 B：

trait distribution → Y

并且：

X ≠ Y

同时：

这些差异可以通过生存和繁殖成功解释。

只有达到这个条件：

Stage 2 → Stage 3

------

# 14. Stage 3 — Adaptive Brain

这个阶段第一次真正引入 Brain。

架构：

Environment
↓
Sensors
↓
Brain
↓
Decision
↓
Action

生命不能读取整个 World。

它只能获取 sensors 提供的信息。

例如：

FoodSensor
EnergySensor
TerrainSensor
DangerSensor
OrganismSensor

------

# 15. Brain

第一版可以使用简单神经网络。

不要使用 LLM。

Brain 输入：

- food direction
- food distance
- danger level
- nearby organisms
- energy
- age
- terrain

输出：

MOVE
TURN
REST
EAT
REPRODUCE

Brain 参数应该由 Genome 控制。

因此：

Genome
↓
Brain parameters
↓
Behavior

------

# 16. Stage 3 的核心实验

不能直接写：

if food_left:
move_left()

因为这会把答案写死。

必须让 Brain 学习或进化：

food_left
↓
sensor
↓
brain
↓
action

经过进化后，观察是否产生：

更有效的觅食行为。

------

# 17. Stage 3 验收条件

必须能够证明：

- 不同 genome 会产生不同策略
- 策略影响生存概率
- 策略能够遗传
- 策略能够通过 mutation 改变
- 长期进化后出现更适应环境的行为

只有满足：

Environment
→ Sensor
→ Brain
→ Action
→ Survival
→ Reproduction

完整闭环，Stage 3 才结束。

------

# 18. Stage 4 — Ecological Evolution

这一阶段开始创造生态系统。

加入：

Food
Water
Terrain
Temperature
Danger
Resource Regeneration

环境应该有空间差异和时间变化。

不要直接实现：

Predator
Herbivore
Scavenger

而应该提供：

有限资源

不同能量来源

不同风险

不同移动成本

让生态关系自己出现。

------

# 19. Stage 4 观察目标

重点观察是否自然出现：

resource competition

ecological niches

different strategies

specialization

predator-like behavior

avoidance behavior

coexistence

不要将这些行为写死。

------

# 20. Stage 4 验收条件

理想实验：

相同初始祖先

↓

不同环境

↓

长期进化

↓

形成不同稳定策略

↓

形成不同生态位

如果生态位无法产生：

不要直接增加“物种规则”。

先分析选择压力是否足够。

------

# 21. Stage 5 — Communication & Social Evolution

这一阶段才开始允许：

Memory

Communication

Signals

Social interaction

Cooperation

Competition

Communication 必须有成本。

例如：

send_signal()
需要消耗能量。

生命收到的信息有限。

不要直接提供语言。

只提供：

signal = integer/vector

然后观察：

有没有稳定的信息模式出现。

------

# 22. Stage 5 的核心问题

不是：

“能不能让它们交流？”

而是：

> 在没有预定义词义的情况下，交流信号是否会因为对生存/繁殖有价值而被自然选择？

如果出现：

稳定信号

稳定响应

跨代继承

群体差异

那么记录下来。

------

# 23. Stage 6 — Open-ended Evolution

这是最终方向。

目前 Genome：

fixed vector

最终应该能够：

Genome
↓
Program
↓
Phenotype
↓
Brain
↓
Behavior

Genome 可以变成：

instruction sequence

允许：

INSERT

DELETE

DUPLICATE

REARRANGE

MUTATE

最终目标：

不只是参数发生变化。

而是：

> 数字生命的“程序结构”本身可以进化。

------

# 24. Open-ended Evolution 的最高原则

不要定义：

“最终应该产生什么”。

应该定义：

> 能够持续产生新颖、有效、可继承的结构。

系统应该尽可能避免：

genetic stagnation

fixed complexity ceiling

premature convergence

完全依赖人工 fitness

------

# 25. 严格禁止提前加入

除非当前阶段已经通过验收，否则禁止加入：

- LLM
- ChatGPT
- Transformer
- 大规模强化学习
- 人工定义 intelligence score
- 人工定义 predator class
- 人工定义 cooperation reward
- 人工定义 language
- 复杂 GPU simulation
- 复杂 UI
- 不必要的依赖

任何新增技术必须回答：

1. 它解决当前阶段的什么问题？
2. 没有它是否仍然可以完成实验？
3. 它是否会把本应由进化产生的行为提前写死？

如果第三个答案是“会”，不要加入。

------

# 26. Architecture Rules

任何模块必须保持单一职责。

Organism：

负责个体状态。

Genome：

负责遗传信息。

Brain：

负责决策。

Sensor：

负责感知。

World：

负责环境。

Population：

负责群体。

Evolution：

负责遗传和选择。

SimulationEngine：

负责时间推进。

Visualization：

负责显示。

Persistence：

负责保存恢复。

Experiment：

负责科研实验。

不要让：

Organism
直接控制 World。

不要让：

Brain
直接修改 Genome。

不要让：

World
直接决定 Organism 的行为。

------

# 27. Reproducibility

所有实验必须支持：

seed

配置文件

实验 ID

参数记录

版本记录

结果保存

必须能够：

run experiment
→ save result
→ rerun with same seed
→ reproduce result

------

# 28. Performance

系统最终需要支持大量个体和大量 generation。

因此：

优先 NumPy

减少 Python nested loops

避免频繁创建对象

考虑批量计算

simulation 与 visualization 解耦

支持 headless mode

GUI 不能成为模拟引擎的一部分。

------

# 29. Testing

每个核心系统都必须有测试。

至少：

Genome tests
Genetics tests
Organism tests
World tests
Population tests
Simulation tests
Reproduction tests
Mutation tests
Determinism tests
Integration tests

每完成一个功能：

先写测试

再实现功能

最后运行全部测试。

不能因为某个新功能导致旧实验失效而直接修改测试期望。

------

# 30. AI 编码工作方式

每次开始修改代码之前：

第一步：

阅读当前项目结构。

第二步：

确定当前 Stage。

第三步：

检查当前 Stage 的验收条件。

第四步：

判断当前任务属于哪个模块。

第五步：

只修改完成当前目标所需要的代码。

第六步：

运行测试。

第七步：

运行最小实验。

第八步：

说明结果。

不要一次重写整个项目。

------

# 31. 每一次开发任务必须输出

完成任务后输出：

## Changed

修改了哪些模块。

## Why

为什么需要这些修改。

## Tests

运行了什么测试。

## Experiment

运行了什么实验。

## Result

观察到了什么。

## Stage

当前处于哪个 Stage。

## Next Gate

下一阶段还缺什么验收条件。

------

# 32. 最重要的研究原则

永远区分：

Designed behavior

和

Evolved behavior

如果一个行为是因为程序员直接写入：

“遇到食物就向食物移动”

它不是进化出来的。

如果一个行为是：

随机初始策略
↓
遗传
↓
变异
↓
资源竞争
↓
选择
↓
长期稳定出现

那么它才是 evolved behavior。

项目必须尽可能记录这种区别。

------

# 33. 最终目标

最终希望得到这样的系统：

一个最初非常简单的数字生命群体，

没有：

预设智能

预设语言

预设社会

预设生态关系

只拥有：

遗传

变异

感知

行为

资源

能量

死亡

繁殖

环境变化

随着时间：

简单结构
↓
适应
↓
复杂行为
↓
生态位
↓
通信
↓
社会
↓
越来越复杂的遗传结构

如果这些复杂性能够自然出现，那么这个项目才真正实现 Artificial Life。

------

# 34. 当前执行规则

永远优先完成当前 Stage。

当前 Stage 未通过：

不要进入下一 Stage。

如果当前系统出现稳定性问题：

优先修复稳定性。

如果性能问题影响实验：

优先修复性能。

如果统计系统不足以证明进化：

优先增强观测能力。

如果没有证据证明某个行为是自然产生的：

不要声称它已经进化。

不要为了让结果“看起来更聪明”而修改规则。

科学实验优先于视觉效果。

可复现性优先于演示效果。

可观察性优先于复杂性。

简单机制优先于复杂模型。