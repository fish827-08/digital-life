# Digital Life Rules

这个项目不是一个预先设计好的游戏。

它是一个人工生命实验。

程序员只定义：

1. 物理规则
2. 能量规则
3. 感知规则
4. 行为接口
5. 遗传规则
6. 变异规则
7. 生命周期
8. 繁殖机制
9. 环境变化

程序员不直接定义：

- 什么生命最优秀
- 什么生命最聪明
- 什么生命应该成为捕食者
- 什么生命应该合作
- 什么生命应该形成社会
- 什么生命应该产生语言
- 什么生命最终应该变成什么

让环境和进化决定。

核心循环：

WORLD
↓
SENSOR
↓
BRAIN
↓
ACTION
↓
ENERGY
↓
SURVIVAL
↓
REPRODUCTION
↓
MUTATION
↓
NEW ORGANISM
↓
WORLD

所有模块必须保持低耦合。

任何未来模块，例如：

Neural Network
Memory
Communication
Gene Expression
Cultural Evolution
Multi-cellularity
Open-ended Evolution

都应该能够作为插件或替代实现加入，而不是推翻核心架构。

优先保证：

可复现性
可测试性
可观测性
可扩展性
性能

不要为了“看起来智能”而提前加入 LLM。

首先证明最简单的规则能够产生可观察的进化。