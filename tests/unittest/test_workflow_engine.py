"""Tests for workflow orchestration system."""

import pytest
import tempfile
from pathlib import Path
from pr_agent.workflow_engine import (
    WorkflowEngine,
    StepType,
    StepStatus,
    WorkflowStatus,
    ConditionOperator
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def engine(temp_storage):
    """Create workflow engine instance."""
    return WorkflowEngine(storage_path=temp_storage)


@pytest.fixture
def simple_workflow_steps():
    """Simple workflow steps."""
    return [
        {
            "step_id": "step1",
            "name": "Review Code",
            "type": "review",
            "config": {"reviewer": "alice"}
        },
        {
            "step_id": "step2",
            "name": "Run Tests",
            "type": "test",
            "depends_on": ["step1"]
        },
        {
            "step_id": "step3",
            "name": "Approve",
            "type": "approval",
            "depends_on": ["step2"]
        }
    ]


@pytest.fixture
def conditional_workflow_steps():
    """Workflow with conditional steps."""
    return [
        {
            "step_id": "step1",
            "name": "Quality Check",
            "type": "quality_check"
        },
        {
            "step_id": "step2",
            "name": "Security Scan",
            "type": "security_scan",
            "depends_on": ["step1"],
            "conditions": [
                {
                    "field": "quality_score",
                    "operator": "greater_than",
                    "value": 80
                }
            ]
        },
        {
            "step_id": "step3",
            "name": "Manual Review",
            "type": "review",
            "depends_on": ["step1"],
            "conditions": [
                {
                    "field": "quality_score",
                    "operator": "less_than",
                    "value": 80
                }
            ]
        }
    ]


class TestWorkflowCreation:
    """Test workflow creation."""

    def test_create_workflow(self, engine, simple_workflow_steps):
        """Test creating a workflow."""
        workflow = engine.create_workflow(
            name="Simple Review",
            description="A simple review workflow",
            steps=simple_workflow_steps
        )

        assert workflow.workflow_id is not None
        assert workflow.name == "Simple Review"
        assert len(workflow.steps) == 3
        assert workflow.status == WorkflowStatus.PENDING

    def test_workflow_persisted(self, engine, simple_workflow_steps):
        """Test workflow is persisted to disk."""
        workflow = engine.create_workflow(
            name="Test Workflow",
            description="Test",
            steps=simple_workflow_steps
        )

        workflow_file = engine.storage_path / f"{workflow.workflow_id}.json"
        assert workflow_file.exists()

    def test_get_workflow(self, engine, simple_workflow_steps):
        """Test getting a workflow."""
        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        retrieved = engine.get_workflow(workflow.workflow_id)
        assert retrieved is not None
        assert retrieved.workflow_id == workflow.workflow_id

    def test_list_workflows(self, engine, simple_workflow_steps):
        """Test listing workflows."""
        engine.create_workflow("Workflow 1", "Test", simple_workflow_steps)
        engine.create_workflow("Workflow 2", "Test", simple_workflow_steps)

        workflows = engine.list_workflows()
        assert len(workflows) == 2

    def test_delete_workflow(self, engine, simple_workflow_steps):
        """Test deleting a workflow."""
        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        result = engine.delete_workflow(workflow.workflow_id)
        assert result is True
        assert engine.get_workflow(workflow.workflow_id) is None


class TestStepHandlers:
    """Test step handler registration."""

    def test_register_handler(self, engine):
        """Test registering a step handler."""
        def test_handler(step, context):
            return {"result": "success"}

        engine.register_step_handler(StepType.REVIEW, test_handler)
        assert StepType.REVIEW in engine.step_handlers

    def test_handler_execution(self, engine, simple_workflow_steps):
        """Test handler is called during execution."""
        called = []

        def test_handler(step, context):
            called.append(step.step_id)
            return {"result": "success"}

        # Register handlers for all step types
        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        engine.run_workflow(workflow.workflow_id)

        assert len(called) == 3
        assert "step1" in called


class TestWorkflowExecution:
    """Test workflow execution."""

    def test_start_execution(self, engine, simple_workflow_steps):
        """Test starting a workflow execution."""
        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.start_execution(workflow.workflow_id)

        assert execution.execution_id is not None
        assert execution.workflow_id == workflow.workflow_id
        assert execution.status == WorkflowStatus.RUNNING

    def test_execution_with_context(self, engine, simple_workflow_steps):
        """Test execution with initial context."""
        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        context = {"pr_id": "123", "author": "alice"}
        execution = engine.start_execution(workflow.workflow_id, context)

        assert execution.context["pr_id"] == "123"
        assert execution.context["author"] == "alice"

    def test_run_workflow(self, engine, simple_workflow_steps):
        """Test running a complete workflow."""
        def test_handler(step, context):
            return {"step_result": f"{step.step_id}_done"}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)

        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 3
        assert execution.completed_at is not None

    def test_workflow_with_failure(self, engine, simple_workflow_steps):
        """Test workflow with step failure."""
        def failing_handler(step, context):
            if step.step_id == "step2":
                raise Exception("Test failure")
            return {"result": "success"}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, failing_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)

        assert execution.status == WorkflowStatus.FAILED
        assert "step2" in execution.failed_steps
        assert len(execution.completed_steps) == 1  # Only step1 completed


