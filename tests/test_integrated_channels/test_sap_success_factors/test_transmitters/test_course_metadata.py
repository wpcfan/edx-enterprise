# -*- coding: utf-8 -*-
"""
Tests for SAPSF course metadata transmissions.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import json
import unittest

import mock
from integrated_channels.integrated_channel.models import CatalogTransmissionAudit
from integrated_channels.sap_success_factors.models import (
    SAPSuccessFactorsEnterpriseCustomerConfiguration,
    SAPSuccessFactorsGlobalConfiguration,
)
from integrated_channels.sap_success_factors.transmitters import course_metadata
from pytest import mark
from requests import RequestException

from test_utils.factories import EnterpriseCustomerFactory


@mark.django_db
class TestSuccessFactorsCourseTransmitter(unittest.TestCase):
    """
    Tests for the class ``SapSuccessFactorsCourseTransmitter``.
    """

    def setUp(self):
        super(TestSuccessFactorsCourseTransmitter, self).setUp()
        SAPSuccessFactorsGlobalConfiguration.objects.create(
            completion_status_api_path="",
            course_api_path="",
            oauth_api_path=""
        )

        enterprise_customer = EnterpriseCustomerFactory(
            name='Starfleet Academy',
        )

        self.enterprise_config = SAPSuccessFactorsEnterpriseCustomerConfiguration(
            enterprise_customer=enterprise_customer,
            key="client_id",
            sapsf_base_url="http://test.successfactors.com/",
            sapsf_company_id="company_id",
            sapsf_user_id="user_id",
            secret="client_secret"
        )
        self.payload = [{'course1': 'test1'}, {'course2': 'test2'}]

        # Mocks
        get_oauth_access_token_mock = mock.patch(
            'integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.get_oauth_access_token'
        )
        self.get_oauth_access_token_mock = get_oauth_access_token_mock.start()
        self.get_oauth_access_token_mock.return_value = "token", datetime.datetime.utcnow()
        self.addCleanup(get_oauth_access_token_mock.stop)

        send_course_import_mock = mock.patch(
            'integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.send_course_import'
        )
        self.send_course_import_mock = send_course_import_mock.start()
        self.addCleanup(send_course_import_mock.stop)

    def test_transmit_success(self):
        """
        The catalog data transmission audit that gets saved after the transmission completes contains success data.
        """
        self.send_course_import_mock.return_value = 200, '{"success":"true"}'
        course_exporter_mock = mock.MagicMock(courses=self.payload)
        course_exporter_mock.export.return_value = [json.dumps(self.payload)]
        course_exporter_mock.resolve_removed_courses.return_value = {}
        transmitter = course_metadata.SapSuccessFactorsCourseTransmitter(self.enterprise_config)
        transmitter.transmit(course_exporter_mock)
        self.send_course_import_mock.assert_called_with(json.dumps(self.payload))
        course_exporter_mock.resolve_removed_courses.assert_called_with({})
        course_exporter_mock.export.assert_called()
        catalog_transmission_audit = CatalogTransmissionAudit.objects.filter(
            enterprise_customer_uuid=self.enterprise_config.enterprise_customer.uuid
        ).latest('created')
        assert catalog_transmission_audit.enterprise_customer_uuid == self.enterprise_config.enterprise_customer.uuid
        assert catalog_transmission_audit.total_courses == len(self.payload)
        assert catalog_transmission_audit.status == '200'
        assert catalog_transmission_audit.error_message == ''

    def test_transmit_failure(self):
        """
        The catalog data transmission audit that gets saved after the transmission completes contains error data.
        """
        self.send_course_import_mock.side_effect = RequestException('error occurred')
        course_exporter_mock = mock.MagicMock(courses=self.payload)
        course_exporter_mock.export.return_value = [json.dumps(self.payload)]
        course_exporter_mock.resolve_removed_courses.return_value = {}
        transmitter = course_metadata.SapSuccessFactorsCourseTransmitter(self.enterprise_config)
        transmitter.transmit(course_exporter_mock)
        self.send_course_import_mock.assert_called_with(json.dumps(self.payload))
        course_exporter_mock.export.assert_called()
        course_exporter_mock.resolve_removed_courses.assert_called_with({})
        catalog_transmission_audit = CatalogTransmissionAudit.objects.filter(
            enterprise_customer_uuid=self.enterprise_config.enterprise_customer.uuid
        ).latest('created')
        assert catalog_transmission_audit.enterprise_customer_uuid == self.enterprise_config.enterprise_customer.uuid
        assert catalog_transmission_audit.total_courses == len(self.payload)
        assert catalog_transmission_audit.status == '500'
        assert catalog_transmission_audit.error_message == 'error occurred'

    def test_transmit_with_previous_audit(self):
        """
        Covers the case where transmission occurs and there existed a catalog data transmission audit previously.
        """
        audit_summary = {
            'test_course': {
                'in_catalog': True,
                'status': 'ACTIVE',
            }
        }
        transmission_audit = CatalogTransmissionAudit(
            enterprise_customer_uuid=self.enterprise_config.enterprise_customer.uuid,
            total_courses=2,
            status='200',
            error_message='',
            audit_summary=json.dumps(audit_summary),
        )
        transmission_audit.save()
        self.send_course_import_mock.return_value = 200, '{"success":"true"}'
        course_exporter_mock = mock.MagicMock(courses=self.payload)
        course_exporter_mock.export.return_value = [json.dumps(self.payload)]
        course_exporter_mock.resolve_removed_courses.return_value = {}
        transmitter = course_metadata.SapSuccessFactorsCourseTransmitter(self.enterprise_config)
        transmitter.transmit(course_exporter_mock)
        self.send_course_import_mock.assert_called_with(json.dumps(self.payload))
        course_exporter_mock.resolve_removed_courses.assert_called_with(audit_summary)
        course_exporter_mock.export.assert_called()
        catalog_transmission_audit = CatalogTransmissionAudit.objects.filter(
            enterprise_customer_uuid=self.enterprise_config.enterprise_customer.uuid
        ).latest('created')
        assert catalog_transmission_audit.enterprise_customer_uuid == self.enterprise_config.enterprise_customer.uuid
        assert catalog_transmission_audit.total_courses == len(self.payload)
        assert catalog_transmission_audit.status == '200'
        assert catalog_transmission_audit.error_message == ''
