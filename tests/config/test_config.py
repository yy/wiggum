"""Consolidated tests for .wiggum.toml configuration.

Tests config reading/writing for all sections: [security], [loop], [output], [session].
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from wiggum.agents import AgentResult, get_available_agents
from wiggum.cli import app
from wiggum.config import read_config, write_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


# --- Parameterized tests for reading single config values ---


@pytest.mark.parametrize(
    "config_content,section,key,expected",
    [
        # [loop] section
        ("[loop]\nmax_iterations = 25\n", "loop", "max_iterations", 25),
        (
            '[loop]\ntasks_file = "CUSTOM_TASKS.md"\n',
            "loop",
            "tasks_file",
            "CUSTOM_TASKS.md",
        ),
        (
            '[loop]\nprompt_file = "MY-PROMPT.md"\n',
            "loop",
            "prompt_file",
            "MY-PROMPT.md",
        ),
        ('[loop]\nagent = "codex"\n', "loop", "agent", "codex"),
        # [output] section
        ('[output]\nlog_file = "loop.log"\n', "output", "log_file", "loop.log"),
        ("[output]\nverbose = true\n", "output", "verbose", True),
        ("[output]\nverbose = false\n", "output", "verbose", False),
        # [session] section
        ("[session]\ncontinue_session = true\n", "session", "continue_session", True),
        ("[session]\ncontinue_session = false\n", "session", "continue_session", False),
    ],
    ids=[
        "loop-max_iterations",
        "loop-tasks_file",
        "loop-prompt_file",
        "loop-agent",
        "output-log_file",
        "output-verbose-true",
        "output-verbose-false",
        "session-continue-true",
        "session-continue-false",
    ],
)
def test_read_config_value(
    tmp_path: Path, config_content: str, section: str, key: str, expected
) -> None:
    """read_config returns correct value from specified section."""
    os.chdir(tmp_path)
    (tmp_path / ".wiggum.toml").write_text(config_content)

    config = read_config()

    assert config.get(section, {}).get(key) == expected


def test_read_all_sections(tmp_path: Path) -> None:
    """read_config returns all sections when present."""
    config_content = """[security]
yolo = true
allow_paths = "src/"

[loop]
max_iterations = 50
agent = "gemini"

[output]
log_file = "loop.log"
verbose = true

