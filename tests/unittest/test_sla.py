"""Tests for SLA management system."""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import shutil

from pr_agent.sla import (
    SLAManager,
    SLAPolicy,
    SLATarget,
    SLAViolation,
    SLAPriority,
    SLAStatus,
    SLAMetric
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sla_manager(temp_storage):
    """Create SLA manager instance."""
    return SLAManager(storage_path=temp_storage)


def test_create_policy(sla_manager):
    """Test creating an SLA policy."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        ),
        SLATarget(
            metric=SLAMetric.REVIEW_COMPLETION_TIME,
            target_hours=24.0
        )
    ]

    policy = sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]}
    )

    assert policy.policy_id == "standard"
    assert policy.name == "Standard SLA"
    assert policy.priority == SLAPriority.NORMAL
    assert len(policy.targets) == 2
    assert policy.enabled is True


def test_update_policy(sla_manager):
    """Test updating a policy."""
    targets = [
        SLATarget(metric=SLAMetric.FIRST_RESPONSE_TIME, target_hours=2.0)
    ]

    sla_manager.create_policy(
        policy_id="test",
        name="Test",
        description="Test policy",
        priority=SLAPriority.NORMAL,
        targets=targets
    )

    updated = sla_manager.update_policy(
        "test",
        name="Updated Test",
        enabled=False
    )

    assert updated.name == "Updated Test"
    assert updated.enabled is False


def test_delete_policy(sla_manager):
    """Test deleting a policy."""
    targets = [
        SLATarget(metric=SLAMetric.FIRST_RESPONSE_TIME, target_hours=2.0)
    ]

    sla_manager.create_policy(
        policy_id="test",
        name="Test",
        description="Test policy",
        priority=SLAPriority.NORMAL,
        targets=targets
    )

    assert sla_manager.get_policy("test") is not None

    sla_manager.delete_policy("test")

    assert sla_manager.get_policy("test") is None


def test_list_policies(sla_manager):
    """Test listing policies."""
    targets = [
        SLATarget(metric=SLAMetric.FIRST_RESPONSE_TIME, target_hours=2.0)
    ]

    sla_manager.create_policy(
        policy_id="policy1",
        name="Policy 1",
        description="First policy",
        priority=SLAPriority.NORMAL,
        targets=targets
    )

    sla_manager.create_policy(
        policy_id="policy2",
        name="Policy 2",
        description="Second policy",
        priority=SLAPriority.HIGH,
        targets=targets
    )

    policies = sla_manager.list_policies()
    assert len(policies) == 2

    # Disable one policy
    sla_manager.update_policy("policy2", enabled=False)

    enabled_policies = sla_manager.list_policies(enabled_only=True)
    assert len(enabled_policies) == 1
    assert enabled_policies[0].policy_id == "policy1"


def test_start_tracking(sla_manager):
    """Test starting review tracking."""
    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    assert "rev-123" in sla_manager.review_tracking
    tracking = sla_manager.review_tracking["rev-123"]
    assert tracking["repository"] == "myorg/myrepo"
    assert tracking["priority"] == SLAPriority.NORMAL
    assert tracking["started_at"] is not None


def test_record_event(sla_manager):
    """Test recording review events."""
    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    now = datetime.now(timezone.utc)

    sla_manager.record_event("rev-123", "first_response", now)
    tracking = sla_manager.review_tracking["rev-123"]
    assert tracking["first_response_at"] == now

    sla_manager.record_event("rev-123", "completed", now + timedelta(hours=1))
    assert tracking["completed_at"] == now + timedelta(hours=1)


def test_check_compliance_compliant(sla_manager):
    """Test checking compliance for a compliant review."""
    # Create policy
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]}
    )

    # Start tracking
    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Record response within SLA
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.record_event(
        "rev-123",
        "first_response",
        started + timedelta(hours=1)
    )

    # Check compliance
    compliance = sla_manager.check_compliance("rev-123")

    assert compliance is not None
    assert compliance.status == SLAStatus.COMPLIANT
    assert len(compliance.violations) == 0


def test_check_compliance_at_risk(sla_manager):
    """Test checking compliance for an at-risk review."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0,
            warning_threshold_percent=80.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]}
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Simulate time passing (85% of target)
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=1.7)

    compliance = sla_manager.check_compliance("rev-123")

    assert compliance is not None
    assert compliance.status == SLAStatus.AT_RISK
    assert len(compliance.violations) == 0


def test_check_compliance_violated(sla_manager):
    """Test checking compliance for a violated review."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=False
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Simulate time passing (exceed target)
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=3)

    compliance = sla_manager.check_compliance("rev-123")

    assert compliance is not None
    assert compliance.status == SLAStatus.VIOLATED
    assert len(compliance.violations) == 1

    violation = compliance.violations[0]
    assert violation.metric == SLAMetric.FIRST_RESPONSE_TIME
    assert violation.actual_hours > violation.target_hours


def test_escalation(sla_manager):
    """Test violation escalation."""
    escalation_called = []

    def escalation_callback(violation, policy):
        escalation_called.append((violation, policy))

    sla_manager.register_escalation_callback(escalation_callback)

    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=True,
        escalation_targets=["senior-reviewer"]
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Simulate violation
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=3)

    compliance = sla_manager.check_compliance("rev-123")

    assert len(escalation_called) == 1
    violation, policy = escalation_called[0]
    assert violation.escalated is True
    assert violation.escalated_to == "senior-reviewer"


def test_violation_callback(sla_manager):
    """Test violation callback."""
    violations_detected = []

    def violation_callback(violation):
        violations_detected.append(violation)

    sla_manager.register_violation_callback(violation_callback)

    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=False
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Simulate violation
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=3)

    sla_manager.check_compliance("rev-123")

    assert len(violations_detected) == 1
    assert violations_detected[0].review_id == "rev-123"


def test_resolve_violation(sla_manager):
    """Test resolving a violation."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=False
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Create violation
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=3)

    compliance = sla_manager.check_compliance("rev-123")
    violation = compliance.violations[0]

    assert violation.resolved is False

    # Resolve violation
    sla_manager.resolve_violation(violation.violation_id)

    assert violation.resolved is True
    assert violation.resolved_at is not None


