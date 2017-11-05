# -*- coding: utf-8 -*-
"""
Class for transmitting learner data to Degreed.
"""

from __future__ import absolute_import, unicode_literals

import logging

from integrated_channels.degreed.client import DegreedAPIClient
from integrated_channels.integrated_channel.transmitters.learner_data import LearnerTransmitter
from requests import RequestException

from django.apps import apps

LOGGER = logging.getLogger(__name__)


class DegreedLearnerTransmitter(LearnerTransmitter):
    """
    This endpoint is intended to receive learner data routed from the integrated_channel app that is ready to be
    sent to Degreed.
    """

    def __init__(self, enterprise_configuration, client=DegreedAPIClient):
        """
        Ensure that, by default, the client used for Degreed Learner Data transmission is ``DegreedAPIClient``.
        """
        super(DegreedLearnerTransmitter, self).__init__(
            enterprise_configuration=enterprise_configuration,
            client=client
        )

    def transmit(self, payload):
        """
        Send a completion status call to Degreed using the client.

        Args:
            payload: The learner completion data payload to send to Degreed
        """
        DegreedLearnerDataTransmissionAudit = apps.get_model(  # pylint: disable=invalid-name
            app_label='degreed',
            model_name='DegreedLearnerDataTransmissionAudit'
        )
        for learner_data in payload.export():
            serialized_payload = {
                'orgCode': self.enterprise_configuration.degreed_company_id,
                'completions': [learner_data.serialize()]
            }
            LOGGER.info(serialized_payload)

            enterprise_enrollment_id = learner_data.enterprise_course_enrollment_id
            if learner_data.completed_timestamp is None:
                # The user has not completed the course, so we shouldn't send a completion status call
                LOGGER.debug('Skipping in progress enterprise enrollment {}'.format(enterprise_enrollment_id))
                return None

            previous_transmissions = DegreedLearnerDataTransmissionAudit.objects.filter(
                enterprise_course_enrollment_id=enterprise_enrollment_id,
                error_message=''
            )
            if previous_transmissions.exists():
                # We've already sent a completion status call for this enrollment
                LOGGER.debug('Skipping previously sent enterprise enrollment {}'.format(enterprise_enrollment_id))
                return None

            try:
                code, body = self.client.send_completion_status(learner_data.degreed_user_id, serialized_payload)
                LOGGER.debug('Successfully sent completion status call for enterprise enrollment {} with payload {}'.
                             format(enterprise_enrollment_id, serialized_payload))
            except RequestException as request_exception:
                code = 500
                body = str(request_exception)
                LOGGER.error('Failed to send completion status call for enterprise enrollment {} with payload {}'
                             '\nError message: {}'.format(enterprise_enrollment_id, learner_data, body))

            learner_data.status = str(code)
            learner_data.error_message = body if code >= 400 else ''
            learner_data.save()
