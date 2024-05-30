#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Orchestrators for launching docker containers.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import NamedTemporaryFile
from typing import Iterable, List

# vendor libraries
import click

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.crypto import crypto
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.dev_mode import wrap_dev_mode

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class Orchestrator:
    """
    Interface for Orchestrators. Use a subclass, all methods in this class raise NotImplementedError.

    Raises:
        NotImplementedError: If any of these methods are called directly.
    """

    def start(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Starts Docker containers (services). Optionally accepts a tuple of service names to start.

        Args:
            cli_context (CliContext): The current CLI context.
            service_names (tuple[str,...], optional): Names of the services to start. If not provided, starts all services.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def shutdown(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Stops Docker containers (services). Optionally accepts a tuple of service names to shutdown.

        Args:
            cli_context (CliContext): The current CLI context.
            service_names (tuple[str,...], optional): Names of the services to shutdown. If not provided, shuts down all services.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def status(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Gets the status of Docker containers (services). Optionally accepts a tuple of service names to get the status of.

        Args:
            cli_context (CliContext): The current CLI context.
            service_names (tuple[str,...], optional): Names of the services to get the status of. If not provided, gets the status of all services.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def task(
        self,
        cli_context: CliContext,
        service_name: str,
        extra_args: Iterable[str],
        detached: bool = False,
    ) -> CompletedProcess:
        """
        Runs a specified Docker container which is expected to exit
        upon completing a short-lived task.

        Args:
            cli_context (CliContext): The current CLI context.
            service_name (str): Name of the container to run.
            extra_args (Iterable[str]): Extra arguments for running the container.
            detached (bool): Optional - defaults to False. Whether the task should run in `--detached` mode or not.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def exec(
        self,
        cli_context: CliContext,
        service_name: str,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ) -> CompletedProcess:
        """
        Executes a command in a running container.

        Args:
            cli_context (CliContext): The current CLI context.
            service_name (str): Name of the container to be acted upon.
            command (str): The command to be executed, along with any arguments.
            stdin_input (str): Optional - defaults to None. String passed through to the stdin of the exec command.
            capture_output (bool): Optional - defaults to False. True to capture stdout/stderr for the run command.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def get_logs_command(self) -> click.Command:
        """
        Returns a click command which streams logs for Docker containers.

        Args:
            cli_context (CliContext): The current CLI context.

        Returns:
            click.Command: Command for streaming logs.
        """
        raise NotImplementedError

    def get_additional_commands(self) -> Iterable[click.Command]:
        """
        Returns any additional commands supported by this orchestrator.

        Returns:
            Iterable[click.Command]: Additional orchestrator specific commands.
        """
        return ()

    def get_name(self) -> str:
        """
        Returns the name of this orchestrator.

        Returns:
            str: the name of this orchestrator.
        """
        raise NotImplementedError

    def verify_service_names(
        self, cli_context: CliContext, service_names: tuple[str, ...]
    ) -> bool:
        """
        Checks whether a list of named services exist. Returns True if all services exist, otherwise returns False.

        Args:
            cli_context (CliContext): The current CLI context.
            service_names (tuple[str,...]): Names of the services.

        Returns:
            bool: if the services exists.
        """
        raise NotImplementedError

    def get_disabled_commands(self) -> list[str]:
        """
        Returns the list of default appcli commands which this orchestrator wants to disable.
        E.g. ['init', 'backup'].

        This allows orchestrators to prevent commands being run which are not supported.

        Returns:
            list[str]: The disabled command names.
        """
        return []


class DockerComposeOrchestrator(Orchestrator):
    """
    Uses Docker Compose to orchestrate containers.
    """

    def __init__(
        self,
        docker_compose_file: Path = Path("docker-compose.yml"),
        docker_compose_override_directory: Path = Path("docker-compose.override.d/"),
        docker_compose_task_file: Path = Path("docker-compose.tasks.yml"),
        docker_compose_task_override_directory: Path = Path(
            "docker-compose.tasks.override.d/"
        ),
    ):
        """
        Creates a new instance of an orchestrator for docker-compose-based applications.

        Args:
            docker_compose_file (Path): Path to a docker compose file containing long-running services. Path is relative
                to the generated configuration directory.
            docker_compose_override_directory (Path, optional): Path to a directory containing any additional
                docker-compose override files. Overrides are applied in alphanumeric order of filename. Path is relative
                to the generated configuration directory.
            docker_compose_task_file (Path): Path to a docker compose file containing services to be run as short-lived
                tasks. Path is relative to the generated configuration directory.
            docker_compose_task_override_directory (Path): Path to a directory containing any additional
                docker-compose override files for services used as tasks. Path is relative to the generated
                configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_directory = docker_compose_override_directory
        self.docker_compose_task_file = docker_compose_task_file
        self.docker_compose_task_override_directory = (
            docker_compose_task_override_directory
        )

    def start(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        command = ("up", "-d")
        if service_names is not None and len(service_names) > 0:
            command += service_names
        return self.__compose_service(cli_context, command)

    def shutdown(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        if service_names is not None and len(service_names) > 0:
            # We cannot use the 'down' command as it removes more than just the specified service (by design).
            # https://github.com/docker/compose/issues/5420
            # `-fsv` flags mean forcibly stop the container before removing, and delete attached anonymous volumes
            command = ("rm", "-fsv") + service_names
            return self.__compose_service(cli_context, command)
        return self.__compose_service(cli_context, ("down",))

    def status(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        command = ("ps", "-a")
        if service_names is not None and len(service_names) > 0:
            command += service_names
        return self.__compose_service(cli_context, command)

    def task(
        self,
        cli_context: CliContext,
        service_name: str,
        extra_args: Iterable[str],
        detached: bool = False,
    ) -> CompletedProcess:
        command = ["run"]  # Command is: run [OPTIONS] --rm TASK [ARGS]
        if detached:
            command.append("-d")
        command.append("--rm")
        command.append(service_name)
        command.extend(list(extra_args))
        return self.__compose_task(cli_context, command)

    def exec(
        self,
        cli_context: CliContext,
        service_name: str,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ) -> CompletedProcess:
        cmd = ["exec"]  # Command is: exec SERVICE COMMAND
        # If there's stdin_input being piped to the command, we need to provide
        # the -T flag to `docker-compose`: https://github.com/docker/compose/issues/7306
        if stdin_input is not None:
            cmd.append("-T")
        cmd.append(service_name)
        cmd.extend(list(command))
        return self.__compose_service(cli_context, cmd, stdin_input, capture_output)

    def verify_service_names(
        self, cli_context: CliContext, service_names: tuple[str, ...]
    ) -> bool:
        if service_names is None or len(service_names) == 0:
            return True
        command = ["config", "--services"]
        result = self.__compose_service(cli_context, command, capture_output=True)
        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(
                f"An unexpected error occured while verifying services. Error: {error_msg}"
            )
            return False

        # Converts the byte type into list of names, and removes trailing empty string
        valid_service_names = result.stdout.decode().split("\n")[:-1]
        logger.debug("Valid Services: %s", ", ".join(valid_service_names))
        return service_name_verifier(service_names, valid_service_names)

    def get_logs_command(self):
        @click.command(
            help="Prints logs from all services (or the ones specified).",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.option(
            "--lines",
            "-n",
            help="Output the last NUM lines instead of all.",
            type=click.STRING,
            required=False,
            default="all",
        )
        @click.argument("service", nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, lines, service):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_LOGS
            )
            subcommand = ["logs", "--follow", f"--tail={lines}"]
            subcommand.extend(service)
            result = self.__compose_service(cli_context, subcommand)
            sys.exit(result.returncode)

        return logs

    def get_additional_commands(self):
        @click.command(help="List the status of services.")
        @click.pass_context
        def ps(ctx):
            result = self.__compose_service(ctx.obj, ("ps",))
            sys.exit(result.returncode)

        @click.command(
            help="Runs a docker compose command.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("command", nargs=-1, type=click.UNPROCESSED)
        def compose(ctx, command):
            result = self.__compose_service(ctx.obj, command)
            sys.exit(result.returncode)

        return (
            ps,
            compose,
        )

    def get_name(self):
        return "compose"

    def __compose_service(
        self,
        cli_context: CliContext,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_file,
            self.docker_compose_override_directory,
            stdin_input=stdin_input,
            capture_output=capture_output,
        )

    def __compose_task(
        self,
        cli_context: CliContext,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_task_file,
            self.docker_compose_task_override_directory,
            stdin_input=stdin_input,
            capture_output=capture_output,
        )


class DockerSwarmOrchestrator(Orchestrator):
    """
    Uses Docker Swarm to orchestrate containers.
    """

    def __init__(
        self,
        docker_compose_file: Path = Path("docker-compose.yml"),
        docker_compose_override_directory: Path = Path("docker-compose.override.d/"),
        docker_compose_task_file: Path = Path("docker-compose.tasks.yml"),
        docker_compose_task_override_directory: Path = Path(
            "docker-compose.tasks.override.d/"
        ),
    ):
        """
        Creates a new instance of an orchestrator for docker swarm applications.

        Args:
            docker_compose_file (Path): Path to a docker compose file containing long-running services. Path is relative
                to the generated configuration directory.
            docker_compose_override_directory (Path, optional): Path to a directory containing any additional
                docker-compose override files. Overrides are applied in alphanumeric order of filename. Path is relative
                to the generated configuration directory.
            docker_compose_task_file (Path): Path to a docker compose file containing services to be run as short-lived
                tasks. Path is relative to the generated configuration directory.
            docker_compose_task_override_directory (Path): Path to a directory containing any additional
                docker-compose override files for services used as tasks. Path is relative to the generated
                configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_directory = docker_compose_override_directory
        self.docker_compose_task_file = docker_compose_task_file
        self.docker_compose_task_override_directory = (
            docker_compose_task_override_directory
        )

    def start(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        if service_names is not None and len(service_names) > 0:
            logger.error(
                "Docker Swarm orchestrator cannot start individual services. Attempted to start [%s].",
                service_names,
            )
            return CompletedProcess(args=None, returncode=1)

        subcommand = ["deploy"]
        compose_files = decrypt_docker_compose_files(
            cli_context,
            self.docker_compose_file,
            self.docker_compose_override_directory,
        )
        if len(compose_files) == 0:
            logger.error(
                "No valid docker compose files were found. Expected file [%s] or files in directory [%s]",
                self.docker_compose_file,
                self.docker_compose_override_directory,
            )
            return CompletedProcess(args=None, returncode=1)
        for compose_file in compose_files:
            subcommand.extend(("--compose-file", str(compose_file)))

        return self.__docker_stack(cli_context, subcommand)

    def shutdown(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        if service_names is not None and len(service_names) > 0:
            logger.error(
                "Docker Swarm orchestrator cannot stop individual services. Attempted to shutdown [%s].",
                service_names,
            )
            return CompletedProcess(args=None, returncode=1)

        return self.__docker_stack(cli_context, ("rm",))

    def status(
        self, cli_context: CliContext, service_names: tuple[str, ...] = None
    ) -> CompletedProcess:
        if service_names is not None and len(service_names) > 0:
            logger.error(
                "Docker Swarm orchestrator cannot check the status of individual services. Attempted to get the status of [%s].",
                service_names,
            )
            return CompletedProcess(args=None, returncode=1)

        return self.__docker_stack(cli_context, ("ps",))

    def task(
        self,
        cli_context: CliContext,
        service_name: str,
        extra_args: Iterable[str],
        detached: bool = False,
    ) -> CompletedProcess:
        command = ["run"]  # Command is: run [OPTIONS] --rm TASK [ARGS]
        if detached:
            command.append("-d")
        command.append("--rm")
        command.append(service_name)
        command.extend(list(extra_args))
        return self.__compose_task(cli_context, command)

    def exec(
        self,
        cli_context: CliContext,
        service_name: str,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ) -> CompletedProcess:
        # Running 'docker exec' on containers in a docker swarm is non-trivial
        # due to the distributed nature of docker swarm, and the fact there could
        # be replicas of a single service.
        raise NotImplementedError

    def verify_service_names(
        self, cli_context: CliContext, service_names: tuple[str, ...]
    ) -> bool:
        if service_names is None or len(service_names) == 0:
            return True
        subcommand = ["config", "--services"]
        result = self.__docker_stack(cli_context, subcommand, capture_output=True)
        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(
                f"An unexpected error occured while verifying services. Error: {error_msg}"
            )
            return False

        # Converts the byte type into list of names, and removes trailing empty string
        valid_service_names = result.stdout.decode().split("\n")[:-1]
        logger.debug("Valid Services: %s", ", ".join(valid_service_names))
        return service_name_verifier(service_names, valid_service_names)

    def get_logs_command(self):
        @click.command(
            help="Prints logs from the specified service.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.option(
            "--lines",
            "-n",
            help="Output the last NUM lines instead of all.",
            type=click.STRING,
            required=False,
            default="all",
        )
        @click.argument("service", type=click.STRING)
        def logs(ctx, lines, service):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_LOGS
            )
            command = ["docker", "service", "logs", "--follow", f"--tail={lines}"]
            command.append(f"{cli_context.get_project_name()}_{service}")
            result = self.__exec_command(command)
            sys.exit(result.returncode)

        return logs

    def get_additional_commands(self):
        @click.command(help="List the status of services.")
        @click.pass_context
        def ps(ctx):
            result = self.__docker_stack(ctx.obj, ("ps",))
            sys.exit(result.returncode)

        @click.command(help="List the defined services.")
        @click.pass_context
        def ls(ctx):
            result = self.__docker_stack(ctx.obj, ("services",))
            sys.exit(result.returncode)

        return (ps, ls)

    def get_name(self):
        return "swarm"

    def __docker_stack(
        self, cli_context: CliContext, subcommand: Iterable[str]
    ) -> CompletedProcess:
        command = ["docker", "stack"]
        command.extend(subcommand)
        command.append(cli_context.get_project_name())
        return self.__exec_command(command)

    def __compose_task(
        self,
        cli_context: CliContext,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_task_file,
            self.docker_compose_task_override_directory,
            stdin_input=stdin_input,
            capture_output=capture_output,
        )

    def __exec_command(self, command: Iterable[str]) -> CompletedProcess:
        logger.debug("Running [%s]", " ".join(command))
        return subprocess.run(command, capture_output=False)


class HelmOrchestrator(Orchestrator):
    """
    Uses helm to provision a kubernetes backed helm chart.
    """

    DEV_CHART_VARIABLE_NAME = "DEV_MODE_HELM_CHART"
    " Name suffix for the DEV_MODE chart location variable. "

    def __init__(
        self,
        chart_location: Path = Path("cli/helm/chart"),
        helm_set_values_dir: Path = Path("cli/helm/set-values"),
        helm_set_files_dir: Path = Path("cli/helm/set-files"),
    ):
        """
        Creates a new instance of an orchestrator for helm-based applications.

        NOTE: All `Path` objects are relative to the configuration directory.

        Args:
            chart_location (Path): Path to the helm chart file/directory to deploy.
            helm_set_values_dir (Path): The directory containing all main `values.yaml` files.
                Defaults to: `${GENERATED_CONFIGURATION_DIR}/cli/helm/set-values`

                All files in this directory are applied with:
                    --values <file>

                See below for more details.

            helm_set_files_dir (Path): The directory containing all key-specific files.
                Defaults to: `${GENERATED_CONFIGURATION_DIR}/cli/helm/set-files`

                Take the following directory:

                ```
                ./
                ├── set-files/
                │  ├── baz/
                │  │  ├── foo.json
                │  │  └── qux.waldo.txt
                │  └── thud.bang.yml
                └── set-values/
                   ├── foo.yml
                   └── bar.txt
                ```

                This would result in the following arguments being passed to helm:

                ```
                --set-file baz.foo=cli/helm/set-files/baz/foo.json
                --set-file baz.qux=cli/helm/set-files/baz/qux.waldo.yml    # NOTE: Key is `qux` not `qux.waldo`.
                --set-file thud=cli/helm/set-files/thud.bang.yml           # NOTE: Key is `thud` not `thud.bang`.
                --values cli/helm/set-values/foo.yml
                --values cli/helm/set-values/bar.yml
                ```
        """
        self.chart_location = chart_location
        self.helm_set_values_dir = helm_set_values_dir
        self.helm_set_files_dir = helm_set_files_dir

    def start(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Installs (or upgrades) a helm chart inside the current kubernetes cluster.

        Args:
            cli_context (CliContext): The current CLI context.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        # Generate the command string.
        command = [
            "helm",
            "upgrade",
            "--install",
            "--namespace",
            cli_context.get_project_name(make_helm_safe=True),
            "--create-namespace",
        ]
        # Set values args.
        for arg in self.__generate_values_args(
            cli_context.get_generated_configuration_dir()
        ):
            command.append(arg)
        # Set release name.
        command.append(cli_context.get_project_name(make_helm_safe=True))
        # Set chart location.
        # If we're in `DEV_MODE` and `<APP-NAME>_DEV_MODE_HELM_CHART` is set, use that.
        if (
            cli_context.is_dev_mode
            and f"{cli_context.app_name_slug.upper()}_{HelmOrchestrator.DEV_CHART_VARIABLE_NAME}"
            in cli_context.dev_mode_variables.keys()
        ):
            with wrap_dev_mode():
                chart_location = cli_context.dev_mode_variables[
                    f"{cli_context.app_name_slug.upper()}_{HelmOrchestrator.DEV_CHART_VARIABLE_NAME}"
                ]
                logger.debug(
                    f"Found DEV_MODE chart. Ignoring bundled chart from `{self.chart_location}`"
                )
                logger.debug(f"Deploying chart from `{chart_location}`")
        # If not, then generate the absolute path to the `chart_location`.
        else:
            chart_location = (
                cli_context.get_generated_configuration_dir() / self.chart_location
            )
        command.append(chart_location)

        # Run the command.
        return self.__run_command(command)

    def shutdown(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Uninstalls a helm chart from current kubernetes cluster.

        Args:
            cli_context (CliContext): The current CLI context.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        # Generate the command string.
        command = [
            "helm",
            "uninstall",
            cli_context.get_project_name(make_helm_safe=True),
            "-n",
            cli_context.get_project_name(make_helm_safe=True),
        ]

        # Run the command.
        return self.__run_command(command)

    def status(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        """
        Get the status of the chart (through `helm status`).

        Args:
            cli_context (CliContext): The current CLI context.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        # Generate the command string.
        command = [
            "helm",
            "status",
            cli_context.get_project_name(make_helm_safe=True),
            "-n",
            cli_context.get_project_name(make_helm_safe=True),
        ]

        # Run the command.
        return self.__run_command(command)

    def task(
        self,
        cli_context: CliContext,
        service_name: str,
        extra_args: Iterable[str],
        detached: bool = False,
    ) -> CompletedProcess:
        logger.info("HelmOrchestrator has no services to run tasks for.")
        return None

    def exec(
        self,
        cli_context: CliContext,
        service_name: str,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ) -> CompletedProcess:
        logger.info("HelmOrchestrator does not support executing arbitrary commands.")
        return None

    def get_logs_command(self) -> click.Command:
        @click.command()
        def log():
            logger.info("HelmOrchestrator does not support getting logs.")
            return None

        return log

    def get_additional_commands(self):
        # TODO: AF-248: Add `kubectl`, `helm` and possibly `k9s` as commands that can be called.
        return []

    def get_name(self) -> str:
        return "helm"

    def verify_service_names(
        self, cli_context: CliContext, service_names: tuple[str, ...]
    ) -> bool:
        if service_names is None or len(service_names) == 0:
            return True
        logger.info("HelmOrchestrator has no services.")
        return False

    def get_disabled_commands(self) -> list[str]:
        # The `init` command is disabled because it's used to initialise additional services, and this orchestrator
        # The `task` command is disabled because helm is only used for install/upgrade/uninstall/downgrade operations.
        # has no services. NOTE: The `init` command will be removed in the future.
        return ["init", "task"]

    def __run_command(self, command: list[str]) -> CompletedProcess:
        """Run the given command and return the CompletedProcess.

        Args:
            command (list[str]): The command to execute.

        Returns:
            CompletedProcess: The execution result.
        """
        logger.debug(f"Executing {str(command)}")
        result = subprocess.run(command, capture_output=False)
        if result.returncode != 0:
            message = f"Unknown error from running: {str(command)}."
            logger.error(message)
            raise subprocess.CalledProcessError(
                result.returncode,
                command,
                result.stdout,
                result.stderr,
            )
        return result

    def __generate_values_args(self, generated_configuration_dir: Path) -> list[str]:
        """Recursively takes all the values files in the directories and generates an args array to
        pass to helm through either `--values` or `--set-file` (depending on the location).
        e.g:

            ["--values", "values.yaml", "--set-file", "path.to.foo=path/to/foo.yaml"...

        Args:
            generated_configuration_dir (Path): Generated configuration directory form the cli object, e.g:
                `cli_context.get_generated_configuration_dir()`

        Returns:
            list[str]: The arg list.
        """
        arg_list = []

        # Create all `--values` args.
        values_dir = generated_configuration_dir / self.helm_set_values_dir
        values = [
            file
            for file in list(values_dir.rglob("*"))
            if file.suffix in [".yml", ".yaml"]
        ]
        for file in values:
            arg_list.append("--values")
            arg_list.append(str(file))

        # Create all `--set-file` args.
        values_files_dir = generated_configuration_dir / self.helm_set_files_dir
        values_files = [
            file for file in list(values_files_dir.rglob("*")) if file.is_file()
        ]
        for file in values_files:
            # NOTE: Make path relative to `helm_values_files_dir` so we know which helm key to set it as.
            relative_file = file.relative_to(
                generated_configuration_dir / self.helm_set_files_dir
            )
            # Get the helm key in `dot.notation.to.value`
            key = ".".join(
                [*relative_file.parent.parts, relative_file.stem.split(".")[0]]
            )
            arg_list.append("--set-file")
            arg_list.append(f"{key}={file}")

        return arg_list


class NullOrchestrator(Orchestrator):
    """
    Orchestrator which has no services to orchestrate. This is useful for appcli applications which
    consist only of the launcher container containing various additional CLI command groups.
    """

    def start(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        logger.info("NullOrchestrator has no services to start.")
        return None

    def shutdown(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        logger.info("NullOrchestrator has no services to shutdown.")
        return None

    def status(
        self, cli_context: CliContext, service_name: tuple[str, ...] = None
    ) -> CompletedProcess:
        logger.info("NullOrchestrator has no services to get the status of.")
        return None

    def task(
        self,
        cli_context: CliContext,
        service_name: str,
        extra_args: Iterable[str],
        detached: bool = False,
    ) -> CompletedProcess:
        logger.info("NullOrchestrator has no services to run tasks for.")
        return None

    def exec(
        self,
        cli_context: CliContext,
        service_name: str,
        command: Iterable[str],
        stdin_input: str = None,
        capture_output: bool = False,
    ) -> CompletedProcess:
        logger.info(
            "NullOrchestrator has no running containers to execute commands in."
        )
        return None

    def get_logs_command(self) -> click.Command:
        @click.command()
        def log():
            logger.info("NullOrchestrator has no services to get logs of.")
            return None

        return log

    def get_name(self) -> str:
        return "null_orchestrator"

    def verify_service_names(
        self, cli_context: CliContext, service_names: tuple[str, ...]
    ) -> bool:
        if service_names is None or len(service_names) == 0:
            return True
        logger.info("NullOrchestrator has no services.")
        return False

    def get_disabled_commands(self) -> list[str]:
        # The `service` and `task` commands are disabled because they are used for managing and interacting with
        # services, and this orchestrator has no services.
        # The `init` command is disabled because it's used to initialise additional services, and this orchestrator
        # has no services. NOTE: The `init` command will be removed in the future.
        return ["init", "service", "task"]


# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def service_name_verifier(
    service_names: tuple[str, ...], valid_service_names: List[str]
) -> bool:
    """Verify all services exist.

    Args:
        service_names (tuple[str, ...]): The list of service names to check.
        valid_service_names [List[str]]: The list of valid service names.

    """
    invalid_service_names = set(service_names) - set(valid_service_names)

    for service_name in invalid_service_names:
        logger.error("Service [%s] does not exist", service_name)

    return len(invalid_service_names) == 0


def decrypt_docker_compose_files(
    cli_context: CliContext,
    docker_compose_file_relative_path: Path,
    docker_compose_override_directory_relative_path: Path,
) -> List[Path]:
    """Decrypt docker-compose and docker-compose override files.

    Args:
        cli_context (CliContext): The current CLI context.
        docker_compose_file_relative_path (Path): The relative path to the docker-compose file. Path is relative to the
            generated configuration directory.
        docker_compose_override_directory_relative_path (Path): The relative path to a directory containing
            docker-compose override files. Path is relative to the generated configuration directory.

    Returns:
        List[Path]: sorted list of absolute paths to decrypted docker-compose files. The first path is the decrypted
            docker-compose file, and the rest of the paths are the alphanumerically sorted docker compose override
            files in the docker compose override directory.
    """

    compose_files = []

    if docker_compose_file_relative_path is not None:
        docker_compose_file = cli_context.get_generated_configuration_dir().joinpath(
            docker_compose_file_relative_path
        )
        if os.path.isfile(docker_compose_file):
            compose_files.append(docker_compose_file)

    if docker_compose_override_directory_relative_path is not None:
        docker_compose_override_directory = (
            cli_context.get_generated_configuration_dir().joinpath(
                docker_compose_override_directory_relative_path
            )
        )
        if os.path.isdir(docker_compose_override_directory):
            docker_compose_override_files: List[Path] = [
                Path(os.path.join(docker_compose_override_directory, file))
                for file in os.listdir(docker_compose_override_directory)
                if os.path.isfile(os.path.join(docker_compose_override_directory, file))
            ]

            if len(docker_compose_override_files) > 0:
                docker_compose_override_files.sort()
                logger.debug(
                    "Detected docker compose override files [%s]",
                    docker_compose_override_files,
                )
                compose_files.extend(docker_compose_override_files)

    # decrypt files if key is available
    key_file = cli_context.get_key_file()
    decrypted_files = [
        decrypt_file(encrypted_file, key_file) for encrypted_file in compose_files
    ]
    return decrypted_files


def decrypt_file(encrypted_file: Path, key_file: Path) -> Path:
    """
    Decrypts the specified file using the supplied key.

    Args:
        encrypted_file (Path): File to decrypt.
        key_file (Path): Key to use for decryption.

    Returns:
        Path: Path to the decrypted file.
    """
    if not key_file.is_file():
        logger.info(
            "No decryption key found. [%s] will not be decrypted.", encrypted_file
        )
        return encrypted_file

    logger.debug("Decrypting file [%s] using [%s].", str(encrypted_file), key_file)
    decrypted_file: Path = Path(NamedTemporaryFile(delete=False).name)
    crypto.decrypt_values_in_file(encrypted_file, decrypted_file, key_file)
    return decrypted_file


def execute_compose(
    cli_context: CliContext,
    command: Iterable[str],
    docker_compose_file_relative_path: Path,
    docker_compose_override_directory_relative_path: Path,
    stdin_input: str = None,
    capture_output: bool = False,
) -> CompletedProcess:
    """Builds and executes a docker-compose command.

    Args:
        cli_context (CliContext): The current CLI context.
        command (Iterable[str]): The command to execute with docker-compose.
        docker_compose_file_relative_path (Path): The relative path to the docker-compose file. Path is relative to the
            generated configuration directory.
        docker_compose_override_directory_relative_path (Path): The relative path to a directory containing
            docker-compose override files. Path is relative to the generated configuration directory.
        stdin_input (str): Optional - defaults to None. String passed through to the subprocess via stdin.
        capture_output (bool): Optional - defaults to False. True to capture stdout/stderr for the run command.

    Returns:
        CompletedProcess: The completed process and its exit code.
    """
    docker_compose_command = [
        "docker",
        "compose",
        "--project-name",
        cli_context.get_project_name(),
    ]

    compose_files = decrypt_docker_compose_files(
        cli_context,
        docker_compose_file_relative_path,
        docker_compose_override_directory_relative_path,
    )

    if len(compose_files) == 0:
        logger.error(
            "No valid docker compose files were found. Expected file [%s] or files in directory [%s]",
            docker_compose_file_relative_path,
            docker_compose_override_directory_relative_path,
        )
        return CompletedProcess(args=None, returncode=1)

    for compose_file in compose_files:
        docker_compose_command.extend(("--file", str(compose_file)))

    if command is not None:
        docker_compose_command.extend(command)

    logger.debug(docker_compose_command)
    logger.debug("Running [%s]", " ".join(docker_compose_command))
    encoded_input = stdin_input.encode("utf-8") if stdin_input is not None else None
    logger.debug("Encoded input: [%s]", encoded_input)
    result = subprocess.run(
        docker_compose_command,
        capture_output=capture_output,
        input=encoded_input,
    )

    return result
