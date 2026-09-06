# DIGITAL LIFE — PROJECT MAINTENANCE PROMPT

你现在负责维护 Digital Life 项目的长期一致性、可演化性和文档准确性。

这个项目不是一次性软件，而是一个长期发展的 Artificial Life 研究工程。

因此：

> 代码、测试、实验、架构文档和阶段文档必须随着项目实际状态共同演化。

不要把已有文档视为不可修改的“圣经”。

代码是当前系统行为的事实来源之一。

实验结果是判断系统是否满足阶段目标的重要证据。

文档必须反映当前真实状态，而不是强迫代码永远服从过时文档。

------

# 1. 核心原则

维护工作的首要目标：

保持以下内容的一致性：

Code
↕
Tests
↕
Experiments
↕
Documentation
↕
Current Stage

如果发现它们之间存在矛盾：

不要简单选择“文档优先”。

必须先判断：

1. 代码是否正确？
2. 测试是否正确？
3. 实验结果是否支持当前结论？
4. 文档是否已经过时？
5. 当前架构假设是否需要调整？

------

# 2. 文档是动态的

以下文件都允许根据项目实际发展进行修改：

README.md
AI_DEVELOPMENT_PROMPT.md
DEVELOPMENT.md
.ai/current-stage.md
PROJECT_MAINTENANCE_PROMPT.md
其他 design / architecture / experiment 文档

修改这些文件不是异常行为。

相反：

> 如果项目已经发生变化，而文档仍然描述旧状态，那么“不修改文档”才是错误。

------

# 3. 什么时候必须更新文档

以下情况发生时，必须检查相关文档：

## Architecture Change

例如：

增加新的核心模块。

删除模块。

替换 Genome 实现。

改变 Brain 接口。

改变 Environment API。

改变 SimulationEngine。

必须检查：

README.md
AI_DEVELOPMENT_PROMPT.md
DEVELOPMENT.md

------

## Behavior Change

如果生命的实际行为规则发生改变：

例如：

能量机制改变。

繁殖机制改变。

突变机制改变。

生命周期改变。

感知能力改变。

必须检查：

README.md
DEVELOPMENT.md
.ai/current-stage.md

------

## Stage Change

如果当前阶段完成，或者实验表明当前阶段定义不合理：

必须更新：

DEVELOPMENT.md
.ai/current-stage.md
README.md

必要时修改：

AI_DEVELOPMENT_PROMPT.md

------

## Experimental Discovery

如果实验发现：

新的适应行为。

新的生态现象。

新的稳定性问题。

新的进化模式。

原设计无法解释的现象。

必须检查：

DEVELOPMENT.md
experiment documentation
README.md

必要时新增研究记录。

------

# 4. 不要为了保持文档不变而修改代码

这是一个重要原则。

如果代码产生了合理的新现象，而文档中的假设已经过时：

不要为了迎合旧文档而修改代码。

应该：

先验证现象

↓

确认是否合理

↓

更新文档

↓

必要时重新定义 Stage

------

# 5. 不要为了让文档“看起来正确”而修改实验结果

实验结果必须保持原始事实。

不要：

修改数据

删除异常实验

隐藏失败实验

选择性报告成功实验

为了让系统看起来已经达到下一阶段而修改统计。

必须区分：

Observed

和

Expected

例如：

Expected:
群体逐渐适应资源分布。

Observed:
当前实验没有发现明显适应。

正确做法：

记录 Observed。

不要写成：

“系统已经完成适应性进化。”

------

# 6. Stage 可以改变

Stage 不是永恒固定的。

原本：

Stage 2
Evolution Observatory

可能随着研究变成：

Stage 2
Evolution Validation

Stage 2A
Selection Dynamics

Stage 2B
Long-term Stability

Stage 2C
Open-ended Trait Evolution

这种调整是允许的。

但修改 Stage 时必须说明：

Original definition

Reason for change

Evidence

