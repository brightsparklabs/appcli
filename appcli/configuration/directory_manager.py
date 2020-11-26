from enum import Enum, auto


class AppcliCommand(Enum):
    CONFIGURE_APPLY = auto()
    CONFIGURE_DIFF = auto()
    CONFIGURE_EDIT = auto()
    CONFIGURE_GET = auto()
    CONFIGURE_INIT = auto()
    CONFIGURE_SET = auto()
    CONFIGURE_TEMPLATE = auto()
    ENCRYPT = auto()
    LAUNCHER = auto()
    MIGRATE = auto()
    ORCHESTRATOR = auto()
    SERVICE_LOGS = auto()
    SERVICE_SHUTDOWN = auto()
    SERVICE_START = auto()
    TASK_RUN = auto()


class DirectoryManager:
    def __init__(self) -> None:
        self.command_checks = {}
        for command in AppcliCommand:
            self.command_checks[command] = self.default_command_check

    def default_command_check(self, force: bool) -> bool:
        return True

    def check_command(self, command: AppcliCommand, force: bool):
        return self.command_checks[command](force)


class ConfigurationDirectoryManagerFactory:
    def get_configuration_directory_manager() -> DirectoryManager:
        # TODO: Impl logic to get different types of conf directory managers
        return CleanConfigurationDirectoryManager()


class CleanConfigurationDirectoryManager(DirectoryManager):
    def __init__(self) -> None:
        super().__init__()
        self.command_checks[AppcliCommand.CONFIGURE_INIT] = self.disallow_configure_init

    def disallow_configure_init(self, force: bool) -> bool:
        # logger.error("Cannot initialise pre-existing configuration directory")
        return False


class DirtyConfigurationDirectoryManager(DirectoryManager):
    def __init__(self) -> None:
        super().__init__()
        self.command_checks[AppcliCommand.CONFIGURE_INIT] = self.disallow_configure_init
        self.command_checks[AppcliCommand.MIGRATE] = self.disallow_migrate

    def disallow_configure_init(self, force: bool) -> bool:
        # logger.error("Cannot initialise pre-existing configuration directory")
        return False

    def disallow_migrate(self, force: bool) -> bool:
        # logger.error("Cannot migrate a dirty configuration. Run 'configure apply'.")
        return False


class InvalidConfigurationDirectoryManager(DirectoryManager):
    def __init__(self, issues: str) -> None:
        super().__init__()
        self.issues = issues

        failing_commands = [
            AppcliCommand.CONFIGURE_APPLY,
            AppcliCommand.CONFIGURE_DIFF,
            AppcliCommand.CONFIGURE_EDIT,
            AppcliCommand.CONFIGURE_GET,
            AppcliCommand.CONFIGURE_INIT,
            AppcliCommand.CONFIGURE_SET,
            AppcliCommand.CONFIGURE_TEMPLATE,
            AppcliCommand.ENCRYPT,
            AppcliCommand.LAUNCHER,
            AppcliCommand.MIGRATE,
        ]

        for failing_command in failing_commands:
            self.command_checks[failing_command] = self.disallow_and_show_issues

    def disallow_and_show_issues(self, force: bool):
        # logger.error(
        #     "Invalid configuration state. Error(s) are: %s",
        #     self.issues,
        # )
        return False


class MissingConfigurationDirectoryManager(DirectoryManager):
    def __init__(self) -> None:
        super().__init__()
        failing_commands = [
            AppcliCommand.CONFIGURE_APPLY,
            AppcliCommand.CONFIGURE_DIFF,
            AppcliCommand.CONFIGURE_EDIT,
            AppcliCommand.CONFIGURE_GET,
            AppcliCommand.CONFIGURE_SET,
            AppcliCommand.CONFIGURE_TEMPLATE,
            AppcliCommand.ENCRYPT,
            AppcliCommand.LAUNCHER,
            AppcliCommand.MIGRATE,
        ]

        for failing_command in failing_commands:
            self.command_checks[failing_command] = self.disallow_command

    def disallow_command(self, force: bool):
        # logger.error("Cannot run this command due to missing configuration directory.")
        return False