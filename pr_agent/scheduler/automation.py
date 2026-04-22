"""
Code Review Automation Scheduler

Automates code review workflows with scheduling, queuing, and event-driven triggers.
"""

import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from queue import PriorityQueue
import threading
import logging


logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Review trigger types."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PR_CREATED = "pr_created"
    PR_UPDATED = "pr_updated"
    COMMIT_PUSHED = "commit_pushed"
    BRANCH_UPDATED = "branch_updated"


class ReviewPriority(Enum):
    """Review priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ReviewStatus(Enum):
    """Review job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReviewJob:
    """Review job definition."""
    job_id: str
    repository: str
    pr_number: Optional[int]
    branch: Optional[str]
    commit_hash: Optional[str]
    trigger_type: TriggerType
    priority: ReviewPriority
    status: ReviewStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __lt__(self, other):
        """Compare jobs by priority for queue ordering."""
        # Higher priority value = higher priority
        return self.priority.value > other.priority.value


@dataclass
class ScheduleConfig:
    """Schedule configuration."""
    schedule_id: str
    repository: str
    cron_expression: str
    enabled: bool
    priority: ReviewPriority
    branches: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TriggerConfig:
    """Event trigger configuration."""
    trigger_id: str
    repository: str
    trigger_type: TriggerType
    enabled: bool
    priority: ReviewPriority
    filters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ReviewScheduler:
    """
    Code review automation scheduler.

    Features:
    - Job queue with priority scheduling
    - Cron-based scheduled reviews
    - Event-driven triggers
    - Concurrent execution control
    - Job persistence and recovery
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_concurrent: int = 3,
        job_timeout: int = 3600
    ):
        """
        Initialize scheduler.

        Args:
            storage_path: Path to store scheduler state
            max_concurrent: Maximum concurrent review jobs
            job_timeout: Job timeout in seconds
        """
        self.storage_path = storage_path or Path.home() / ".pr_agent" / "scheduler"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_concurrent = max_concurrent
        self.job_timeout = job_timeout

        # Job queue (priority queue)
        self.job_queue: PriorityQueue = PriorityQueue()

        # Active jobs
        self.active_jobs: Dict[str, ReviewJob] = {}

        # Job history
        self.job_history: List[ReviewJob] = []

        # Schedules and triggers
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.triggers: Dict[str, TriggerConfig] = {}

        # Review executor callback
        self.review_executor: Optional[Callable] = None

        # Worker threads
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()

        # Load state
        self._load_state()

    def set_review_executor(self, executor: Callable):
        """Set the review executor callback."""
        self.review_executor = executor

    def submit_job(
        self,
        repository: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        priority: ReviewPriority = ReviewPriority.NORMAL,
        pr_number: Optional[int] = None,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReviewJob:
        """
        Submit a review job.

        Args:
            repository: Repository identifier
            trigger_type: What triggered the review
            priority: Job priority
            pr_number: PR number if applicable
            branch: Branch name if applicable
            commit_hash: Commit hash if applicable
            metadata: Additional metadata

        Returns:
            Created review job
        """
        job_id = f"{repository}_{datetime.now(timezone.utc).timestamp()}"

        job = ReviewJob(
            job_id=job_id,
            repository=repository,
            pr_number=pr_number,
            branch=branch,
            commit_hash=commit_hash,
            trigger_type=trigger_type,
            priority=priority,
            status=ReviewStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata
        )

        # Add to queue
        with self.lock:
            job.status = ReviewStatus.QUEUED
            self.job_queue.put(job)
            self._save_state()

        logger.info(f"Submitted job {job_id} with priority {priority.name}")
        return job

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        with self.lock:
            # Check active jobs
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                if job.status == ReviewStatus.RUNNING:
                    job.status = ReviewStatus.CANCELLED
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    self.job_history.append(job)
                    del self.active_jobs[job_id]
                    self._save_state()
                    logger.info(f"Cancelled running job {job_id}")
                    return True

            # Check queue (need to rebuild queue without the job)
            # Note: This is inefficient but PriorityQueue doesn't support removal
            temp_jobs = []
            found = False
            while not self.job_queue.empty():
                job = self.job_queue.get()
                if job.job_id == job_id:
                    job.status = ReviewStatus.CANCELLED
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    self.job_history.append(job)
                    found = True
                    logger.info(f"Cancelled queued job {job_id}")
                else:
                    temp_jobs.append(job)

            # Rebuild queue
            for job in temp_jobs:
                self.job_queue.put(job)

            if found:
                self._save_state()

            return found

    def get_job(self, job_id: str) -> Optional[ReviewJob]:
        """Get job by ID."""
        with self.lock:
            # Check active jobs
            if job_id in self.active_jobs:
                return self.active_jobs[job_id]

            # Check queue (need to iterate without removing)
            temp_jobs = []
            found_job = None
            while not self.job_queue.empty():
                job = self.job_queue.get()
                temp_jobs.append(job)
                if job.job_id == job_id:
                    found_job = job

            # Rebuild queue
            for job in temp_jobs:
                self.job_queue.put(job)

            if found_job:
                return found_job

            # Check history
            for job in self.job_history:
                if job.job_id == job_id:
                    return job

        return None

    def list_jobs(
        self,
        status: Optional[ReviewStatus] = None,
        repository: Optional[str] = None,
        limit: int = 100
    ) -> List[ReviewJob]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by status
            repository: Filter by repository
            limit: Maximum number of jobs to return

        Returns:
            List of matching jobs
        """
        jobs = []

        with self.lock:
            # Add active jobs
            jobs.extend(self.active_jobs.values())

            # Add queued jobs
            temp_jobs = []
            while not self.job_queue.empty():
                job = self.job_queue.get()
                temp_jobs.append(job)
                jobs.append(job)

            # Rebuild queue
            for job in temp_jobs:
                self.job_queue.put(job)

            # Add history
            jobs.extend(self.job_history)

        # Apply filters
        if status:
            jobs = [j for j in jobs if j.status == status]
        if repository:
            jobs = [j for j in jobs if j.repository == repository]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def add_schedule(
        self,
        schedule_id: str,
        repository: str,
        cron_expression: str,
        priority: ReviewPriority = ReviewPriority.NORMAL,
        branches: Optional[List[str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScheduleConfig:
        """
        Add a scheduled review.

        Args:
            schedule_id: Unique schedule identifier
            repository: Repository to review
            cron_expression: Cron expression (e.g., "0 9 * * *")
            priority: Job priority
            branches: Branches to review (None = all)
            enabled: Whether schedule is enabled
            metadata: Additional metadata

        Returns:
            Created schedule configuration
        """
        schedule = ScheduleConfig(
            schedule_id=schedule_id,
            repository=repository,
            cron_expression=cron_expression,
            enabled=enabled,
            priority=priority,
            branches=branches,
            metadata=metadata
        )

        with self.lock:
            self.schedules[schedule_id] = schedule
            self._save_state()

        logger.info(f"Added schedule {schedule_id} for {repository}")
        return schedule

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        with self.lock:
            if schedule_id in self.schedules:
                del self.schedules[schedule_id]
                self._save_state()
                logger.info(f"Removed schedule {schedule_id}")
                return True
        return False

    def add_trigger(
        self,
        trigger_id: str,
        repository: str,
        trigger_type: TriggerType,
        priority: ReviewPriority = ReviewPriority.NORMAL,
        filters: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TriggerConfig:
        """
        Add an event trigger.

        Args:
            trigger_id: Unique trigger identifier
            repository: Repository to monitor
            trigger_type: Type of event to trigger on
            priority: Job priority
            filters: Event filters (e.g., branch patterns)
            enabled: Whether trigger is enabled
            metadata: Additional metadata

        Returns:
            Created trigger configuration
        """
        trigger = TriggerConfig(
            trigger_id=trigger_id,
            repository=repository,
            trigger_type=trigger_type,
            enabled=enabled,
            priority=priority,
            filters=filters,
            metadata=metadata
        )

        with self.lock:
            self.triggers[trigger_id] = trigger
            self._save_state()

        logger.info(f"Added trigger {trigger_id} for {repository}")
        return trigger

    def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a trigger."""
        with self.lock:
            if trigger_id in self.triggers:
                del self.triggers[trigger_id]
                self._save_state()
                logger.info(f"Removed trigger {trigger_id}")
                return True
        return False

    def list_schedules(self) -> List[ScheduleConfig]:
        """List all schedules."""
        with self.lock:
            return list(self.schedules.values())

    def list_triggers(self) -> List[TriggerConfig]:
        """List all triggers."""
        with self.lock:
            return list(self.triggers.values())

    def handle_event(
        self,
        event_type: TriggerType,
        repository: str,
        pr_number: Optional[int] = None,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ReviewJob]:
        """
        Handle an event and create jobs for matching triggers.

        Args:
            event_type: Type of event
            repository: Repository identifier
            pr_number: PR number if applicable
            branch: Branch name if applicable
            commit_hash: Commit hash if applicable
            metadata: Event metadata

        Returns:
            List of created jobs
        """
        # First, collect matching triggers (with lock)
        matching_triggers = []

        with self.lock:
            for trigger in self.triggers.values():
                if not trigger.enabled:
                    continue

                if trigger.repository != repository:
                    continue

                if trigger.trigger_type != event_type:
                    continue

                # Apply filters
                if trigger.filters:
                    if "branches" in trigger.filters and branch:
                        if branch not in trigger.filters["branches"]:
                            continue

                matching_triggers.append(trigger)

        # Then create jobs (without lock to avoid deadlock)
        jobs = []
        for trigger in matching_triggers:
            job = self.submit_job(
                repository=repository,
                trigger_type=event_type,
                priority=trigger.priority,
                pr_number=pr_number,
                branch=branch,
                commit_hash=commit_hash,
                metadata=metadata
            )
            jobs.append(job)

        return jobs

    def start(self):
        """Start the scheduler workers."""
        if self.running:
            return

        self.running = True

        # Start worker threads
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

        logger.info(f"Started scheduler with {self.max_concurrent} workers")

    def stop(self):
        """Stop the scheduler workers."""
        self.running = False

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        self.workers.clear()
        logger.info("Stopped scheduler")

    def _worker(self):
        """Worker thread that processes jobs from the queue."""
        while self.running:
            try:
                # Get job from queue (with timeout to check running flag)
                try:
                    job = self.job_queue.get(timeout=1)
                except:
                    continue

                # Execute job
                self._execute_job(job)

            except Exception as e:
                logger.error(f"Worker error: {e}")

    def _execute_job(self, job: ReviewJob):
        """Execute a review job."""
        with self.lock:
            job.status = ReviewStatus.RUNNING
            job.started_at = datetime.now(timezone.utc).isoformat()
            self.active_jobs[job.job_id] = job

        logger.info(f"Executing job {job.job_id}")

        try:
            # Call review executor
            if self.review_executor:
                result = self.review_executor(job)
                job.result = result
            else:
                logger.warning("No review executor configured")
                job.result = {"status": "skipped", "message": "No executor"}

            job.status = ReviewStatus.COMPLETED

        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            job.status = ReviewStatus.FAILED
            job.error = str(e)

        finally:
            with self.lock:
                job.completed_at = datetime.now(timezone.utc).isoformat()
                self.job_history.append(job)
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
                self._save_state()

    def _save_state(self):
        """Save scheduler state to disk."""
        # Convert enums to strings for JSON serialization
        def serialize_obj(obj):
            if isinstance(obj, dict):
                return {k: serialize_obj(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_obj(item) for item in obj]
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj

        state = {
            "schedules": {k: serialize_obj(asdict(v)) for k, v in self.schedules.items()},
            "triggers": {k: serialize_obj(asdict(v)) for k, v in self.triggers.items()},
            "job_history": [serialize_obj(asdict(j)) for j in self.job_history[-1000:]],  # Keep last 1000
        }

        state_file = self.storage_path / "state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load scheduler state from disk."""
        state_file = self.storage_path / "state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            # Load schedules
            for schedule_data in state.get("schedules", {}).values():
                schedule = ScheduleConfig(**schedule_data)
                self.schedules[schedule.schedule_id] = schedule

            # Load triggers
            for trigger_data in state.get("triggers", {}).values():
                trigger_data["trigger_type"] = TriggerType(trigger_data["trigger_type"])
                trigger_data["priority"] = ReviewPriority(trigger_data["priority"])
                trigger = TriggerConfig(**trigger_data)
                self.triggers[trigger.trigger_id] = trigger

            # Load job history
            for job_data in state.get("job_history", []):
                job_data["trigger_type"] = TriggerType(job_data["trigger_type"])
                job_data["priority"] = ReviewPriority(job_data["priority"])
                job_data["status"] = ReviewStatus(job_data["status"])
                job = ReviewJob(**job_data)
                self.job_history.append(job)

            logger.info("Loaded scheduler state")

        except Exception as e:
            logger.error(f"Failed to load state: {e}")


# Global scheduler instance
_scheduler: Optional[ReviewScheduler] = None


def get_scheduler(
    storage_path: Optional[Path] = None,
    max_concurrent: int = 3
) -> ReviewScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReviewScheduler(
            storage_path=storage_path,
            max_concurrent=max_concurrent
        )
    return _scheduler
