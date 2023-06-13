#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for the backup manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


# standard libraries
import datetime
import os
import tarfile
from pathlib import Path, PurePath

# vendor libraries
import click
import pytest

# local libraries
from appcli.backup_manager.backup_manager import BackupConfig, BackupManager
from appcli.models.cli_context import CliContext

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

BASE_CONF_DIR: Path = Path("conf")
BASE_DATA_DIR: Path = Path("data")
BASE_BACKUP_DIR: Path = Path("backup")

DATA_FILES = set({"1.txt", "2.txt", "3.yml", "4.log", "5.log"})
DATA_FOLDERS_EMPTY = set({"empty_folder"})
DATA_FOLDERS_POPULATED = set({"populated_folder"})
DATA_FOLDERS_ALL = DATA_FOLDERS_EMPTY.union(DATA_FOLDERS_POPULATED)
DATA_NESTED_FILES = set(
    {
        "populated_folder/first.txt",
        "populated_folder/second.txt",
        "populated_folder/third.log",
    }
)
DATA_FILES_ALL = DATA_FILES.union(DATA_NESTED_FILES)

CONF_FILES = set({"6.txt", "7.txt", "8.log", "9.yml"})
CONF_FOLDERS_EMPTY = set({"empty"})
CONF_FOLDERS_POPULATED = set({".hidden", "not_hidden"})
CONF_FOLDERS_ALL = CONF_FOLDERS_EMPTY.union(CONF_FOLDERS_POPULATED)
CONF_NESTED_FILES = set(
    {".hidden/10.txt", ".hidden/11.log", "not_hidden/12.yml", "not_hidden/13.log"}
)
CONF_FILES_ALL = CONF_FILES.union(CONF_NESTED_FILES)


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


class MockTime:
    """A class for manipulating the monkeypatched datetime for more consistent testing."""

    original_value = datetime.datetime(2020, 12, 25, 17, 5, 55)
    current = original_value

    def getTime(self):
        return self.current

    def setTime(self, date: datetime.datetime):
        self.current = date

    def increment(self):
        """Increment `datetime.now` by 1 second."""
        self.current = self.current + time_delta(seconds=1)

    def reset(self):
        """Reset `datetime.now` to the initial state."""
        self.current = self.original_value


@pytest.fixture
def reset_mockTime():
    """Fixture for reseting `datetime.now`."""
    mock_time.reset()


@pytest.fixture
def patch_datetime_now(monkeypatch):
    """Fixture for monkeypatching `datetime.now` into an object we can manipulate."""

    class mydatetime:
        @classmethod
        def now(cls, utc=None):
            return mock_time.getTime()

    monkeypatch.setattr(
        "appcli.backup_manager.backup_manager.datetime.datetime", mydatetime
    )


@pytest.fixture(scope="session")
def populate_conf_dir(tmpdir_factory):
    """
    Populate a common conf directory to be used by all tests.
    As this is a session fixture any changes to this will effect all tests.
    """
    conf_dir = tmpdir_factory.mktemp(BASE_CONF_DIR)

    # Populate the conf directory with empty files
    for file in CONF_FILES:
        with open(os.path.join(conf_dir, file), "w"):
            pass
    for folder in CONF_FOLDERS_ALL:
        os.mkdir(os.path.join(conf_dir, folder))
    for file in CONF_NESTED_FILES:
        with open(os.path.join(conf_dir, file), "w"):
            pass
    return conf_dir


@pytest.fixture(scope="session")
def populate_data_dir(tmpdir_factory):
    """
    Populate a common data directory to be used by all tests.
    As this is a session fixture any changes to this will effect all tests.
    """
    data_dir = tmpdir_factory.mktemp(BASE_DATA_DIR)

    # Populate the data directory with empty files
    for file in DATA_FILES:
        with open(os.path.join(data_dir, file), "w"):
            pass
    for folder in DATA_FOLDERS_ALL:
        os.mkdir(os.path.join(data_dir, folder))
    for file in DATA_NESTED_FILES:
        with open(os.path.join(data_dir, file), "w"):
            pass
    return data_dir


@pytest.fixture(scope="session")
def backup_tgz(populate_conf_dir, populate_data_dir, tmpdir_factory) -> Path:
    """
    Populate a common backup directory and create a backup to be used by all tests.
    As this is a session fixture any changes to this will effect all tests.
        Returns:
            backup: (Path). The backup created.
    """
    backup_dir = tmpdir_factory.mktemp(BASE_BACKUP_DIR)

    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf = {
        "name": "full",
    }

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    return backup


