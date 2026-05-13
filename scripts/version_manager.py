"""
规则版本控制引擎
管理评分规则的历史版本，支持追溯、对比和回滚

核心功能：
1. 版本化存储 - 每个规则变更都有版本号和时间戳
2. 历史追溯 - 查看某需求在历史版本下的评分结果
3. 变更对比 - 对比两个版本的规则差异
4. 影响分析 - 分析规则变更对历史需求的影响
"""

import yaml
import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path


class RulesVersionManager:
    """规则版本管理器"""

    def __init__(self, rules_path: str = None, history_path: str = None):
        """
        初始化版本管理器
        
        Args:
            rules_path: 当前规则文件路径
            history_path: 历史记录存储路径
        """
        if rules_path is None:
            rules_path = os.path.join(os.path.dirname(__file__), '..', 'rules', 'demand_scoring_rules.yaml')
        
        self.rules_path = rules_path
        
        if history_path is None:
            history_path = os.path.join(os.path.dirname(__file__), '..', 'rules', 'version_history.json')
        
        self.history_path = history_path
        self.history = self._load_history()
    
    def _load_history(self) -> dict:
        """加载版本历史"""
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            'versions': [],
            'current_version': '1.0',
            'created_at': datetime.now().isoformat()
        }
    
    def _save_history(self):
        """保存版本历史"""
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def create_snapshot(self, version: str = None, description: str = None) -> str:
        """
        创建当前规则的快照
        
        Args:
            version: 版本号，自动生成
            description: 版本描述
            
        Returns:
            版本号
        """
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            rules_content = yaml.safe_load(f)
        
        # 生成版本号
        if version is None:
            existing_versions = [v['version'] for v in self.history['versions']]
            if not existing_versions:
                version = '1.0'
            else:
                latest = max([float(v) for v in existing_versions if v.replace('.', '').isdigit()])
                version = f"{latest + 0.1:.1f}"
        
        snapshot = {
            'version': version,
            'created_at': datetime.now().isoformat(),
            'description': description or f'规则版本 {version}',
            'rules': rules_content,
            'file_hash': hash(json.dumps(rules_content, sort_keys=True))
        }
        
        # 检查是否已存在相同版本
        for v in self.history['versions']:
            if v['version'] == version:
                v['updated_at'] = snapshot['created_at']
                v['description'] = snapshot['description']
                v['rules'] = snapshot['rules']
                v['file_hash'] = snapshot['file_hash']
                break
        else:
            self.history['versions'].append(snapshot)
        
        self.history['current_version'] = version
        self._save_history()
        
        return version
    
    def get_version(self, version: str) -> Optional[dict]:
        """获取指定版本"""
        for v in self.history['versions']:
            if v['version'] == version:
                return v
        return None
    
    def list_versions(self) -> list:
        """列出所有版本"""
        return [
            {
                'version': v['version'],
                'created_at': v['created_at'],
                'description': v.get('description', '')
            }
            for v in self.history['versions']
        ]
    
    def compare_versions(self, version1: str, version2: str) -> dict:
        """对比两个版本的差异"""
        v1 = self.get_version(version1)
        v2 = self.get_version(version2)
        
        if not v1 or not v2:
            return {'error': '版本不存在'}
        
        diff = {
            'version1': version1,
            'version2': version2,
            'changes': []
        }
        
        # 对比权重变化
        dims1 = v1['rules'].get('dimensions', {})
        dims2 = v2['rules'].get('dimensions', {})
        
        all_dims = set(list(dims1.keys()) + list(dims2.keys()))
        
        for dim in all_dims:
            d1 = dims1.get(dim, {})
            d2 = dims2.get(dim, {})
            
            if d1.get('weight') != d2.get('weight'):
                diff['changes'].append({
                    'type': 'weight_change',
                    'dimension': dim,
                    'old': d1.get('weight'),
                    'new': d2.get('weight')
                })
            
            # 对比规则变化
            rules1 = d1.get('rules', [])
            rules2 = d2.get('rules', [])
            if len(rules1) != len(rules2):
                diff['changes'].append({
                    'type': 'rule_count_change',
                    'dimension': dim,
                    'old_count': len(rules1),
                    'new_count': len(rules2)
                })
        
        # 对比分级阈值
        grades1 = v1['rules'].get('grade_rules', {})
        grades2 = v2['rules'].get('grade_rules', {})
        
        for grade in set(list(grades1.keys()) + list(grades2.keys())):
            g1 = grades1.get(grade, {})
            g2 = grades2.get(grade, {})
            
            if g1.get('min') != g2.get('min'):
                diff['changes'].append({
                    'type': 'threshold_change',
                    'grade': grade,
                    'old_min': g1.get('min'),
                    'new_min': g2.get('min')
                })
        
        return diff
    
    def analyze_impact(self, version1: str, version2: str, demands: list) -> dict:
        """
        分析规则变更对需求的影响
        
        Args:
            version1: 旧版本
            version2: 新版本
            demands: 需求列表
            
        Returns:
            影响分析结果
        """
        from scripts.demand_scorer import DemandScorer
        
        v1 = self.get_version(version1)
        v2 = self.get_version(version2)
        
        if not v1 or not v2:
            return {'error': '版本不存在'}
        
        # 临时保存旧版本规则
        temp_path1 = self.rules_path + '.tmp_v1'
        temp_path2 = self.rules_path + '.tmp_v2'
        
        with open(temp_path1, 'w', encoding='utf-8') as f:
            yaml.dump(v1['rules'], f, allow_unicode=True)
        
        with open(temp_path2, 'w', encoding='utf-8') as f:
            yaml.dump(v2['rules'], f, allow_unicode=True)
        
        # 评分对比
        scorer1 = DemandScorer(temp_path1)
        scorer2 = DemandScorer(temp_path2)
        
        results = []
        for demand in demands:
            r1 = scorer1.score_demand(demand)
            r2 = scorer2.score_demand(demand)
            
            grade_changed = r1['grade'] != r2['grade']
            score_diff = r2['total_score'] - r1['total_score']
            
            results.append({
                'id': demand.get('id', 'unknown'),
                'old_score': r1['total_score'],
                'new_score': r2['total_score'],
                'old_grade': r1['grade'],
                'new_grade': r2['grade'],
                'grade_changed': grade_changed,
                'score_diff': score_diff
            })
        
        # 清理临时文件
        for path in [temp_path1, temp_path2]:
            if os.path.exists(path):
                os.remove(path)
        
        grade_changes = len([r for r in results if r['grade_changed']])
        
        return {
            'version1': version1,
            'version2': version2,
            'total_demands': len(demands),
            'grade_changes': grade_changes,
            'change_rate': grade_changes / len(demands) if demands else 0,
            'demands_affected': [r for r in results if r['grade_changed']]
        }
    
    def export_rules_for_version(self, version: str, output_path: str = None) -> str:
        """导出指定版本的规则文件"""
        v = self.get_version(version)
        if not v:
            return None
        
        if output_path is None:
            output_path = self.rules_path.replace('.yaml', f'_v{version}.yaml')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(v['rules'], f, allow_unicode=True, default_flow_style=False)
        
        return output_path
    
    def get_version_changelog(self, version: str) -> list:
        """获取版本变更日志"""
        versions = self.history['versions']
        version_idx = None
        
        for i, v in enumerate(versions):
            if v['version'] == version:
                version_idx = i
                break
        
        if version_idx is None or version_idx == 0:
            return []
        
        prev_version = versions[version_idx - 1]['version']
        return self.compare_versions(prev_version, version)


def create_version_manager(rules_path: str = None, history_path: str = None) -> RulesVersionManager:
    """便捷函数：创建版本管理器"""
    return RulesVersionManager(rules_path, history_path)


if __name__ == '__main__':
    mgr = create_version_manager()
    
    # 创建初始快照
    version = mgr.create_snapshot(description='初始版本')
    print(f"创建版本: {version}")
    
    # 列出所有版本
    print("\n版本列表:")
    for v in mgr.list_versions():
        print(f"  {v['version']} - {v['created_at']} - {v['description']}")
