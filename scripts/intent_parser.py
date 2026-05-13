"""
NLP 意图解析引擎
从原始需求文本中自动提取特征，智能补全缺失字段，辅助评分决策

核心功能：
1. 关键词特征提取 - 自动识别紧急/高风险关键词
2. 价值量化推断 - 从描述中提取可量化指标
3. 部门影响推断 - 识别跨部门协同关系
4. 资源投入估算 - 根据复杂度推断人天
"""

import re
from typing import Optional


class IntentParser:
    """意图解析器 - 从原始文本中提取评分特征"""

    # 紧急程度关键词库
    URGENCY_KEYWORDS = {
        'critical': ['崩溃', '宕机', '瘫痪', '中断', '故障', '失效', '不可用', '事故', '紧急', '立刻', '马上'],
        'high': ['合规', '风险', '审计', '监管', '处罚', '违约', '客户流失', '投诉', '截止', '到期', '限期'],
        'medium': ['影响', '延迟', '瓶颈', '阻塞', '积压', '堆积', '影响进度'],
        'low': ['优化', '改善', '体验', '升级', '重构', '整理', '归档']
    }

    # 价值类型关键词
    VALUE_KEYWORDS = {
        'revenue': ['收入', '营收', '销售额', '变现', '转化', '订单', '客户增长', '市场占有率'],
        'cost_saving': ['降本', '节省', '减少投入', '降低', '减少人力', '自动化', '替代人工'],
        'efficiency': ['效率', '提速', '加速', '缩短', '提升', '优化', '减少耗时'],
        'quality': ['差错', '错误率', '准确性', '质量', '稳定性', '可靠性', '故障率']
    }

    # 部门识别词库
    DEPARTMENT_KEYWORDS = {
        '销售部': ['销售', '业务', '客户', '签单', '合同', '渠道', '代理商'],
        '财务部': ['财务', '资金', '预算', '报销', '对账', '发票', '税务'],
        '供应链': ['供应链', '物流', '仓储', '采购', '库存', '发货'],
        '技术部': ['技术', '研发', '开发', '架构', '运维', '系统'],
        '人力资源部': ['人事', '招聘', '培训', '绩效', '员工'],
        '市场部': ['市场', '品牌', '推广', '营销', '活动'],
        '客服部': ['客服', '售后', '服务', '投诉', '反馈']
    }

    # 资源投入模式匹配
    RESOURCE_PATTERNS = [
        (r'(\d+)\s*人\s*月', 'man_month'),
        (r'(\d+)\s*人\s*天', 'man_day'),
        (r'(\d+)\s*人周', 'man_week'),
        (r'(\d+)\s*人年', 'man_year'),
        (r'(\d+)\s*万', 'money_wan'),
        (r'(\d+)\s*千', 'money_qian'),
    ]

    # 效率提升模式匹配
    EFFICIENCY_PATTERNS = [
        (r'提升\s*(\d+)\s*%', 'efficiency_up'),
        (r'提[昇升高]\s*(\d+)\s*%', 'efficiency_up'),
        (r'减少\s*(\d+)\s*%', 'reduce'),
        (r'降低\s*(\d+)\s*%', 'reduce'),
        (r'节省\s*(\d+)\s*%', 'reduce'),
        (r'缩短\s*(\d+)\s*%', 'reduce'),
    ]

    def __init__(self):
        self.compiled_urgency = {
            level: re.compile('|'.join(keywords))
            for level, keywords in self.URGENCY_KEYWORDS.items()
        }
        self.compiled_value = {
            vtype: re.compile('|'.join(keywords))
            for vtype, keywords in self.VALUE_KEYWORDS.items()
        }

    def parse_demand_text(self, demand: dict) -> dict:
        """
        解析需求文本，提取评分特征
        
        Args:
            demand: 原始需求字典
            
        Returns:
            提取的特征字典
        """
        merged_text = self._merge_text(demand)
        
        return {
            'urgency_analysis': self._analyze_urgency(merged_text),
            'value_analysis': self._analyze_value(merged_text),
            'department_analysis': self._analyze_departments(merged_text),
            'resource_estimation': self._estimate_resource(merged_text),
            'efficiency_metrics': self._extract_efficiency_metrics(merged_text),
            'risk_indicators': self._identify_risks(merged_text),
            'complexity_hints': self._estimate_complexity(merged_text)
        }

    def _merge_text(self, demand: dict) -> str:
        """合并所有文本字段"""
        fields = [
            demand.get('description', ''),
            demand.get('usage_scenario', ''),
            demand.get('expected_value', ''),
            demand.get('cross_department_impact', ''),
            demand.get('resource_input', ''),
            demand.get('deadline_risk', ''),
            demand.get('background', ''),
            demand.get('demand_name', '')
        ]
        return " ".join([str(f) for f in fields if f])

    def _analyze_urgency(self, text: str) -> dict:
        """分析紧急程度"""
        result = {
            'level': 'low',
            'score_hint': 3,
            'matched_keywords': [],
            'reasoning': '无明确紧急信号'
        }

        matched_keywords = []
        for level in ['critical', 'high', 'medium', 'low']:
            pattern = self.compiled_urgency[level]
            matches = pattern.findall(text)
            if matches:
                matched_keywords.extend(matches)
                result['level'] = level
                result['score_hint'] = {
                    'critical': 14,
                    'high': 11,
                    'medium': 7,
                    'low': 3
                }[level]
                result['reasoning'] = f"检测到{level}级别关键词: {', '.join(matches)}"
                break

        result['matched_keywords'] = matched_keywords
        return result

    def _analyze_value(self, text: str) -> dict:
        """分析业务价值类型"""
        result = {
            'types': [],
            'matched_keywords': [],
            'score_hint': 10,
            'reasoning': '未检测到明确业务价值'
        }

        for vtype in ['revenue', 'cost_saving', 'efficiency', 'quality']:
            pattern = self.compiled_value[vtype]
            matches = pattern.findall(text)
            if matches:
                result['types'].append(vtype)
                result['matched_keywords'].extend(matches)

        if result['types']:
            if 'revenue' in result['types']:
                result['score_hint'] = 22
            elif 'cost_saving' in result['types'] or 'efficiency' in result['types']:
                result['score_hint'] = 18
            elif 'quality' in result['types']:
                result['score_hint'] = 15

        return result

    def _analyze_departments(self, text: str) -> dict:
        """分析影响部门"""
        affected_departments = []
        for dept, keywords in self.DEPARTMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    affected_departments.append(dept)
                    break

        unique_depts = list(set(affected_departments))
        dept_count = len(unique_depts)

        if dept_count >= 3:
            score_hint = 14
        elif dept_count >= 2:
            score_hint = 10
        elif dept_count >= 1:
            score_hint = 6
        else:
            score_hint = 2

        return {
            'departments': unique_depts,
            'count': dept_count,
            'score_hint': score_hint,
            'reasoning': f"影响{dept_count}个部门" if dept_count > 0 else "未检测到跨部门影响"
        }

    def _estimate_resource(self, text: str) -> dict:
        """估算资源投入"""
        resources = {
            'man_months': 0,
            'man_days': 0,
            'money': 0,
            'score_hint': 10,
            'reasoning': '未检测到明确资源信息'
        }

        for pattern, rtype in self.RESOURCE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                value = int(match.group(1))
                if rtype == 'man_month':
                    resources['man_months'] = value
                elif rtype == 'man_day':
                    resources['man_days'] = value
                elif rtype == 'man_week':
                    resources['man_days'] = value * 5
                elif rtype == 'man_year':
                    resources['man_months'] = value * 12
                elif rtype in ['money_wan', 'money_qian']:
                    resources['money'] = value * (10000 if rtype == 'money_wan' else 1000)

        # 根据资源估算打分（投入越大，ROI评分可能越低）
        if resources['man_months'] <= 1 or resources['man_days'] <= 20:
            resources['score_hint'] = 13
            resources['reasoning'] = '低资源投入'
        elif resources['man_months'] <= 3 or resources['man_days'] <= 60:
            resources['score_hint'] = 10
            resources['reasoning'] = '中等资源投入'
        elif resources['man_months'] <= 6:
            resources['score_hint'] = 7
            resources['reasoning'] = '较高资源投入'
        else:
            resources['score_hint'] = 3
            resources['reasoning'] = '高资源投入'

        return resources

    def _extract_efficiency_metrics(self, text: str) -> dict:
        """提取效率提升指标"""
        metrics = {
            'efficiency_up_percent': 0,
            'reduce_percent': 0,
            'has_quantifiable_value': False
        }

        for pattern, mtype in self.EFFICIENCY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                value = int(match.group(1))
                if mtype == 'efficiency_up':
                    metrics['efficiency_up_percent'] = max(metrics['efficiency_up_percent'], value)
                elif mtype == 'reduce':
                    metrics['reduce_percent'] = max(metrics['reduce_percent'], value)
                metrics['has_quantifiable_value'] = True

        return metrics

    def _identify_risks(self, text: str) -> dict:
        """识别潜在风险"""
        risks = []
        risk_keywords = {
            'technical': ['技术瓶颈', '架构', '重构', '迁移', '兼容性', '性能'],
            'business': ['客户流失', '收入下降', '市场份额', '竞争'],
            'compliance': ['合规', '审计', '监管', '处罚', '法律', '数据安全', '隐私'],
            'operational': ['人员离职', '培训成本', '运维压力', '支持']
        }

        for risk_type, keywords in risk_keywords.items():
            for kw in keywords:
                if kw in text:
                    risks.append({'type': risk_type, 'keyword': kw})

        return {
            'risks': risks,
            'has_risk': len(risks) > 0,
            'risk_count': len(risks)
        }

    def _estimate_complexity(self, text: str) -> dict:
        """估算实施复杂度"""
        complexity_indicators = {
            'simple': ['简单', '快速', '配置', '修改', '调整', '按钮', '颜色', '样式'],
            'medium': ['开发', '功能', '模块', '接口', '对接'],
            'complex': ['系统', '平台', '架构', '重构', '迁移', '跨系统', '集成', '数据中台']
        }

        level = 'simple'
        for check_level in ['complex', 'medium', 'simple']:
            for kw in complexity_indicators[check_level]:
                if kw in text:
                    level = check_level
                    break
            if level != 'simple':
                break

        return {
            'level': level,
            'score_hint': {
                'simple': 9,
                'medium': 6,
                'complex': 3
            }[level],
            'reasoning': f"识别为{level}复杂度"
        }

    def enhance_demand(self, demand: dict, strategy_focus: list = None) -> dict:
        """
        增强需求数据 - 自动补全缺失字段
        
        Args:
            demand: 原始需求字典
            strategy_focus: 战略重点
            
        Returns:
            增强后的需求字典
        """
        features = self.parse_demand_text(demand)
        
        # 创建增强后的需求副本
        enhanced = demand.copy()
        
        # 智能补全策略
        if not enhanced.get('deadline_risk') or enhanced.get('deadline_risk') in ['', '无', '未知']:
            urgency = features['urgency_analysis']
            if urgency['level'] in ['critical', 'high']:
                enhanced['deadline_risk'] = urgency['reasoning']
        
        if not enhanced.get('expected_value') or enhanced.get('expected_value') in ['', '无', '未知']:
            value = features['value_analysis']
            metrics = features['efficiency_metrics']
            parts = []
            if metrics['has_quantifiable_value']:
                if metrics['efficiency_up_percent']:
                    parts.append(f"预计提升效率{metrics['efficiency_up_percent']}%")
                if metrics['reduce_percent']:
                    parts.append(f"预计减少{metrics['reduce_percent']}%")
            if parts:
                enhanced['expected_value'] = "；".join(parts)
        
        if not enhanced.get('cross_department_impact') or enhanced.get('cross_department_impact') in ['', '无', '未知']:
            depts = features['department_analysis']
            if depts['count'] > 0:
                enhanced['cross_department_impact'] = f"涉及部门：{', '.join(depts['departments'])}"
        
        # 添加元数据供评分引擎使用
        enhanced['_nlp_features'] = features
        enhanced['_enhanced'] = True
        
        return enhanced


