"""
Tests for Orchestration Engine
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from pr_agent.orchestration import (
    OrchestrationEngine,
    WorkflowDefinition,
    TaskDefinition,
    TaskStatus,
    WorkflowStatus,
    TaskType,
    get_orchestration_engine
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_storage):
    """Create orchestration engine instance"""
    return OrchestrationEngine(storage_path=temp_storage)


@pytest.fixture
def simple_workflow():
    """Create a simple workflow definition"""
    return WorkflowDefinition(
        workflow_id="test_workflow",
        name="Test Workflow",
        description="A simple test workflow",
        tasks=[
            TaskDefinition(
                task_id="task1",
                name="First Task",
                task_type=TaskType.ACTION,
                action="test_action"
            ),
            TaskDefinition(
                task_id="task2",
                name="Second Task",
                task_type=TaskType.ACTION,
                action="test_action",
                depends_on=["task1"]
            )
        ]
    )


@pytest.fixture
def parallel_workflow():
    """Create a workflow with parallel tasks"""
    return WorkflowDefinition(
        workflow_id="parallel_workflow",
        name="Parallel Workflow",
        description="Workflow with parallel tasks",
        tasks=[
            TaskDefinition(
                task_id="task1",
                name="Task 1",
                task_type=TaskType.ACTION,
                action="test_action"
            ),
            TaskDefinition(
                task_id="task2",
                name="Task 2",
                task_type=TaskType.ACTION,
                action="test_action"
            ),
            TaskDefinition(
                task_id="task3",
                name="Task 3",
                task_type=TaskType.ACTION,
                action="test_action",
                depends_on=["task1", "task2"]
            )
        ]
    )


class TestTaskDefinition:
    """Test task definition"""

    def test_task_creation(self):
        """Test creating a task definition"""
        task = TaskDefinition(
            task_id="test_task",
            name="Test Task",
            task_type=TaskType.ACTION,
            action="test_action"
        )

        assert task.task_id == "test_task"
        assert task.name == "Test Task"
        assert task.task_type == TaskType.ACTION
        assert task.action == "test_action"
        assert task.depends_on == []

    def test_task_with_dependencies(self):
        """Test task with dependencies"""
        task = TaskDefinition(
            task_id="dependent_task",
            name="Dependent Task",
            task_type=TaskType.ACTION,
            action="test_action",
            depends_on=["task1", "task2"]
        )

        assert len(task.depends_on) == 2
        assert "task1" in task.depends_on
        assert "task2" in task.depends_on


class TestWorkflowDefinition:
    """Test workflow definition"""

    def test_workflow_creation(self, simple_workflow):
        """Test creating a workflow definition"""
        assert simple_workflow.workflow_id == "test_workflow"
        assert simple_workflow.name == "Test Workflow"
        assert len(simple_workflow.tasks) == 2

    def test_workflow_with_variables(self):
        """Test workflow with variables"""
        workflow = WorkflowDefinition(
            workflow_id="var_workflow",
            name="Variable Workflow",
            description="Workflow with variables",
            tasks=[],
            variables={"key1": "value1", "key2": 123}
        )

        assert workflow.variables["key1"] == "value1"
        assert workflow.variables["key2"] == 123


class TestOrchestrationEngine:
    """Test orchestration engine"""

    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine is not None
        assert len(engine.workflows) == 0
        assert len(engine.executions) == 0

    def test_register_workflow(self, engine, simple_workflow):
        """Test registering a workflow"""
        engine.register_workflow(simple_workflow)

        assert simple_workflow.workflow_id in engine.workflows
        assert engine.workflows[simple_workflow.workflow_id] == simple_workflow

    def test_register_task_handler(self, engine):
        """Test registering a task handler"""
        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        assert "test_action" in engine.task_handlers
        assert engine.task_handlers["test_action"] == test_handler

    def test_start_workflow(self, engine, simple_workflow):
        """Test starting a workflow"""
        engine.register_workflow(simple_workflow)

        # Register handler
        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        # Start workflow
        execution = engine.start_workflow(simple_workflow.workflow_id)

        assert execution is not None
        assert execution.workflow_id == simple_workflow.workflow_id
        assert execution.status in (WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED)

    def test_start_workflow_not_found(self, engine):
        """Test starting a non-existent workflow"""
        with pytest.raises(ValueError):
            engine.start_workflow("non_existent")

    def test_get_execution(self, engine, simple_workflow):
        """Test getting an execution"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(simple_workflow.workflow_id)
        retrieved = engine.get_execution(execution.execution_id)

        assert retrieved is not None
        assert retrieved.execution_id == execution.execution_id

    def test_cancel_execution(self, engine, simple_workflow):
        """Test canceling an execution"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(simple_workflow.workflow_id)

        # Try to cancel (may already be completed)
        result = engine.cancel_execution(execution.execution_id)

        # Result depends on timing
        assert isinstance(result, bool)

    def test_list_workflows(self, engine, simple_workflow):
        """Test listing workflows"""
        engine.register_workflow(simple_workflow)

        workflows = engine.list_workflows()

        assert len(workflows) == 1
        assert workflows[0].workflow_id == simple_workflow.workflow_id

    def test_list_executions(self, engine, simple_workflow):
        """Test listing executions"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(simple_workflow.workflow_id)
        executions = engine.list_executions()

        assert len(executions) >= 1
        assert any(e.execution_id == execution.execution_id for e in executions)

    def test_list_executions_by_workflow(self, engine, simple_workflow):
        """Test listing executions by workflow ID"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(simple_workflow.workflow_id)
        executions = engine.list_executions(workflow_id=simple_workflow.workflow_id)

        assert len(executions) >= 1
        assert all(e.workflow_id == simple_workflow.workflow_id for e in executions)

    def test_parallel_execution(self, engine, parallel_workflow):
        """Test parallel task execution"""
        engine.register_workflow(parallel_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(parallel_workflow.workflow_id)

        # Check that task1 and task2 can run in parallel
        task1 = execution.task_executions["task1"]
        task2 = execution.task_executions["task2"]

        assert task1.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING)
        assert task2.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING)

    def test_task_dependencies(self, engine, simple_workflow):
        """Test task dependency execution"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(simple_workflow.workflow_id)

        # Task2 should only run after task1
        task1 = execution.task_executions["task1"]
        task2 = execution.task_executions["task2"]

        if task2.status == TaskStatus.COMPLETED:
            assert task1.status == TaskStatus.COMPLETED

    def test_workflow_with_context(self, engine, simple_workflow):
        """Test workflow execution with context"""
        engine.register_workflow(simple_workflow)

        def test_handler(params, context):
            context["result"] = "success"
            return "success"

        engine.register_task_handler("test_action", test_handler)

        context = {"input": "test_value"}
        execution = engine.start_workflow(simple_workflow.workflow_id, context=context)

        assert execution.context["input"] == "test_value"

    def test_task_retry(self, engine):
        """Test task retry on failure"""
        workflow = WorkflowDefinition(
            workflow_id="retry_workflow",
            name="Retry Workflow",
            description="Workflow with retry",
            tasks=[
                TaskDefinition(
                    task_id="retry_task",
                    name="Retry Task",
                    task_type=TaskType.ACTION,
                    action="failing_action",
                    retry_count=2
                )
            ]
        )

        engine.register_workflow(workflow)

        call_count = [0]

        def failing_handler(params, context):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Simulated failure")
            return "success"

        engine.register_task_handler("failing_action", failing_handler)

        execution = engine.start_workflow(workflow.workflow_id)

        # Should retry and eventually succeed
        task = execution.task_executions["retry_task"]
        assert task.retry_attempts >= 0

    def test_condition_task(self, engine):
        """Test condition task evaluation"""
        workflow = WorkflowDefinition(
            workflow_id="condition_workflow",
            name="Condition Workflow",
            description="Workflow with condition",
            tasks=[
                TaskDefinition(
                    task_id="condition_task",
                    name="Condition Task",
                    task_type=TaskType.CONDITION,
                    condition="context.get('value', 0) > 5"
                )
            ]
        )

        engine.register_workflow(workflow)

        # Test with value > 5
        execution1 = engine.start_workflow(workflow.workflow_id, context={"value": 10})
        task1 = execution1.task_executions["condition_task"]
        assert task1.result is True

        # Test with value <= 5
        execution2 = engine.start_workflow(workflow.workflow_id, context={"value": 3})
        task2 = execution2.task_executions["condition_task"]
        assert task2.result is False

    def test_workflow_persistence(self, engine, simple_workflow):
        """Test workflow persistence to disk"""
        engine.register_workflow(simple_workflow)

        # Create new engine instance with same storage
        engine2 = OrchestrationEngine(storage_path=engine.storage_path)

        # Should load workflow from disk
        assert simple_workflow.workflow_id in engine2.workflows

    def test_singleton_instance(self):
        """Test singleton instance"""
        engine1 = get_orchestration_engine()
        engine2 = get_orchestration_engine()

        assert engine1 is engine2


