"""
动态阈值引擎
根据资源水位、战略周期、组织状态自动调节评分分级阈值

核心功能：
1. 资源水位调节 - 排期满时提高准入门槛
2. 战略周期适配 - 不同季度侧重不同
3. 组织弹性策略 - 根据团队状态调整
"""

from datetime import datetime
from typing import Optional


class DynamicThresholdManager:
    """动态阈值管理器"""

    def __init__(self, config: dict = None):
        """
        初始化动态阈值
        
        Args:
            config: 阈值配置字典
        """
        self.base_thresholds = {
            'A': 80,
            'B': 60,
            'C': 40,
            'D': 0
        }
        
        self.config = config or {}
        self.adjustments = []
    
    def get_current_thresholds(self) -> dict:
        """
        获取当前调整后的阈值
        
        Returns:
            调整后的分级阈值字典
        """
        thresholds = self.base_thresholds.copy()
        total_adjustment = 0
        
        # 1. 资源水位调整
        resource_adjustment = self._calculate_resource_adjustment()
        total_adjustment += resource_adjustment
        if resource_adjustment != 0:
            self.adjustments.append({
                'type': 'resource_watermark',
                'value': resource_adjustment,
                'reason': self.config.get('resource_status', {}).get('reason', '资源水位调节')
            })
        
        # 2. 战略周期调整
        strategy_adjustment = self._calculate_strategy_adjustment()
        total_adjustment += strategy_adjustment
        if strategy_adjustment != 0:
            self.adjustments.append({
                'type': 'strategy_cycle',
                'value': strategy_adjustment,
                'reason': self.config.get('strategy_cycle', {}).get('reason', '战略周期调节')
            })
        
        # 3. 特殊时期调整
        special_adjustment = self._calculate_special_adjustment()
        total_adjustment += special_adjustment
        if special_adjustment != 0:
            self.adjustments.append({
                'type': 'special_period',
                'value': special_adjustment,
                'reason': self.config.get('special_period', {}).get('reason', '特殊时期调节')
            })
        
        # 应用调整
        thresholds['A'] = max(60, min(95, self.base_thresholds['A'] + total_adjustment))
        thresholds['B'] = max(45, min(80, self.base_thresholds['B'] + total_adjustment * 0.8))
        thresholds['C'] = max(30, min(55, self.base_thresholds['C'] + total_adjustment * 0.5))
        
        return thresholds
    
    def _calculate_resource_adjustment(self) -> float:
        """根据资源水位计算调整值"""
        resource_status = self.config.get('resource_status', {})
        utilization = resource_status.get('current_utilization', 0.7)
        
        if utilization >= 0.95:
            return 10  # 极紧，大幅提高门槛
        elif utilization >= 0.90:
            return 5   # 紧张，适度提高门槛
        elif utilization >= 0.80:
            return 2   # 较满，小幅提高门槛
        elif utilization <= 0.50:
            return -3  # 宽松，适度降低门槛
        elif utilization <= 0.30:
            return -5  # 空闲，显著降低门槛
        
        return 0
    
    def _calculate_strategy_adjustment(self) -> float:
        """根据战略周期计算调整值"""
        strategy_cycle = self.config.get('strategy_cycle', {})
        phase = strategy_cycle.get('phase', 'normal')
        
        phase_adjustments = {
            'startup': 0,      # 创业期，降低门槛
            'growth': -2,      # 成长期，鼓励创新
            'mature': 3,       # 成熟期，严格把关
            'transformation': 0,  # 转型期，保持标准
            'normal': 0        # 常规期
        }
        
        return phase_adjustments.get(phase, 0)
    
    def _calculate_special_adjustment(self) -> float:
        """特殊时期调整"""
        special = self.config.get('special_period', {})
        if special.get('is_frozen', False):
            return 15  # 冻结期，大幅提高门槛
        elif special.get('is_sprint', False):
            return -2  # 冲刺期，略微降低门槛
        
        return 0
    
    def grade_demand(self, score: float) -> dict:
        """
        根据动态阈值定级
        
        Args:
            score: 需求总分
            
        Returns:
            定级结果
        """
        thresholds = self.get_current_thresholds()
        
        if score >= thresholds['A']:
            grade = 'A'
        elif score >= thresholds['B']:
            grade = 'B'
        elif score >= thresholds['C']:
            grade = 'C'
        else:
            grade = 'D'
        
        return {
            'score': score,
            'grade': grade,
            'thresholds_used': thresholds,
            'adjustments_applied': self.adjustments
        }
    
    def explain_adjustments(self) -> str:
        """生成调整说明文本"""
        if not self.adjustments:
            return "当前使用标准阈值，无特殊调整。"
        
        parts = ["当前阈值调整说明："]
        for adj in self.adjustments:
            direction = "上调" if adj['value'] > 0 else "下调"
            parts.append(f"- {adj['reason']}: A级门槛{direction}{abs(adj['value'])}分")
        
        thresholds = self.get_current_thresholds()
        parts.append(f"\n调整后阈值：A级≥{thresholds['A']:.0f}分，B级≥{thresholds['B']:.0f}分，C级≥{thresholds['C']:.0f}分")
        
        return "\n".join(parts)