def auto_enhance_demands(demands: list, strategy_focus: list = None) -> list:
    """
    批量增强需求数据
    
    Args:
        demands: 需求列表
        strategy_focus: 战略重点
        
    Returns:
        增强后的需求列表
    """
    parser = IntentParser()
    return [parser.enhance_demand(d, strategy_focus) for d in demands]


if __name__ == '__main__':
    parser = IntentParser()
    
    test_demand = {
        'demand_name': '紧急修复订单系统',
        'description': '系统频繁崩溃，客户投诉激增，需要紧急修复',
        'usage_scenario': '供应链和销售部门都在用',
        'expected_value': '减少50%的故障率',
        'resource_input': '2人月',
    }
    
    result = parser.parse_demand_text(test_demand)
    
    print("=== NLP 意图解析结果 ===\n")
    print(f"紧急程度分析:")
    print(f"  级别: {result['urgency_analysis']['level']}")
    print(f"  评分提示: {result['urgency_analysis']['score_hint']}")
    print(f"  匹配词: {result['urgency_analysis']['matched_keywords']}")
    print(f"  原因: {result['urgency_analysis']['reasoning']}")
    
    print(f"\n业务价值分析:")
    print(f"  类型: {result['value_analysis']['types']}")
    print(f"  匹配词: {result['value_analysis']['matched_keywords']}")
    print(f"  评分提示: {result['value_analysis']['score_hint']}")
    
    print(f"\n部门影响分析:")
    print(f"  部门: {result['department_analysis']['departments']}")
    print(f"  数量: {result['department_analysis']['count']}")
    print(f"  评分提示: {result['department_analysis']['score_hint']}")
    
    print(f"\n资源估算:")
    print(f"  人月: {result['resource_estimation']['man_months']}")
    print(f"  评分提示: {result['resource_estimation']['score_hint']}")
    
    print(f"\n风险识别:")
    print(f"  有风险: {result['risk_indicators']['has_risk']}")
    print(f"  风险数: {result['risk_indicators']['risk_count']}")
    
    enhanced = parser.enhance_demand(test_demand)
    print(f"\n=== 增强后需求 ===")
    print(f"deadline_risk: {enhanced.get('deadline_risk')}")
    print(f"cross_department_impact: {enhanced.get('cross_department_impact')}")
