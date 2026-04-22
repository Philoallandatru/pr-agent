"""
SLA (Service Level Agreement) Management System

Manages SLA policies, monitors compliance, and handles escalations for code reviews.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
from collections import defaultdict


class SLAPriority(Enum):
    """SLA priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SLAStatus(Enum):
    """SLA compliance status."""
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    VIOLATED = "violated"
    ESCALATED = "escalated"


class SLAMetric(Enum):
    """SLA metric types."""
    FIRST_RESPONSE_TIME = "first_response_time"
    REVIEW_COMPLETION_TIME = "review_completion_time"
    APPROVAL_TIME = "approval_time"
    MERGE_TIME = "merge_time"


@dataclass
class SLATarget:
    """SLA time target."""
    metric: SLAMetric
    target_hours: float
    warning_threshold_percent: float = 80.0  # Warn at 80% of target
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['metric'] = self.metric.value
        return data


@dataclass
class SLAPolicy:
    """SLA policy definition."""
    policy_id: str
    name: str
    description: str
    priority: SLAPriority
    targets: List[SLATarget]
    applies_to: Dict[str, Any] = field(default_factory=dict)  # repositories, teams, etc.
    escalation_enabled: bool = True
    escalation_targets: List[str] = field(default_factory=list)  # User IDs to escalate to
    notification_enabled: bool = True
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['priority'] = self.priority.value
        data['targets'] = [t.to_dict() for t in self.targets]
        return data


@dataclass
class SLAViolation:
    """SLA violation record."""
    violation_id: str
    policy_id: str
    review_id: str
    metric: SLAMetric
    target_hours: float
    actual_hours: float
    violation_percent: float
    detected_at: datetime
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    escalated_to: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['metric'] = self.metric.value
        data['detected_at'] = self.detected_at.isoformat()
        if self.escalated_at:
            data['escalated_at'] = self.escalated_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class SLACompliance:
    """SLA compliance report."""
    policy_id: str
    review_id: str
    status: SLAStatus
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    violations: List[SLAViolation] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['violations'] = [v.to_dict() for v in self.violations]
        data['checked_at'] = self.checked_at.isoformat()
        return data


