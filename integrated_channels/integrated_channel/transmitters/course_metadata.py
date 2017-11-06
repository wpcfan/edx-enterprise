# -*- coding: utf-8 -*-
"""
Generic course metadata transmitter for integrated channels.
"""

from __future__ import absolute_import, unicode_literals

import json
import logging

from integrated_channels.integrated_channel.client import IntegratedChannelApiClient
from integrated_channels.integrated_channel.transmitters import Transmitter
from requests import RequestException

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

LOGGER = logging.getLogger(__name__)


class CourseTransmitter(Transmitter):
    """
    A generic course metadata transmitter.

    It may be subclassed by specific integrated channel course metadata transmitters for
    each integrated channel's particular course metadata transmission requirements and expectations.
    """

    def __init__(self, enterprise_configuration, client=IntegratedChannelApiClient):
        """

        """
        super(CourseTransmitter, self).__init__(
            enterprise_configuration=enterprise_configuration,
            client=client
        )

    def transmit(self, payload):
        """
        Transmit the course metadata payload to the integrated channel.
        """
        # pylint: disable=invalid-name
        CatalogTransmissionAudit = apps.get_model('integrated_channel', 'CatalogTransmissionAudit')
        try:
            # TODO: Make what catalog transmission audit class we use configurable -- different integrated channels
            # may use subclassed catalog transmission audits, but still reuse CourseTransmitter's
            # pre-built transmission functionality.
            last_catalog_transmission = CatalogTransmissionAudit.objects.filter(
                error_message='',
                enterprise_customer_uuid=self.enterprise_configuration.enterprise_customer.uuid
            ).latest('created')
        except ObjectDoesNotExist:
            last_audit_summary = {}
        else:
            last_audit_summary = json.loads(last_catalog_transmission.audit_summary)

        total_transmitted = 0
        errors = []
        status_codes = []
        for course_metadata in payload.export():
            status_code, body = self.transmit_block(course_metadata)
            status_codes.append(str(status_code))
            error_message = body if status_code >= 400 else ''
            if error_message:
                errors.append(error_message)
            else:
                total_transmitted += len(course_metadata)

        error_message = ', '.join(errors) if errors else ''
        code_string = ', '.join(status_codes)

        catalog_transmission_audit = CatalogTransmissionAudit(
            enterprise_customer_uuid=self.enterprise_configuration.enterprise_customer.uuid,
            total_courses=len(payload.courses),
            status=code_string,
            error_message=error_message,
            audit_summary=json.dumps(payload.resolve_removed_courses(last_audit_summary)),
        )
        catalog_transmission_audit.save()

    def transmit_block(self, course_metadata):
        """
        SAPSuccessFactors can only send 1000 items at a time, so this method sends one "page" at a time.

        Args:
            course_metadata (bytes): A set of bytes containing a page's worth of course metadata

        Returns:
            status_code (int): An integer status for the HTTP request
            body (str): The SAP SuccessFactors server's response body
        """
        LOGGER.info(course_metadata)
        try:
            status_code, body = self.client.send_course_import(course_metadata)
        except RequestException as request_exception:
            status_code = 500
            body = str(request_exception)

        if status_code >= 400:
            LOGGER.error('Failed to send course metadata for Enterprise Customer {}\nError Message {}'.
                         format(self.enterprise_configuration.enterprise_customer.name, body))
        else:
            LOGGER.debug('Successfully sent course metadata for Enterprise Customer {}'.
                         format(self.enterprise_configuration.enterprise_customer.name))

        return status_code, body