[session]
continue_session = true
"""
    os.chdir(tmp_path)
    (tmp_path / ".wiggum.toml").write_text(config_content)

    config = read_config()

    assert config.get("security", {}).get("yolo") is True
    assert config.get("loop", {}).get("max_iterations") == 50
    assert config.get("loop", {}).get("agent") == "gemini"
    assert config.get("output", {}).get("verbose") is True
    assert config.get("session", {}).get("continue_session") is True


# --- Parameterized tests for writing config values ---


@pytest.mark.parametrize(
    "config_dict,expected_section,expected_content",
    [
        # [loop] section
        (
            {"security": {"yolo": False}, "loop": {"max_iterations": 15}},
            "[loop]",
            "max_iterations = 15",
        ),
        (
            {"security": {"yolo": False}, "loop": {"agent": "codex"}},
            "[loop]",
            'agent = "codex"',
        ),
        # [output] section
        (
            {"security": {"yolo": False}, "output": {"verbose": True}},
            "[output]",
            "verbose = true",
        ),
        (
            {"security": {"yolo": False}, "output": {"log_file": "output.log"}},
            "[output]",
            'log_file = "output.log"',
        ),
        # [session] section
        (
            {"security": {"yolo": False}, "session": {"continue_session": True}},
            "[session]",
            "continue_session = true",
        ),
        (
            {"security": {"yolo": False}, "session": {"continue_session": False}},
            "[session]",
            "continue_session = false",
        ),
    ],
    ids=[
        "loop-max_iterations",
        "loop-agent",
        "output-verbose",
        "output-log_file",
        "session-continue-true",
        "session-continue-false",
    ],
)
def test_write_config_value(
    tmp_path: Path, config_dict: dict, expected_section: str, expected_content: str
) -> None:
    """write_config writes correct value to specified section."""
    os.chdir(tmp_path)

    write_config(config_dict)

    content = (tmp_path / ".wiggum.toml").read_text()
    assert expected_section in content
    assert expected_content in content


def test_write_all_sections(tmp_path: Path) -> None:
    """write_config writes all sections together."""
    os.chdir(tmp_path)

    write_config(
        {
            "security": {"yolo": True, "allow_paths": "src/"},
            "loop": {"max_iterations": 20, "agent": "codex"},
            "output": {"log_file": "loop.log", "verbose": True},
            "session": {"continue_session": True},
        }
    )

    content = (tmp_path / ".wiggum.toml").read_text()
    assert "[security]" in content
    assert "[loop]" in content
    assert "[output]" in content
    assert "[session]" in content
    assert "yolo = true" in content
    assert "max_iterations = 20" in content
    assert 'agent = "codex"' in content
    assert 'log_file = "loop.log"' in content
    assert "verbose = true" in content
    assert "continue_session = true" in content


# --- Tests for config values used in run command ---


class TestRunCommandConfig:
    """Tests for applying config values in run command."""

    def _setup_project(
        self, tmp_path: Path, config_content: str = ""
    ) -> tuple[Path, Path]:
        """Set up a minimal project for run command tests."""
        os.chdir(tmp_path)
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")
        if config_content:
            (tmp_path / ".wiggum.toml").write_text(config_content)
        return prompt_file, tasks_file

    # --- max_iterations tests ---

    def test_max_iterations_from_config(self, tmp_path: Path) -> None:
        """run uses max_iterations from config."""
        self._setup_project(tmp_path, "[loop]\nmax_iterations = 3\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "3 iterations" in result.output
        assert result.exit_code == 0

    def test_max_iterations_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI --max-iterations flag overrides config."""
        self._setup_project(tmp_path, "[loop]\nmax_iterations = 100\n")

        result = runner.invoke(app, ["run", "--dry-run", "-n", "5"])

        assert "5 iterations" in result.output
        assert result.exit_code == 0

    # --- tasks_file tests ---

    def test_tasks_file_from_config(self, tmp_path: Path) -> None:
        """run uses tasks_file from config."""
        os.chdir(tmp_path)
        (tmp_path / "LOOP-PROMPT.md").write_text("test prompt")
        (tmp_path / "CUSTOM_TASKS.md").write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        (tmp_path / ".wiggum.toml").write_text(
            '[loop]\ntasks_file = "CUSTOM_TASKS.md"\n'
        )

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "CUSTOM_TASKS.md" in result.output
        assert result.exit_code == 0

    def test_tasks_file_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI --tasks flag overrides config."""
        os.chdir(tmp_path)
        (tmp_path / "LOOP-PROMPT.md").write_text("test prompt")
        cli_tasks = tmp_path / "CLI_TASKS.md"
        cli_tasks.write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        (tmp_path / ".wiggum.toml").write_text(
            '[loop]\ntasks_file = "CONFIG_TASKS.md"\n'
        )

        result = runner.invoke(app, ["run", "--dry-run", "--tasks", str(cli_tasks)])

        assert "CLI_TASKS.md" in result.output
        assert result.exit_code == 0

    # --- prompt_file tests ---

    def test_prompt_file_from_config(self, tmp_path: Path) -> None:
        """run uses prompt_file from config."""
        os.chdir(tmp_path)
        (tmp_path / "MY-PROMPT.md").write_text("custom prompt content")
        (tmp_path / "TASKS.md").write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        (tmp_path / ".wiggum.toml").write_text('[loop]\nprompt_file = "MY-PROMPT.md"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "custom prompt content" in result.output
        assert result.exit_code == 0

    def test_prompt_file_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI -f flag overrides config prompt_file."""
        os.chdir(tmp_path)
        cli_prompt = tmp_path / "cli-prompt.md"
        cli_prompt.write_text("cli prompt content")
        (tmp_path / "config-prompt.md").write_text("config prompt content")
        (tmp_path / "TASKS.md").write_text("# Tasks\n\n## Done\n\n- [x] done\n")
        (tmp_path / ".wiggum.toml").write_text(
            '[loop]\nprompt_file = "config-prompt.md"\n'
        )

        result = runner.invoke(app, ["run", "--dry-run", "-f", str(cli_prompt)])

        assert "cli prompt content" in result.output
        assert result.exit_code == 0

    # --- log_file tests ---

    def test_log_file_from_config(self, tmp_path: Path) -> None:
        """run uses log_file from config."""
        self._setup_project(tmp_path, '[output]\nlog_file = "loop.log"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "loop.log" in result.output
        assert result.exit_code == 0

    def test_log_file_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI --log-file flag overrides config."""
        self._setup_project(tmp_path, '[output]\nlog_file = "config.log"\n')

        result = runner.invoke(app, ["run", "--dry-run", "--log-file", "cli.log"])

        assert "cli.log" in result.output
        assert result.exit_code == 0

    # --- verbose tests ---

    def test_verbose_from_config(self, tmp_path: Path) -> None:
        """run uses verbose from config."""
        self._setup_project(tmp_path, "[output]\nverbose = true\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "Progress tracking: enabled" in result.output
        assert result.exit_code == 0

    def test_verbose_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI -v flag overrides config verbose."""
        self._setup_project(tmp_path, "[output]\nverbose = false\n")

        result = runner.invoke(app, ["run", "--dry-run", "-v"])

        assert "Progress tracking: enabled" in result.output
        assert result.exit_code == 0

    # --- agent tests ---

    def test_agent_from_config(self, tmp_path: Path) -> None:
        """run uses agent from config."""
        prompt_file, tasks_file = self._setup_project(
            tmp_path, '[loop]\nagent = "gemini"\n'
        )

        mock_agent = MagicMock()
        mock_agent.name = "gemini"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent) as mock_get_agent:
            result = runner.invoke(app, ["run", "-n", "1"])

        assert result.exit_code == 0
        mock_get_agent.assert_called_with("gemini")

    def test_agent_cli_overrides_config(self, tmp_path: Path) -> None:
        """CLI --agent flag overrides config."""
        prompt_file, tasks_file = self._setup_project(
            tmp_path, '[loop]\nagent = "gemini"\n'
        )

        mock_agent = MagicMock()
        mock_agent.name = "codex"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent) as mock_get_agent:
            result = runner.invoke(app, ["run", "-n", "1", "--agent", "codex"])

        assert result.exit_code == 0
        mock_get_agent.assert_called_with("codex")

    def test_default_agent_is_claude(self, tmp_path: Path) -> None:
        """Default agent when not specified is claude."""
        prompt_file, tasks_file = self._setup_project(tmp_path)

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent) as mock_get_agent:
            result = runner.invoke(app, ["run", "-n", "1"])

        assert result.exit_code == 0
        mock_get_agent.assert_called_with(None)

    # --- session tests ---

    def test_continue_session_from_config(self, tmp_path: Path) -> None:
        """run uses continue_session from config."""
        prompt_file, tasks_file = self._setup_project(
            tmp_path, "[session]\ncontinue_session = true\n"
        )

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        # Add a second task
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        assert call_count == 2
        # Second call should have -c flag
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-c" in second_call_args

    def test_reset_flag_overrides_config(self, tmp_path: Path) -> None:
        """CLI --reset flag overrides continue_session=true in config."""
        prompt_file, tasks_file = self._setup_project(
            tmp_path, "[session]\ncontinue_session = true\n"
        )

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run", "--reset"])

        assert result.exit_code == 0
        # --reset should override config - NO call should have -c
        for call_args in mock_run.call_args_list:
            args = call_args[0][0]
            assert "-c" not in args

    def test_continue_flag_overrides_config(self, tmp_path: Path) -> None:
        """CLI --continue flag overrides continue_session=false in config."""
        prompt_file, tasks_file = self._setup_project(
            tmp_path, "[session]\ncontinue_session = false\n"
        )

        call_count = 0

        def mock_subprocess_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            elif call_count == 2:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        with patch(
            "wiggum.agents_claude.subprocess.run", side_effect=mock_subprocess_run
        ) as mock_run:
            result = runner.invoke(app, ["run", "--continue"])

        assert result.exit_code == 0
        # CLI flag should override config - second call should have -c
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-c" in second_call_args

    # --- dry-run display tests ---

    def test_dry_run_shows_defaults(self, tmp_path: Path) -> None:
        """Dry run uses defaults when no config file exists."""
        os.chdir(tmp_path)
        (tmp_path / "LOOP-PROMPT.md").write_text("test prompt")
        (tmp_path / "TASKS.md").write_text("# Tasks\n\n## Done\n\n- [x] done\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        assert "10 iterations" in result.output
        assert "TASKS.md" in result.output
        assert result.exit_code == 0

    def test_dry_run_shows_session_mode_from_config(self, tmp_path: Path) -> None:
        """Dry run shows continue mode from config."""
        self._setup_project(tmp_path, "[session]\ncontinue_session = true\n")

        result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "continue" in result.output.lower()

    @pytest.mark.parametrize(
        "agent_name",
        ["claude", "codex", "gemini"],
    )
    def test_dry_run_shows_agent(self, tmp_path: Path, agent_name: str) -> None:
        """Dry run shows selected agent."""
        self._setup_project(tmp_path)

        result = runner.invoke(app, ["run", "--dry-run", "--agent", agent_name])

        assert result.exit_code == 0
        assert f"Agent: {agent_name}" in result.output

    def test_dry_run_shows_agent_from_config(self, tmp_path: Path) -> None:
        """Dry run shows agent from config file."""
        self._setup_project(tmp_path, '[loop]\nagent = "gemini"\n')

        result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "Agent: gemini" in result.output


class TestAgentErrorHandling:
    """Tests for error handling with invalid agent names."""

    def test_unknown_agent_shows_error(self, tmp_path: Path) -> None:
        """Unknown agent name should show error with available agents."""
        os.chdir(tmp_path)
        (tmp_path / "LOOP-PROMPT.md").write_text("test prompt")
        (tmp_path / "TASKS.md").write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        result = runner.invoke(app, ["run", "-n", "1", "--agent", "unknown_agent"])

        assert result.exit_code == 1
        assert "Unknown agent" in result.output or "unknown_agent" in result.output


class TestAvailableAgents:
    """Tests for listing available agents."""

    def test_get_available_agents_returns_registered(self) -> None:
        """get_available_agents should return list of registered agent names."""
        agents = get_available_agents()

        assert isinstance(agents, list)
        assert "claude" in agents
        assert "codex" in agents
        assert "gemini" in agents