class TestDependencies:
    """Test step dependencies."""

    def test_sequential_execution(self, engine, simple_workflow_steps):
        """Test steps execute in order based on dependencies."""
        execution_order = []

        def tracking_handler(step, context):
            execution_order.append(step.step_id)
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, tracking_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        engine.run_workflow(workflow.workflow_id)

        assert execution_order == ["step1", "step2", "step3"]

    def test_parallel_execution(self, engine):
        """Test parallel step execution."""
        steps = [
            {
                "step_id": "step1",
                "name": "Step 1",
                "type": "review"
            },
            {
                "step_id": "step2",
                "name": "Step 2",
                "type": "test",
                "parallel": True
            },
            {
                "step_id": "step3",
                "name": "Step 3",
                "type": "security_scan",
                "parallel": True
            }
        ]

        def test_handler(step, context):
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.SECURITY_SCAN]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=steps
        )

        execution = engine.run_workflow(workflow.workflow_id)

        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 3


class TestConditions:
    """Test conditional execution."""

    def test_condition_evaluation(self, engine, conditional_workflow_steps):
        """Test condition evaluation."""
        def test_handler(step, context):
            if step.step_id == "step1":
                return {"quality_score": 85}
            return {}

        for step_type in [StepType.QUALITY_CHECK, StepType.SECURITY_SCAN, StepType.REVIEW]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=conditional_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)

        # step2 should execute (quality_score > 80)
        # step3 should not execute (quality_score not < 80)
        assert "step2" in execution.completed_steps
        assert "step3" not in execution.completed_steps

    def test_condition_operators(self, engine):
        """Test different condition operators."""
        from pr_agent.workflow_engine import Condition

        context = {
            "score": 85,
            "status": "approved",
            "tags": "python,review"
        }

        # Test EQUALS
        cond = Condition("status", ConditionOperator.EQUALS, "approved")
        assert cond.evaluate(context) is True

        # Test NOT_EQUALS
        cond = Condition("status", ConditionOperator.NOT_EQUALS, "rejected")
        assert cond.evaluate(context) is True

        # Test GREATER_THAN
        cond = Condition("score", ConditionOperator.GREATER_THAN, 80)
        assert cond.evaluate(context) is True

        # Test LESS_THAN
        cond = Condition("score", ConditionOperator.LESS_THAN, 90)
        assert cond.evaluate(context) is True

        # Test CONTAINS
        cond = Condition("tags", ConditionOperator.CONTAINS, "python")
        assert cond.evaluate(context) is True

        # Test NOT_CONTAINS
        cond = Condition("tags", ConditionOperator.NOT_CONTAINS, "java")
        assert cond.evaluate(context) is True


