#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Orchestrators for launching docker containers.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

import sys

# standard libraries
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import NamedTemporaryFile
from typing import Iterable

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
            cli_context (CliContext): Context for this CLI run.
            container (str, optional): Name of the container to start. Defaults to all containers.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        """
        Stops all Docker containers.

        Args:
            cli_context (CliContext): Context for this CLI run.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def get_logs_command(self) -> click.Command:
        """
        Retuns a click command which streams logs for Docker containers.

        Args:
            cli_context (CliContext): Context for this CLI run.

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
        docker_compose_file: Path,
        docker_compose_override_files: Iterable[Path] = [],
    ):
        """
        Creates a new instance.

        Args:
            docker_compose_file (Path): Path to a `docker-compose.yml` file relative to the generated configuration directory.
            docker_compose_override_files (Iterable[Path], optional): Paths to any additional docker-compose override files relative to the generated configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_files = docker_compose_override_files

    def start(self, cli_context: CliContext) -> CompletedProcess:
        return self.__compose(cli_context, ("up", "-d"))

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        return self.__compose(cli_context, ("down",))

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
            result = self.__compose(cli_context, subcommand)
            sys.exit(result.returncode)

        return logs

    def get_additional_commands(self):
        @click.command(help="List the status of services.")
        @click.pass_context
        def ps(ctx):
            result = self.__compose(ctx.obj, ("ps",))
            sys.exit(result.returncode)

        @click.command(
            help="Runs a docker compose command.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("command", nargs=-1, type=click.UNPROCESSED)
        def compose(ctx, command):
            result = self.__compose(ctx.obj, command)
            sys.exit(result.returncode)

        return (
            ps,
            compose,
        )

    def get_name(self):
        return "compose"

    def __compose(
        self, cli_context: CliContext, command: Iterable[str]
    ) -> CompletedProcess:
        docker_compose_command = [
            "docker-compose",
            "--project-name",
            cli_context.get_project_name(),
        ]

        compose_files = decrypt_files(
            cli_context, self.docker_compose_file, self.docker_compose_override_files
        )
        for compose_file in compose_files:
            docker_compose_command.extend(("--file", str(compose_file)))

        docker_compose_command.extend(command)
        logger.debug("Running [%s]", " ".join(docker_compose_command))
        result = run(docker_compose_command)
        return result


class DockerSwarmOrchestrator(Orchestrator):
    """
    Uses Docker Swarm to orchestrate containers.
    """

    def __init__(
        self,
        docker_compose_file: Path,
        docker_compose_override_files: Iterable[Path] = [],
    ):
        """
        Creates a new instance.

        Args:
            docker_compose_file (Path): Path to a `docker-compose.yml` file relative to the generated configuration directory.
            docker_compose_override_files (Iterable[Path], optional): Paths to any additional docker-compose override files relative to the generated configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_files = docker_compose_override_files

    def start(self, cli_context: CliContext) -> CompletedProcess:
        subcommand = ["deploy"]
        compose_files = decrypt_files(
            cli_context, self.docker_compose_file, self.docker_compose_override_files
        )
        for compose_file in compose_files:
            subcommand.extend(("--compose-file", str(compose_file)))

        return self.__docker_stack(cli_context, subcommand)

    def shutdown(self, cli_context: CliContext) -> CompletedProcess:
        return self.__docker_stack(cli_context, ("rm",))

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

    def __exec_command(self, command: str) -> CompletedProcess:
        logger.debug("Running [%s]", " ".join(command))
        return run(command)


# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def decrypt_files(
    cli_context: CliContext,
    docker_compose_file: Path,
    docker_compose_override_files: Iterable[Path],
):
    compose_files = [docker_compose_file]
    compose_files.extend(docker_compose_override_files)
    # turn relative paths into absolute paths
    compose_files = [
        cli_context.get_generated_configuration_dir().joinpath(relative_path)
        for relative_path in compose_files
    ]

    # decrypt files if key is available
    key_file = cli_context.get_key_file()
    decrypted_files = [
        decrypt_file(encrypted_file, key_file) for encrypted_file in compose_files
    ]
    return decrypted_files


def decrypt_file(encrypted_file: Path, key_file: Path):
    """
    Decrypts the specified file using the supplied key.

    Args:
        encrypted_file (Path): File to decrypt.
        key_file (Path): Key to use for decryption.

    Returns:
        [type]: Path to the decrypted file.
    """
    if not key_file.is_file():
        logger.info(
            "No decryption key found. [%s] will not be decrypted.", encrypted_file
        )
        return encrypted_file

    logger.info("Decrypting file [%s] using [%s].", str(encrypted_file), key_file)
    decrypted_file: Path = Path(NamedTemporaryFile(delete=False).name)
    crypto.decrypt_values_in_file(encrypted_file, decrypted_file, key_file)
    return decrypted_file