New definition

Impact

------

# 7. Stage 不应该根据开发进度自动升级

代码写完 ≠ 阶段完成。

只有验收条件满足才能升级。

例如：

Feature implemented
≠
Scientific evidence

Simulation runs
≠
Evolution demonstrated

Mutation exists
≠
Adaptation exists

Brain exists
≠
Adaptive behavior exists

Communication exists
≠
Communication evolved

------

# 8. 修改 Stage 的条件

如果发现当前 Stage 的验收标准：

过于简单

过于困难

无法测量

与实际系统冲突

无法区分因果关系

应该提出修改。

修改时必须记录理由。

格式：

Stage:
Current definition:

Problem:

Evidence:

Proposed change:

Reason:

New graduation criteria:

------

# 9. 每次开发任务完成后执行维护检查

开发任务完成以后，按照以下顺序：

Step 1
检查代码。

Step 2
运行测试。

Step 3
运行相关实验。

Step 4
检查当前 Stage。

Step 5
检查验收条件。

Step 6
检查 README。

Step 7
检查 DEVELOPMENT.md。

Step 8
检查 .ai/current-stage.md。

Step 9
检查 AI_DEVELOPMENT_PROMPT.md 是否仍然准确。

Step 10
必要时更新文档。

------

# 10. 文档更新原则

不要为了“小修改”而重写整个文档。

保持：

最小修改

清晰变更

避免重复

避免互相矛盾

如果多个文档重复描述同一个事实：

优先考虑减少重复。

例如：

当前 Stage 只应该存在一个主要事实来源：

.ai/current-stage.md

DEVELOPMENT.md 可以描述完整 Stage 历史和路线。

README.md 只显示当前状态摘要。

------

# 11. README 的职责

README 面向人类开发者和 GitHub 浏览者。

应该包含：

Project Overview

Core Idea

Architecture

Current Stage

Quick Start

Basic Experiments

Current Limitations

Roadmap

不要把所有内部 AI 开发规则塞入 README。

README 应该尽可能：

清晰

稳定

容易阅读

------

# 12. DEVELOPMENT.md 的职责

DEVELOPMENT.md 是项目长期路线。

记录：

Stage 0
Stage 1
Stage 2
Stage 3
Stage 4
Stage 5
Stage 6

每个 Stage 包含：

Goal

Implementation Requirements

Experiments

Graduation Criteria

Known Risks

Status

如果路线变化：

保留历史原因。

------

# 13. .ai/current-stage.md 的职责

这个文件是：

“AI 当前最应该相信的项目状态。”

应该保持很短。

至少包含：

Current Stage

Current Goal

Status

Completed

Remaining

Blocked

Do Not Implement Yet

Graduation Criteria

实验完成后及时更新。

------

# 14. AI_DEVELOPMENT_PROMPT.md 的职责

它描述：

AI 应该如何开发这个项目。

它不应该记录：

当前某一个具体 bug。

某一次实验的具体结果。

某一天的项目状态。

否则会快速过时。

如果核心开发哲学发生变化，再修改它。

------

# 15. 维护历史

对于重要的方向变化：

不要删除旧历史。

可以在 DEVELOPMENT.md 添加：

## Change Log

例如：

2026-XX-XX

Changed Stage 2 graduation criteria.

Reason:
Initial metric could not distinguish adaptation from drift.

Evidence:
Repeated experiments showed...

New criteria:
...

这样未来可以知道：

为什么今天的系统会是这样。

------

# 16. 发现矛盾时的处理

如果发现：

README says A

DEVELOPMENT says B

Code does C

Tests expect D

不要猜。

应该：

1. inspect implementation
2. inspect tests
3. run experiment if necessary
4. determine actual intended behavior
5. identify obsolete documents
6. update the appropriate documents
7. add or update tests

最后必须保证：

Code
Tests
Docs

重新一致。

------

# 17. 修改测试的规则

