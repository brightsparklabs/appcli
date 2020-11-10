#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Orchestrators for launching docker containers.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

import os
import sys

# standard libraries
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import NamedTemporaryFile
from typing import Iterable, List

# vendor libraries
import click

# local libraries
from appcli.crypto import crypto
from appcli.logger import logger
from appcli.models.cli_context import CliContext

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class Orchestrator:
    """
    Interface for Orchestrators. Use a subclass, all methods in this class raise NotImplementedError.

    Raises:
        NotImplementedError: If any of these methods are called directly.
    """

    def start(self, cli_context: CliContext, container: str = ()) -> CompletedProcess:
        """
        Starts Docker containers.

        Args:
            cli_context (CliContext): The current cli context.
            container (str, optional): Name of the container to start. Defaults to all containers.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        """
        Stops all Docker containers.

        Args:
            cli_context (CliContext): The current cli context.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def oneshot(
        self, cli_context: CliContext, service_name: str, extra_args: Iterable[str]
    ) -> CompletedProcess:
        """
        Runs a specified Docker container which is expected to exit
        upon completing a short-lived task.

        Args:
            cli_context (CliContext): The current cli context.
            service_name (str): Name of the container to run.
            extra_args (Iterable[str]): Extra arguments to the oneshot command.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def get_logs_command(self) -> click.Command:
        """
        Retuns a click command which streams logs for Docker containers.

        Args:
            cli_context (CliContext): The current cli context.

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


class DockerComposeOrchestrator(Orchestrator):
    """
    Uses Docker Compose to orchestrate containers.
    """

    def __init__(
        self,
        docker_compose_file: Path = Path("docker-compose.yml"),
        docker_compose_override_directory: Path = Path("docker-compose-overrides/"),
        docker_compose_oneshot_file: Path = Path("docker-compose.oneshot.yml"),
        docker_compose_oneshot_override_directory: Path = Path(
            "docker-compose-oneshot-overrides/"
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
            docker_compose_oneshot_file (Path): Path to a docker compose file containing short-lived oneshot containers.
                Path is relative to the generated configuration directory.
            docker_compose_oneshot_override_directory (Path): Path to a directory containing any additional
                docker-compose override files for oneshot containers. Path is relative to the generated configuration
                directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_directory = docker_compose_override_directory
        self.docker_compose_oneshot_file = docker_compose_oneshot_file
        self.docker_compose_oneshot_override_directory = (
            docker_compose_oneshot_override_directory
        )

    def start(self, cli_context: CliContext) -> CompletedProcess:
        return self.__compose_service(cli_context, ("up", "-d"))

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        return self.__compose_service(cli_context, ("down",))

    def oneshot(
        self, cli_context: CliContext, service_name: str, extra_args: Iterable[str]
    ) -> CompletedProcess:
        command = ["run", "--rm", service_name]
        command.extend(extra_args)
        return self.__compose_oneshot(cli_context, command)

    def get_logs_command(self):
        @click.command(
            help="Prints logs from all services (or the ones specified).",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("service", nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, service):
            cli_context = ctx.obj
            subcommand = ["logs", "--follow"]
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
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_file,
            self.docker_compose_override_directory,
        )

    def __compose_oneshot(
        self,
        cli_context: CliContext,
        command: Iterable[str],
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_oneshot_file,
            self.docker_compose_oneshot_override_directory,
        )


class DockerSwarmOrchestrator(Orchestrator):
    """
    Uses Docker Swarm to orchestrate containers.
    """

    def __init__(
        self,
        docker_compose_file: Path = Path("docker-compose.yml"),
        docker_compose_override_directory: Path = Path("docker-compose-overrides/"),
        docker_compose_oneshot_file: Path = Path("docker-compose.oneshot.yml"),
        docker_compose_oneshot_override_directory: Path = Path(
            "docker-compose-oneshot-overrides/"
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
            docker_compose_oneshot_file (Path): Path to a docker compose file containing short-lived oneshot containers.
                Path is relative to the generated configuration directory.
            docker_compose_oneshot_override_directory (Path): Path to a directory containing any additional
                docker-compose override files for oneshot containers. Path is relative to the generated configuration
                directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_directory = docker_compose_override_directory
        self.docker_compose_oneshot_file = docker_compose_oneshot_file
        self.docker_compose_oneshot_override_directory = (
            docker_compose_oneshot_override_directory
        )

    def start(self, cli_context: CliContext) -> CompletedProcess:
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

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        return self.__docker_stack(cli_context, ("rm",))

    def oneshot(
        self, cli_context: CliContext, service_name: str, extra_args: Iterable[str]
    ) -> CompletedProcess:
        return self.__compose_oneshot(
            cli_context, ["run", "--rm", service_name].extend(extra_args)
        )

    def get_logs_command(self):
        @click.command(
            help="Prints logs from the specified service.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("service", type=click.STRING)
        def logs(ctx, service):
            cli_context = ctx.obj
            command = ["docker", "service", "logs", "--follow"]
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

    def __compose_oneshot(
        self,
        cli_context: CliContext,
        command: Iterable[str],
    ):
        return execute_compose(
            cli_context,
            command,
            self.docker_compose_oneshot_file,
            self.docker_compose_oneshot_override_directory,
        )

    def __exec_command(self, command: str) -> CompletedProcess:
        logger.debug("Running [%s]", " ".join(command))
        return run(command)


# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def decrypt_docker_compose_files(
    cli_context: CliContext,
    docker_compose_file_relative_path: Path,
    docker_compose_override_directory_relative_path: Path,
) -> List[Path]:
    """Decrypt docker-compose and docker-compose override files.

    Args:
        cli_context (CliContext): The current cli context.
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
) -> CompletedProcess:
    """Builds and executes a docker-compose command.

    Args:
        cli_context (CliContext): The current cli context.
        command (Iterable[str]): The command to execute with docker-compose.
        docker_compose_file_relative_path (Path): The relative path to the docker-compose file. Path is relative to the
            generated configuration directory.
        docker_compose_override_directory_relative_path (Path): The relative path to a directory containing
            docker-compose override files. Path is relative to the generated configuration directory.

    Returns:
        CompletedProcess: The completed process and its exit code.
    """
    docker_compose_command = [
        "docker-compose",
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

    logger.debug("Running [%s]", " ".join(docker_compose_command))
    result = run(docker_compose_command)
    return result
