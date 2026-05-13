"""
需求智能治理主入口 v2 - 专业版
整合 NLP 解析、动态阈值、ROI 计算、版本控制、雷达图生成

新增功能：
- NLP 文本意图解析 - 自动提取特征，智能补全缺失字段
- 动态阈值调节 - 根据资源水位自动调整分级门槛
- ROI 量化计算 - 公式驱动投入产出比评分
- 规则版本控制 - 追溯历史评分变化
- 雷达图输出 - 可视化维度得分分布
"""

import os
import sys
from typing import Optional

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from intent_parser import auto_enhance_demands
from demand_scorer import auto_score_demand
from dynamic_threshold import create_threshold_manager, DynamicThresholdManager
from roi_calculator import ROICalculator, calculate_demand_roi
from version_manager import create_version_manager
from radar_chart import generate_radar_chart, RadarChartGenerator
from document_generator import generate_submission_package, format_report
from notice_generator import generate_governance_notice


def execute(
    demand_list: list,
    dept_submitter: str,
    is_trial_period: bool,
    strategy_focus: list = None,
    scoring_rules_path: str = None,
    # 新增：动态阈值参数
    resource_utilization: float = 0.7,
    strategy_phase: str = 'normal',
    is_frozen: bool = False,
    is_sprint: bool = False,
    # 新增：ROI 参数
    man_day_cost: int = 1500,
    # 新增：输出选项
    generate_radar: bool = True,
    output_path: str = None
) -> dict:
    """
    执行需求智能治理流程（专业版）
    
    Args:
        demand_list: 研发部原始需求列表
        dept_submitter: 研发部需求对接人姓名
        is_trial_period: 是否为试用期
        strategy_focus: 公司当前战略重点方向
        scoring_rules_path: 评分规则文件路径
        
        resource_utilization: 当前资源利用率 (0-1)
        strategy_phase: 战略阶段 (startup/growth/mature/transformation/normal)
        is_frozen: 是否冻结期
        is_sprint: 是否冲刺期
        
        man_day_cost: 人天成本（元）
        
        generate_radar: 是否生成雷达图
        output_path: 输出路径
        
    Returns:
        完整决策报告
    """
    # 0. 初始化各组件
    threshold_mgr = create_threshold_manager(
        resource_utilization=resource_utilization,
        strategy_phase=strategy_phase,
        is_frozen=is_frozen,
        is_sprint=is_sprint
    )
    
    roi_calc = ROICalculator(man_day_cost)
    
    version_mgr = create_version_manager(scoring_rules_path)
    version_mgr.create_snapshot(description='当前评分规则')
    
    # 1. NLP 增强需求数据
    enhanced_demands = auto_enhance_demands(demand_list, strategy_focus)
    
    # 2. 评分
    scoring_result = auto_score_demand(enhanced_demands, scoring_rules_path, strategy_focus)
    
    scored_demands = scoring_result['scored_demands']
    stats = scoring_result['stats']
    
    # 3. ROI 计算
    roi_results = {}
    for demand, enhanced in zip(demand_list, enhanced_demands):
        nlp_features = enhanced.get('_nlp_features', None)
        roi_result = roi_calc.calculate_roi_score(demand, nlp_features)
        roi_results[demand.get('id', 'unknown')] = roi_result
    
    # 4. 动态阈值定级
    graded_results = []
    for demand in scored_demands:
        grade_info = threshold_mgr.grade_demand(demand['total_score'])
        graded_results.append({
            **demand,
            'dynamic_grade': grade_info['grade'],
            'thresholds_used': grade_info['thresholds_used'],
            'adjustments': grade_info['adjustments_applied']
        })
    
    # 5. 区分合规/无效需求
    valid_demands = [d for d in graded_results if d['grade'] != 'D']
    invalid_demands = [d for d in graded_results if d['grade'] == 'D']
    reject_reasons = {d['id']: d['reject_reason'] for d in invalid_demands}
    
    # 6. 生成提报材料
    submission_package = generate_submission_package(
        graded_results,
        dept_submitter,
        is_trial_period,
        strategy_focus
    )
    
    # 7. 生成宣导文案
    notice_text = generate_governance_notice(dept_submitter, is_trial_period, graded_results)
    
    # 8. 生成雷达图
    radar_results = {}
    if generate_radar:
        gen = RadarChartGenerator()
        for result in graded_results:
            html = gen.generate_radar_html(result)
            radar_results[result['id']] = html
            
            if output_path:
                radar_path = os.path.join(output_path, f"radar_{result['id']}.html")
                os.makedirs(output_path, exist_ok=True)
                with open(radar_path, 'w', encoding='utf-8') as f:
                    f.write(html)
    
    # 9. 生成格式化报告
    formatted_report = format_report(submission_package, invalid_demands)
    
    # 10. 生成阈值调整说明
    threshold_explanation = threshold_mgr.explain_adjustments()
    
    return {
        '需求智能评分报告': graded_results,
        'ROI 分析报告': roi_results,
        '预审总览': f"合规需求{stats['valid']}条（A:{stats['A']}、B:{stats['B']}、C:{stats['C']}），无效需求{stats['invalid']}条",
        '无效需求清单与驳回原因': reject_reasons,
        '合规需求优先级排序': [
            {'id': d['id'], 'grade': d['grade'], 'type': d['demand_type'], 'score': d['total_score']}
            for d in valid_demands
        ],
        '标准化提报材料': submission_package,
        '部门宣导文案': notice_text,
        '格式化报告': formatted_report,
        '评分统计': stats,
        '评分时间': scoring_result['scoring_time'],
        '动态阈值说明': threshold_explanation,
        '规则版本': version_mgr.history['current_version'],
        '雷达图': radar_results if generate_radar else None,
        'NLP 增强说明': '已自动补全缺失字段' if any(d.get('_enhanced') for d in enhanced_demands) else '原始数据完整'
    }


if __name__ == '__main__':
    # 测试示例
    test_demands = [
        {
            'id': 'D001',
            'description': '跨部门订单数据同步系统开发',
            'submitter': '研发-张三',
            'usage_scenario': '供应链、销售、财务跨部门数据协同',
            'expected_value': '减少数据重复录入，提升30%对账效率，降低5%财务差错率',
            'cross_department_impact': '供应链、销售、财务3个部门',
            'resource_input': '2人月开发资源',
            'deadline_risk': '无刚性时间节点，为年度战略重点项目'
        },
        {
            'id': 'D002',
            'description': '个人操作界面按钮位置调整',
            'submitter': '研发-李四',
            'usage_scenario': '仅个人操作习惯优化',
            'expected_value': '无业务效率提升',
            'cross_department_impact': '无跨部门影响',
            'resource_input': '0.5人天资源',
            'deadline_risk': '无紧急性'
        }
    ]
    
    result = execute(
        test_demands,
        dept_submitter='研发部-小夏',
        is_trial_period=True,
        strategy_focus=['跨部门数据协同', '运营效率提升'],
        resource_utilization=0.75,
        generate_radar=True
    )
    
    print(result['预审总览'])
    print(result['动态阈值说明'])
    print(result['NLP 增强说明'])
    print(result['部门宣导文案'])
