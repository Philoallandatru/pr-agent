"""
EfficiencyTracker - 追踪PR review的效率指标

使用context manager模式在review过程中自动收集指标
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger
from pr_agent.monitoring.estimation import calculate_complexity_score, estimate_human_review_time
from pr_agent.storage.database import Database


class EfficiencyTracker:
    """追踪PR review的效率指标"""

    def __init__(self, pr_review_id: int, git_provider):
        self.pr_review_id = pr_review_id
        self.git_provider = git_provider
        self.metrics = self._init_metrics()
        self.start_time = None
        self.end_time = None
        self.logger = get_logger()

    def _init_metrics(self) -> Dict[str, Any]:
        """初始化指标字典"""
        return {
            'issues_found_total': 0,
            'issues_high_severity': 0,
            'issues_medium_severity': 0,
            'issues_low_severity': 0,
            'security_issues_found': 0,
            'code_suggestions_count': 0,
            'tokens_prompt': 0,
            'tokens_completion': 0,
            'tokens_total': 0,
            'api_calls_count': 0,
            'api_cost_usd': 0.0,
            'agentic_search_iterations': 0,
            'pr_size_lines': 0,
            'pr_files_count': 0,
            'pr_languages': [],
            'pr_complexity_score': 0.0,
            'model_used': None,
            'review_type': 'standard'
        }

    def __enter__(self):
        """进入context时收集PR特征"""
        self.start_time = time.time()
        try:
            self._collect_pr_features()
        except Exception as e:
            self.logger.error(f"Failed to collect PR features: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出context时保存指标"""
        self.end_time = time.time()
        self.metrics['review_processing_time_seconds'] = (
            self.end_time - self.start_time
        )

        try:
            self._calculate_derived_metrics()
            self._save_to_database()
            self._update_prometheus()
        except Exception as e:
            self.logger.error(f"Failed to save efficiency metrics: {e}")

        return False

    def _collect_pr_features(self):
        """收集PR基础特征"""
        try:
            diff_files = self.git_provider.get_diff_files()
        except Exception as e:
            self.logger.warning(f"Failed to get diff files: {e}")
            return

        # 计算文件数
        self.metrics['pr_files_count'] = len(diff_files)

        # 计算代码行数和识别语言
        total_lines = 0
        languages = set()
        file_paths = []

        for file in diff_files:
            if not file.filename:
                continue

            file_paths.append(file.filename)

            # 计算行数（增加+删除）
            if file.patch:
                lines = file.patch.split('\n')
                added = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
                deleted = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
                total_lines += added + deleted

            # 识别语言
            ext = Path(file.filename).suffix.lower()
            lang = self._extension_to_language(ext)
            if lang:
                languages.add(lang)

        self.metrics['pr_size_lines'] = total_lines
        self.metrics['pr_languages'] = list(languages)

        # 计算复杂度评分
        pr_features = {
            'files_count': self.metrics['pr_files_count'],
            'size_lines': self.metrics['pr_size_lines'],
            'languages': self.metrics['pr_languages'],
            'file_paths': file_paths
        }
        self.metrics['pr_complexity_score'] = calculate_complexity_score(pr_features)

    def _extension_to_language(self, ext: str) -> Optional[str]:
        """将文件扩展名映射到编程语言"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.sh': 'Shell',
            '.sql': 'SQL',
            '.html': 'HTML',
            '.css': 'CSS',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.json': 'JSON',
            '.xml': 'XML',
            '.md': 'Markdown'
        }
        return ext_map.get(ext)

    def _calculate_derived_metrics(self):
        """计算派生指标"""
        # 计算总token数
        self.metrics['tokens_total'] = (
            self.metrics['tokens_prompt'] +
            self.metrics['tokens_completion']
        )

        # 估算人工审查时间
        pr_features = {
            'files_count': self.metrics['pr_files_count'],
            'size_lines': self.metrics['pr_size_lines'],
            'languages': self.metrics['pr_languages'],
            'complexity_score': self.metrics['pr_complexity_score']
        }
        self.metrics['estimated_human_time_saved_minutes'] = (
            estimate_human_review_time(pr_features)
        )

    def _save_to_database(self):
        """保存到数据库"""
        if not get_settings().get('efficiency_metrics.enabled', True):
            return

        try:
            db = Database()
            # 转换pr_languages为JSON字符串
            metrics_to_save = self.metrics.copy()
            metrics_to_save['pr_languages'] = json.dumps(metrics_to_save['pr_languages'])

            db.add_efficiency_metrics(self.pr_review_id, metrics_to_save)
            db.close()
        except Exception as e:
            self.logger.error(f"Failed to save to database: {e}")

    def _update_prometheus(self):
        """更新Prometheus指标"""
        try:
            from pr_agent.monitoring import metrics
            if not metrics.PROMETHEUS_AVAILABLE:
                return

            # 获取repository名称（从git_provider）
            repo_name = getattr(self.git_provider, 'repo', 'unknown')

            # 更新Counters
            if self.metrics['issues_high_severity'] > 0:
                metrics.ai_issues_found_total.labels(
                    repository=repo_name,
                    severity='high'
                ).inc(self.metrics['issues_high_severity'])

            if self.metrics['issues_medium_severity'] > 0:
                metrics.ai_issues_found_total.labels(
                    repository=repo_name,
                    severity='medium'
                ).inc(self.metrics['issues_medium_severity'])

            if self.metrics['issues_low_severity'] > 0:
                metrics.ai_issues_found_total.labels(
                    repository=repo_name,
                    severity='low'
                ).inc(self.metrics['issues_low_severity'])

            if self.metrics['code_suggestions_count'] > 0:
                metrics.ai_code_suggestions_total.labels(
                    repository=repo_name
                ).inc(self.metrics['code_suggestions_count'])

            if self.metrics['api_calls_count'] > 0:
                model = self.metrics['model_used'] or 'unknown'
                metrics.ai_api_calls_total.labels(
                    model=model,
                    repository=repo_name
                ).inc(self.metrics['api_calls_count'])

            if self.metrics['tokens_prompt'] > 0:
                model = self.metrics['model_used'] or 'unknown'
                metrics.ai_tokens_used_total.labels(
                    model=model,
                    token_type='prompt'
                ).inc(self.metrics['tokens_prompt'])

            if self.metrics['tokens_completion'] > 0:
                model = self.metrics['model_used'] or 'unknown'
                metrics.ai_tokens_used_total.labels(
                    model=model,
                    token_type='completion'
                ).inc(self.metrics['tokens_completion'])

            if self.metrics['api_cost_usd'] > 0:
                model = self.metrics['model_used'] or 'unknown'
                metrics.ai_cost_usd_total.labels(
                    model=model,
                    repository=repo_name
                ).inc(self.metrics['api_cost_usd'])

            # 更新Histograms
            metrics.ai_review_processing_time_seconds.labels(
                repository=repo_name,
                review_type=self.metrics['review_type']
            ).observe(self.metrics['review_processing_time_seconds'])

            if self.metrics['pr_size_lines'] > 0:
                metrics.ai_pr_size_lines.labels(
                    repository=repo_name
                ).observe(self.metrics['pr_size_lines'])

            if self.metrics['pr_complexity_score'] > 0:
                metrics.ai_pr_complexity_score.labels(
                    repository=repo_name
                ).observe(self.metrics['pr_complexity_score'])

            if self.metrics.get('estimated_human_time_saved_minutes'):
                metrics.ai_time_saved_minutes.labels(
                    repository=repo_name
                ).observe(self.metrics['estimated_human_time_saved_minutes'])

            # 更新Gauges
            if self.metrics['agentic_search_iterations'] > 0:
                metrics.ai_agentic_iterations.labels(
                    repository=repo_name
                ).set(self.metrics['agentic_search_iterations'])

        except Exception as e:
            self.logger.error(f"Failed to update Prometheus metrics: {e}")

    def track_api_call(self, tokens_prompt: int, tokens_completion: int, cost: float):
        """追踪单次API调用"""
        self.metrics['tokens_prompt'] += tokens_prompt
        self.metrics['tokens_completion'] += tokens_completion
        self.metrics['api_calls_count'] += 1
        self.metrics['api_cost_usd'] += cost

    def track_issues_found(self, issues: List[Dict]):
        """追踪发现的问题"""
        self.metrics['issues_found_total'] = len(issues)

        for issue in issues:
            severity = issue.get('severity', 'low').lower()
            if severity == 'high':
                self.metrics['issues_high_severity'] += 1
            elif severity == 'medium':
                self.metrics['issues_medium_severity'] += 1
            else:
                self.metrics['issues_low_severity'] += 1

            if issue.get('type') == 'security':
                self.metrics['security_issues_found'] += 1

    def track_code_suggestions(self, suggestions: List[Dict]):
        """追踪代码改进建议"""
        self.metrics['code_suggestions_count'] = len(suggestions)

    def track_agentic_iteration(self):
        """追踪agentic review迭代"""
        self.metrics['agentic_search_iterations'] += 1

    def set_review_type(self, review_type: str):
        """设置review类型"""
        self.metrics['review_type'] = review_type

    def set_model(self, model: str):
        """设置使用的模型"""
        self.metrics['model_used'] = model

    def set_agentic_iterations(self, iterations: int):
        """设置agentic迭代次数"""
        self.metrics['agentic_search_iterations'] = iterations
