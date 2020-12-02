from enum import Enum, auto


class AppcliCommand(Enum):
    CONFIGURE_INIT = auto()
    CONFIGURE_APPLY = auto()
    CONFIGURE_GET = auto()
    CONFIGURE_SET = auto()
    CONFIGURE_DIFF = auto()
    CONFIGURE_EDIT = auto()

    CONFIGURE_TEMPLATE_LS = auto()
    CONFIGURE_TEMPLATE_GET = auto()
    CONFIGURE_TEMPLATE_OVERRIDE = auto()
    CONFIGURE_TEMPLATE_DIFF = auto()

    DEBUG_INFO = auto()

    ENCRYPT = auto()

    INSTALL = auto()

    LAUNCHER = auto()

    MIGRATE = auto()

    SERVICE_START = auto()
    SERVICE_SHUTDOWN = auto()
    SERVICE_LOGS = auto()  # TODO: Deal with... Comes from the orchestrator...

    TASK_RUN = auto()

    ORCHESTRATOR = auto()  # TODO: Do we need to do something with this?