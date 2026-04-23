"""
Code Review Orchestration Engine

Provides advanced workflow orchestration for automated code reviews with support for:
- Workflow definition and execution
- Task scheduling and dependencies
- Conditional execution and branching
- Parallel processing
- Error handling and retry logic
- State management and persistence
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import json
import uuid
from pathlib import Path


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task types"""
    ACTION = "action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    WAIT = "wait"


@dataclass
class TaskDefinition:
    """Task definition in a workflow"""
    task_id: str
    name: str
    task_type: TaskType
    action: Optional[str] = None
    condition: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    timeout: Optional[int] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    on_failure: Optional[str] = None  # Task to run on failure


@dataclass
class TaskExecution:
    """Task execution state"""
    task_id: str
    execution_id: str
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_attempts: int = 0


@dataclass
class WorkflowDefinition:
    """Workflow definition"""
    workflow_id: str
    name: str
    description: str
    tasks: List[TaskDefinition]
    variables: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkflowExecution:
    """Workflow execution state"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    task_executions: Dict[str, TaskExecution] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class OrchestrationEngine:
    """
    Orchestration engine for automated code review workflows
    """

    def __init__(self, storage_path: str = ".pr_agent/orchestration"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.task_handlers: Dict[str, Callable] = {}

        self._load_workflows()

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition"""
        self.workflows[workflow.workflow_id] = workflow
        self._save_workflow(workflow)

    def register_task_handler(self, action: str, handler: Callable) -> None:
        """Register a task handler function"""
        self.task_handlers[action] = handler

    def start_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Start a workflow execution"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        execution_id = str(uuid.uuid4())

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            context=context or {}
        )

        # Initialize task executions
        for task in workflow.tasks:
            execution.task_executions[task.task_id] = TaskExecution(
                task_id=task.task_id,
                execution_id=execution_id,
                status=TaskStatus.PENDING
            )

        self.executions[execution_id] = execution
        self._save_execution(execution)

        # Start execution
        self._execute_workflow(execution_id)

        return execution

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID"""
        return self.executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution"""
        execution = self.executions.get(execution_id)
        if not execution or execution.status != WorkflowStatus.RUNNING:
            return False

        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        self._save_execution(execution)
        return True

    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all registered workflows"""
        return list(self.workflows.values())

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowExecution]:
        """List workflow executions with optional filters"""
        executions = list(self.executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        return executions

    def _execute_workflow(self, execution_id: str) -> None:
        """Execute a workflow"""
        execution = self.executions[execution_id]
        workflow = self.workflows[execution.workflow_id]

        try:
            # Build dependency graph
            ready_tasks = self._get_ready_tasks(execution, workflow)

            while ready_tasks and execution.status == WorkflowStatus.RUNNING:
                # Execute ready tasks
                for task_def in ready_tasks:
                    self._execute_task(execution, task_def)

                # Check if workflow is complete
                if self._is_workflow_complete(execution):
                    # Check for failures first
                    failed_tasks = [
                        t for t in execution.task_executions.values()
                        if t.status == TaskStatus.FAILED
                    ]
                    if failed_tasks:
                        execution.status = WorkflowStatus.FAILED
                        execution.error = f"{len(failed_tasks)} task(s) failed"
                    else:
                        execution.status = WorkflowStatus.COMPLETED
                    execution.completed_at = datetime.now(timezone.utc)
                    break

                # Get next batch of ready tasks
                ready_tasks = self._get_ready_tasks(execution, workflow)

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = str(e)

        finally:
            self._save_execution(execution)

    def _execute_task(
        self,
        execution: WorkflowExecution,
        task_def: TaskDefinition
    ) -> None:
        """Execute a single task"""
        task_exec = execution.task_executions[task_def.task_id]
        task_exec.status = TaskStatus.RUNNING
        task_exec.started_at = datetime.now(timezone.utc)

        try:
            if task_def.task_type == TaskType.CONDITION:
                # Evaluate condition
                result = self._evaluate_condition(
                    task_def.condition,
                    execution.context
                )
                task_exec.result = result
                task_exec.status = TaskStatus.COMPLETED

            elif task_def.task_type == TaskType.ACTION:
                # Execute action
                if task_def.action not in self.task_handlers:
                    raise ValueError(f"No handler for action: {task_def.action}")

                handler = self.task_handlers[task_def.action]
                result = handler(task_def.parameters, execution.context)
                task_exec.result = result
                task_exec.status = TaskStatus.COMPLETED

            elif task_def.task_type == TaskType.WAIT:
                # Wait task (simulated)
                task_exec.status = TaskStatus.COMPLETED

            else:
                task_exec.status = TaskStatus.SKIPPED

        except Exception as e:
            task_exec.status = TaskStatus.FAILED
            task_exec.error = str(e)

            # Handle retry
            if task_exec.retry_attempts < task_def.retry_count:
                task_exec.retry_attempts += 1
                task_exec.status = TaskStatus.PENDING

        finally:
            task_exec.completed_at = datetime.now(timezone.utc)
            self._save_execution(execution)

    def _get_ready_tasks(
        self,
        execution: WorkflowExecution,
        workflow: WorkflowDefinition
    ) -> List[TaskDefinition]:
        """Get tasks that are ready to execute"""
        ready = []

        for task_def in workflow.tasks:
            task_exec = execution.task_executions[task_def.task_id]

            # Skip if not pending
            if task_exec.status != TaskStatus.PENDING:
                continue

            # Check dependencies
            deps_satisfied = all(
                execution.task_executions[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task_def.depends_on
            )

            if deps_satisfied:
                ready.append(task_def)

        return ready

    def _is_workflow_complete(self, execution: WorkflowExecution) -> bool:
        """Check if workflow execution is complete"""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.FAILED)
            for t in execution.task_executions.values()
        )

    def _evaluate_condition(
        self,
        condition: Optional[str],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition expression"""
        if not condition:
            return True

        # Simple condition evaluation (can be extended)
        try:
            return eval(condition, {"context": context})
        except Exception:
            return False

    def _save_workflow(self, workflow: WorkflowDefinition) -> None:
        """Save workflow definition to disk"""
        file_path = self.storage_path / f"workflow_{workflow.workflow_id}.json"
        with open(file_path, 'w') as f:
            json.dump({
                'workflow_id': workflow.workflow_id,
                'name': workflow.name,
                'description': workflow.description,
                'tasks': [
                    {
                        'task_id': t.task_id,
                        'name': t.name,
                        'task_type': t.task_type.value,
                        'action': t.action,
                        'condition': t.condition,
                        'depends_on': t.depends_on,
                        'retry_count': t.retry_count,
                        'timeout': t.timeout,
                        'parameters': t.parameters,
                        'on_failure': t.on_failure
                    }
                    for t in workflow.tasks
                ],
                'variables': workflow.variables,
                'timeout': workflow.timeout,
                'created_at': workflow.created_at.isoformat()
            }, f, indent=2)

    def _save_execution(self, execution: WorkflowExecution) -> None:
        """Save execution state to disk"""
        file_path = self.storage_path / f"execution_{execution.execution_id}.json"
        with open(file_path, 'w') as f:
            json.dump({
                'execution_id': execution.execution_id,
                'workflow_id': execution.workflow_id,
                'status': execution.status.value,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'task_executions': {
                    tid: {
                        'task_id': t.task_id,
                        'execution_id': t.execution_id,
                        'status': t.status.value,
                        'started_at': t.started_at.isoformat() if t.started_at else None,
                        'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                        'result': t.result,
                        'error': t.error,
                        'retry_attempts': t.retry_attempts
                    }
                    for tid, t in execution.task_executions.items()
                },
                'context': execution.context,
                'error': execution.error
            }, f, indent=2)

    def _load_workflows(self) -> None:
        """Load workflows from disk"""
        for file_path in self.storage_path.glob("workflow_*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    workflow = WorkflowDefinition(
                        workflow_id=data['workflow_id'],
                        name=data['name'],
                        description=data['description'],
                        tasks=[
                            TaskDefinition(
                                task_id=t['task_id'],
                                name=t['name'],
                                task_type=TaskType(t['task_type']),
                                action=t.get('action'),
                                condition=t.get('condition'),
                                depends_on=t.get('depends_on', []),
                                retry_count=t.get('retry_count', 0),
                                timeout=t.get('timeout'),
                                parameters=t.get('parameters', {}),
                                on_failure=t.get('on_failure')
                            )
                            for t in data['tasks']
                        ],
                        variables=data.get('variables', {}),
                        timeout=data.get('timeout'),
                        created_at=datetime.fromisoformat(data['created_at'])
                    )
                    self.workflows[workflow.workflow_id] = workflow
            except Exception:
                pass


# Global instance
_engine: Optional[OrchestrationEngine] = None


def get_orchestration_engine() -> OrchestrationEngine:
    """Get the global orchestration engine instance"""
    global _engine
    if _engine is None:
        _engine = OrchestrationEngine()
    return _engine
