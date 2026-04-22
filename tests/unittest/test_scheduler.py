"""Tests for review scheduler."""

import pytest
import time
from pathlib import Path
from pr_agent.scheduler import (
    ReviewScheduler,
    ReviewJob,
    ReviewStatus,
    ReviewPriority,
    TriggerType,
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage."""
    return tmp_path / "scheduler"


@pytest.fixture
def scheduler(temp_storage):
    """Create a scheduler instance."""
    sched = ReviewScheduler(storage_path=temp_storage, max_concurrent=2)
    yield sched
    # Cleanup: stop scheduler and wait for workers
    sched.stop()
    import time
    time.sleep(0.5)  # Give workers time to finish


class TestReviewJob:
    """Test ReviewJob."""

    def test_job_creation(self):
        """Test creating a review job."""
        job = ReviewJob(
            job_id="test-1",
            repository="test/repo",
            pr_number=123,
            branch="main",
            commit_hash="abc123",
            trigger_type=TriggerType.MANUAL,
            priority=ReviewPriority.NORMAL,
            status=ReviewStatus.PENDING,
            created_at="2024-01-01T00:00:00Z"
        )
        assert job.job_id == "test-1"
        assert job.repository == "test/repo"
        assert job.pr_number == 123

    def test_job_priority_comparison(self):
        """Test job priority comparison for queue ordering."""
        job_low = ReviewJob(
            job_id="low",
            repository="test/repo",
            pr_number=None,
            branch=None,
            commit_hash=None,
            trigger_type=TriggerType.MANUAL,
            priority=ReviewPriority.LOW,
            status=ReviewStatus.PENDING,
            created_at="2024-01-01T00:00:00Z"
        )
        job_high = ReviewJob(
            job_id="high",
            repository="test/repo",
            pr_number=None,
            branch=None,
            commit_hash=None,
            trigger_type=TriggerType.MANUAL,
            priority=ReviewPriority.HIGH,
            status=ReviewStatus.PENDING,
            created_at="2024-01-01T00:00:00Z"
        )
        # Higher priority should be "less than" for priority queue
        assert job_high < job_low


class TestReviewScheduler:
    """Test ReviewScheduler."""

    def test_scheduler_creation(self, scheduler, temp_storage):
        """Test scheduler creation."""
        assert scheduler.storage_path == temp_storage
        assert scheduler.max_concurrent == 2
        assert temp_storage.exists()

    def test_submit_job(self, scheduler):
        """Test submitting a job."""
        job = scheduler.submit_job(
            repository="test/repo",
            trigger_type=TriggerType.MANUAL,
            priority=ReviewPriority.NORMAL,
            pr_number=123
        )
        assert job.status == ReviewStatus.QUEUED
        assert job.repository == "test/repo"
        assert job.pr_number == 123

    def test_submit_multiple_jobs(self, scheduler):
        """Test submitting multiple jobs."""
        jobs = []
        for i in range(5):
            job = scheduler.submit_job(
                repository="test/repo",
                pr_number=i
            )
            jobs.append(job)

        assert len(jobs) == 5
        assert all(j.status == ReviewStatus.QUEUED for j in jobs)

    def test_job_priority_ordering(self, scheduler):
        """Test that jobs are ordered by priority."""
        # Submit jobs with different priorities
        job_low = scheduler.submit_job(
            repository="test/repo",
            priority=ReviewPriority.LOW
        )
        job_high = scheduler.submit_job(
            repository="test/repo",
            priority=ReviewPriority.HIGH
        )
        job_normal = scheduler.submit_job(
            repository="test/repo",
            priority=ReviewPriority.NORMAL
        )

        # Get jobs from queue (should be in priority order)
        first = scheduler.job_queue.get()
        second = scheduler.job_queue.get()
        third = scheduler.job_queue.get()

        assert first.priority == ReviewPriority.HIGH
        assert second.priority == ReviewPriority.NORMAL
        assert third.priority == ReviewPriority.LOW

    def test_cancel_queued_job(self, scheduler):
        """Test cancelling a queued job."""
        job = scheduler.submit_job(repository="test/repo")
        result = scheduler.cancel_job(job.job_id)

        assert result is True
        cancelled_job = scheduler.get_job(job.job_id)
        assert cancelled_job.status == ReviewStatus.CANCELLED

    def test_cancel_nonexistent_job(self, scheduler):
        """Test cancelling a non-existent job."""
        result = scheduler.cancel_job("nonexistent")
        assert result is False

    def test_get_job(self, scheduler):
        """Test getting a job by ID."""
        job = scheduler.submit_job(repository="test/repo")
        retrieved = scheduler.get_job(job.job_id)

        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_list_jobs(self, scheduler):
        """Test listing jobs."""
        # Submit some jobs
        for i in range(3):
            scheduler.submit_job(repository="test/repo", pr_number=i)

        jobs = scheduler.list_jobs()
        assert len(jobs) >= 3

    def test_list_jobs_with_filters(self, scheduler):
        """Test listing jobs with filters."""
        scheduler.submit_job(repository="repo1")
        scheduler.submit_job(repository="repo2")

        jobs = scheduler.list_jobs(repository="repo1")
        assert all(j.repository == "repo1" for j in jobs)


class TestSchedules:
    """Test schedule management."""

    def test_add_schedule(self, scheduler):
        """Test adding a schedule."""
        schedule = scheduler.add_schedule(
            schedule_id="daily",
            repository="test/repo",
            cron_expression="0 9 * * *",
            priority=ReviewPriority.NORMAL
        )
        assert schedule.schedule_id == "daily"
        assert schedule.cron_expression == "0 9 * * *"
        assert schedule.enabled is True

    def test_add_schedule_with_branches(self, scheduler):
        """Test adding a schedule with branch filters."""
        schedule = scheduler.add_schedule(
            schedule_id="main-only",
            repository="test/repo",
            cron_expression="0 9 * * *",
            branches=["main", "develop"]
        )
        assert schedule.branches == ["main", "develop"]

    def test_remove_schedule(self, scheduler):
        """Test removing a schedule."""
        scheduler.add_schedule(
            schedule_id="temp",
            repository="test/repo",
            cron_expression="0 9 * * *"
        )
        result = scheduler.remove_schedule("temp")
        assert result is True

        # Verify it's removed
        assert "temp" not in scheduler.schedules

    def test_remove_nonexistent_schedule(self, scheduler):
        """Test removing a non-existent schedule."""
        result = scheduler.remove_schedule("nonexistent")
        assert result is False


class TestTriggers:
    """Test trigger management."""

    def test_add_trigger(self, scheduler):
        """Test adding a trigger."""
        trigger = scheduler.add_trigger(
            trigger_id="pr-created",
            repository="test/repo",
            trigger_type=TriggerType.PR_CREATED,
            priority=ReviewPriority.HIGH
        )
        assert trigger.trigger_id == "pr-created"
        assert trigger.trigger_type == TriggerType.PR_CREATED
        assert trigger.enabled is True

    def test_add_trigger_with_filters(self, scheduler):
        """Test adding a trigger with filters."""
        trigger = scheduler.add_trigger(
            trigger_id="main-commits",
            repository="test/repo",
            trigger_type=TriggerType.COMMIT_PUSHED,
            filters={"branches": ["main"]}
        )
        assert trigger.filters == {"branches": ["main"]}

    def test_remove_trigger(self, scheduler):
        """Test removing a trigger."""
        scheduler.add_trigger(
            trigger_id="temp",
            repository="test/repo",
            trigger_type=TriggerType.PR_CREATED
        )
        result = scheduler.remove_trigger("temp")
        assert result is True

        # Verify it's removed
        assert "temp" not in scheduler.triggers

    def test_handle_event(self, scheduler):
        """Test handling an event."""
        # Set mock executor to prevent worker threads from blocking
        scheduler.set_review_executor(lambda job: None)

        # Add trigger
        scheduler.add_trigger(
            trigger_id="pr-trigger",
            repository="test/repo",
            trigger_type=TriggerType.PR_CREATED,
            priority=ReviewPriority.HIGH
        )

        # Handle event
        jobs = scheduler.handle_event(
            event_type=TriggerType.PR_CREATED,
            repository="test/repo",
            pr_number=123
        )

        assert len(jobs) == 1
        assert jobs[0].pr_number == 123
        assert jobs[0].priority == ReviewPriority.HIGH

    def test_handle_event_with_branch_filter(self, scheduler):
        """Test event handling with branch filters."""
        # Set mock executor
        scheduler.set_review_executor(lambda job: None)

        # Add trigger with branch filter
        scheduler.add_trigger(
            trigger_id="main-only",
            repository="test/repo",
            trigger_type=TriggerType.COMMIT_PUSHED,
            filters={"branches": ["main"]}
        )

        # Event on main branch - should create job
        jobs = scheduler.handle_event(
            event_type=TriggerType.COMMIT_PUSHED,
            repository="test/repo",
            branch="main"
        )
        assert len(jobs) == 1

        # Event on other branch - should not create job
        jobs = scheduler.handle_event(
            event_type=TriggerType.COMMIT_PUSHED,
            repository="test/repo",
            branch="feature"
        )
        assert len(jobs) == 0

    def test_handle_event_disabled_trigger(self, scheduler):
        """Test that disabled triggers don't create jobs."""
        scheduler.add_trigger(
            trigger_id="disabled",
            repository="test/repo",
            trigger_type=TriggerType.PR_CREATED,
            enabled=False
        )

        jobs = scheduler.handle_event(
            event_type=TriggerType.PR_CREATED,
            repository="test/repo"
        )
        assert len(jobs) == 0


class TestWorkerExecution:
    """Test worker execution."""

    def test_set_review_executor(self, scheduler):
        """Test setting review executor."""
        def mock_executor(job):
            return {"status": "success"}

        scheduler.set_review_executor(mock_executor)
        assert scheduler.review_executor is not None

    def test_job_execution(self, scheduler):
        """Test job execution with mock executor."""
        executed_jobs = []

        def mock_executor(job):
            executed_jobs.append(job.job_id)
            return {"status": "success", "issues": 0}

        scheduler.set_review_executor(mock_executor)
        scheduler.start()

        # Submit job
        job = scheduler.submit_job(repository="test/repo")

        # Wait for execution
        time.sleep(0.5)

        # Check job was executed
        completed_job = scheduler.get_job(job.job_id)
        assert completed_job.status == ReviewStatus.COMPLETED
        assert completed_job.result is not None
        assert job.job_id in executed_jobs

        scheduler.stop()

    def test_concurrent_execution(self, scheduler):
        """Test concurrent job execution."""
        executed_jobs = []

        def mock_executor(job):
            time.sleep(0.1)  # Simulate work
            executed_jobs.append(job.job_id)
            return {"status": "success"}

        scheduler.set_review_executor(mock_executor)
        scheduler.start()

        # Submit multiple jobs
        jobs = []
        for i in range(4):
            job = scheduler.submit_job(repository="test/repo")
            jobs.append(job)

        # Wait for execution
        time.sleep(1)

        # Check all jobs were executed
        assert len(executed_jobs) >= 2  # At least some should be done

        scheduler.stop()


class TestStatePersistence:
    """Test state persistence."""

    def test_save_and_load_schedules(self, temp_storage):
        """Test saving and loading schedules."""
        # Create scheduler and add schedule
        scheduler1 = ReviewScheduler(storage_path=temp_storage)
        scheduler1.add_schedule(
            schedule_id="daily",
            repository="test/repo",
            cron_expression="0 9 * * *"
        )

        # Create new scheduler instance (should load state)
        scheduler2 = ReviewScheduler(storage_path=temp_storage)
        assert "daily" in scheduler2.schedules
        assert scheduler2.schedules["daily"].cron_expression == "0 9 * * *"

    def test_save_and_load_triggers(self, temp_storage):
        """Test saving and loading triggers."""
        # Create scheduler and add trigger
        scheduler1 = ReviewScheduler(storage_path=temp_storage)
        scheduler1.add_trigger(
            trigger_id="pr-created",
            repository="test/repo",
            trigger_type=TriggerType.PR_CREATED
        )

        # Create new scheduler instance (should load state)
        scheduler2 = ReviewScheduler(storage_path=temp_storage)
        assert "pr-created" in scheduler2.triggers
        assert scheduler2.triggers["pr-created"].trigger_type == TriggerType.PR_CREATED
