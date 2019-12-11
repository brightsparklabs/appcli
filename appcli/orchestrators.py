#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Orchestrators for launching docker containers.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable
from subprocess import CompletedProcess, run

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

    def stop(self, cli_context: CliContext) -> CompletedProcess:
        """
        Stops all Docker containers.

        Args:
            cli_context (CliContext): Context for this CLI run.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def logs(self, cli_context: CliContext, container: str) -> CompletedProcess:
        """
        Streams logs for Docker containers.

        Args:
            cli_context (CliContext): Context for this CLI run.
            container (str, optional): Name of the container to stream logs for. Defaults to all containers.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError

    def raw_command(
        self, cli_context: CliContext, command: Iterable[str]
    ) -> CompletedProcess:
        """
        Runs a raw orchestrator command.

        Args:
            cli_context (CliContext): Context for this CLI run.
            command (str): Command to run.

        Returns:
            CompletedProcess: Result of the orchestrator command.
        """
        raise NotImplementedError


class DockerComposeOrchestrator(Orchestrator):
    """
    Uses Docker Compose to orchestrate containers.
    """

    def __init__(
        self, docker_compose_file: Path, docker_compose_override_files: Iterable[Path]
    ):
        """
        Creates a new instance.

        Args:
            docker_compose_file (Path): Path to a `docker-compose.yml` file relative to the generated configuration directory.
            docker_compose_override_files (Iterable[Path]): Paths to any additional docker-compose override files relative to the generated configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_files = docker_compose_override_files

    def start(self, cli_context: CliContext, container: str) -> CompletedProcess:
        return self.raw_command(cli_context, ("up", "-d") + container)

    def stop(self, cli_context: CliContext) -> CompletedProcess:
        return self.raw_command(cli_context, ["down"])

    def logs(self, cli_context: CliContext, container: str) -> CompletedProcess:
        return self.raw_command(cli_context, ("logs", "-f") + container)

    def raw_command(
        self, cli_context: CliContext, command: Iterable[str]
    ) -> CompletedProcess:
        docker_compose_command = [
            "docker-compose",
            "--project-name",
            cli_context.project_name,
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
        self, docker_compose_file: Path, docker_compose_override_files: Iterable[Path]
    ):
        """
        Creates a new instance.

        Args:
            docker_compose_file (Path): Path to a `docker-compose.yml` file relative to the generated configuration directory.
            docker_compose_override_files (Iterable[Path]): Paths to any additional docker-compose override files relative to the generated configuration directory.
        """
        self.docker_compose_file = docker_compose_file
        self.docker_compose_override_files = docker_compose_override_files

    def start(self, cli_context: CliContext, container: str) -> CompletedProcess:
        subcommand = ["stack", "deploy"]

        compose_files = decrypt_files(
            cli_context, self.docker_compose_file, self.docker_compose_override_files
        )
        for compose_file in compose_files:
            subcommand.extend(("--compose-file", str(compose_file)))

        subcommand.append(cli_context.project_name)
        return self.raw_command(cli_context, subcommand)

    def stop(self, cli_context: CliContext) -> CompletedProcess:
        subcommand = ("stack", "rm", cli_context.project_name)
        return self.raw_command(cli_context, subcommand)

    def logs(self, cli_context: CliContext, service: str) -> CompletedProcess:
        if service is None:
            logger.warning("Specify the container/service to retrieve logs for")
            return

        subcommand = ("service", "logs", "--follow", service)
        return self.raw_command(cli_context, subcommand)

    def raw_command(
        self, cli_context: CliContext, command: Iterable[str]
    ) -> CompletedProcess:
        docker_command = ["docker"]
        docker_command.extend(command)

        logger.debug("Running [%s]", " ".join(docker_command))
        result = run(docker_command)
        return result


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
        cli_context.generated_configuration_dir.joinpath(relative_path)
        for relative_path in compose_files
    ]

    # decrypt files if key is available
    key_file = cli_context.key_file
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