def create_threshold_manager(
    resource_utilization: float = 0.7,
    strategy_phase: str = 'normal',
    is_frozen: bool = False,
    is_sprint: bool = False,
    resource_reason: str = None,
    strategy_reason: str = None,
    special_reason: str = None
) -> DynamicThresholdManager:
    """
    便捷函数：创建阈值管理器
    
    Args:
        resource_utilization: 当前资源利用率（0-1）
        strategy_phase: 战略阶段（startup/growth/mature/transformation/normal）
        is_frozen: 是否冻结期
        is_sprint: 是否冲刺期
        resource_reason: 资源调整原因
        strategy_reason: 战略调整原因
        special_reason: 特殊调整原因
        
    Returns:
        阈值管理器实例
    """
    config = {
        'resource_status': {
            'current_utilization': resource_utilization,
            'reason': resource_reason or f'当前资源利用率{resource_utilization*100:.0f}%'
        },
        'strategy_cycle': {
            'phase': strategy_phase,
            'reason': strategy_reason or f'当前处于{strategy_phase}阶段'
        },
        'special_period': {
            'is_frozen': is_frozen,
            'is_sprint': is_sprint,
            'reason': special_reason or ('冻结期' if is_frozen else ('冲刺期' if is_sprint else '常规期'))
        }
    }
    
    return DynamicThresholdManager(config)


if __name__ == '__main__':
    print("=== 场景 1: 资源极度紧张（95%利用率） ===")
    mgr1 = create_threshold_manager(resource_utilization=0.95, resource_reason="本月研发排期已满95%")
    thresholds1 = mgr1.get_current_thresholds()
    print(f"阈值: A≥{thresholds1['A']:.0f}, B≥{thresholds1['B']:.0f}, C≥{thresholds1['C']:.0f}")
    result1 = mgr1.grade_demand(82)
    print(f"82分定级: {result1['grade']}")
    print(mgr1.explain_adjustments())
    
    print("\n=== 场景 2: 资源空闲（30%利用率） ===")
    mgr2 = create_threshold_manager(resource_utilization=0.30, resource_reason="本月研发排期仅30%")
    thresholds2 = mgr2.get_current_thresholds()
    print(f"阈值: A≥{thresholds2['A']:.0f}, B≥{thresholds2['B']:.0f}, C≥{thresholds2['C']:.0f}")
    result2 = mgr2.grade_demand(75)
    print(f"75分定级: {result2['grade']}")
    print(mgr2.explain_adjustments())
    
    print("\n=== 场景 3: 冻结期 ===")
    mgr3 = create_threshold_manager(is_frozen=True, resource_reason="年度预算冻结")
    thresholds3 = mgr3.get_current_thresholds()
    print(f"阈值: A≥{thresholds3['A']:.0f}, B≥{thresholds3['B']:.0f}, C≥{thresholds3['C']:.0f}")
    result3 = mgr3.grade_demand(85)
    print(f"85分定级: {result3['grade']}")
    print(mgr3.explain_adjustments())