def test_get_violations(sla_manager):
    """Test getting violations with filters."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=False
    )

    # Create multiple violations
    for i in range(3):
        review_id = f"rev-{i}"
        sla_manager.start_tracking(
            review_id=review_id,
            repository="myorg/myrepo",
            priority=SLAPriority.NORMAL
        )

        started = sla_manager.review_tracking[review_id]["started_at"]
        sla_manager.review_tracking[review_id]["started_at"] = started - timedelta(hours=3)

        sla_manager.check_compliance(review_id)

    # Get all violations
    all_violations = sla_manager.get_violations()
    assert len(all_violations) == 3

    # Get violations for specific review
    review_violations = sla_manager.get_violations(review_id="rev-1")
    assert len(review_violations) == 1
    assert review_violations[0].review_id == "rev-1"

    # Resolve one violation
    sla_manager.resolve_violation(all_violations[0].violation_id)

    # Get unresolved violations
    unresolved = sla_manager.get_violations(resolved=False)
    assert len(unresolved) == 2


def test_get_statistics(sla_manager):
    """Test getting SLA statistics."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]}
    )

    # Create compliant review
    sla_manager.start_tracking(
        review_id="rev-1",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )
    started = sla_manager.review_tracking["rev-1"]["started_at"]
    sla_manager.record_event("rev-1", "first_response", started + timedelta(hours=1))
    sla_manager.check_compliance("rev-1")

    # Create violated review
    sla_manager.start_tracking(
        review_id="rev-2",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )
    started = sla_manager.review_tracking["rev-2"]["started_at"]
    sla_manager.review_tracking["rev-2"]["started_at"] = started - timedelta(hours=3)
    sla_manager.check_compliance("rev-2")

    # Get statistics
    stats = sla_manager.get_statistics()

    assert len(stats) == 1
    policy_stats = stats[0]
    assert policy_stats.policy_id == "standard"
    assert policy_stats.total_reviews == 2
    assert policy_stats.compliant_reviews == 1
    assert policy_stats.violated_reviews == 1
    assert policy_stats.compliance_rate == 50.0


def test_persistence(temp_storage):
    """Test policy and violation persistence."""
    # Create manager and add policy
    manager1 = SLAManager(storage_path=temp_storage)

    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        )
    ]

    manager1.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets
    )

    # Create violation
    manager1.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )
    started = manager1.review_tracking["rev-123"]["started_at"]
    manager1.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=3)
    manager1.check_compliance("rev-123")

    # Create new manager instance
    manager2 = SLAManager(storage_path=temp_storage)

    # Verify policy persisted
    policy = manager2.get_policy("standard")
    assert policy is not None
    assert policy.name == "Standard SLA"

    # Verify violations persisted
    violations = manager2.get_violations()
    assert len(violations) == 1


def test_multiple_metrics(sla_manager):
    """Test policy with multiple metrics."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=2.0
        ),
        SLATarget(
            metric=SLAMetric.REVIEW_COMPLETION_TIME,
            target_hours=24.0
        )
    ]

    sla_manager.create_policy(
        policy_id="standard",
        name="Standard SLA",
        description="Standard review SLA",
        priority=SLAPriority.NORMAL,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]},
        escalation_enabled=False
    )

    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # First response within SLA
    started = sla_manager.review_tracking["rev-123"]["started_at"]
    sla_manager.record_event("rev-123", "first_response", started + timedelta(hours=1))

    # Simulate review not completed after 25 hours
    # Modify started_at to simulate 25 hours passing
    sla_manager.review_tracking["rev-123"]["started_at"] = started - timedelta(hours=25)
    # Also adjust first_response_at to maintain the 1-hour response time
    sla_manager.review_tracking["rev-123"]["first_response_at"] = started - timedelta(hours=24)

    compliance = sla_manager.check_compliance("rev-123")

    assert compliance is not None
    assert len(compliance.metrics) == 2
    assert compliance.metrics["first_response_time"]["violated"] is False
    assert compliance.metrics["review_completion_time"]["violated"] is True
    assert len(compliance.violations) == 1
    assert compliance.violations[0].metric == SLAMetric.REVIEW_COMPLETION_TIME


def test_priority_matching(sla_manager):
    """Test policy matching by priority."""
    targets = [
        SLATarget(
            metric=SLAMetric.FIRST_RESPONSE_TIME,
            target_hours=1.0
        )
    ]

    # Create high priority policy
    sla_manager.create_policy(
        policy_id="high-priority",
        name="High Priority SLA",
        description="High priority review SLA",
        priority=SLAPriority.HIGH,
        targets=targets,
        applies_to={"repositories": ["myorg/myrepo"]}
    )

    # Track normal priority review
    sla_manager.start_tracking(
        review_id="rev-123",
        repository="myorg/myrepo",
        priority=SLAPriority.NORMAL
    )

    # Should not match high priority policy
    compliance = sla_manager.check_compliance("rev-123")
    assert compliance is None

    # Track high priority review
    sla_manager.start_tracking(
        review_id="rev-456",
        repository="myorg/myrepo",
        priority=SLAPriority.HIGH
    )

    # Should match high priority policy
    compliance = sla_manager.check_compliance("rev-456")
    assert compliance is not None
    assert compliance.policy_id == "high-priority"
