"""Observatory：演化观测层（Stage 2 — Evolution Observatory）。

只做"观测与统计"，不做任何决策/推断：
- statistics：纯函数统计聚合（trait 分布 / 基因组多样性 / 谱系）
- observer：以世代为轴的系统采样（generation-level statistics）
- experiment：确定性实验调度（5 类实验矩阵）
不引入 LLM / NN / 人工 fitness / 物种分类（阶段红线）。
"""