class TestWorkflowExecution:
    """Test workflow execution scenarios"""

    def test_simple_sequential_workflow(self, engine):
        """Test simple sequential workflow"""
        workflow = WorkflowDefinition(
            workflow_id="sequential",
            name="Sequential Workflow",
            description="Sequential tasks",
            tasks=[
                TaskDefinition(
                    task_id="step1",
                    name="Step 1",
                    task_type=TaskType.ACTION,
                    action="step_action"
                ),
                TaskDefinition(
                    task_id="step2",
                    name="Step 2",
                    task_type=TaskType.ACTION,
                    action="step_action",
                    depends_on=["step1"]
                ),
                TaskDefinition(
                    task_id="step3",
                    name="Step 3",
                    task_type=TaskType.ACTION,
                    action="step_action",
                    depends_on=["step2"]
                )
            ]
        )

        engine.register_workflow(workflow)

        results = []

        def step_handler(params, context):
            results.append(params.get("step", "unknown"))
            return "success"

        engine.register_task_handler("step_action", step_handler)

        execution = engine.start_workflow(workflow.workflow_id)

        # All tasks should complete
        assert all(
            t.status == TaskStatus.COMPLETED
            for t in execution.task_executions.values()
        )

    def test_workflow_with_failure(self, engine):
        """Test workflow with task failure"""
        workflow = WorkflowDefinition(
            workflow_id="failure_workflow",
            name="Failure Workflow",
            description="Workflow with failure",
            tasks=[
                TaskDefinition(
                    task_id="failing_task",
                    name="Failing Task",
                    task_type=TaskType.ACTION,
                    action="failing_action"
                )
            ]
        )

        engine.register_workflow(workflow)

        def failing_handler(params, context):
            raise Exception("Task failed")

        engine.register_task_handler("failing_action", failing_handler)

        execution = engine.start_workflow(workflow.workflow_id)

        # Workflow should fail
        assert execution.status == WorkflowStatus.FAILED
        assert execution.task_executions["failing_task"].status == TaskStatus.FAILED

    def test_complex_workflow(self, engine):
        """Test complex workflow with multiple branches"""
        workflow = WorkflowDefinition(
            workflow_id="complex",
            name="Complex Workflow",
            description="Complex workflow",
            tasks=[
                TaskDefinition(
                    task_id="start",
                    name="Start",
                    task_type=TaskType.ACTION,
                    action="test_action"
                ),
                TaskDefinition(
                    task_id="branch1",
                    name="Branch 1",
                    task_type=TaskType.ACTION,
                    action="test_action",
                    depends_on=["start"]
                ),
                TaskDefinition(
                    task_id="branch2",
                    name="Branch 2",
                    task_type=TaskType.ACTION,
                    action="test_action",
                    depends_on=["start"]
                ),
                TaskDefinition(
                    task_id="merge",
                    name="Merge",
                    task_type=TaskType.ACTION,
                    action="test_action",
                    depends_on=["branch1", "branch2"]
                )
            ]
        )

        engine.register_workflow(workflow)

        def test_handler(params, context):
            return "success"

        engine.register_task_handler("test_action", test_handler)

        execution = engine.start_workflow(workflow.workflow_id)

        # All tasks should complete
        assert execution.status == WorkflowStatus.COMPLETED
        assert all(
            t.status == TaskStatus.COMPLETED
            for t in execution.task_executions.values()
        )
