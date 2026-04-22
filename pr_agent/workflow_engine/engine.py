"""
Workflow orchestration system for code review processes.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json
from pathlib import Path
import uuid


class StepType(Enum):
    """Type of workflow step."""
    REVIEW = "review"
    APPROVAL = "approval"
    QUALITY_CHECK = "quality_check"
    SECURITY_SCAN = "security_scan"
    TEST = "test"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConditionOperator(Enum):
    """Condition operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"


@dataclass
class Condition:
    """A condition for conditional execution."""
    field: str
    operator: ConditionOperator
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the condition against context."""
        actual_value = context.get(self.field)

        if self.operator == ConditionOperator.EQUALS:
            return actual_value == self.value
        elif self.operator == ConditionOperator.NOT_EQUALS:
            return actual_value != self.value
        elif self.operator == ConditionOperator.GREATER_THAN:
            return actual_value > self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return actual_value < self.value
        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in str(actual_value)
        elif self.operator == ConditionOperator.NOT_CONTAINS:
            return self.value not in str(actual_value)

        return False


@dataclass
class WorkflowStep:
    """A step in a workflow."""
    step_id: str
    name: str
    type: StepType
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    parallel: bool = False
    timeout: Optional[int] = None
    retry_count: int = 0
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def can_execute(self, context: Dict[str, Any], completed_steps: List[str]) -> bool:
        """Check if step can be executed."""
        # Check dependencies
        for dep in self.depends_on:
            if dep not in completed_steps:
                return False

        # Check conditions
        for condition in self.conditions:
            if not condition.evaluate(context):
                return False

        return True


@dataclass
class Workflow:
    """A workflow definition."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """A workflow execution instance."""
    execution_id: str
    workflow_id: str
    workflow: Workflow
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """Workflow orchestration engine."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize workflow engine."""
        self.storage_path = storage_path or Path(".pr_agent/workflows")
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.step_handlers: Dict[StepType, Callable] = {}

        # Load existing workflows
        if self.storage_path.exists():
            self._load_workflows()

    def register_step_handler(self, step_type: StepType, handler: Callable):
        """Register a handler for a step type."""
        self.step_handlers[step_type] = handler

    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())

        # Convert step dicts to WorkflowStep objects
        workflow_steps = []
        for step_data in steps:
            conditions = []
            for cond_data in step_data.get("conditions", []):
                conditions.append(Condition(
                    field=cond_data["field"],
                    operator=ConditionOperator(cond_data["operator"]),
                    value=cond_data["value"]
                ))

            step = WorkflowStep(
                step_id=step_data["step_id"],
                name=step_data["name"],
                type=StepType(step_data["type"]),
                config=step_data.get("config", {}),
                depends_on=step_data.get("depends_on", []),
                conditions=conditions,
                parallel=step_data.get("parallel", False),
                timeout=step_data.get("timeout"),
                retry_count=step_data.get("retry_count", 0)
            )
            workflow_steps.append(step)

        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            metadata=metadata or {}
        )

        self.workflows[workflow_id] = workflow
        self._save_workflow(workflow)

        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        return list(self.workflows.values())

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id not in self.workflows:
            return False

        del self.workflows[workflow_id]

        # Delete file
        workflow_file = self.storage_path / f"{workflow_id}.json"
        if workflow_file.exists():
            workflow_file.unlink()

        return True

    def start_execution(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Start a workflow execution."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow=workflow,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            context=context or {}
        )

        self.executions[execution_id] = execution

        return execution

    def execute_step(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep
    ) -> bool:
        """Execute a single step."""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc)
        execution.current_step = step.step_id

        try:
            # Get handler for step type
            handler = self.step_handlers.get(step.type)
            if not handler:
                raise ValueError(f"No handler registered for step type {step.type}")

            # Execute handler
            result = handler(step, execution.context)

            # Update step
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
            step.result = result

            # Update context with result
            if result:
                execution.context.update(result)

            execution.completed_steps.append(step.step_id)

            return True

        except Exception as e:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now(timezone.utc)
            step.error = str(e)
            execution.failed_steps.append(step.step_id)

            return False

    def run_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Run a complete workflow."""
        execution = self.start_execution(workflow_id, context)

        try:
            # Get all steps
            steps = execution.workflow.steps

            # Execute steps
            while True:
                # Find executable steps
                executable_steps = []
                for step in steps:
                    if step.status == StepStatus.PENDING:
                        if step.can_execute(execution.context, execution.completed_steps):
                            executable_steps.append(step)

                if not executable_steps:
                    break

                # Execute steps (parallel if marked)
                parallel_steps = [s for s in executable_steps if s.parallel]
                sequential_steps = [s for s in executable_steps if not s.parallel]

                # Execute parallel steps
                for step in parallel_steps:
                    self.execute_step(execution, step)

                # Execute sequential steps
                for step in sequential_steps:
                    success = self.execute_step(execution, step)
                    if not success and step.retry_count == 0:
                        # Stop on failure if no retries
                        execution.status = WorkflowStatus.FAILED
                        execution.completed_at = datetime.now(timezone.utc)
                        return execution

            # Check if all steps completed
            all_completed = all(
                s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
                for s in steps
            )

            if all_completed:
                execution.status = WorkflowStatus.COMPLETED
            else:
                execution.status = WorkflowStatus.FAILED

            execution.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.context["error"] = str(e)

        return execution

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get an execution by ID."""
        return self.executions.get(execution_id)

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowExecution]:
        """List executions."""
        executions = list(self.executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        return executions

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        if execution.status != WorkflowStatus.RUNNING:
            return False

        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)

        return True

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed execution status."""
        execution = self.executions.get(execution_id)
        if not execution:
            return {}

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "current_step": execution.current_step,
            "completed_steps": execution.completed_steps,
            "failed_steps": execution.failed_steps,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "type": step.type.value,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": step.error
                }
                for step in execution.workflow.steps
            ]
        }

    def _save_workflow(self, workflow: Workflow):
        """Save workflow to disk."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        workflow_file = self.storage_path / f"{workflow.workflow_id}.json"

        data = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "type": step.type.value,
                    "config": step.config,
                    "depends_on": step.depends_on,
                    "conditions": [
                        {
                            "field": c.field,
                            "operator": c.operator.value,
                            "value": c.value
                        }
                        for c in step.conditions
                    ],
                    "parallel": step.parallel,
                    "timeout": step.timeout,
                    "retry_count": step.retry_count
                }
                for step in workflow.steps
            ],
            "created_at": workflow.created_at.isoformat(),
            "metadata": workflow.metadata
        }

        with open(workflow_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_workflows(self):
        """Load workflows from disk."""
        for workflow_file in self.storage_path.glob("*.json"):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    steps = []
                    for step_data in data["steps"]:
                        conditions = []
                        for cond_data in step_data.get("conditions", []):
                            conditions.append(Condition(
                                field=cond_data["field"],
                                operator=ConditionOperator(cond_data["operator"]),
                                value=cond_data["value"]
                            ))

                        step = WorkflowStep(
                            step_id=step_data["step_id"],
                            name=step_data["name"],
                            type=StepType(step_data["type"]),
                            config=step_data.get("config", {}),
                            depends_on=step_data.get("depends_on", []),
                            conditions=conditions,
                            parallel=step_data.get("parallel", False),
                            timeout=step_data.get("timeout"),
                            retry_count=step_data.get("retry_count", 0)
                        )
                        steps.append(step)

                    workflow = Workflow(
                        workflow_id=data["workflow_id"],
                        name=data["name"],
                        description=data["description"],
                        steps=steps,
                        created_at=datetime.fromisoformat(data["created_at"]),
                        metadata=data.get("metadata", {})
                    )

                    self.workflows[workflow.workflow_id] = workflow
            except Exception:
                pass


# Global workflow engine instance
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get global workflow engine instance."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