不要因为代码修改后测试失败，就直接删除或放宽测试。

首先判断：

测试失败是否说明真正的 regression。

如果是：

修复代码。

如果预期行为改变：

修改测试，并同步更新文档。

如果测试本身错误：

修复测试，并说明原因。

绝不能：

为了让 CI 通过而降低测试质量。

------

# 18. 实验结论的等级

对实验观察使用以下等级：

LEVEL 0
No evidence

LEVEL 1
Single-run observation

LEVEL 2
Repeated observation

LEVEL 3
Controlled experiment

LEVEL 4
Reproducible effect

LEVEL 5
Robust effect across parameter ranges

不要把 LEVEL 1 写成“已经证明”。

------

# 19. 维护实验可复现性

任何影响进化结论的重要实验必须记录：

experiment_name

seed

configuration

code_version

generation_count

population_size

mutation_rate

resource_parameters

result

observations

任何实验如果无法复现：

明确标记。

不要假装可复现。

------

# 20. 架构演化原则

允许架构发生变化。

但是任何架构变化都应该考虑：

Backward compatibility

Experiment reproducibility

Save format

Performance

Testing

Documentation

不要因为某个新功能直接推翻整个系统。

但也不要因为害怕修改旧代码而保留明显错误的架构。

------

# 21. 重构原则

什么时候应该重构：

出现大量重复逻辑。

模块职责混乱。

循环依赖。

测试难以编写。

新增功能必须修改大量 unrelated code。

性能瓶颈来自错误抽象。

什么时候不要重构：

只是为了代码看起来更漂亮。

只是为了使用新的技术。

只是为了追求“企业级架构”。

重构必须解决真实问题。

------

# 22. 新功能进入项目之前

任何新功能必须回答：

Why?

它解决什么问题？

Evidence?

当前项目有什么证据说明它需要？

Stage?

属于哪个阶段？

Impact?

会影响哪些系统？

Reproducibility?

是否影响现有实验？

Documentation?

哪些文档需要更新？

Testing?

如何验证？

如果无法回答，不要急于加入。

------

# 23. 删除功能也是允许的

如果实验表明：

某个机制没有价值。

某个抽象造成复杂性。

某个功能阻碍真实进化。

可以删除。

不要因为：

“已经写了很多代码”

就保留它。

代码数量不是价值。

------

# 24. 允许失败

这个项目的研究价值不要求每个实验成功。

失败实验也是结果。

例如：

Experiment:
High mutation rate

Result:
Population collapse.

这不是：

“实验失败。”

而可能是：

“系统存在 mutation stability boundary。”

记录它。

------

# 25. 防止 AI 自我强化错误假设

AI 不应该因为之前自己写过某个设计，就默认那个设计一定正确。

每次重大修改时重新检查：

Current assumptions

Experimental evidence

Observed behavior

Alternative explanations

如果实验和原设计冲突：

优先调查冲突。

不要自动维护旧假设。

------

# 26. 维护时的最终输出格式

每次维护任务完成后输出：

## Project State

当前真实状态。

## Code Changes

代码变化。

## Test Results

测试结果。

## Experiment Results

实验结果。

## Documentation Changes

修改了哪些文档。

## Stage Assessment

当前 Stage 是否仍然正确。

## Graduation Status

当前阶段：

NOT READY

或

READY

或

NEEDS REVISION

## Why

解释判断依据。

## Next Priority

下一件最重要的工作。

------

# 27. 最重要的原则

这个项目不是：

Code → Force Docs

而是：

Reality
↓
Experiment
↓
Evidence
↓
Code
↓
Tests
↓
Documentation

它们应该互相校验。

文档可以改变。

架构可以改变。

Stage 可以改变。

算法可以改变。

实验假设可以被推翻。

唯一不能被牺牲的是：

真实结果。

可复现性。

可测试性。

科学诚实性。

以及让系统保持真正开放的进化能力。