def create_click_ctx(conf_dir, data_dir, backup_dir) -> click.Context:
    """
    Creates a click context object with the minimum set of values to enable backup & restore.

        Returns:
            ctx: (click.Context). A click library context object.
    """
    service_commands = type(
        "service_commands",
        (object,),
        {"commands": {"shutdown": lambda: None, "start": lambda: None}},
    )()
    commands = {"service": service_commands}

    ctx = click.Context(
        obj=CliContext(
            configuration_dir=conf_dir,
            application_context_files_dir=None,
            data_dir=data_dir,
            backup_dir=backup_dir,
            app_name_slug="test_app",
            additional_data_dirs=None,
            additional_env_variables=None,
            environment="test",
            docker_credentials_file=None,
            subcommand_args=None,
            debug=True,
            is_dev_mode=False,
            app_version="1.0",
            commands=commands,
        ),
        command=click.Command(
            name="backup", context_settings={"allow_extra_args": False}
        ),
    )
    return ctx


def get_tar_contents(tar: str):
    """Return a set of all files in the provided tar"""

    files = set()

    with tarfile.open(tar) as extracted_tar:
        for member in extracted_tar.getmembers():
            files.add(member.name)

    return files


def get_expected_files(tmp_folder_path, file_list):
    """Take a given file list and prepend a given string."""
    tar_path = PurePath(tmp_folder_path).name

    expected_files = set()
    for f in file_list:
        expected_files.add(tar_path + "/" + f)

    return expected_files


# ------------------------------------------------------------------------------
# INSTANCE VARIABLES
# ------------------------------------------------------------------------------

