# Tests for module structure after refactoring


class TestModuleStructure:
    """Tests verifying the module organization after refactoring."""

    def test_config_module_exists_and_importable(self):
        """Config module should be importable."""
        from wiggum import config

        assert hasattr(config, "read_config")
        assert hasattr(config, "write_config")
        assert callable(config.read_config)
        assert callable(config.write_config)

    def test_tasks_module_exists_and_importable(self):
        """Tasks module should be importable."""
        from wiggum import tasks

        assert hasattr(tasks, "tasks_remaining")
        assert hasattr(tasks, "get_current_task")
        assert hasattr(tasks, "add_task_to_file")
        assert callable(tasks.tasks_remaining)
        assert callable(tasks.get_current_task)
        assert callable(tasks.add_task_to_file)

    def test_parsing_module_exists_and_importable(self):
        """Parsing module should be importable."""
        from wiggum import parsing

        assert hasattr(parsing, "parse_markdown_from_output")
        assert callable(parsing.parse_markdown_from_output)

    def test_runner_module_exists_and_importable(self):
        """Runner module should be importable."""
        from wiggum import runner

        assert hasattr(runner, "run_claude_for_planning")
        assert hasattr(runner, "get_file_changes")
        assert hasattr(runner, "write_log_entry")
        assert callable(runner.run_claude_for_planning)
        assert callable(runner.get_file_changes)
        assert callable(runner.write_log_entry)

    def test_cli_module_exists_and_importable(self):
        """CLI module should remain with the app."""
        from wiggum import cli

        assert hasattr(cli, "app")
        assert hasattr(cli, "run")
        assert hasattr(cli, "init")
        assert hasattr(cli, "add")

    def test_backwards_compatible_imports_from_cli(self):
        """Functions should still be importable from cli for backwards compat."""
        from wiggum.cli import (
            read_config,
            write_config,
            tasks_remaining,
            get_current_task,
            parse_markdown_from_output,
        )

        assert callable(read_config)
        assert callable(write_config)
        assert callable(tasks_remaining)
        assert callable(get_current_task)
        assert callable(parse_markdown_from_output)

    def test_agents_module_exists_and_importable(self):
        """Agents module should be importable."""
        from wiggum import agents

        assert hasattr(agents, "Agent")
        assert hasattr(agents, "AgentConfig")
        assert hasattr(agents, "AgentResult")
        assert hasattr(agents, "get_agent")
        assert hasattr(agents, "get_available_agents")
        assert callable(agents.get_agent)
        assert callable(agents.get_available_agents)
