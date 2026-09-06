# Current Stage — 当前阶段状态

> 本文件是"AI 当前最应该相信的项目状态"的唯一事实来源（PROJECT_MAINTENANCE_PROMPT §13）。
> 实验完成后及时更新。完整实验细节见 `RESEARCH.md`。

## Current Stage

**Stage 2 — Evolution Observatory**（毕业评估：READY，2026-09-06）

## Current Goal

证明"环境选择压力导致群体统计特征发生稳定、可解释、可重复的跨世代变化"这一毕业条件，并将其归档为研究记录。

## Status

- Stage 2 验收标准已由对照矩阵（R-2）+ 万代基线（R-1）共同满足；
- VecEngine 性能重构完成（SoA 数组化，~20× 提速），万代实验已重跑通过（19 min / 13.3M tick / 10,000 代）。

## Completed

- [x] Stage 0–1 全部验收（139+ 测试基线）
- [x] Stage 2 可观测性：EvolutionObserver / EvolutionStatistics / ExperimentRunner / headless CLI
- [x] Stage 2 五类实验：baseline / resource_pressure / resource_distribution / mutation_rate / repeated_seeds
- [x] 10,000 代长程实验（VecEngine，s2_10k/baseline，finished_normally）
- [x] 全量回归 151 项通过
- [x] 毕业评估归档（RESEARCH.md R-1/R-2）

## Remaining

- 万代级跨 seed 重复实验（3 × 10,000 代，VecEngine 下 ~1 小时），补强 X≠Y 的万代维度（推荐，非必须）
- 资源分布形态（集中/分散/丰歉）长世代验证（1,000+ 代），区分"分布慢变量"与"无效应"（未验证假设）
- 收敛到基因边界的安全性验证（更高 gene_max 区分 ESS vs 边界截断）

## Blocked

- 无

## Do Not Implement Yet

- Brain / Sensor（Stage 3）——须通过 Stage 2 正式验收交接后再开始
- LLM / 人工 fitness / 预设物种类别（全程禁止，见 README）
- 复杂 GUI；实验层保持 headless

## Graduation Criteria（Stage 2）

> 在不人为指定目标性状的情况下，环境变化能够导致群体统计特征发生稳定、可解释、可重复的变化，且 X ≠ Y 可由生存/繁殖成功解释。

**Status: READY**（2026-09-06 评估；证据：mutation 梯度多样性 0.30/0.53/0.70 单调、资源临界→灭绝、资源低压→种群 76；万代稳态 1 万代不漂移；repeated seeds 3 次一致；详见 RESEARCH.md）

## 验收交接提示（进入 Stage 3 前）

1. 确认 Stage 2 毕业状态记录入本文件与 RESEARCH.md；
2. 更新 README 当前阶段摘要（如从"Stage 2"改为"Stage 3 准备"）；
3. 按 AI_DEVELOPMENT_PROMPT §14 定义 Sensor/Brain 接口后开始 Stage 3。