# -*- coding: utf-8 -*-
"""
Database models for Enterprise Integrated Channel.
"""

from __future__ import absolute_import, unicode_literals

import json
import logging

from integrated_channels.integrated_channel.exporters.course_metadata import CourseExporter
from integrated_channels.integrated_channel.exporters.learner_data import LearnerExporter
from integrated_channels.integrated_channel.transmitters.course_metadata import CourseTransmitter
from integrated_channels.integrated_channel.transmitters.learner_data import LearnerTransmitter

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from model_utils.models import TimeStampedModel

from enterprise.models import EnterpriseCustomer

LOGGER = logging.getLogger(__name__)


class EnterpriseCustomerPluginConfiguration(TimeStampedModel):
    """
    Abstract base class for information related to integrating with external systems for an enterprise customer.

    EnterpriseCustomerPluginConfiguration should be extended by configuration models in other integrated channel
    apps to provide uniformity across different integrated channels.

    The configuration provides default exporters and transmitters if the ``get_x_data_y`` methods aren't
    overridden, where ``x`` and ``y`` are (learner, course) and (exporter, transmitter) respectively.
    """

    enterprise_customer = models.OneToOneField(
        EnterpriseCustomer,
        blank=False,
        null=False
    )

    active = models.BooleanField(
        blank=False,
        null=False
    )

    class Meta:
        abstract = True

    @staticmethod
    def channel_code():
        """
        Returns an capitalized identifier for this channel class, unique among subclasses.
        """
        raise NotImplementedError('Implemented in concrete subclass.')

    def get_learner_data_exporter(self, user):
        """
        Returns the class that can serialize the learner course completion data to the integrated channel.
        """
        return LearnerExporter(user, self)

    def get_learner_data_transmitter(self):
        """
        Returns the class that can transmit the learner course completion data to the integrated channel.
        """
        return LearnerTransmitter(self)

    def get_course_data_exporter(self, user):
        """
        Returns a class that can retrieve, transform, and serialize the courseware data to the integrated channel.
        """
        return CourseExporter(user, self)

    def get_course_data_transmitter(self):
        """
        Returns a class that can transmit the courseware data to the integrated channel.
        """
        return CourseTransmitter(self)

    def transmit_learner_data(self, user):
        """
        Iterate over each learner data record and transmit it to the integrated channel.
        """
        exporter = self.get_learner_data_exporter(user)
        transmitter = self.get_learner_data_transmitter()
        transmitter.transmit(exporter)

    def transmit_course_data(self, user):
        """
        Compose the details from the concrete subclass to transmit the relevant data.
        """
        exporter = self.get_course_data_exporter(user)
        transmitter = self.get_course_data_transmitter()
        transmitter.transmit(exporter)


@python_2_unicode_compatible
class LearnerDataTransmissionAudit(models.Model):
    """
    The payload we send to an integrated channel  at a given point in time for an enterprise course enrollment.
    """

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
        app_label = 'integrated_channel'

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        """
        return (
            '<LearnerDataTransmissionAudit {transmission_id} for enterprise enrollment {enrollment}, '
            'and course {course_id}>'.format(
                transmission_id=self.id,
                enrollment=self.enterprise_course_enrollment_id,
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
        return None

    def serialize(self):
        """
        Return a JSON-serialized representation.

        Sort the keys so the result is consistent and testable.
        """
        return json.dumps(self._payload_data(), sort_keys=True)

    def _payload_data(self):
        """
        Convert the audit record's fields into SAP SuccessFactors key/value pairs.
        """
        return dict(
            courseID=self.course_id,
            courseCompleted="true" if self.course_completed else "false",
            completedTimestamp=self.completed_timestamp,
            grade=self.grade,
        )


@python_2_unicode_compatible
class CatalogTransmissionAudit(TimeStampedModel):
    """
    The summary of instances when the course catalog was sent to the integrated channel for an enterprise.
    """

    enterprise_customer_uuid = models.UUIDField(blank=False, null=False)
    total_courses = models.PositiveIntegerField(blank=False, null=False)
    status = models.CharField(max_length=100, blank=False, null=False)
    error_message = models.TextField(blank=True)
    audit_summary = models.TextField(default='{}')

    class Meta:
        app_label = 'integrated_channel'

    def __str__(self):
        """
        Return human-readable string representation.
        """
        return "<CatalogTransmissionAudit {} for Enterprise {}> for {} courses>".format(
            self.id,
            self.enterprise_customer_uuid,
            self.total_courses
        )

    def __repr__(self):
        """
        Return uniquely identifying string representation.
        """
        return self.__str__()
