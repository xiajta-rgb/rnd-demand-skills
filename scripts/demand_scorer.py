"""
需求智能评分引擎 v4 - LLM 辅助版
使用 LLM 语义理解 + 规则约束进行精确评分
"""

import yaml
from datetime import datetime
from typing import Optional


class DemandScorer:
    """需求评分器 v4 - LLM 辅助"""
    
    def __init__(self, rules_path: str = None):
        if rules_path is None:
            import os
            rules_path = os.path.join(os.path.dirname(__file__), '..', 'rules', 'demand_scoring_rules.yaml')
        
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        
        self.dimensions = self.rules['dimensions']
        self.grade_rules = self.rules['grade_rules']
    
    def _build_scoring_prompt(self, demand: dict, strategy_focus: list = None) -> str:
        """构建评分提示词"""
        return f"""你是一个专业的需求评审专家。请根据以下评分规则对需求进行评分。

## 需求信息
- 需求ID: {demand.get('id', 'unknown')}
- 需求描述: {demand.get('description', '')}
- 使用场景: {demand.get('usage_scenario', '')}
- 预期价值: {demand.get('expected_value', '')}
- 跨部门影响: {demand.get('cross_department_impact', '')}
- 资源投入: {demand.get('resource_input', '')}
- 截止风险: {demand.get('deadline_risk', '')}
{f'- 战略重点: {", ".join(strategy_focus)}' if strategy_focus else ''}

## 评分规则
### 1. 业务价值 (25分)
- 21-25分: 显著提升收入/降本（≥10%），或解决核心业务痛点
- 16-20分: 提升效率/降低差错（≥20%），或解决重要业务环节问题
- 11-15分: 局部优化，效率提升<20%，或解决非核心痛点
- 0-10分: 无明确业务价值，或仅个人习惯优化

### 2. 战略匹配度 (20分)
- 17-20分: 完全匹配公司当前核心战略重点
- 13-16分: 部分匹配战略方向，支持部门级重点目标
- 9-12分: 与战略方向无直接冲突，但无明显匹配度
- 0-8分: 与公司战略重点无关

### 3. 影响范围 (15分)
- 13-15分: 影响3个及以上部门/业务链路
- 9-12分: 影响2个部门/多个岗位
- 5-8分: 仅影响单个部门的1-2个岗位
- 0-4分: 仅个人使用，无跨岗位/跨部门影响

### 4. 投入产出比 (15分)
- 13-15分: 低资源投入，高预期收益，ROI≥3:1
- 9-12分: 资源投入合理，收益明确，ROI在1:1-3:1之间
- 5-8分: 资源投入较高，收益一般，ROI<1:1
- 0-4分: 资源投入高，无明确收益预期

### 5. 紧急程度 (15分)
- 13-15分: 存在明确合规/履约/客户风险，或有刚性时间节点要求
- 9-12分: 影响业务正常推进，有较明确的时间要求
- 5-8分: 无明确时间压力，属于可延后优化项
- 0-4分: 无紧急性，属于长期优化或非必要需求

### 6. 实施复杂度 (10分，反向计分)
- 8-10分: 技术实现简单，无跨部门依赖，可快速落地
- 5-7分: 实现难度中等，依赖可控，无重大风险
- 2-4分: 实现难度较高，存在跨部门协同成本
- 0-1分: 实现难度极高，依赖复杂，存在技术瓶颈

## 输出格式
请以JSON格式输出评分结果，格式如下：
{{
  "business_value": {{ "score": 分数, "reason": "评分理由" }},
  "strategy_alignment": {{ "score": 分数, "reason": "评分理由" }},
  "impact_scope": {{ "score": 分数, "reason": "评分理由" }},
  "roi": {{ "score": 分数, "reason": "评分理由" }},
  "urgency": {{ "score": 分数, "reason": "评分理由" }},
  "implementation_complexity": {{ "score": 分数, "reason": "评分理由" }}
}}

请仔细分析需求内容，严格按照评分规则给出分数。
"""

    def _parse_llm_score(self, response: str) -> dict:
        """解析 LLM 评分结果"""
        import json
        import re
        
        # 提取 JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return None
        
        try:
            return json.loads(json_match.group())
        except:
            return None
    
    def score_demand(self, demand: dict, strategy_focus: list = None) -> dict:
        """
        对单个需求进行完整评分（由 AI Agent 调用时执行）
        
        注意：此方法在脚本中返回占位符，实际评分由 AI Agent 基于提示词执行。
        """
        # 构建评分提示词
        prompt = self._build_scoring_prompt(demand, strategy_focus)
        
        # 返回提示词供 AI Agent 使用
        return {
            'id': demand.get('id', 'unknown'),
            'description': demand.get('description', ''),
            'submitter': demand.get('submitter', ''),
            'scoring_prompt': prompt,
            'note': '请将此提示词发送给 AI 进行评分，然后使用 parse_llm_score() 解析结果'
        }
    
    def score_batch(self, demands: list, strategy_focus: list = None) -> list:
        """批量评分"""
        results = []
        for demand in demands:
            result = self.score_demand(demand, strategy_focus)
            results.append(result)
        
        return results


def auto_score_demand(demands: list, rules_path: str = None, strategy_focus: list = None) -> dict:
    """便捷函数：自动对需求列表进行评分"""
    scorer = DemandScorer(rules_path)
    scored_demands = scorer.score_batch(demands, strategy_focus)
    
    return {
        'scored_demands': scored_demands,
        'stats': {
            'total': len(scored_demands),
            'note': '实际评分需由 AI Agent 执行'
        },
        'scoring_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == '__main__':
    # 示例：展示如何构建评分提示词
    test_demand = {
        'id': 'D001',
        'description': '跨部门订单数据同步系统开发',
        'submitter': '研发-张三',
        'usage_scenario': '供应链、销售、财务跨部门数据协同',
        'expected_value': '减少数据重复录入，提升30%对账效率，降低5%财务差错率',
        'cross_department_impact': '供应链、销售、财务3个部门',
        'resource_input': '2人月开发资源',
        'deadline_risk': '无刚性时间节点，为年度战略重点项目'
    }
    
    scorer = DemandScorer()
    result = scorer.score_demand(test_demand, strategy_focus=['跨部门数据协同', '运营效率提升'])
    
    print("=== 评分提示词（供 AI Agent 使用） ===\n")
    print(result['scoring_prompt'])
