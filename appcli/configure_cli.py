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
from .logger import logger, enable_debug_logging
from .models import Configuration, ConfigSettingsGroup, ConfigSetting

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------


class ConfigureCli:

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        self.app_name = self.cli_configuration.app_name

        env_config_dir = f'{self.app_name}_CONFIG_DIR'.upper()
        self.config_dir = Path(os.environ.get(env_config_dir))
        env_data_dir = f'{self.app_name}_DATA_DIR'.upper()
        self.data_dir = Path(os.environ.get(env_data_dir))
        self.mandatory_env_variables = (
            env_config_dir,
            env_data_dir
        )

        # application configuration file used to populate templates
        self.app_configuration_file = self.config_dir.joinpath(
            f'{self.app_name}.yaml')

        # directory containing templates of configuration files
        self.templates_dir = self.config_dir.joinpath('templates')

        # the output generated configuration directory
        self.generated_config_dir = self.config_dir.joinpath('.generated/conf')

        # file to store record of configuration run
        self.configuration_record_file = self.generated_config_dir.joinpath(
            'configure-metadata')

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help='Configures the application')
        @click.pass_context
        def configure(ctx):
            if not ctx.invoked_subcommand is None:
                # subcommand provided, do not enter interactive mode
                return

            self.__print_header('Configuring the application')

            if not self.__prequisites_met():
                logger.error('Prerequisite checks failed')
                sys.exit(1)

            #self.__print_header('Running pre-configuration steps')
            #self.cli_configuration.pre_configuration_callback()

            self.__print_header('Populating the configuration directory')
            self.__seed_configuration_dir()

            #app_config_manager = ConfigurationManager(self.app_configuration_file)
            #self.__configure_all_settings(app_config_manager)

            #self.__print_header('Running configuration settings callback')
            #self.cli_configuration.apply_configuration_settings_callback(app_config_manager)

            #self.__save_configuration(app_config_manager)

        @configure.command(help='Reads a setting from the configuration')
        @click.argument('setting')
        def get(setting):
            configuration = ConfigurationManager(self.app_configuration_file)
            print(configuration.get(setting))

        @configure.command(help='Saves a setting to the configuration')
        @click.argument('setting')
        @click.argument('value')
        def set(setting, value):
            configuration = ConfigurationManager(self.app_configuration_file)
            configuration.set(setting, value)
            configuration.save()

        @configure.command(help='Applies the settings from the configuration')
        def apply():
            configuration = ConfigurationManager(self.app_configuration_file)
            self.__generate_configuration_files(configuration)

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
                logger.error(
                    f'Mandatory environment variable is not defined [{env_variable}]')
                result = False

        return result

    def __seed_configuration_dir(self):
        logger.info('Seeding configuration directory ...')
        self.config_dir.mkdir(parents=True, exist_ok=True)

        seed_dir = self.cli_configuration.seed_dir
        if not seed_dir.is_dir():
            logger.error(
                f'Seed directory [{seed_dir}] is not valid. Release is corrupt.')
            sys.exit(1)

        for source_file in seed_dir.glob('**/*'):
            logger.info(source_file)
            relative_file = source_file.relative_to(seed_dir)
            target_file = self.config_dir.joinpath(relative_file)

            if source_file.is_dir():
                logger.debug(f'Creating directory [{target_file}] ...')
                target_file.mkdir(parents=True, exist_ok=True)
            else:
                logger.debug(f'Copying seed file to [{target_file}] ...')
                shutil.copy2(source_file, target_file)

    def __configure_all_settings(self, config_manager: ConfigurationManager):
        settings_group: ConfigSettingsGroup
        for settings_group in self.cli_configuration.config_cli.settings_groups:
            self.__configure_settings(config_manager, settings_group)

    def __configure_settings(self, config_manager: ConfigurationManager, settings_group: ConfigSettingsGroup):
        self.__print_header(f'Configure {settings_group.title} settings')
        self.__print_current_settings(settings_group.settings, config_manager)
        if self.__confirm(f'Modify {settings_group.title} settings?'):
            self.__prompt_and_update_configuration(
                settings_group.settings, config_manager)

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
            output_file.write(datetime.utcnow().replace(
                tzinfo=timezone.utc).isoformat())

    def __generate_configuration_files(self, configuration):
        self.__print_header(f'Generating configuration files')

        self.__clear_successful_configuration_record()
        self.generated_config_dir.mkdir(parents=True, exist_ok=True)

        for template_file in self.templates_dir.glob('**/*'):
            relative_file = template_file.relative_to(self.templates_dir)
            target_file = self.generated_config_dir.joinpath(relative_file)

            if template_file.is_dir():
                logger.debug(f'Creating directory [{target_file}] ...')
                target_file.mkdir(parents=True, exist_ok=True)
                continue

            if template_file.suffix == '.j2':
                # parse jinja2 templates against configuration
                target_file = target_file.with_suffix('')
                logger.info(
                    f'Generating configuration file [{target_file}] ...')
                self.__generate_from_template(
                    template_file, target_file, configuration.get_as_dict())
            else:
                logger.info(
                    f'Copying configuration file to [{target_file}] ...')
                shutil.copy2(template_file, target_file)

        self.__set_successful_configuration_record()

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
            logger.info('  {0:<45} = {1}'.format(
                getattr(setting, 'message'), config_manager.get(getattr(setting, 'path'))))
        print('')

    def __prompt_and_update_configuration(self, settings, configuration):
        questions = []
        for setting in settings:
            path = setting['path']
            validate = setting.get('validate', lambda _, x: True)
            default_value = configuration.get(path)
            if isinstance(default_value, str):
                # need to explicitly escape brackets
                default_value = default_value.replace(
                    '{', '{{').replace('}', '}}')
            questions.append(
                inquirer.Text(
                    path, message=setting['message'], default=default_value, validate=validate)
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
            logger.error(
                f'Could not generate file from template. The configuration file is likely missing a setting: {e}')
            exit(1)
