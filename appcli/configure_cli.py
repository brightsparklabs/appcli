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

# vendor libraries
import click
import coloredlogs
import inquirer
from jinja2 import Template
from ruamel.yaml import YAML

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

# environment variables which must be defined
MANDATORY_ENV_VARIABLES=[
    'INSILICO_EXT_INSILICO_HOME',
    'INSILICO_EXT_HOST_ROOT',
]

# the insilico-ops directory
INSILICO_OPS_DIR = os.path.realpath(f'{BASE_DIR}/../main')

# insilico home ('current') directory
INSILICO_HOME = os.environ.get('INSILICO_EXT_INSILICO_HOME')

# insilico root directory
INSILICO_ROOT = os.path.realpath(f'{INSILICO_HOME}/..')

# physical hosts root directory
HOST_ROOT_DIR = os.environ.get('INSILICO_EXT_HOST_ROOT')

# insilico configuration file
CONFIGURATION_FILE = f'{INSILICO_HOME}/custom/conf/insilico.yaml'

# file to store record of configuration run
CONFIGURATION_RECORD_FILE = f'{INSILICO_HOME}/.configured'

# ------------------------------------------------------------------------------
# CLI METHODS
# ------------------------------------------------------------------------------

@click.group(invoke_without_command=True, help='Configures insilico')
@click.option('--force', is_flag=True, default=False, help='Force reconfiguration. Any changes to flow file will be lost')
@click.pass_context
def configure(ctx, force):
    if not ctx.invoked_subcommand is None:
        # subcommand provided, do not enter interactive mode
        return

    __print_header('Configuring insilico')
    logger.info('Running in %s', BASE_DIR)

    if not __prequisites_met():
        logger.error('Prerequisite checks failed')
        sys.exit(1)

    if force:
        __force_reconfigure()

    __populate_conf_dir()
    configuration = __load_configuration()
    __configure_ldap(configuration)
    __configure_nifi(configuration)
    __configure_system_dirs(configuration)
    __configure_certificates(configuration)
    __save_configuration(configuration)

    __clear_successful_configuration_record()
    #__copy_flow_file(configuration)
    __generate_environment_file(configuration)
    __generate_configuration_files(configuration)
    __set_successful_configuration_record()

@configure.command(help='Reads a setting from the Insilico configuration')
@click.argument('setting')
def get(setting):
    configuration = __load_configuration()
    print(configuration.get(setting))

@configure.command(help='Saves a setting to the Insilico configuration')
@click.argument('setting')
@click.argument('value')
def set(setting, value):
    configuration = __load_configuration()
    configuration.set(setting, value)
    configuration.save()

@configure.command(help='Applies the settings from the Insilico configuration')
@click.option('--file', type=Path,
    help='Applies the settings from the suppplied configuration file. NOTE: This will replace the extant configuration file.')
