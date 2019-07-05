#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import gzip
import io
import logging
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path
from typing import List

# vendor libraries
import click
import coloredlogs
import inquirer
from jinja2 import Template
from ruamel.yaml import YAML

# our library
from .configuration_manager import ConfigurationManager
from .models import Configuration, ConfigSettingsGroup, ConfigSetting

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger(__name__)
coloredlogs.install(logger=logger, fmt=FORMAT)

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

class ConfigureCli:

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        self.app_name = self.cli_configuration.app_name
        env_app_home = f'{self.app_name.upper()}_EXT_{self.app_name.upper()}_HOME'
        env_host_root = f'{self.app_name.upper()}_EXT_HOST_ROOT'

        # environment variables which must be defined
        self.mandatory_env_variables=[
            env_app_home,
            env_host_root
        ]

        # the application directory
        self.app_ops_dir = os.path.realpath(self.cli_configuration.ops_dir.as_posix())

        # application home ('current') directory
        self.app_home = os.environ.get(env_app_home)

        # application root directory
        self.app_root = os.path.realpath(f'{self.app_home}/..')

        # physical hosts root directory
        self.host_root_dir = os.environ.get(env_host_root)

        # application configuration file
        self.configuration_file = f'{self.app_home}/conf/{self.app_name}.yaml'

        # file to store record of configuration run
        self.configuration_record_file = f'{self.app_home}/.configured'

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help='Configures the application')
        @click.option('--force', is_flag=True, default=False, help='Force reconfiguration. Any changes to flow file will be lost')
        @click.pass_context
        def configure(ctx, force):
            if not ctx.invoked_subcommand is None:
                # subcommand provided, do not enter interactive mode
                return

            self.__print_header('Configuring the application')
            logger.info('Running in %s', BASE_DIR)

            if not self.__prequisites_met():
                logger.error('Prerequisite checks failed')
                sys.exit(1)

            if force:
                self.__force_reconfigure()

            self.__populate_conf_dir()

            app_config_manager: ConfigurationManager = ConfigurationManager(self.configuration_file)
            self.__configure_all_settings(app_config_manager)

            self.cli_configuration.apply_configuration_settings_callback(app_config_manager)

            print("Finished configuring things. Exiting cleanly.")
            sys.exit(0)

            self.__save_configuration(app_config_manager)
            self.__clear_successful_configuration_record()
            self.__generate_environment_file(app_config_manager)
            self.__generate_configuration_files(app_config_manager)
            self.__set_successful_configuration_record()


        @configure.command(help='Reads a setting from the configuration')
        @click.argument('setting')
        def get(setting):
            configuration = ConfigurationManager(self.configuration_file)
            print(configuration.get(setting))

        @configure.command(help='Saves a setting to the configuration')
        @click.argument('setting')
        @click.argument('value')
        def set(setting, value):
            configuration = ConfigurationManager(self.configuration_file)
            configuration.set(setting, value)
            configuration.save()

        @configure.command(help='Applies the settings from the configuration')
        @click.option('--file', type=Path,
            help='Applies the settings from the suppplied configuration file. NOTE: This will replace the extant configuration file.')
        def apply(file):
            # NOTE: currently we just overwrite the extant file
            # in future we will want to do something smarter like a merge
            source = Path(f'{self.host_root_dir}/{file}')
            if not source.is_file():
                logger.error('Cannot access [%s]', file)
                sys.exit(1)

            target = Path(self.configuration_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            logger.info('Copying [%s] to [%s]', source, target)
            shutil.copy2(source, target)

            self.__clear_successful_configuration_record()
            configuration = ConfigurationManager(self.configuration_file)
            self.__generate_environment_file(configuration)
            self.__generate_configuration_files(configuration)
            self.__set_successful_configuration_record()

        self.command = configure

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __prequisites_met(self):
        logger.info('Checking prerequisites ...')
        result = True

        for env_variable in self.mandatory_env_variables:
            value = os.environ.get(env_variable)
            if value == None:
                logger.error('Mandatory environment variable is not defined [%s]', env_variable)
                result = False

        for dir in [self.app_home, self.host_root_dir]:
            if dir and not os.path.isdir(dir):
                logger.error('Mandatory directory does not exist [%s]', dir)
                result = False

        return result

    def __force_reconfigure(self):
        self.__print_header(f'Force reconfiguration')

        flow_file = f'{self.app_home}/nifi-flow/flow.xml.gz'
        if not os.path.isfile(flow_file):
            logger.warning(f'No flow file found at [{flow_file}]. No need to force.')
            return

        if not self.__confirm('This will delete the current flow. Do you wish to continue?'):
            sys.exit(1)

        logger.info('Removing flow file ...')
        os.remove(flow_file)
        # clear last configured so that profile can be changed
        self.__clear_successful_configuration_record()

    def __populate_conf_dir(self):
        logger.info('Populating [conf] directory ...')
        conf_dir = f'{self.app_home}/conf'
        os.makedirs(conf_dir, exist_ok=True)

        previous_dir = f'{self.app_home}/../previous'

        # ensure application.yaml exists
        relative_name = f'conf/{self.app_name}.yaml'
        target = self.configuration_file
        if not os.path.exists(target):
            previous_version = f'{previous_dir}/{relative_name}'
            # prefer files from previous version if they exist
            source = previous_version if os.path.exists(previous_version) else f'{self.app_ops_dir}/{relative_name}'
            logger.info('Copying application .yaml from [%s]', source)
            shutil.copy2(source, target)

    def __configure_all_settings(self, config_manager: ConfigurationManager):
        settings_group: ConfigSettingsGroup
        for settings_group in self.cli_configuration.config_cli.settings_groups:
            self.__configure_settings(config_manager, settings_group)

    def __configure_settings(self, config_manager: ConfigurationManager, settings_group: ConfigSettingsGroup):
        self.__print_header(f'Configure {settings_group.title} settings')
        self.__print_current_settings(settings_group.settings, config_manager)
        if self.__confirm(f'Modify {settings_group.title} settings?'):
            self.__prompt_and_update_configuration(settings_group.settings, config_manager)

    def __save_configuration(self, configuration):
        self.__print_header(f'Saving configuration')
        configuration.save()

    def __clear_successful_configuration_record(self):
        logger.info('Clearing successful configuration record ...')
        if os.path.exists(self.configuration_record_file):
            os.remove(self.configuration_record_file)

    def __set_successful_configuration_record(self):
        logger.info('Saving successful configuration record ...')
        with open(self.configuration_record_file, 'w') as output_file:
            output_file.write(datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())

    def __generate_environment_file(self, configuration):
        self.__print_header(f'Generating environment file')
        target_file = f'{self.app_home}/{self.app_name}-host.env'
        logger.info(f'Writing environment to [{target_file}]')
        self.__generate_from_template(
            f'{BASE_DIR}/templates/{self.app_name}-host.env.j2',
            target_file,
            configuration.get_as_dict()
        )

    def __generate_configuration_files(self, configuration):
        self.__print_header(f'Generating configuration files')

        output_dir = f'{self.app_home}/.conf/generated'
        os.makedirs(output_dir, exist_ok=True)

        template_dir = f'{self.app_ops_dir}/template'
        for root, dirs, files in os.walk(template_dir):
            for filename in files:
                source = os.path.join(root, filename)
                # strip off template_dir prefix
                target = output_dir + source[len(template_dir):]
                target_dir = os.path.dirname(target)
                os.makedirs(target_dir, exist_ok=True)

                if source.endswith('.j2'):
                    # strip off .j2
                    target = target[:-3]
                    logger.info(f'Generating file [{target}]')
                    self.__generate_from_template(source, target, configuration.get_as_dict())
                else:
                    logger.info(f'Copying to [{target}]')
                    shutil.copy2(source, target)

    def __print_header(self, title):
        print('\n============================================================')
        print(title.upper())
        print('============================================================\n')

    def __confirm(self, message, default=False):
        answer = inquirer.prompt([
            inquirer.Confirm('result', message=message, default=default)
        ])
        return answer['result']

    def __print_current_settings(self, settings: List[ConfigSetting], config_manager: ConfigurationManager):
        logger.info('Current Settings:')
        setting: ConfigSetting
        for setting in settings:
            logger.info('  {0:<45} = {1}'.format(getattr(setting, 'message'), config_manager.get(getattr(setting, 'path'))))
        print('')

    def __prompt_and_update_configuration(self, settings, configuration):
        questions = []
        for setting in settings:
            path = setting['path']
            validate = setting.get('validate', lambda _,x: True)
            default_value = configuration.get(path)
            if isinstance(default_value, str):
                # need to explicitly escape brackets
                default_value = default_value.replace('{', '{{').replace('}', '}}')
            questions.append(
                inquirer.Text(path, message=setting['message'], default=default_value, validate=validate)
            )

        answers = inquirer.prompt(questions)
        for setting in settings:
            path = setting['path']
            configuration.set(path, answers[path])

    def __generate_from_template(self, template_file, target_file, configuration):
        with open(template_file) as f:
            template = Template(f.read())
        try:
            output_text = template.render(configuration)
            with open(target_file, 'w') as f:
                f.write(output_text)
        except Exception as e:
            logger.error(f'Could not generate file from template. The configuration file is likely missing a setting: {e}')
            exit(1)
