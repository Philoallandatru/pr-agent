import pytest

import pr_agent.git_providers as git_providers


def test_get_git_provider_with_context_reports_provider_and_cause(monkeypatch):
    class FailingProvider:
        def __init__(self, pr_url):
            raise RuntimeError("provider boom")

    old_provider = git_providers.get_settings().get("CONFIG.GIT_PROVIDER", None)
    old_provider_class = git_providers._GIT_PROVIDERS.get("bitbucket_server")
    git_providers._GIT_PROVIDERS["bitbucket_server"] = FailingProvider
    git_providers.get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

    try:
        with pytest.raises(ValueError) as exc_info:
            git_providers.get_git_provider_with_context("https://bitbucket.example.com/projects/P/repos/r/pull-requests/1")
    finally:
        if old_provider_class:
            git_providers._GIT_PROVIDERS["bitbucket_server"] = old_provider_class
        git_providers.get_settings().set("CONFIG.GIT_PROVIDER", old_provider)

    message = str(exc_info.value)
    assert "using provider 'bitbucket_server'" in message
    assert "provider boom" in message
