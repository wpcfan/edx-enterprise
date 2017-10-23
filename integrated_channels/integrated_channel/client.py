# -*- coding: utf-8 -*-
"""
Base API client for integrated channels.
"""

from __future__ import absolute_import, unicode_literals


class IntegratedChannelApiClient(object):
    """
    This is the interface to be implemented by API clients for integrated channels.

    The interface contains the following method(s):

    send_completion_status(user_id, payload)
        Makes a POST request to the integrated channel's completion API for the given user with information
        available in the payload.

    send_course_import(payload):
        Make a POST request to the integrated channel's course content API with course metadata available
        in the payload.
    """

    def send_completion_status(self, user_id, payload):
        """
        Make a POST request to the integrated channel's completion API to update completion status for a user.

        :param user_id: The ID of the user for whom completion status must be updated.
        :param payload: The JSON encoded payload containing the completion data.
        """
        raise NotImplementedError('Implement in concrete subclass.')

    def send_course_import(self, payload):
        """
        Make a POST request to the integrated channel's course content API to update course metadata.

        :param payload: The JSON encoded payload containing the course metadata.
        """
        raise NotImplementedError('Implement in concrete subclass.')