@dataclass
class SLAStatistics:
    """SLA statistics."""
    policy_id: str
    total_reviews: int = 0
    compliant_reviews: int = 0
    at_risk_reviews: int = 0
    violated_reviews: int = 0
    escalated_reviews: int = 0
    compliance_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    avg_completion_time_hours: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SLAManager:
    """SLA management system."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize SLA manager."""
        self.storage_path = storage_path or Path.home() / ".pr_agent" / "sla"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.policies: Dict[str, SLAPolicy] = {}
        self.violations: List[SLAViolation] = []
        self.compliance_history: List[SLACompliance] = []
        self.review_tracking: Dict[str, Dict[str, Any]] = {}

        # Callbacks
        self.violation_callbacks: List[Callable] = []
        self.escalation_callbacks: List[Callable] = []

        self._load_policies()
        self._load_violations()

    def _load_policies(self):
        """Load policies from storage."""
        policies_file = self.storage_path / "policies.json"
        if policies_file.exists():
            try:
                with open(policies_file, 'r') as f:
                    data = json.load(f)
                    for policy_data in data.get('policies', []):
                        policy = self._deserialize_policy(policy_data)
                        self.policies[policy.policy_id] = policy
            except Exception:
                pass

    def _save_policies(self):
        """Save policies to storage."""
        policies_file = self.storage_path / "policies.json"
        data = {
            'policies': [p.to_dict() for p in self.policies.values()]
        }
        with open(policies_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_violations(self):
        """Load violations from storage."""
        violations_file = self.storage_path / "violations.json"
        if violations_file.exists():
            try:
                with open(violations_file, 'r') as f:
                    data = json.load(f)
                    for v_data in data.get('violations', []):
                        violation = self._deserialize_violation(v_data)
                        self.violations.append(violation)
            except Exception:
                pass

    def _save_violations(self):
        """Save violations to storage."""
        violations_file = self.storage_path / "violations.json"
        data = {
            'violations': [v.to_dict() for v in self.violations]
        }
        with open(violations_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _deserialize_policy(self, data: Dict[str, Any]) -> SLAPolicy:
        """Deserialize policy from dict."""
        targets = []
        for t_data in data.get('targets', []):
            target = SLATarget(
                metric=SLAMetric(t_data['metric']),
                target_hours=t_data['target_hours'],
                warning_threshold_percent=t_data.get('warning_threshold_percent', 80.0),
                metadata=t_data.get('metadata', {})
            )
            targets.append(target)

        return SLAPolicy(
            policy_id=data['policy_id'],
            name=data['name'],
            description=data['description'],
            priority=SLAPriority(data['priority']),
            targets=targets,
            applies_to=data.get('applies_to', {}),
            escalation_enabled=data.get('escalation_enabled', True),
            escalation_targets=data.get('escalation_targets', []),
            notification_enabled=data.get('notification_enabled', True),
            enabled=data.get('enabled', True),
            metadata=data.get('metadata', {})
        )

    def _deserialize_violation(self, data: Dict[str, Any]) -> SLAViolation:
        """Deserialize violation from dict."""
        return SLAViolation(
            violation_id=data['violation_id'],
            policy_id=data['policy_id'],
            review_id=data['review_id'],
            metric=SLAMetric(data['metric']),
            target_hours=data['target_hours'],
            actual_hours=data['actual_hours'],
            violation_percent=data['violation_percent'],
            detected_at=datetime.fromisoformat(data['detected_at']),
            escalated=data.get('escalated', False),
            escalated_at=datetime.fromisoformat(data['escalated_at']) if data.get('escalated_at') else None,
            escalated_to=data.get('escalated_to'),
            resolved=data.get('resolved', False),
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
            metadata=data.get('metadata', {})
        )

    def create_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        priority: SLAPriority,
        targets: List[SLATarget],
        applies_to: Optional[Dict[str, Any]] = None,
        escalation_enabled: bool = True,
        escalation_targets: Optional[List[str]] = None,
        notification_enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SLAPolicy:
        """Create a new SLA policy."""
        policy = SLAPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            priority=priority,
            targets=targets,
            applies_to=applies_to or {},
            escalation_enabled=escalation_enabled,
            escalation_targets=escalation_targets or [],
            notification_enabled=notification_enabled,
            metadata=metadata or {}
        )

        self.policies[policy_id] = policy
        self._save_policies()

        return policy

    def update_policy(self, policy_id: str, **updates) -> SLAPolicy:
        """Update an existing policy."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]

        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)

        self._save_policies()
        return policy

    def delete_policy(self, policy_id: str):
        """Delete a policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
            self._save_policies()

    def get_policy(self, policy_id: str) -> Optional[SLAPolicy]:
        """Get policy by ID."""
        return self.policies.get(policy_id)

    def list_policies(self, enabled_only: bool = False) -> List[SLAPolicy]:
        """List all policies."""
        policies = list(self.policies.values())
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        return policies

    def start_tracking(
        self,
        review_id: str,
        repository: str,
        priority: SLAPriority = SLAPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Start tracking a review for SLA compliance."""
        self.review_tracking[review_id] = {
            'review_id': review_id,
            'repository': repository,
            'priority': priority,
            'started_at': datetime.now(timezone.utc),
            'first_response_at': None,
            'completed_at': None,
            'approved_at': None,
            'merged_at': None,
            'metadata': metadata or {}
        }

    def record_event(
        self,
        review_id: str,
        event_type: str,
        timestamp: Optional[datetime] = None
    ):
        """Record a review event."""
        if review_id not in self.review_tracking:
            return

        timestamp = timestamp or datetime.now(timezone.utc)
        tracking = self.review_tracking[review_id]

        if event_type == 'first_response' and not tracking['first_response_at']:
            tracking['first_response_at'] = timestamp
        elif event_type == 'completed':
            tracking['completed_at'] = timestamp
        elif event_type == 'approved':
            tracking['approved_at'] = timestamp
        elif event_type == 'merged':
            tracking['merged_at'] = timestamp

    def check_compliance(self, review_id: str) -> Optional[SLACompliance]:
        """Check SLA compliance for a review."""
        if review_id not in self.review_tracking:
            return None

        tracking = self.review_tracking[review_id]
        repository = tracking['repository']
        priority = tracking['priority']

        # Find applicable policies
        applicable_policies = self._find_applicable_policies(repository, priority)

        if not applicable_policies:
            return None

        # Check against first applicable policy
        policy = applicable_policies[0]
        compliance = SLACompliance(
            policy_id=policy.policy_id,
            review_id=review_id,
            status=SLAStatus.COMPLIANT,
            metrics={}
        )

        now = datetime.now(timezone.utc)
        started_at = tracking['started_at']

        for target in policy.targets:
            metric_status = self._check_metric(
                target, tracking, started_at, now
            )
            compliance.metrics[target.metric.value] = metric_status

            # Check for violations
            if metric_status['violated']:
                violation = SLAViolation(
                    violation_id=f"{review_id}_{target.metric.value}_{int(now.timestamp())}",
                    policy_id=policy.policy_id,
                    review_id=review_id,
                    metric=target.metric,
                    target_hours=target.target_hours,
                    actual_hours=metric_status['actual_hours'],
                    violation_percent=metric_status['violation_percent'],
                    detected_at=now
                )
                compliance.violations.append(violation)
                self.violations.append(violation)
                compliance.status = SLAStatus.VIOLATED

                # Trigger callbacks
                for callback in self.violation_callbacks:
                    callback(violation)

                # Handle escalation
                if policy.escalation_enabled and not violation.escalated:
                    self._escalate_violation(violation, policy)

            elif metric_status['at_risk'] and compliance.status == SLAStatus.COMPLIANT:
                compliance.status = SLAStatus.AT_RISK

        self.compliance_history.append(compliance)
        self._save_violations()

        return compliance

    def _find_applicable_policies(
        self,
        repository: str,
        priority: SLAPriority
    ) -> List[SLAPolicy]:
        """Find policies applicable to a review."""
        applicable = []

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            # Check priority match
            if policy.priority != priority:
                continue

            # Check repository match
            applies_to = policy.applies_to
            if 'repositories' in applies_to:
                if repository not in applies_to['repositories']:
                    continue

            applicable.append(policy)

        return applicable

    def _check_metric(
        self,
        target: SLATarget,
        tracking: Dict[str, Any],
        started_at: datetime,
        now: datetime
    ) -> Dict[str, Any]:
        """Check a specific metric against target."""
        metric = target.metric
        target_hours = target.target_hours
        warning_threshold = target_hours * (target.warning_threshold_percent / 100)

        actual_hours = 0.0
        completed = False

        if metric == SLAMetric.FIRST_RESPONSE_TIME:
            if tracking['first_response_at']:
                actual_hours = (tracking['first_response_at'] - started_at).total_seconds() / 3600
                completed = True
            else:
                actual_hours = (now - started_at).total_seconds() / 3600

        elif metric == SLAMetric.REVIEW_COMPLETION_TIME:
            if tracking['completed_at']:
                actual_hours = (tracking['completed_at'] - started_at).total_seconds() / 3600
                completed = True
            else:
                actual_hours = (now - started_at).total_seconds() / 3600

        elif metric == SLAMetric.APPROVAL_TIME:
            if tracking['approved_at']:
                actual_hours = (tracking['approved_at'] - started_at).total_seconds() / 3600
                completed = True
            else:
                actual_hours = (now - started_at).total_seconds() / 3600

        elif metric == SLAMetric.MERGE_TIME:
            if tracking['merged_at']:
                actual_hours = (tracking['merged_at'] - started_at).total_seconds() / 3600
                completed = True
            else:
                actual_hours = (now - started_at).total_seconds() / 3600

        violated = actual_hours > target_hours
        at_risk = actual_hours > warning_threshold and not violated
        violation_percent = ((actual_hours - target_hours) / target_hours * 100) if violated else 0.0

        return {
            'metric': metric.value,
            'target_hours': target_hours,
            'actual_hours': round(actual_hours, 2),
            'completed': completed,
            'violated': violated,
            'at_risk': at_risk,
            'violation_percent': round(violation_percent, 2)
        }

    def _escalate_violation(self, violation: SLAViolation, policy: SLAPolicy):
        """Escalate a violation."""
        if not policy.escalation_targets:
            return

        violation.escalated = True
        violation.escalated_at = datetime.now(timezone.utc)
        violation.escalated_to = policy.escalation_targets[0]

        # Trigger escalation callbacks
        for callback in self.escalation_callbacks:
            callback(violation, policy)

    def resolve_violation(self, violation_id: str):
        """Mark a violation as resolved."""
        for violation in self.violations:
            if violation.violation_id == violation_id:
                violation.resolved = True
                violation.resolved_at = datetime.now(timezone.utc)
                self._save_violations()
                break

    def get_violations(
        self,
        review_id: Optional[str] = None,
        policy_id: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[SLAViolation]:
        """Get violations with optional filters."""
        violations = self.violations

        if review_id:
            violations = [v for v in violations if v.review_id == review_id]
        if policy_id:
            violations = [v for v in violations if v.policy_id == policy_id]
        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]

        return violations

    def get_statistics(
        self,
        policy_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SLAStatistics]:
        """Get SLA statistics."""
        stats_by_policy: Dict[str, SLAStatistics] = {}

        # Filter compliance history
        history = self.compliance_history
        if start_date:
            history = [c for c in history if c.checked_at >= start_date]
        if end_date:
            history = [c for c in history if c.checked_at <= end_date]
        if policy_id:
            history = [c for c in history if c.policy_id == policy_id]

        # Calculate statistics
        for compliance in history:
            pid = compliance.policy_id
            if pid not in stats_by_policy:
                stats_by_policy[pid] = SLAStatistics(policy_id=pid)

            stats = stats_by_policy[pid]
            stats.total_reviews += 1

            if compliance.status == SLAStatus.COMPLIANT:
                stats.compliant_reviews += 1
            elif compliance.status == SLAStatus.AT_RISK:
                stats.at_risk_reviews += 1
            elif compliance.status == SLAStatus.VIOLATED:
                stats.violated_reviews += 1
            elif compliance.status == SLAStatus.ESCALATED:
                stats.escalated_reviews += 1

        # Calculate rates and averages
        for stats in stats_by_policy.values():
            if stats.total_reviews > 0:
                stats.compliance_rate = round(
                    (stats.compliant_reviews / stats.total_reviews) * 100, 2
                )

        return list(stats_by_policy.values())

    def register_violation_callback(self, callback: Callable):
        """Register a callback for violations."""
        self.violation_callbacks.append(callback)

    def register_escalation_callback(self, callback: Callable):
        """Register a callback for escalations."""
        self.escalation_callbacks.append(callback)


# Global instance
_sla_manager: Optional[SLAManager] = None


def get_sla_manager() -> SLAManager:
    """Get global SLA manager instance."""
    global _sla_manager
    if _sla_manager is None:
        _sla_manager = SLAManager()
    return _sla_manager


def configure_sla_manager(storage_path: Path):
    """Configure global SLA manager."""
    global _sla_manager
    _sla_manager = SLAManager(storage_path=storage_path)
