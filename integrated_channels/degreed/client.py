# -*- coding: utf-8 -*-
"""
Client for connecting to Degreed.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import time

import requests

from django.apps import apps


class DegreedAPIClient(object):
    """
    Client for connecting to Degreed.

    Specifically, this class supports obtaining access tokens and posting to the courses and
    completion status endpoints.
    """

    CONTENT_PROVIDER_SCOPE = 'provider_content'
    COMPLETION_PROVIDER_SCOPE = 'provider_completion'
    SESSION_TIMEOUT = 60

    def __init__(self, enterprise_configuration):
        """
        Instantiate a new client.

        Args:
            enterprise_configuration (DegreedEnterpriseCustomerConfiguration): An enterprise customers's
            configuration model for connecting with Degreed

        Raises:
            ValueError: If a URL or access token are not provided.
        """

        if not enterprise_configuration:
            raise ValueError('An DegreedEnterpriseCustomerConfiguration must be supplied!')

        self.global_degreed_config = apps.get_model('degreed', 'DegreedGlobalConfiguration').current()
        self.enterprise_configuration = enterprise_configuration
        self.session = None
        self.expires_at = None

    def send_completion_status(self, payload):
        """
        Send a completion status payload to the Degreed Completion Status endpoint

        Args:
            degreed_user_id (str): The degreed user id that the completion status is being sent for.
            payload (str): JSON encoded object (serialized from DegreedLearnerDataTransmissionAudit)
                containing completion status fields per Degreed documentation.

        Returns:
            The body of the response from Degreed, if successful
        Raises:
            HTTPError: if we received a failure response code from Degreed
        """
        url = self.global_degreed_config.degreed_base_url + self.global_degreed_config.completion_status_api_path
        return self._post(url, payload, self.COMPLETION_PROVIDER_SCOPE)

    def send_course_import(self, payload):
        """
        Send courses payload to the Degreed Course Content endpoint

        Args:
            payload: JSON encoded object containing course import data per Degreed documentation.

        Returns:
            The body of the response from Degreed, if successful
        Raises:
            HTTPError: if we received a failure response code from Degreed
        """
        url = self.global_degreed_config.degreed_base_url + self.global_degreed_config.course_api_path
        return self._post(url, payload, self.CONTENT_PROVIDER_SCOPE)

    def _post(self, url, data, scope):
        """
        Make a post request using the session object to a Degreed endpoint.

        Args:
            url (str): The url to post to.
            data (str): The json encoded payload to post.
            scope (str): Must be one of
        """
        now = datetime.datetime.utcnow()
        if now >= self.expires_at or self.session is None:
            # Create a new session with a valid token
            if self.session:
                self.session.close()
            self._create_session(scope)
        response = self.session.post(url, data=data)
        return response.status_code, response.text

    def _create_session(self, scope):
        """
        Instantiate a new session object for use in connecting with Degreed
        """
        oauth_access_token, expires_at = self._get_oauth_access_token(
            self.enterprise_configuration.key,
            self.enterprise_configuration.secret,
            self.global_degreed_config.degreed_user_id,
            self.global_degreed_config.degreed_user_password,
            scope
        )
        session = requests.Session()
        session.timeout = self.SESSION_TIMEOUT
        session.headers['Authorization'] = 'Bearer {}'.format(oauth_access_token)
        session.headers['content-type'] = 'application/json'
        self.session = session
        self.expires_at = expires_at

    def _get_oauth_access_token(self, client_id, client_secret, user_id, user_password, scope):
        """ Retrieves OAuth 2.0 access token using the client credentials grant.

        Args:
            url_base (str): Oauth2 access token endpoint
            client_id (str): client ID
            client_secret (str): client secret
            company_id (str): Degreed company ID
            user_id (str): Degreed user ID
            user_type (str): type of Degreed user (admin or user)

        Returns:
            tuple: Tuple containing access token string and expiration datetime.
        Raises:
            HTTPError: If we received a failure response code from Degreed.
            RequestException: If an unexpected response format was received that we could not parse.
            ValueError: If the provided scope does not match any available Degreed API provider scopes.
        """
        url = self.global_degreed_config.oauth_api_path + self.global_degreed_config.oauth_api_path

        response = requests.post(
            url,
            json={
                'grant_type': 'password',
                'username': user_id,
                'password': user_password,
                'scope': scope,
            },
            auth=(client_id, client_secret),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        response.raise_for_status()
        data = response.json()
        try:
            return data['access_token'], datetime.datetime.utcfromtimestamp(data['expires_in'] + int(time.time()))
        except KeyError:
            raise requests.RequestException(response=response)