def apply(file):
    # NOTE: currently we just overwrite the extant file
    # in future we will want to do something smarter like a merge
    source = Path(f'{HOST_ROOT_DIR}/{file}')
    if not source.is_file():
        logger.error('Cannot access [%s]', file)
        sys.exit(1)

    target = Path(CONFIGURATION_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info('Copying [%s] to [%s]', source, target)
    shutil.copy2(source, target)

    __clear_successful_configuration_record()
    configuration = __load_configuration()
    __generate_environment_file(configuration)
    __generate_configuration_files(configuration)
    __set_successful_configuration_record()

# ------------------------------------------------------------------------------
# PRIVATE METHODS
# ------------------------------------------------------------------------------

def __prequisites_met():
    logger.info('Checking prerequisites ...')
    result = True

    for env_variable in MANDATORY_ENV_VARIABLES:
        value = os.environ.get(env_variable)
        if value == None:
            logger.error('Mandatory environment variable is not defined [%s]', env_variable)
            result = False

    for dir in [INSILICO_HOME, HOST_ROOT_DIR]:
        if dir and not os.path.isdir(dir):
            logger.error('Mandatory directory does not exist [%s]', dir)
            result = False

    return result

def __populate_conf_dir():
    logger.info('Populating [conf] directory ...')
    custom_dir = f'{INSILICO_HOME}/custom'
    conf_dir = f'{custom_dir}/conf'
    os.makedirs(conf_dir, exist_ok=True)

    previous_custom_dir = f'{INSILICO_HOME}/../previous/custom'

    # ensure insilico.yaml exists
    relative_name = 'conf/insilico.yaml'
    target = CONFIGURATION_FILE
    if not os.path.exists(target):
        previous_version = f'{previous_custom_dir}/{relative_name}'
        # prefer files from previous version if they exist
        source = previous_version if os.path.exists(previous_version) else f'{INSILICO_OPS_DIR}/{relative_name}'
        logger.info('Copying insilico.yaml from [%s]', source)
        shutil.copy2(source, target)

def __load_configuration():
    logger.info(f'Reading configuration from [{CONFIGURATION_FILE}]...')
    return ConfigurationManager(CONFIGURATION_FILE)

def __force_reconfigure():
    __print_header(f'Force reconfiguration')

    flow_file = f'{INSILICO_HOME}/custom/nifi-flow/flow.xml.gz'
    if not os.path.isfile(flow_file):
        logger.warning(f'No flow file found at [{flow_file}]. No need to force.')
        return

    if not __confirm('This will delete the current flow. Do you wish to continue?'):
        sys.exit(1)

    logger.info('Removing flow file ...')
    os.remove(flow_file)
    # clear last configured so that profile can be changed
    __clear_successful_configuration_record()

def __configure_ldap(configuration):
    __print_header(f'Configure LDAP settings')
    settings = [
        {
            'path': 'insilico.external.ldap.url',
            'message': 'URL of the LDAP server'
        },
        {
            'path': 'insilico.external.ldap.managerDN',
            'message': 'Distinguished Name (DN) for binding to LDAP'
        },
        {
            'path': 'insilico.external.ldap.managerPassword',
            'message': 'Password for binding to LDAP'
        },
    ]
    __print_current_settings(settings, configuration)
    if __confirm('Modify LDAP settings?'):
        __prompt_and_update_configuration(settings, configuration)

    __print_header(f'Configure LDAP user/group syncing settings')
    settings = [
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userSearchBase',
            'message': 'User Search Base'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userObjectClass',
            'message': 'User Object Class'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userSearchScope',
            'message': 'User Search Scope'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userSearchFilter',
            'message': 'User Search Filter'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userIdentityAttribute',
            'message': 'User Identity Attribute'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userGroupNameAttribute',
            'message': 'User Group Name Attribute'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.userGroupNameAttributeReferencedGroupAttribute',
            'message': 'User Group Name Attribute - Referenced Group Attribute'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupSearchBase',
            'message': 'Group Search Base'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupObjectClass',
            'message': 'Group Object Class'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupSearchScope',
            'message': 'Group Search Scope'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupSearchFilter',
            'message': 'Group Search Filter'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupNameAttribute',
            'message': 'Group Name Attribute'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupMemberAttribute',
            'message': 'Group Member Attribute'
        },
        {
            'path': 'insilico.external.ldap.userGroupSyncing.groupMemberAttributeReferencedUserAttribute',
            'message': 'Group Member Attribute - Referenced User Attribute'
        },

    ]
    __print_current_settings(settings, configuration)
    if __confirm('Modify LDAP user/group syncing settings?'):
        __prompt_and_update_configuration(settings, configuration)

def __configure_nifi(configuration):
    __print_header(f'Configure NiFi settings')
    settings = [
        {
            'path': 'insilico.nifi.url',
            'message': 'Comma separated list of URLs used to access NiFi web ui'
        },
        {
            'path': 'insilico.external.ldap.login.userSearchBase',
            'message': 'Base DN for searching for users'
        },
        {
            'path': 'insilico.external.ldap.login.userSearchFilter',
            'message': 'Filter for searching through users'
        },
        {
            'path': 'insilico.role.nifi.admin.username',
            'message': 'LDAP username for the NiFi administrator user'
        },
        {
            'path': 'insilico.role.nifi.admin.password',
            'message': 'LDAP password for the NiFi administrator user'
        },
    ]
    __print_current_settings(settings, configuration)
    if __confirm('Modify NiFi settings?'):
        __prompt_and_update_configuration(settings, configuration)

