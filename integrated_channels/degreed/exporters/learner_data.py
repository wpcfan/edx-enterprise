# -*- coding: utf-8 -*-
"""
Learner data exporter for Enterprise Integrated Channel Degreed.
"""


from __future__ import absolute_import, unicode_literals

from logging import getLogger

from integrated_channels.integrated_channel.exporters.learner_data import LearnerExporter
from integrated_channels.utils import parse_datetime_to_epoch

from django.apps import apps

LOGGER = getLogger(__name__)


class DegreedLearnerExporter(LearnerExporter):
    """
    Base class for exporting learner completion data to integrated channels.
    """

    GRADE_PASSING = 'Pass'
    GRADE_FAILING = 'Fail'
    GRADE_INCOMPLETE = 'In Progress'

    def get_learner_data_record(self, enterprise_enrollment, completed_date=None, grade=None, is_passing=False):
        """
        Return a DegreedLearnerDataTransmissionAudit with the given enrollment and course completion data.

        If completed_date is None, then course completion has not been met.

        If no remote ID can be found, return None.
        """
        completed_timestamp = None
        course_completed = False
        if completed_date is not None:
            completed_timestamp = parse_datetime_to_epoch(completed_date)
            course_completed = is_passing

        degreed_user_id = enterprise_enrollment.enterprise_customer_user.get_remote_id()

        if degreed_user_id is not None:
            DegreedLearnerDataTransmissionAudit = apps.get_model(  # pylint: disable=invalid-name
                'degreed',
                'DegreedLearnerDataTransmissionAudit'
            )
            return DegreedLearnerDataTransmissionAudit(
                enterprise_course_enrollment_id=enterprise_enrollment.id,
                degreed_user_id=degreed_user_id,
                course_id=enterprise_enrollment.course_id,
                course_completed=course_completed,
                completed_timestamp=completed_timestamp,
                grade=grade,
            )
        else:
            LOGGER.debug(
                'No learner data was sent for user "%s" because an Degreed user ID could not be found.',
                enterprise_enrollment.enterprise_customer_user.username
            )
