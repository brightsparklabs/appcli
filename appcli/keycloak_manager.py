#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Keycloak API wrapper to enable access to Keycloak administration functions.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
from keycloak import KeycloakAdmin

# local libraries
from appcli.logger import logger

# ------------------------------------------------------------------------------
# EXTERNAL CLASSES
# ------------------------------------------------------------------------------


class KeycloakManager:
    """Class to provide simplified access to common keycloak functionality.

    This class is mostly a clean BSL-type wrapper around the `python-keycloak` library which is
    available here: https://github.com/marcospereirampj/python-keycloak.

      Typical usage example:

      keycloak = KeycloakManager("http://localhost/auth/", "admin", "password")
      keycloak.create_realm("example-realm")
      keycloak.create_client("example-realm", "example-client", {"redirectUris" : [ "*" ]})
    """

    def __init__(self, server_url, admin_username, admin_password, insecure=False):
        """Main constructor.

        Creates a new KeycloakManager object.

        Args:
            server_url (string): URL to the keycloak server's auth API endpoint. e.g. "http://localhost/auth/"
            admin_username (string): Administrator username for accessing the Keycloak admin API endpoint.
            admin_password (string): The password to the administrator user.
            insecure (boolean): Whether to allow insecure SSL connections to Keycloak. Defaults to 'False'.

        Returns:
            The initialised KeycloakManager object
        """

        self.server_url = server_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.insecure = insecure

        # A dict containing instances of the KeycloakAdmin for different realms
        self.keycloak_admins = {}

        # Connect to the master realm to ensure the url/username/password are correct
        self.__get_keycloak_admin()

    def __get_keycloak_admin(self, realm_name="master") -> KeycloakAdmin:
        """Private function to get a Keycloak administration object which points at a specific realm.

        Uses a dict to store all instances of the Keycloak administration object as a cache. This
        ensures that we use one and only one admin object per realm.

        Args:
            realm_name (string): name of the realm to associate the keycloak admin object

        Returns:
            The initialised Keycloak admin object

        Raises:
            keycloak.exceptions.KeycloakConnectionError: Failed to connect to keycloak (invalid url/server unavailable)
            keycloak.exceptions.KeycloakAuthenticationError: Invalid user credentials
        """

        if realm_name not in self.keycloak_admins:
            # Can't log directly into a non-master realm, set the realm after logging in to the 'master' realm
            # There's flipped logic for 'self.insecure' and 'verify', as 'verified connection == not insecure'
            self.keycloak_admins[realm_name] = KeycloakAdmin(
                server_url=self.server_url,
                username=self.admin_username,
                password=self.admin_password,
                realm_name="master",
                verify=(not self.insecure),
            )
            self.keycloak_admins[realm_name].realm_name = realm_name
        return self.keycloak_admins[realm_name]

    def create_realm(self, realm_name, custom_payload={}):
        """Create a realm with a given name.

        Args:
            realm_name (string): name of the realm to create
            custom_payload (dict): additional payload to send to the API endpoint. This allows for
                setting additional properties on the newly-created object.
        """

        payload = {"realm": realm_name, "enabled": "true", **custom_payload}
        kc = self.__get_keycloak_admin()
        kc.create_realm(payload=payload, skip_exists=False)

    def create_client(self, realm_name, client_name, custom_payload={}):
        """Create a client in a given realm with a given name.

        Args:
            realm_name (string): parent realm of the client
            client_name (string): name of the client
            custom_payload (dict): additional payload to send to the API endpoint. This allows for
                setting additional properties on the newly-created object.
        """

        payload = {"clientId": client_name, "enabled": "true", **custom_payload}
        kc = self.__get_keycloak_admin(realm_name)
        kc.create_client(payload=payload, skip_exists=False)
        client_id = kc.get_client_id(client_name)
        return kc.get_client_secrets(client_id)

    def get_client_secret(self, realm_name, client_name):
        """Get the client secret of a given client in a given realm.

        Args:
            realm_name (string): parent realm of the client
            client_name (string): name of the client
        """

        kc = self.__get_keycloak_admin(realm_name)
        client_id = kc.get_client_id(client_name)
        return kc.get_client_secrets(client_id)["value"]

    def create_realm_role(self, realm_name, role_name, custom_payload={}):
        """Create a role at the realm level.

        Args:
            realm_name (string): parent realm of the role
            role_name (string): name of the role
            custom_payload (dict): additional payload to send to the API endpoint. This allows for
                setting additional properties on the newly-created object.
        """

        payload = {"name": role_name, **custom_payload}
        kc = self.__get_keycloak_admin(realm_name)
        kc.create_realm_role(payload=payload)

    def create_user(
        self,
        realm_name,
        username,
        password,
        first_name,
        last_name,
        email,
        custom_payload={},
    ):
        """Create a user in a given realm.

        Args:
            realm_name (string): realm of the user
            username (string): user's username
            password (string): user's password
            first_name (string): user's first name
            last_name (string): user's last name
            email (string): user's email address
            custom_payload (dict): additional payload to send to the API endpoint. This allows for
                setting additional properties on the newly-created object.
        """

        payload = {
            "username": username,
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "emailVerified": "true",
            "enabled": "true",
            **custom_payload,
        }
        kc = self.__get_keycloak_admin(realm_name)
        kc.create_user(payload=payload)
        user_id = kc.get_user_id(username)
        kc.set_user_password(user_id, password, False)

    def assign_realm_role(self, realm_name, username, role_name):
        """Assign a realm role to a user.

        Args:
            realm_name (string): realm containing the role and the user
            username (string): username of the user to add the role
            role_name (string): name of the role to add to the user
            custom_payload (dict): additional payload to send to the API endpoint. This allows for
                setting additional properties on the newly-created object.
        """

        kc = self.__get_keycloak_admin(realm_name)
        user_id = kc.get_user_id(username)
        all_realm_roles = kc.get_realm_roles()
        roles = [role for role in all_realm_roles if role["name"] == role_name]
        kc.assign_realm_roles(user_id, None, roles)

    def configure_default(self, app_name_slug):
        """Applies the default opinionated configuration to Keycloak

        This does the following:
         - Creates a realm named '<app_name_slug>'
         - For realm '<app_name_slug>', creates a client with the name '<app_name_slug>', which has an audience mapper to itself,
           and redirect URIs of ["*"]
         - For realm '<app_name_slug>', creates a realm role '<app_name_slug>-admin'
         - For realm '<app_name_slug>', creates a user 'test.user' with password 'password', and assigns the realm role
           '<app_name_slug>-admin'

        """
        self.create_realm(app_name_slug)
        logger.debug(f"Created realm [{app_name_slug}]")

        client_payload = {
            "redirectUris": ["*"],
            "protocolMappers": [
                {
                    "name": f"{app_name_slug}-audience",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-audience-mapper",
                    "consentRequired": "false",
                    "config": {
                        "included.client.audience": app_name_slug,
                        "id.token.claim": "false",
                        "access.token.claim": "true",
                    },
                }
            ],
        }
        self.create_client(app_name_slug, app_name_slug, client_payload)
        secret = self.get_client_secret(app_name_slug, app_name_slug)
        logger.debug(f"Created client [{app_name_slug}] with secret [{secret}]")

        realm_role = f"{app_name_slug}-admin"
        self.create_realm_role(app_name_slug, realm_role)
        logger.debug(f"Created realm role [{realm_role}]")

        username = "test.user"
        self.create_user(
            app_name_slug, username, "password", "Test", "User", "test.user@email.test"
        )
        logger.debug(
            f"Created user [test.user] with password [password] in realm [{app_name_slug}]"
        )

        self.assign_realm_role(app_name_slug, username, realm_role)
        logger.debug(f"Assigned realm role [{realm_role}] to user [test.user]")
