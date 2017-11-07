# -*- coding: utf-8 -*-
"""
Database models for Enterprise Integrated Channel Degreed.
"""

from __future__ import absolute_import, unicode_literals

import json
from logging import getLogger

from config_models.models import ConfigurationModel
from integrated_channels.degreed.exporters.course_metadata import DegreedCourseExporter
from integrated_channels.degreed.exporters.learner_data import DegreedLearnerExporter
from integrated_channels.degreed.transmitters.course_metadata import DegreedCourseTransmitter
from integrated_channels.degreed.transmitters.learner_data import DegreedLearnerTransmitter
from integrated_channels.integrated_channel.models import EnterpriseCustomerPluginConfiguration
from simple_history.models import HistoricalRecords

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

LOGGER = getLogger(__name__)


@python_2_unicode_compatible
class DegreedGlobalConfiguration(ConfigurationModel):
    """
    The global configuration for integrating with Degreed.
    """

    completion_status_api_path = models.CharField(max_length=255)
    course_api_path = models.CharField(max_length=255)
    oauth_api_path = models.CharField(max_length=255)
    provider_id = models.CharField(max_length=100, default='EDX')

    class Meta:
        app_label = 'degreed'

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        """
        return "<DegreedGlobalConfiguration with id {id}>".format(id=self.id)

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()


@python_2_unicode_compatible
class DegreedEnterpriseCustomerConfiguration(EnterpriseCustomerPluginConfiguration):
    """
    The Enterprise specific configuration we need for integrating with Degreed.
    """

    USER_TYPE_USER = 'user'
    USER_TYPE_ADMIN = 'admin'

    USER_TYPE_CHOICES = (
        (USER_TYPE_USER, 'User'),
        (USER_TYPE_ADMIN, 'Admin'),
    )

    key = models.CharField(max_length=255, blank=True, verbose_name="Client ID")
    degreed_base_url = models.CharField(max_length=255, verbose_name="Degreed Base URL")
    degreed_company_id = models.CharField(max_length=255, blank=True, verbose_name="Degreed Company ID")
    degreed_user_id = models.CharField(max_length=255, blank=True, verbose_name="Degreed User ID")
    secret = models.CharField(max_length=255, blank=True, verbose_name="Client Secret")
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        blank=False,
        default=USER_TYPE_USER,
        verbose_name="Degreed User Type"
    )

    history = HistoricalRecords()

    class Meta:
        app_label = 'degreed'

    def __str__(self):
        """
        Return human-readable string representation.
        """
        return "<DegreedEnterpriseCustomerConfiguration for Enterprise {enterprise_name}>".format(
            enterprise_name=self.enterprise_customer.name
        )

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()

    @staticmethod
    def channel_code():
        """
        Returns an capitalized identifier for this channel class, unique among subclasses.
        """
        return 'Degreed'

    @property
    def provider_id(self):
        '''
        Fetch ``provider_id`` from global configuration settings
        '''
        return DegreedGlobalConfiguration.current().provider_id

    def get_learner_data_transmitter(self):
        """
        Return a ``DegreedLearnerTransmitter`` instance.
        """
        return DegreedLearnerTransmitter(self)

    def get_learner_data_exporter(self, user):
        """
        Return a ``DegreedLearnerDataExporter`` instance.
        """
        return DegreedLearnerExporter(user, self)

    def get_course_data_transmitter(self):
        """
        Return a ``DegreedCourseTransmitter`` instance.
        """
        return DegreedCourseTransmitter(self)

    def get_course_data_exporter(self, user):
        """
        Return a ``DegreedCourseExporter`` instance.
        """
        return DegreedCourseExporter(user, self)


@python_2_unicode_compatible
class DegreedLearnerDataTransmissionAudit(models.Model):
    """
    The payload we sent to Degreed at a given point in time for an enterprise course enrollment.
    """

    degreed_user_id = models.CharField(max_length=255, blank=False, null=False)
    enterprise_course_enrollment_id = models.PositiveIntegerField(blank=False, null=False)
    course_id = models.CharField(max_length=255, blank=False, null=False)
    course_completed = models.BooleanField(default=True)
    completed_timestamp = models.BigIntegerField()
    instructor_name = models.CharField(max_length=255, blank=True)
    grade = models.CharField(max_length=100, blank=False, null=False)
    status = models.CharField(max_length=100, blank=False, null=False)
    error_message = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'degreed'

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        """
        return (
            '<DegreedLearnerDataTransmissionAudit {transmission_id} for enterprise enrollment {enrollment}, '
            'Degreed user {degreed_user_id}, and course {course_id}>'.format(
                transmission_id=self.id,
                enrollment=self.enterprise_course_enrollment_id,
                degreed_user_id=self.degreed_user_id,
                course_id=self.course_id
            )
        )

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()

    @property
    def provider_id(self):
        """
        Fetch ``provider_id`` from global configuration settings
        """
        return DegreedGlobalConfiguration.current().provider_id

    def serialize(self):
        """
        Return a JSON-serialized representation.

        Sort the keys so the result is consistent and testable.
        """
        return json.dumps(self._payload_data(), sort_keys=True)

    def _payload_data(self):
        """
        Convert the audit record's fields into Degreed key/value pairs.
        """
        return dict(
            userID=self.degreed_user_id,
            courseID=self.course_id,
            providerID=self.provider_id,
            courseCompleted="true" if self.course_completed else "false",
            completedTimestamp=self.completed_timestamp,
            grade=self.grade,
        )