def __configure_system_dirs(configuration):
    __print_header(f'Configure system directories')

    # we are prepared to create the default 'insilico/common' directory but if the user wants 'common' to be
    # outside our 'insilico' directories, then they must have created the directory first
    host_data_dir = f'{INSILICO_ROOT}/common'
    logger.info(f'Creating system data directory [{host_data_dir}] ...')

    data_dir = f'{HOST_ROOT_DIR}/{host_data_dir}'
    os.makedirs(data_dir, exist_ok=True)

    settings = [
        {
            'path': 'insilico.directories.dataDir',
            'message': 'Directory to store all system data',
            'validate': lambda _, x: os.path.isdir(f'{HOST_ROOT_DIR}/{x}')
        },
    ]

    __print_current_settings(settings, configuration)
    if __confirm('Modify system data directory location?'):
        __prompt_and_update_configuration(settings, configuration)

    host_data_dir = f'{configuration.get("insilico.directories.dataDir")}'
    logger.info(f'Ensuring required sub-directories exist under [{host_data_dir}]')

    data_dir = f'{HOST_ROOT_DIR}/{host_data_dir}'
    os.makedirs(data_dir, exist_ok=True)
    subdirs = [
        'data/input',
        'data/output',
        'data/error',
        'data/nifi',
        'data/elasticsearch'
    ]
    _make_dirs(data_dir, subdirs)

    # Update configuration's input & databaseDir values so the paths are still relative to 'common',
    # but allow users to set data-heavy dirs (input, database) outside of this default.
    input_dir = f'{configuration.get("insilico.directories.dataDir")}/data/input'
    configuration.set('insilico.directories.inputDir', input_dir)
    database_dir = f'{configuration.get("insilico.directories.dataDir")}/data/elasticsearch'
    configuration.set('insilico.directories.databaseDir', database_dir)

    settings = [
        {
            'path': 'insilico.directories.inputDir',
            'message': 'Directory to detect and ingest input files',
            'validate': lambda _, x: os.path.isdir(f'{HOST_ROOT_DIR}/{x}')
        },
    ]

    __print_current_settings(settings, configuration)
    if __confirm('Modify system input directory location?'):
        __prompt_and_update_configuration(settings, configuration)

    settings = [
        {
            'path': 'insilico.directories.databaseDir',
            'message': 'Directory to store Database files',
            'validate': lambda _, x: os.path.isdir(f'{HOST_ROOT_DIR}/{x}')
        }
    ]

    __print_current_settings(settings, configuration)
    if __confirm('Modify system database directory location?'):
        __prompt_and_update_configuration(settings, configuration)

    output_dir = f'{configuration.get("insilico.directories.dataDir")}/data/output'
    configuration.set('insilico.directories.outputDir.localPath', output_dir)

    settings = [
        {
            'path': 'insilico.directories.outputDir.localPath',
            'message': 'Local directory to store output files',
            'validate': lambda _, x: os.path.isdir(f'{HOST_ROOT_DIR}/{x}')
        },
        {
            'path': 'insilico.directories.outputDir.externalPath',
            'message': 'External directory mounted to corresponding local directory'
            # no validation as this path is outside our system and we cannot validate it exists/is a
            # directory
        }
    ]

    __print_current_settings(settings, configuration)
    if __confirm('Modify system output directory location?'):
        __prompt_and_update_configuration(settings, configuration)

    # TODO: INS-378 determine if all these files need to live in data dir

    database_dir = f'{HOST_ROOT_DIR}/{configuration.get("insilico.directories.databaseDir")}'
    logger.info('Extracting sample database ...')
    with tarfile.open(f'{INSILICO_OPS_DIR}/data/elasticsearch/sample-db.tar.gz') as t:
        t.extractall(f'{database_dir}/')

    logger.info('Copying volume files ...')
    files = [
        'elasticsearch.yml',
        'jvm.options',
    ]
    _copy_files(files, f'{INSILICO_OPS_DIR}/data/elasticsearch', f'{database_dir}')
    _copy_files(['data/kibana/kibana.yml'], f'{INSILICO_OPS_DIR}', f'{data_dir}')

    logger.info('Copying NiFi configuration ...')
    files = [
        'users.xml',
        'authorizations.xml',
    ]
    _copy_files(files, f'{INSILICO_OPS_DIR}/template/insilico-nifi', f'{data_dir}/nifi')
    _copy_files(['nifi/scripts/CustomFieldValueMappingScript.groovy'], f'{INSILICO_OPS_DIR}', f'{data_dir}')

    # TODO: INS-378 we have two flow.xml files in insilico-ops for some reason
    flow_dir = f'{data_dir}/nifi/flow_configuration'
    target_flow_file = f'{flow_dir}/flow.xml.gz'
    if not os.path.exists(target_flow_file):
        os.makedirs(flow_dir, exist_ok=True)
        with gzip.open(target_flow_file, 'wb') as file_out:
            with open(f'{INSILICO_OPS_DIR}/nifi/flow.xml', 'rb') as file_in:
                shutil.copyfileobj(file_in, file_out)

def _make_dirs(parent, children):
    for child in children:
        os.makedirs(f'{parent}/{child}', exist_ok=True)

def _copy_files(files, source_dir, target_dir):
    for file in files:
        source = f'{source_dir}/{file}'
        target = f'{target_dir}/{file}'
        if os.path.exists(target):
            logger.warning(f'Skipping existing file [{target}]')
        else:
            logger.info(f'Copying to [{target}] ...')
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                parent_dir = os.path.dirname(target)
                os.makedirs(parent_dir, exist_ok=True)
                shutil.copy2(source, target)

