"""
Unit test for PollingState.try_mark_processing() race condition fix
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from pr_agent.storage.polling_state import PollingState


def test_try_mark_processing_prevents_duplicate():
    """Test that try_mark_processing prevents duplicate processing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = f.name
        json.dump({}, f)

    try:
        state = PollingState(state_file=state_file)

        repo_key = "TEST/repo"
        pr_id = 123
        pr_version = 1

        # First call should succeed
        result1 = state.try_mark_processing(repo_key, pr_id, pr_version, ["/review"])
        assert result1 is True, "First try_mark_processing should succeed"

        # Second call with same version should fail
        result2 = state.try_mark_processing(repo_key, pr_id, pr_version, ["/review"])
        assert result2 is False, "Second try_mark_processing should fail (already processing)"

        # Verify state
        pr_state = state.get_pr_state(repo_key, pr_id)
        assert pr_state is not None
        assert pr_state['version'] == pr_version
        assert pr_state['status'] == 'processing'

    finally:
        Path(state_file).unlink(missing_ok=True)


def test_try_mark_processing_allows_new_version():
    """Test that try_mark_processing allows processing new version"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = f.name
        json.dump({}, f)

    try:
        state = PollingState(state_file=state_file)

        repo_key = "TEST/repo"
        pr_id = 123

        # Process version 1
        result1 = state.try_mark_processing(repo_key, pr_id, 1, ["/review"])
        assert result1 is True

        # Mark as completed
        state.update_pr_state(repo_key, pr_id, 1, ["/review"], status="completed")

        # Try to process version 1 again - should fail
        result2 = state.try_mark_processing(repo_key, pr_id, 1, ["/review"])
        assert result2 is False

        # Try to process version 2 - should succeed
        result3 = state.try_mark_processing(repo_key, pr_id, 2, ["/review"])
        assert result3 is True

        # Verify state
        pr_state = state.get_pr_state(repo_key, pr_id)
        assert pr_state['version'] == 2
        assert pr_state['status'] == 'processing'

    finally:
        Path(state_file).unlink(missing_ok=True)


def test_try_mark_processing_respects_filtered():
    """Test that try_mark_processing respects filtered status"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = f.name
        json.dump({}, f)

    try:
        state = PollingState(state_file=state_file)

        repo_key = "TEST/repo"
        pr_id = 123
        pr_version = 1

        # Mark as filtered
        state.update_pr_state(repo_key, pr_id, pr_version, [], status="filtered")

        # Try to process - should fail
        result = state.try_mark_processing(repo_key, pr_id, pr_version, ["/review"])
        assert result is False

    finally:
        Path(state_file).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