class TestExecutionManagement:
    """Test execution management."""

    def test_get_execution(self, engine, simple_workflow_steps):
        """Test getting an execution."""
        def test_handler(step, context):
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)
        retrieved = engine.get_execution(execution.execution_id)

        assert retrieved is not None
        assert retrieved.execution_id == execution.execution_id

    def test_list_executions(self, engine, simple_workflow_steps):
        """Test listing executions."""
        def test_handler(step, context):
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        engine.run_workflow(workflow.workflow_id)
        engine.run_workflow(workflow.workflow_id)

        executions = engine.list_executions()
        assert len(executions) == 2

    def test_list_executions_by_workflow(self, engine, simple_workflow_steps):
        """Test listing executions by workflow."""
        def test_handler(step, context):
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow1 = engine.create_workflow("W1", "Test", simple_workflow_steps)
        workflow2 = engine.create_workflow("W2", "Test", simple_workflow_steps)

        engine.run_workflow(workflow1.workflow_id)
        engine.run_workflow(workflow2.workflow_id)

        executions = engine.list_executions(workflow_id=workflow1.workflow_id)
        assert len(executions) == 1
        assert executions[0].workflow_id == workflow1.workflow_id

    def test_list_executions_by_status(self, engine, simple_workflow_steps):
        """Test listing executions by status."""
        def test_handler(step, context):
            if step.step_id == "step2":
                raise Exception("Fail")
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        engine.run_workflow(workflow.workflow_id)

        executions = engine.list_executions(status=WorkflowStatus.FAILED)
        assert len(executions) == 1

    def test_cancel_execution(self, engine, simple_workflow_steps):
        """Test cancelling an execution."""
        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.start_execution(workflow.workflow_id)
        result = engine.cancel_execution(execution.execution_id)

        assert result is True
        assert execution.status == WorkflowStatus.CANCELLED

    def test_get_execution_status(self, engine, simple_workflow_steps):
        """Test getting execution status."""
        def test_handler(step, context):
            return {}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)
        status = engine.get_execution_status(execution.execution_id)

        assert status["execution_id"] == execution.execution_id
        assert status["status"] == "completed"
        assert len(status["steps"]) == 3
        assert len(status["completed_steps"]) == 3


class TestPersistence:
    """Test workflow persistence."""

    def test_workflow_loaded_on_init(self, temp_storage, simple_workflow_steps):
        """Test workflows are loaded on initialization."""
        # Create engine and workflow
        engine1 = WorkflowEngine(storage_path=temp_storage)
        workflow = engine1.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        # Create new engine with same storage
        engine2 = WorkflowEngine(storage_path=temp_storage)

        # Workflow should be loaded
        loaded = engine2.get_workflow(workflow.workflow_id)
        assert loaded is not None
        assert loaded.name == "Test"
        assert len(loaded.steps) == 3


class TestContextPropagation:
    """Test context propagation through workflow."""

    def test_context_updated_by_steps(self, engine, simple_workflow_steps):
        """Test context is updated by step results."""
        def test_handler(step, context):
            return {f"{step.step_id}_result": "done"}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        execution = engine.run_workflow(workflow.workflow_id)

        assert "step1_result" in execution.context
        assert "step2_result" in execution.context
        assert "step3_result" in execution.context

    def test_context_available_to_later_steps(self, engine, simple_workflow_steps):
        """Test context from earlier steps is available to later steps."""
        contexts_seen = []

        def test_handler(step, context):
            contexts_seen.append(dict(context))
            return {f"{step.step_id}_data": step.step_id}

        for step_type in [StepType.REVIEW, StepType.TEST, StepType.APPROVAL]:
            engine.register_step_handler(step_type, test_handler)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=simple_workflow_steps
        )

        engine.run_workflow(workflow.workflow_id)

        # step2 should see step1's data
        assert "step1_data" in contexts_seen[1]
        # step3 should see both step1 and step2's data
        assert "step1_data" in contexts_seen[2]
        assert "step2_data" in contexts_seen[2]