def __configure_certificates(configuration):
    __print_header(f'Configure certificates')

    certificate_dir = f'{configuration.get("insilico.directories.dataDir")}/certificate'
    host_certificate_dir = f'{HOST_ROOT_DIR}/{certificate_dir}'
    os.makedirs(host_certificate_dir, exist_ok=True)

    if not os.path.isfile(f'{host_certificate_dir}/server-key.pem'):
        logger.info(f'Generating default certificates in [{certificate_dir}/] ...')
        command = ['openssl',
            'req',
            '-x509',
            '-days', '3650',
            '-nodes',
            '-newkey', 'rsa:2048',
            '-keyout', f'{host_certificate_dir}/server-key.pem',
            '-out', f'{host_certificate_dir}/server-cert.pem',
            '-subj', '/C=AU/ST=ACT/L=Canberra/O=brightSPARK Labs/OU=insilico/CN=*.insilico.local'
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not result.returncode == 0:
            logger.error('Could not generate default certificates')
            logger.error(result.stderr)
            sys.exit(1)

    if not __confirm('Configure custom certificates?'):
        return

    for target in ['server-key.pem', 'server-cert.pem']:
        answer = inquirer.prompt([
            inquirer.Text(
                'file',
                f'Path to custom [{target}]',
                validate=lambda _, x: os.path.isfile(f'{HOST_ROOT_DIR}/{x}')
            )
        ])
        source = f'{HOST_ROOT_DIR}/{answer["file"]}'
        logger.info(f'Copying certificate to [{certificate_dir}/{target}]')
        shutil.copy2(source, f'{host_certificate_dir}/{target}')

def __copy_flow_file(configuration):
    __print_header(f'Configure flow files')
    profile = configuration.get(PROFILE_SETTING_PATH)
    logger.info(f'Setting up [{profile}] flow ...')

    target_dir = f'{INSILICO_HOME}/custom/nifi-flow'
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    target = f'{target_dir}/flow.xml.gz'
    if os.path.exists(target):
        logger.warning(f'Leaving existing flow file in place at [{target}]')
        return

    source = f'{INSILICO_OPS_DIR}/conf/nifi-flow/{profile}/flow.xml'
    if not os.path.exists(source):
        logger.error(f'Could not find source flow file at [{source}]')
        raise EnvironmentError

    logger.info(f'Copying flow to [{target}]')
    with gzip.open(target, 'wb') as file_out:
        with open(source, 'rb') as file_in:
            shutil.copyfileobj(file_in, file_out)

def __save_configuration(configuration):
    __print_header(f'Saving configuration')
    configuration.save()

def __clear_successful_configuration_record():
    logger.info('Clearing successful configuration record ...')
    if os.path.exists(CONFIGURATION_RECORD_FILE):
        os.remove(CONFIGURATION_RECORD_FILE)

def __set_successful_configuration_record():
    logger.info('Saving successful configuration record ...')
    with open(CONFIGURATION_RECORD_FILE, 'w') as output_file:
        output_file.write(datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())

def __generate_environment_file(configuration):
    __print_header(f'Generating environment file')
    target_file = f'{INSILICO_HOME}/insilico-host.env'
    logger.info(f'Writing environment to [{target_file}]')
    __generate_from_template(
        f'{BASE_DIR}/templates/insilico-host.env.j2',
        target_file,
        configuration.get_as_dict()
    )

def __generate_configuration_files(configuration):
    __print_header(f'Generating configuration files')

    output_dir = f'{INSILICO_HOME}/.conf/generated'
    os.makedirs(output_dir, exist_ok=True)

    template_dir = f'{INSILICO_OPS_DIR}/template'
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
                __generate_from_template(source, target, configuration.get_as_dict())
            else:
                logger.info(f'Copying to [{target}]')
                shutil.copy2(source, target)

def __print_header(title):
    print('\n============================================================')
    print(title.upper())
    print('============================================================\n')

def __confirm(message, default=False):
    answer = inquirer.prompt([
        inquirer.Confirm('result', message=message, default=default)
    ])
    return answer['result']

def __print_current_settings(settings, configuration):
    logger.info('Current Settings:')
    for setting in settings:
        logger.info('  {0:<45} = {1}'.format(setting['message'], configuration.get(setting['path'])))
    print('')

def __prompt_and_update_configuration(settings, configuration):
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

def __generate_from_template(template_file, target_file, configuration):
    with open(template_file) as f:
        template = Template(f.read())
    try:
        output_text = template.render(configuration)
        with open(target_file, 'w') as f:
            f.write(output_text)
    except Exception as e:
        logger.error(f'Could not generate file from template. The configuration file is likely missing a setting: {e}')
        exit(1)

# ------------------------------------------------------------------------------
# ENTRYPOINT
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    configure(None)

