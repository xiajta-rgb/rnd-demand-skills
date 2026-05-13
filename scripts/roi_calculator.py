"""
ROI 量化计算引擎
基于公式：ROI Score = Expected Value (Converted to Currency) / Resource Input (Man-Day Cost)

核心功能：
1. 价值货币化转换 - 将定性描述转为定量金额
2. 人天成本计算 - 根据资源投入估算成本
3. ROI 评分映射 - 将计算出的 ROI 转为 15 分制
"""

import re
from typing import Optional


class ROICalculator:
    """ROI 计算器"""

    # 默认人天成本（元/人天），可根据行业/地区调整
    DEFAULT_MAN_DAY_COST = 1500  # 元/人天

    # 效率提升价值系数
    EFFICIENCY_VALUE_COEFFICIENTS = {
        'efficiency_up': 0.6,   # 效率提升的价值系数
        'reduce': 0.8,          # 减少/降低的价值系数
        'error_reduce': 1.0     # 降低差错的价值系数
    }

    # 部门平均人力成本（元/月）
    DEPARTMENT_MONTHLY_COST = {
        '销售部': 15000,
        '财务部': 18000,
        '供应链': 16000,
        '技术部': 25000,
        '人力资源部': 14000,
        '市场部': 16000,
        '客服部': 12000,
        'default': 15000
    }

    def __init__(self, man_day_cost: int = None, value_coefficients: dict = None):
        """
        初始化 ROI 计算器
        
        Args:
            man_day_cost: 人天成本（元），默认 1500
            value_coefficients: 价值系数配置
        """
        self.man_day_cost = man_day_cost or self.DEFAULT_MAN_DAY_COST
        self.value_coefficients = value_coefficients or self.EFFICIENCY_VALUE_COEFFICIENTS
    
    def calculate_roi_score(self, demand: dict, nlp_features: dict = None) -> dict:
        """
        计算 ROI 评分
        
        Args:
            demand: 需求字典
            nlp_features: NLP 提取的特征
            
        Returns:
            ROI 计算结果
        """
        result = {
            'roi_ratio': 0,
            'annual_benefit': 0,
            'total_cost': 0,
            'score': 0,
            'level': 'unknown',
            'details': {}
        }
        
        # 1. 计算总成本
        total_cost = self._calculate_cost(demand)
        result['total_cost'] = total_cost
        result['details']['man_months'] = total_cost / self.man_day_cost / 22 if total_cost > 0 else 0
        
        # 2. 计算预期收益
        annual_benefit = self._calculate_benefit(demand, nlp_features)
        result['annual_benefit'] = annual_benefit
        
        # 3. 计算 ROI
        if total_cost > 0:
            roi_ratio = annual_benefit / total_cost
        else:
            roi_ratio = 0
        result['roi_ratio'] = round(roi_ratio, 2)
        
        # 4. 映射到 15 分制
        score = self._map_roi_to_score(roi_ratio)
        result['score'] = score
        
        # 5. 确定等级
        result['level'] = self._determine_level(roi_ratio)
        
        return result
    
    def _calculate_cost(self, demand: dict) -> float:
        """计算需求总成本"""
        resource_input = demand.get('resource_input', '')
        if not resource_input:
            return 0
        
        # 解析资源投入
        total_man_days = 0
        
        # 匹配 "X人月"
        match = re.search(r'(\d+)\s*人\s*月', resource_input)
        if match:
            months = int(match.group(1))
            total_man_days += months * 22  # 平均每月 22 个工作日
        
        # 匹配 "X人天"
        match = re.search(r'(\d+)\s*人\s*天', resource_input)
        if match:
            days = int(match.group(1))
            total_man_days += days
        
        # 匹配 "X人周"
        match = re.search(r'(\d+)\s*人\s*周', resource_input)
        if match:
            weeks = int(match.group(1))
            total_man_days += weeks * 5
        
        # 匹配金额（万元）
        match = re.search(r'(\d+)\s*万', resource_input)
        if match:
            amount = int(match.group(1)) * 10000
            # 金额直接返回成本
            return amount
        
        return total_man_days * self.man_day_cost
    
    def _calculate_benefit(self, demand: dict, nlp_features: dict = None) -> float:
        """计算年度预期收益"""
        expected_value = demand.get('expected_value', '')
        if not expected_value:
            return 0
        
        total_benefit = 0
        
        # 1. 提取量化指标
        efficiency_matches = re.findall(r'提升\s*(\d+)\s*%', expected_value)
        for pct in efficiency_matches:
            pct_val = int(pct)
            # 假设效率提升带来的人力节省
            benefit = self._estimate_efficiency_benefit(pct_val, demand)
            total_benefit += benefit
        
        reduce_matches = re.findall(r'减少\s*(\d+)\s*%|降低\s*(\d+)\s*%|节省\s*(\d+)\s*%', expected_value)
        for match in reduce_matches:
            pct_val = int(max([m for m in match if m], default=0))
            benefit = self._estimate_reduce_benefit(pct_val, demand)
            total_benefit += benefit
        
        # 2. 使用 NLP 特征（如果有）
        if nlp_features and nlp_features.get('efficiency_metrics'):
            metrics = nlp_features['efficiency_metrics']
            if metrics.get('efficiency_up_percent') and metrics['efficiency_up_percent'] > 0:
                benefit = self._estimate_efficiency_benefit(metrics['efficiency_up_percent'], demand)
                total_benefit = max(total_benefit, benefit)  # 取最大值，避免重复计算
        
        return round(total_benefit, 2)
    
    def _estimate_efficiency_benefit(self, efficiency_pct: int, demand: dict) -> float:
        """估算效率提升带来的收益"""
        # 基础人力成本
        base_cost = self._estimate_base_cost(demand)
        
        # 效率提升收益 = 基础成本 × 效率提升比例 × 系数
        benefit = base_cost * (efficiency_pct / 100) * self.value_coefficients['efficiency_up']
        
        # 年化收益（假设效率提升持续 12 个月）
        return benefit * 12
    
    def _estimate_reduce_benefit(self, reduce_pct: int, demand: dict) -> float:
        """估算减少/降低带来的收益"""
        base_cost = self._estimate_base_cost(demand)
        
        benefit = base_cost * (reduce_pct / 100) * self.value_coefficients['reduce']
        
        return benefit * 12
    
    def _estimate_base_cost(self, demand: dict) -> float:
        """估算基础人力成本"""
        # 从需求描述中提取涉及的部门
        departments = []
        dept_keywords = {
            '销售部': ['销售', '业务', '客户'],
            '财务部': ['财务', '对账', '报销'],
            '供应链': ['供应链', '物流', '采购'],
            '技术部': ['技术', '研发', '系统'],
            '客服部': ['客服', '售后', '服务']
        }
        
        full_text = " ".join([
            str(demand.get('description', '')),
            str(demand.get('usage_scenario', '')),
            str(demand.get('cross_department_impact', ''))
        ])
        
        for dept, keywords in dept_keywords.items():
            for kw in keywords:
                if kw in full_text:
                    departments.append(dept)
                    break
        
        # 计算总人力成本
        if not departments:
            return self.DEPARTMENT_MONTHLY_COST['default']
        
        total_cost = sum(self.DEPARTMENT_MONTHLY_COST.get(d, self.DEPARTMENT_MONTHLY_COST['default']) 
                        for d in set(departments))
        
        return total_cost
    
    def _map_roi_to_score(self, roi_ratio: float) -> int:
        """将 ROI 比率映射到 15 分制"""
        if roi_ratio >= 3.0:
            return 14  # ROI≥3:1，高分
        elif roi_ratio >= 2.0:
            return 12  # ROI在2:1-3:1之间
        elif roi_ratio >= 1.0:
            return 10  # ROI在1:1-2:1之间
        elif roi_ratio >= 0.5:
            return 7   # ROI<1:1，但有一定收益
        else:
            return 3   # 投入产出严重失衡
    
    def _determine_level(self, roi_ratio: float) -> str:
        """确定 ROI 等级"""
        if roi_ratio >= 3.0:
            return 'excellent'
        elif roi_ratio >= 1.5:
            return 'good'
        elif roi_ratio >= 0.8:
            return 'acceptable'
        else:
            return 'poor'
    
    def format_report(self, roi_result: dict) -> str:
        """格式化 ROI 报告"""
        parts = [
            f"ROI 分析报告",
            f"=" * 40,
            f"预期年度收益: ¥{roi_result['annual_benefit']:,.0f}",
            f"预估总成本:   ¥{roi_result['total_cost']:,.0f}",
            f"ROI 比率:     {roi_result['roi_ratio']}:1",
            f"ROI 等级:     {roi_result['level']}",
            f"评分:         {roi_result['score']}/15",
            f""
        ]
        
        if roi_result['roi_ratio'] >= 3:
            parts.append("✓ 高回报项目，建议优先投入")
        elif roi_result['roi_ratio'] >= 1:
            parts.append("✓ 合理回报，建议纳入评审")
        elif roi_result['roi_ratio'] >= 0.5:
            parts.append("⚠ 回报较低，需进一步评估")
        else:
            parts.append("✗ 投入产出失衡，建议暂缓")
        
        return "\n".join(parts)


def calculate_demand_roi(demand: dict, nlp_features: dict = None, man_day_cost: int = None) -> dict:
    """
    便捷函数：计算单个需求的 ROI
    
    Args:
        demand: 需求字典
        nlp_features: NLP 特征
        man_day_cost: 人天成本
        
    Returns:
        ROI 计算结果
    """
    calc = ROICalculator(man_day_cost)
    return calc.calculate_roi_score(demand, nlp_features)


if __name__ == '__main__':
    test_demands = [
        {
            'id': 'D001',
            'description': '跨部门订单数据同步系统开发',
            'usage_scenario': '供应链、销售、财务跨部门数据协同',
            'expected_value': '减少数据重复录入，提升30%对账效率，降低5%财务差错率',
            'cross_department_impact': '供应链、销售、财务3个部门',
            'resource_input': '2人月开发资源',
        },
        {
            'id': 'D002',
            'description': '个人操作界面按钮位置调整',
            'usage_scenario': '仅个人操作习惯优化',
            'expected_value': '无业务效率提升',
            'resource_input': '0.5人天',
        }
    ]
    
    calc = ROICalculator()
    
    for d in test_demands:
        result = calc.calculate_roi_score(d)
        print(calc.format_report(result))
        print()