mock_time = MockTime()
time_delta = datetime.timedelta


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_minimum_config_required_for_local_backup(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    """
    Try to create a backup file with the minimum of config set.
    Check that the file was created and that its contents were expected.
    """
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration
    conf = {
        "name": "full",
    }

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_backup_no_limit(
    reset_mockTime, patch_datetime_now, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf = {
        "name": "full",
        "backup_limit": 0,
    }

    backup_config = BackupConfig.from_dict(conf)
    for x in range(10):
        backup = backup_config.backup(ctx)
        mock_time.increment()

    assert len(os.listdir(os.path.dirname(backup))) == 10


def test_backup_with_limit_keep_5(
    reset_mockTime, patch_datetime_now, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration.
    conf = {
        "name": "full",
        "backup_limit": 5,
    }
    backup_config = BackupConfig.from_dict(conf)

    for x in range(10):
        backup = backup_config.backup(ctx)
        mock_time.increment()

    assert len(os.listdir(os.path.dirname(backup))) == 5


def test_backup_with_limit_keep_last_5(
    reset_mockTime, patch_datetime_now, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration.
    conf = {
        "name": "full",
        "backup_limit": 5,
    }
    expected_result = set(
        {
            "TEST_APP_FULL_2020-12-25T170600.tgz",
            "TEST_APP_FULL_2020-12-25T170601.tgz",
            "TEST_APP_FULL_2020-12-25T170602.tgz",
            "TEST_APP_FULL_2020-12-25T170603.tgz",
            "TEST_APP_FULL_2020-12-25T170604.tgz",
        }
    )

    backup_config = BackupConfig.from_dict(conf)

    for x in range(10):
        backup = backup_config.backup(ctx)
        mock_time.increment()

    # Compare as a set so list order does not matter.
    assert set(os.listdir(os.path.dirname(backup))) == expected_result


def test_backup_with_unsafe_name_for_files(
    reset_mockTime, patch_datetime_now, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration.
    conf = {
        "name": "Backup: Weekly > Sunday",
    }
    expected_result = [
        "TEST_APP_BACKUP-WEEKLY-SUNDAY_2020-12-25T170555.tgz",
    ]

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    # Compare as a set so list order does not matter.
    assert os.listdir(os.path.dirname(backup)) == expected_result


def test_data_dir_missing_include_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration.
    conf = {"name": "full", "file_filter": {"data_dir": {"include_list": ""}}}
    backup_config = BackupConfig.from_dict(conf)

    backup = backup_config.backup(ctx)

    get_tar_contents(backup)
    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_data_dir_empty_include_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration.
    conf = {"name": "full", "file_filter": {"data_dir": {"include_list": []}}}
    backup_config = BackupConfig.from_dict(conf)

    backup = backup_config.backup(ctx)

    get_tar_contents(backup)
    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_conf_dir_mising_include_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration.
    conf = {"name": "full", "file_filter": {"conf_dir": {"include_list": ""}}}

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    get_tar_contents(backup)
    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_include_list(reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(
        populate_data_dir, set(["1.txt", "populated_folder/first.txt"])
    )
    expected_files = expected_files.union(
        get_expected_files(populate_conf_dir, ["6.txt", "7.txt", ".hidden/10.txt"])
    )
    # Create our configuration.
    conf = {
        "name": "full",
        "file_filter": {
            "data_dir": {"include_list": ["1.txt", "**/first.txt"]},
            "conf_dir": {"include_list": ["**/*.txt"]},
        },
    }

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_data_dir_empty_exclude_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration.
    conf = {"name": "full", "file_filter": {"data_dir": {"exclude_list": []}}}

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_data_dir_missing_exclude_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    # Create our configuration.
    conf = {"name": "full", "file_filter": {"data_dir": {"exclude_list": ""}}}

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_exclude_list(reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    expected_files = expected_files - get_expected_files(
        populate_data_dir, set(["1.txt", "populated_folder/first.txt"])
    )
    expected_files = expected_files - get_expected_files(
        populate_conf_dir, set(["6.txt", "7.txt", ".hidden/10.txt"])
    )
    # Create our configuration.
    conf = {
        "name": "full",
        "file_filter": {
            "data_dir": {"exclude_list": ["1.txt", "**/first.txt"]},
            "conf_dir": {"exclude_list": ["**/*.txt"]},
        },
    }

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_data_dir_include_and_exclude_list(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Build our list of expected files to find in the backup
    expected_files = get_expected_files(populate_data_dir, DATA_FILES_ALL).union(
        get_expected_files(populate_conf_dir, CONF_FILES_ALL)
    )
    expected_files = get_expected_files(populate_conf_dir, set([".hidden/11.log"]))
    expected_files = expected_files.union(
        get_expected_files(populate_data_dir, (set(["populated_folder/third.log"])))
    )
    # Create our configuration.
    conf = {
        "name": "full",
        "file_filter": {
            "data_dir": {"include_list": ["**/*.log"], "exclude_list": ["**/?.log"]},
            "conf_dir": {
                "include_list": [".hidden/**/*"],
                "exclude_list": ["**/*.txt"],
            },
        },
    }

    backup_config = BackupConfig.from_dict(conf)
    backup = backup_config.backup(ctx)

    assert Path(backup).exists()
    assert get_tar_contents(backup) == expected_files


def test_frequency_always_run():
    conf = {"name": "full", "frequency": "* * *"}

    backup_config = BackupConfig.from_dict(conf)
    result = backup_config.should_run()

    assert result


def test_frequency_first_of_month_correct_date(reset_mockTime, monkeypatch):
    monkeypatch.setattr(
        "time.time",
        lambda: 1614568341,  # 1st of march
    )
    conf = {"name": "full", "frequency": "1 * *"}

    backup_config = BackupConfig.from_dict(conf)
    result = backup_config.should_run()

    assert result


def test_frequency_first_of_month_incorrect_date(reset_mockTime, monkeypatch):
    monkeypatch.setattr(
        "time.time",
        lambda: 1614654741,  # 2nd of march
    )

    conf = {"name": "full", "frequency": "1 * *"}

    backup_config = BackupConfig.from_dict(conf)
    result = backup_config.should_run()

    assert not result


def test_will_not_run_with_missing_name(reset_mockTime):
    conf = {
        "frequency": "* * *",
    }

    with pytest.raises(KeyError) as excinfo:
        BackupConfig.from_dict(conf)

    assert "'name'" in str(excinfo.value)


def test_defaults_set_correctly_when_missing(reset_mockTime):
    conf = {
        "name": "full",
    }
    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.name == "full"
    assert backup_config.backup_limit == 0
    assert backup_config.file_filter.data_dir.include_list == ["**/*"]
    assert backup_config.file_filter.data_dir.exclude_list == ["[]"]
    assert backup_config.file_filter.conf_dir.include_list == ["**/*"]
    assert backup_config.file_filter.conf_dir.exclude_list == ["[]"]
    assert backup_config.remote_backups == []
    assert backup_config.frequency == "* * *"


def test_defaults_set_correctly_when_empty(reset_mockTime):
    conf = {
        "name": "full",
        "frequency": "",
        "backup_limit": "",
        "remote_backups": "",
        "file_filter": {},
    }
    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.name == "full"
    assert backup_config.backup_limit == 0
    assert backup_config.file_filter.data_dir.include_list == ["**/*"]
    assert backup_config.file_filter.data_dir.exclude_list == ["[]"]
    assert backup_config.file_filter.conf_dir.include_list == ["**/*"]
    assert backup_config.file_filter.conf_dir.exclude_list == ["[]"]
    assert backup_config.remote_backups == []
    assert backup_config.frequency == "* * *"


def test_defaults_set_correctly_empty_filter_dirs(reset_mockTime):
    conf = {
        "name": "full",
        "frequency": "",
        "backup_limit": "",
        "remote_backups": "",
        "file_filter": {"data_dir": {}, "conf_dir": {}},
    }
    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.file_filter.data_dir.include_list == ["**/*"]
    assert backup_config.file_filter.data_dir.exclude_list == ["[]"]
    assert backup_config.file_filter.conf_dir.include_list == ["**/*"]
    assert backup_config.file_filter.conf_dir.exclude_list == ["[]"]


def test_defaults_set_correctly_empty_include_exclude_lists(reset_mockTime):
    conf = {
        "name": "full",
        "frequency": "",
        "backup_limit": "",
        "remote_backups": "",
        "file_filter": {
            "data_dir": {"include_list": [], "exclude_list": []},
            "conf_dir": {"include_list": [], "exclude_list": []},
        },
    }
    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.file_filter.data_dir.include_list == ["**/*"]
    assert backup_config.file_filter.data_dir.exclude_list == ["[]"]
    assert backup_config.file_filter.conf_dir.include_list == ["**/*"]
    assert backup_config.file_filter.conf_dir.exclude_list == ["[]"]


def test_defaults_set_correctly_missing_include_exclude_lists(reset_mockTime):
    conf = {
        "name": "full",
        "frequency": "",
        "backup_limit": "",
        "remote_backups": "",
        "file_filter": {
            "data_dir": {"include_list": "", "exclude_list": ""},
            "conf_dir": {"include_list": "", "exclude_list": ""},
        },
    }
    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.file_filter.data_dir.include_list == ["**/*"]
    assert backup_config.file_filter.data_dir.exclude_list == ["[]"]
    assert backup_config.file_filter.conf_dir.include_list == ["**/*"]
    assert backup_config.file_filter.conf_dir.exclude_list == ["[]"]


def test_simple_remote_backups_parsing(reset_mockTime):
    conf = {
        "name": "full",
        "remote_backups": [
            {
                "name": "s3_weekley",
                "strategy_type": "S3",
                "configuration": {
                    "bucket_name": "name",
                    "access_key": "asdf123",
                    "secret_key": "qwer456",
                    "bucket_path": "home/weekly",
                    "tags": {"frequency": "weekley", "type": "data"},
                },
            }
        ],
    }

    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.remote_backups[0].name == "s3_weekley"
    assert backup_config.remote_backups[0].strategy_type == "S3"
    assert backup_config.remote_backups[0].frequency == "* * *"


def test_simple_S3_remote_backup_parsing(reset_mockTime):
    conf = {
        "name": "full",
        "remote_backups": [
            {
                "name": "s3_sunday",
                "strategy_type": "S3",
                "frequency": "* * 0",
                "configuration": {
                    "bucket_name": "name",
                    "access_key": "asdf123",
                    "secret_key": "qwer456",
                    "bucket_path": "home/weekly",
                    "tags": {"frequency": "weekley", "type": "data"},
                },
            }
        ],
    }

    backup_config = BackupConfig.from_dict(conf)

    assert backup_config.remote_backups[0].name == "s3_sunday"
    assert backup_config.remote_backups[0].strategy_type == "S3"
    assert backup_config.remote_backups[0].frequency == "* * 0"
    assert backup_config.remote_backups[0].strategy.bucket_name == "name"
    assert backup_config.remote_backups[0].strategy.access_key == "asdf123"
    assert backup_config.remote_backups[0].strategy.secret_key == "qwer456"
    assert backup_config.remote_backups[0].strategy.bucket_path == "home/weekly"
    assert backup_config.remote_backups[0].strategy.tags["frequency"] == "weekley"
    assert backup_config.remote_backups[0].strategy.tags["type"] == "data"


def test_restore_fails_no_backup(
    reset_mockTime, populate_conf_dir, populate_data_dir, tmp_path, caplog
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf = {"backups": [{"name": "full"}]}

    backup_manager = BackupManager(conf)
    with pytest.raises(SystemExit) as excinfo:
        backup_manager.restore(ctx, "fake_file.tgz")
    assert "1" in str(excinfo.value)
    # TODO: We should check the logs here for an error that contains the message "fake_file.tgz] not found"


def test_restore_works_with_empty_filesystem(
    reset_mockTime, populate_conf_dir, populate_data_dir, backup_tgz, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the temporary conf directory to restore into.
    conf_dir = tmp_path / PurePath(populate_conf_dir).name
    conf_dir.mkdir()
    # Create the temporary data directory to restore into.
    data_dir = tmp_path / PurePath(populate_data_dir).name
    data_dir.mkdir()
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(Path(conf_dir), Path(data_dir), Path(backup_dir))
    # Create our configuration
    conf = [{"name": "full"}]

    backup_manager = BackupManager(conf)
    backup_manager.restore(ctx, backup_tgz)

    data_result = set(
        [
            os.path.join(dp[len(str(data_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(data_dir)
            for f in filenames
        ]
    )
    conf_result = set(
        [
            os.path.join(dp[len(str(conf_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(conf_dir)
            for f in filenames
        ]
    )

    assert DATA_FILES_ALL == data_result
    assert CONF_FILES_ALL == conf_result


def test_restore_works_with_existing_files(
    reset_mockTime, populate_conf_dir, populate_data_dir, backup_tgz, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the temporary conf directory to restore into.
    conf_dir = tmp_path / PurePath(populate_conf_dir).name
    conf_dir.mkdir()
    # Create the temporary data directory to restore into.
    data_dir = tmp_path / PurePath(populate_data_dir).name
    data_dir.mkdir()
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(Path(conf_dir), Path(data_dir), Path(backup_dir))
    # Create our configuration
    conf = [{"name": "full"}]
    # Create an existing file that will be overwritten on restore.
    with open(os.path.join(data_dir, "1.txt"), "w") as f:
        f.write("some sample text")

    backup_manager = BackupManager(conf)
    backup_manager.restore(ctx, backup_tgz)

    contents = Path(os.path.join(data_dir, "1.txt")).read_text()

    assert contents == ""


def test_can_restore_with_no_config(
    reset_mockTime, populate_conf_dir, populate_data_dir, backup_tgz, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the temporary conf directory to restore into.
    conf_dir = tmp_path / PurePath(populate_conf_dir).name
    conf_dir.mkdir()
    # Create the temporary data directory to restore into.
    data_dir = tmp_path / PurePath(populate_data_dir).name
    data_dir.mkdir()
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(Path(conf_dir), Path(data_dir), Path(backup_dir))
    # Create our configuration
    conf = []

    backup_manager = BackupManager(conf)
    backup_manager.restore(ctx, backup_tgz)

    data_result = set(
        [
            os.path.join(dp[len(str(data_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(data_dir)
            for f in filenames
        ]
    )
    conf_result = set(
        [
            os.path.join(dp[len(str(conf_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(conf_dir)
            for f in filenames
        ]
    )

    assert DATA_FILES_ALL == data_result
    assert CONF_FILES_ALL == conf_result


def test_restore_triggers_config_backups(
    reset_mockTime,
    patch_datetime_now,
    populate_conf_dir,
    populate_data_dir,
    backup_tgz,
    tmp_path,
):
    expected_result = set({"TEST_APP_FULL_2020-12-25T170555.tgz"})
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the temporary conf directory to restore into.
    conf_dir = tmp_path / PurePath(populate_conf_dir).name
    conf_dir.mkdir()
    # Create the temporary data directory to restore into.
    data_dir = tmp_path / PurePath(populate_data_dir).name
    data_dir.mkdir()
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(Path(conf_dir), Path(data_dir), Path(backup_dir))
    # Create our configuration
    conf = [{"name": "full"}]

    backup_manager = BackupManager(conf)
    backup_manager.restore(ctx, backup_tgz)

    # Compare as a set so list order does not matter.
    assert set(os.listdir(os.path.join(backup_dir, "full"))) == expected_result


# does not replace existing files
def test_restore_does_not_replace_files_not_in_backup(
    reset_mockTime, populate_conf_dir, populate_data_dir, backup_tgz, tmp_path
):
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the temporary conf directory to restore into.
    conf_dir = tmp_path / PurePath(populate_conf_dir).name
    conf_dir.mkdir()
    # Create the temporary data directory to restore into.
    data_dir = tmp_path / PurePath(populate_data_dir).name
    data_dir.mkdir()
    # Create the click context that backup_manager expects to deal with.
    ctx = create_click_ctx(Path(conf_dir), Path(data_dir), Path(backup_dir))
    # Create our configuration
    conf = [{"name": "full"}]
    # Create existing files in our temp data directory that should be kept on restore.
    with open(os.path.join(data_dir, "existing_file_1.txt"), "w"):
        pass

    with open(os.path.join(data_dir, "existing_file_2.yml"), "w"):
        pass

    backup_manager = BackupManager(conf)
    backup_manager.restore(ctx, backup_tgz)

    data_result = set(
        [
            os.path.join(dp[len(str(data_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(data_dir)
            for f in filenames
        ]
    )
    conf_result = set(
        [
            os.path.join(dp[len(str(conf_dir)) :], f).strip("/")  # noqa: E203
            for dp, dn, filenames in os.walk(conf_dir)
            for f in filenames
        ]
    )

    assert (
        DATA_FILES_ALL.union(set({"existing_file_1.txt", "existing_file_2.yml"}))
        == data_result
    )
    assert CONF_FILES_ALL == conf_result


def test_view_backups(
    reset_mockTime,
    patch_datetime_now,
    populate_conf_dir,
    populate_data_dir,
    tmp_path,
    capsys,
):
    expected = "full/TEST_APP_FULL_2020-12-25T170555.tgz\n"
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf = {
        "name": "full",
        "backup_limit": 0,
    }
    # Create a backup to view.
    with capsys.disabled():
        backup_config = BackupConfig.from_dict(conf)
        backup_config.backup(ctx)

    backup_manager = BackupManager(conf)
    backup_manager.view_backups(ctx)

    captured = capsys.readouterr()
    output = captured.out

    assert expected == output


def test_view_multiple_backups_descending_order(
    reset_mockTime,
    patch_datetime_now,
    populate_conf_dir,
    populate_data_dir,
    tmp_path,
    capsys,
):
    expected = (
        "full/TEST_APP_FULL_2020-12-25T170604.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170603.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170602.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170601.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170600.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170559.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170558.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170557.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170556.tgz\n"
        + "full/TEST_APP_FULL_2020-12-25T170555.tgz\n"
    )
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf = {
        "name": "full",
        "backup_limit": 0,
    }
    # Create backups to view.
    with capsys.disabled():
        backup_config = BackupConfig.from_dict(conf)
        for x in range(10):
            backup_config.backup(ctx)
            mock_time.increment()

    backup_manager = BackupManager(conf)
    backup_manager.view_backups(ctx)

    captured = capsys.readouterr()
    output = captured.out

    assert expected == output


def test_view_backups_multiple_backup_strategies(
    reset_mockTime,
    patch_datetime_now,
    populate_conf_dir,
    populate_data_dir,
    tmp_path,
    capsys,
):
    expected = (
        "logs/TEST_APP_LOGS_2020-12-25T170556.tgz\n"
        "full/TEST_APP_FULL_2020-12-25T170555.tgz\n"
    )
    # Set the backup directory.
    backup_dir = tmp_path / BASE_BACKUP_DIR
    # Create the click context that backup_manager expects to deal with
    ctx = create_click_ctx(
        Path(populate_conf_dir), Path(populate_data_dir), Path(backup_dir)
    )
    # Create our configuration
    conf_full = {
        "name": "full",
        "backup_limit": 0,
    }
    conf_logs = {
        "name": "logs",
        "file_filter": {
            "data_dir": {"include_list": ["1.txt", "**/first.txt"]},
            "conf_dir": {"include_list": ["**/*.txt"]},
        },
    }
    # Create a backup to view.
    with capsys.disabled():
        backup_config = BackupConfig.from_dict(conf_full)
        backup_config.backup(ctx)
        mock_time.increment()

        backup_config = BackupConfig.from_dict(conf_logs)
        backup_config.backup(ctx)
        mock_time.increment()

    backup_manager = BackupManager([])
    backup_manager.view_backups(ctx)

    captured = capsys.readouterr()
    output = captured.out

    assert expected == output
