"""全局配置：所有数值参数集中于此，用 Pydantic 强力校验。

设计要点（架构层契约）：
1. 配置即复现（原则 8）：`seed` + 其余参数唯一决定一次模拟；
   保存/恢复、回归测试都从"同一份配置 + 同一种子"开始。
2. 模块间只通过配置传递数值参数，不散落魔法数字；
   后续替换子系统（感知/神经/基因表达）时只改参数与对应模块，
   其余模块不感知（原则 4、6）。
3. 这里只放"金额/参数"类数值；"结构/契约"类决策（如基因→性状的
   映射关系）放在对应领域模块（core/genetics.py），保持可替换性。
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorldConfig(BaseModel):
    """世界几何与边界规则。"""

    width: int = Field(default=128, ge=8, description="网格宽(列数)")
    height: int = Field(default=128, ge=8, description="网格高(行数)")
    wrap: bool = Field(
        default=True,
        description="环形边界(torus)：左右、上下相连，消除边界效应。",
    )


class ResourceConfig(BaseModel):
    """基础资源规则：每格资源存量与再生速率。"""

    capacity: float = Field(default=1.0, gt=0.0, description="每格资源上限")
    initial_fill: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="初始填充比例（乘以 capacity 得到每格初始资源量）",
    )
    regrowth_rate: float = Field(
        default=0.02,
        ge=0.0,
        description="每 tick 每格资源再生量（不超过 capacity）",
    )
    patchiness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="初始资源空间异质性：0=全场均匀；>0 时按块随机调整初始填充率"
        "（块间差异幅度 = ±patchiness×initial_fill）",
    )
    patch_count: int = Field(
        default=4,
        ge=1,
        description="异质分块密度（每边块数，patchiness>0 时生效）",
    )


class OrganismConfig(BaseModel):
    """个体能量收支与生命周期参数。

    默认值按"中位个体可持续生存"标定（可演化的生态而非必死局）：
    静态收支 = 摄入(eat_amount×efficiency=1.5) − 代谢(0.6) − 平均移动(0.5×0.4=0.2)
    约 +0.7/tick，允许能量缓慢积累到繁殖阈值（75）——生存可行、
    生存者优先生殖，构成真正的选择压（原则 1/2/3）。
    """

    initial_energy: float = Field(default=60.0, gt=0.0, description="新生个体的起始能量")
    max_energy: float = Field(default=300.0, gt=0.0, description="能量上限，多余能量溢出丢弃")
    base_metabolism: float = Field(default=0.6, gt=0.0, description="每 tick 基础代谢消耗")
    move_cost: float = Field(default=0.4, gt=0.0, description="移动一格的能量消耗")
    eat_amount: float = Field(default=0.5, gt=0.0, description="每 tick 进食量上限（单位格资源）")
    eat_efficiency: float = Field(default=3.0, gt=0.0, description="每单位食物转化为能量的倍率")

    @model_validator(mode="after")
    def _check_energy_bounds(self) -> "OrganismConfig":
        if self.initial_energy >= self.max_energy:
            raise ValueError("initial_energy 必须小于 max_energy")
        return self


class GenomeConfig(BaseModel):
    """基因底物参数：定长连续基因链 + 变异/交叉。"""

    gene_count: int = Field(default=16, ge=1, description="基因数量（定长基因链）")
    gene_min: float = Field(default=0.0, description="基因取值下限")
    gene_max: float = Field(default=1.0, gt=0.0, description="基因取值上限")
    mutation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="单基因发生变异的概率（每个子代、每个基因）",
    )
    mutation_sigma: float = Field(
        default=0.05,
        gt=0.0,
        description="连续基因震荡幅度，以基因区间宽度为基准（标准差）",
    )
    crossover_rate: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="繁殖时发生单点交叉的概率",
    )

    @model_validator(mode="after")
    def _check_gene_range(self) -> "GenomeConfig":
        if self.gene_max <= self.gene_min:
            raise ValueError("gene_max 必须大于 gene_min")
        return self


class PopulationConfig(BaseModel):
    """种群规模参数。"""

    initial_count: int = Field(default=200, ge=1, description="初始个体数量")
    max_count: int = Field(
        default=2000,
        ge=1,
        description="种群硬上限（防御性上限，防止资源无限时进程失控）",
    )

    @model_validator(mode="after")
    def _check_limits(self) -> "PopulationConfig":
        if self.max_count < self.initial_count:
            raise ValueError("max_count 必须大于等于 initial_count")
        return self


class SimulationConfig(BaseModel):
    """引擎运行参数：主循环时长与终止条件。"""

    ticks: int = Field(
        default=1000,
        ge=1,
        description="计划运行的最大 tick 数（种群提前归零则按终止条件提前停）",
    )
    stop_on_extinction: bool = Field(
        default=True,
        description="种群归零时提前停止（灭绝防护）；False 则继续空转，便于对接外部注入/迁移",
    )
    log_interval: int = Field(
        default=50,
        ge=0,
        description="无头模式进度打印间隔（tick 数）；0 = 从不打印进度",
    )
    history_limit: int = Field(
        default=0,
        ge=0,
        description="全程统计历史（TickStats 序列）保留上限（tick 数）；"
        "0 = 无限保留（默认，保持 Stage 1 语义）。>0 时引擎改为环形保留近期尾部，"
        "并同时维护运行期累计（total_born / total_died / 死因汇总不受裁剪影响），"
        "供超长实验（百万 tick 级）避免无界内存增长。",
    )


class SimConfig(BaseModel):
    """顶层配置：唯一事实来源，决定一次完整模拟。"""

    seed: int | None = Field(
        default=42,
        description="随机数种子；None 表示用系统熵（结果不可复现）",
    )
    world: WorldConfig = Field(default_factory=WorldConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    organisms: OrganismConfig = Field(default_factory=OrganismConfig)
    genome: GenomeConfig = Field(default_factory=GenomeConfig)
    population: PopulationConfig = Field(default_factory=PopulationConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)

    # ---- 可复现性辅助：配置 ⇄ dict / json -----------------------------
    def to_dict(self) -> dict[str, Any]:
        """导出为 JSON 安全 dict（存档时随状态一并保存）。"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimConfig":
        return cls.model_validate(data)

    def fingerprint(self) -> str:
        """配置的规范字符串；两份配置可比较是否完全一致（排查复现偏差用）。"""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)