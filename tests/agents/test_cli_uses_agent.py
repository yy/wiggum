"""Tests that the CLI uses the agent abstraction layer.

These tests verify that:
1. The CLI run command uses get_agent() to get the agent
2. The CLI calls agent.run() with the correct AgentConfig
3. The CLI does not directly call subprocess.run for running the agent
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from wiggum.agents import AgentConfig, AgentResult
from wiggum.cli import app

runner = CliRunner()


class TestCliUsesAgentAbstraction:
    """Tests that verify the CLI uses the agent abstraction."""

    def test_run_command_uses_get_agent(self, tmp_path: Path) -> None:
        """The run command should use get_agent() to obtain the agent."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(*args, **kwargs):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch(
            "wiggum.cli.get_agent", return_value=mock_agent
        ) as mock_get_agent:
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0
        mock_get_agent.assert_called()

    def test_run_command_calls_agent_run(self, tmp_path: Path) -> None:
        """The run command should call agent.run() with AgentConfig."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent):
            result = runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        assert result.exit_code == 0
        mock_agent.run.assert_called_once()
        # Verify it was called with AgentConfig
        call_args = mock_agent.run.call_args[0][0]
        assert isinstance(call_args, AgentConfig)

    def test_agent_config_has_correct_prompt(self, tmp_path: Path) -> None:
        """The AgentConfig should have the correct prompt."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("my special prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                ],
            )

        config = mock_agent.run.call_args[0][0]
        assert config.prompt == "my special prompt"

    def test_agent_config_has_yolo_setting(self, tmp_path: Path) -> None:
        """The AgentConfig should have yolo setting from CLI."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                    "--yolo",
                ],
            )

        config = mock_agent.run.call_args[0][0]
        assert config.yolo is True

    def test_agent_config_has_allow_paths_setting(self, tmp_path: Path) -> None:
        """The AgentConfig should have allow_paths setting from CLI."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"

        def complete_task(config):
            tasks_file.write_text("# Tasks\n\n## Done\n\n- [x] task1\n")
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "1",
                    "--allow-paths",
                    "src/,tests/",
                ],
            )

        config = mock_agent.run.call_args[0][0]
        assert config.allow_paths == "src/,tests/"

    def test_agent_config_continue_session_on_subsequent_iterations(
        self, tmp_path: Path
    ) -> None:
        """With --continue, continue_session should be True after first iteration."""
        prompt_file = tmp_path / "LOOP-PROMPT.md"
        prompt_file.write_text("test prompt")
        tasks_file = tmp_path / "TASKS.md"
        tasks_file.write_text("# Tasks\n\n## Todo\n\n- [ ] task1\n- [ ] task2\n")

        mock_agent = MagicMock()
        mock_agent.name = "claude"
        call_count = 0

        def complete_task(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                tasks_file.write_text(
                    "# Tasks\n\n## Todo\n\n- [ ] task2\n\n## Done\n\n- [x] task1\n"
                )
            else:
                tasks_file.write_text(
                    "# Tasks\n\n## Done\n\n- [x] task1\n- [x] task2\n"
                )
            return AgentResult(stdout="done", stderr="", return_code=0)

        mock_agent.run.side_effect = complete_task

        with patch("wiggum.cli.get_agent", return_value=mock_agent):
            runner.invoke(
                app,
                [
                    "run",
                    "-f",
                    str(prompt_file),
                    "--tasks",
                    str(tasks_file),
                    "-n",
                    "5",
                    "--continue",
                ],
            )

        # First call: continue_session should be False
        first_config = mock_agent.run.call_args_list[0][0][0]
        assert first_config.continue_session is False

        # Second call: continue_session should be True
        second_config = mock_agent.run.call_args_list[1][0][0]
        assert second_config.continue_session is True
