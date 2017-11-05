# -*- coding: utf-8 -*-
"""
Test the Enterprise management commands and related functions.
"""
from __future__ import absolute_import, unicode_literals, with_statement

import logging
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta

import mock
import responses
from faker import Factory as FakerFactory
from freezegun import freeze_time
from integrated_channels.integrated_channel.exporters.learner_data import LearnerExporter
from integrated_channels.sap_success_factors.models import SAPSuccessFactorsEnterpriseCustomerConfiguration
from pytest import mark, raises
from requests.compat import urljoin
from testfixtures import LogCapture

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from enterprise.api_client import lms as lms_api
from test_utils import factories
from test_utils.fake_catalog_api import CourseDiscoveryApiTestMixin
from test_utils.fake_enterprise_api import EnterpriseMockMixin


@mark.django_db
class TestTransmitCoursewareDataManagementCommand(unittest.TestCase, EnterpriseMockMixin, CourseDiscoveryApiTestMixin):
    """
    Test the transmit_course_metadata management command.
    """

    def setUp(self):
        self.user = factories.UserFactory(username='C-3PO')
        self.enterprise_customer = factories.EnterpriseCustomerFactory(
            catalog=1,
            name='Veridian Dynamics',
        )
        self.sapsf = factories.SAPSuccessFactorsEnterpriseCustomerConfigurationFactory(
            enterprise_customer=self.enterprise_customer,
            sapsf_base_url='http://enterprise.successfactors.com/',
            key='key',
            secret='secret',
            active=True,
        )
        self.catalog_api_config_mock = self._make_patch(self._make_catalog_api_location("CatalogIntegration"))
        super(TestTransmitCoursewareDataManagementCommand, self).setUp()

    def test_enterprise_customer_not_found(self):
        faker = FakerFactory.create()
        invalid_customer_id = faker.uuid4()  # pylint: disable=no-member
        error = 'Enterprise customer {} not found, or not active'.format(invalid_customer_id)
        with raises(CommandError) as excinfo:
            call_command('transmit_course_metadata', '--catalog_user', 'C-3PO', enterprise_customer=invalid_customer_id)
        assert str(excinfo.value) == error

    def test_user_not_set(self):
        # Python2 and Python3 have different error strings. So that's great.
        py2error = 'Error: argument --catalog_user is required'
        py3error = 'Error: the following arguments are required: --catalog_user'
        with raises(CommandError) as excinfo:
            call_command('transmit_course_metadata', enterprise_customer=self.enterprise_customer.uuid)
        assert str(excinfo.value) in (py2error, py3error)

    def test_override_user(self):
        error = 'A user with the username bob was not found.'
        with raises(CommandError) as excinfo:
            call_command('transmit_course_metadata', '--catalog_user', 'bob')
        assert str(excinfo.value) == error

    @mock.patch('integrated_channels.integrated_channel.management.commands.transmit_course_metadata.transmit_course_metadata')
    def test_working_user(self, mock_data_task):
        call_command('transmit_course_metadata', '--catalog_user', 'C-3PO')
        mock_data_task.delay.assert_called_once_with('C-3PO', 'SAP', 1)

    @responses.activate
    @mock.patch('enterprise.api_client.lms.JwtBuilder', mock.Mock())
    @mock.patch('integrated_channels.sap_success_factors.exporters.course_metadata.reverse')
    @mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.get_oauth_access_token')
    @mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.send_course_import')
    def test_transmit_courseware_task_with_error(
            self,
            send_course_import_mock,
            get_oauth_access_token_mock,
            track_selection_reverse_mock,
    ):
        """
        Verify the data transmission task for integrated channels with error.

        Test that the management command `transmit_course_metadata` transmits
        courses metadata related to other integrated channels even if an
        integrated channel fails to transmit due to some error.
        """
        get_oauth_access_token_mock.return_value = "token", datetime.utcnow()
        send_course_import_mock.return_value = 200, '{}'
        track_selection_reverse_mock.return_value = '/course_modes/choose/course-v1:edX+DemoX+Demo_Course/'

        # Mock first integrated channel with failure
        enterprise_uuid_for_failure = str(self.enterprise_customer.uuid)
        self.mock_ent_courses_api_with_error(enterprise_uuid=enterprise_uuid_for_failure)

        # Now create a new integrated channel with a new enterprise and mock
        # enterprise courses API to send failure response
        course_run_id_for_success = 'course-v1:edX+DemoX+Demo_Course_1'
        dummy_enterprise_customer = factories.EnterpriseCustomerFactory(
            catalog=1,
            name='Dummy Enterprise',
        )
        enterprise_uuid_for_success = str(dummy_enterprise_customer.uuid)
        factories.SAPSuccessFactorsEnterpriseCustomerConfigurationFactory(
            enterprise_customer=dummy_enterprise_customer,
            sapsf_base_url='http://enterprise.successfactors.com/',
            key='key',
            secret='secret',
            active=True,
        )
        self.mock_ent_courses_api_with_pagination(
            enterprise_uuid=enterprise_uuid_for_success,
            course_run_ids=[course_run_id_for_success]
        )

        expected_dump = (
            '{"ocnCourses": [{"content": [{"contentID": "'+course_run_id_for_success+'", '
            '"contentTitle": "edX Demonstration Course", "launchType": 3, "launchURL": '
            '"'+settings.LMS_ROOT_URL+'/enterprise/'+enterprise_uuid_for_success+'/'
            'course/'+course_run_id_for_success+'/enroll/", "mobileEnabled": '
            'false, "providerID": "EDX"}], "courseID": "'+course_run_id_for_success+'"'
            ', "description": [{"locale": "English", "value": "edX Demonstration Course"}], '
            '"price": [], "providerID": "EDX", "revisionNumber": 1, "schedule": '
            '[{"active": true, "endDate": 2147483647000, "startDate": 1360040400000}], '
            '"status": "ACTIVE", "thumbnailURI": "", "title": [{"locale": "English", '
            '"value": "edX Demonstration Course"}]}]}'
        )
        # Verify that first integrated channel logs failure but the second
        # integrated channel still successfully transmits courseware data.
        expected_messages = [
            'Processing courses for integrated channel using configuration: '
            '<SAPSuccessFactorsEnterpriseCustomerConfiguration for Enterprise Veridian Dynamics>',
            'Transmission of course metadata failed for user "C-3PO" and for integrated channel with '
            'code "SAP" and id "1".',
            'Processing courses for integrated channel using configuration: '
            '<SAPSuccessFactorsEnterpriseCustomerConfiguration for Enterprise Dummy Enterprise>',
            'Retrieving course list for enterprise {}'.format(dummy_enterprise_customer.name),
            'Processing course with ID {}'.format(course_run_id_for_success),
            'Sending course with plugin configuration <SAPSuccessFactorsEnterprise'
            'CustomerConfiguration for Enterprise Dummy Enterprise>',
            expected_dump,
        ]

        with LogCapture(level=logging.INFO) as log_capture:
            call_command('transmit_course_metadata', '--catalog_user', 'C-3PO')
            for index, message in enumerate(expected_messages):
                assert message in log_capture.records[index].getMessage()

    @responses.activate
    @mock.patch('enterprise.api_client.lms.JwtBuilder', mock.Mock())
    @mock.patch('integrated_channels.sap_success_factors.exporters.course_metadata.reverse')
    @mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.get_oauth_access_token')
    @mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.send_course_import')
    def test_transmit_courseware_task_success(
            self,
            send_course_import_mock,
            get_oauth_access_token_mock,
            track_selection_reverse_mock
    ):
        """
        Test the data transmission task.
        """
        get_oauth_access_token_mock.return_value = "token", datetime.utcnow()
        send_course_import_mock.return_value = 200, '{}'

        track_selection_reverse_mock.return_value = '/course_modes/choose/course-v1:edX+DemoX+Demo_Course/'
        uuid = str(self.enterprise_customer.uuid)
        course_run_ids = ['course-v1:edX+DemoX+Demo_Course_1', 'course-v1:edX+DemoX+Demo_Course_2']
        self.mock_ent_courses_api_with_pagination(
            enterprise_uuid=uuid,
            course_run_ids=course_run_ids[:1]
        )

        factories.EnterpriseCustomerCatalogFactory(enterprise_customer=self.enterprise_customer)
        enterprise_catalog_uuid = str(self.enterprise_customer.enterprise_customer_catalogs.first().uuid)
        self.mock_enterprise_customer_catalogs(
            uuid, enterprise_catalog_uuid, course_run_ids[1:]
        )

        expected_dump = (
            '{"ocnCourses": [{"content": [{"contentID": "'+course_run_ids[0]+'", '
            '"contentTitle": "edX Demonstration Course", "launchType": 3, "launchURL": '
            '"'+settings.LMS_ROOT_URL+'/enterprise/'+uuid+'/course/'+course_run_ids[0]+'/enroll/'
            '", "mobileEnabled": false, "providerID": "EDX"}], "courseID": "'+course_run_ids[0]+'"'
            ', "description": [{"locale": "English", "value": "edX Demonstration Course"}], '
            '"price": [], "providerID": "EDX", "revisionNumber": 1, "schedule": '
            '[{"active": true, "endDate": 2147483647000, "startDate": 1360040400000}], '
            '"status": "ACTIVE", "thumbnailURI": "", "title": [{"locale": "English", '
            '"value": "edX Demonstration Course"}]}, {"content": [{"contentID": '
            '"'+course_run_ids[1]+'", "contentTitle": "edX Demonstration Course", "launchType": 3, '
            '"launchURL": "'+settings.LMS_ROOT_URL+'/enterprise/'+uuid+'/course/'
            ''+course_run_ids[1]+'/enroll/", "mobileEnabled": false, "providerID": "EDX"}], '
            '"courseID": "'+course_run_ids[1]+'", "description": [{"locale": "English", '
            '"value": "edX Demonstration Course"}], "price": [], "providerID": "EDX", '
            '"revisionNumber": 1, "schedule": [{"active": true, "endDate": 2147483647000, '
            '"startDate": 1360040400000}], "status": "ACTIVE", "thumbnailURI": "", '
            '"title": [{"locale": "English", "value": "edX Demonstration Course"}]}]}'
        )
        expected_messages = [
            'Processing courses for integrated channel using configuration: '
            '<SAPSuccessFactorsEnterpriseCustomerConfiguration for Enterprise Veridian Dynamics>',
            'Retrieving course list for enterprise {}'.format(self.enterprise_customer.name),
            'Processing course with ID {}'.format(course_run_ids[0]),
            'Sending course with plugin configuration <SAPSuccessFactorsEnterprise'
            'CustomerConfiguration for Enterprise Veridian Dynamics>',
            'Processing course with ID {}'.format(course_run_ids[1]),
            'Sending course with plugin configuration <SAPSuccessFactorsEnterprise'
            'CustomerConfiguration for Enterprise Veridian Dynamics>',
            expected_dump,
        ]

        with LogCapture(level=logging.INFO) as log_capture:
            call_command('transmit_course_metadata', '--catalog_user', 'C-3PO')
            for index, message in enumerate(expected_messages):
                assert message in log_capture.records[index].getMessage()

    @responses.activate
    def test_transmit_courseware_task_no_channel(self):
        """
        Test the data transmission task without any integrated channel.
        """
        user = factories.UserFactory(username='john_doe')
        factories.EnterpriseCustomerFactory(
            catalog=1,
            name='Veridian Dynamics',
        )

        # Remove all integrated channels
        SAPSuccessFactorsEnterpriseCustomerConfiguration.objects.all().delete()
        with LogCapture(level=logging.INFO) as log_capture:
            call_command('transmit_course_metadata', '--catalog_user', user.username)

            # Because there are no IntegratedChannels, the process will end early.
            assert not log_capture.records

    @responses.activate
    def test_transmit_courseware_task_no_catalog(self):
        """
        Test the data transmission task with enterprise customer which have no
        course catalog.
        """
        uuid = str(self.enterprise_customer.uuid)
        course_run_ids = ['course-v1:edX+DemoX+Demo_Course']
        self.mock_ent_courses_api_with_pagination(
            enterprise_uuid=uuid,
            course_run_ids=course_run_ids
        )
        integrated_channel_enterprise = self.sapsf.enterprise_customer
        integrated_channel_enterprise.catalog = None
        integrated_channel_enterprise.save()

        with LogCapture(level=logging.INFO) as log_capture:
            call_command('transmit_course_metadata', '--catalog_user', self.user.username)

            # Because there are no EnterpriseCustomers with a catalog, the process will end early.
            assert not log_capture.records


# Constants used in the parameters for the transmit_learner_data integration tests below.
NOW = datetime(2017, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
NOW_TIMESTAMP = 1483326245000
DAY_DELTA = timedelta(days=1)
PAST = NOW - DAY_DELTA
PAST_TIMESTAMP = NOW_TIMESTAMP - 24*60*60*1000
FUTURE = NOW + DAY_DELTA

COURSE_ID = 'course-v1:edX+DemoX+DemoCourse'

# Mock passing certificate data
MOCK_PASSING_CERTIFICATE = dict(
    grade='A-',
    created_date=NOW.strftime(lms_api.LMS_API_DATETIME_FORMAT),
    status='downloadable',
    is_passing=True,
)

# Mock failing certificate data
MOCK_FAILING_CERTIFICATE = dict(
    grade='D',
    created_date=NOW.strftime(lms_api.LMS_API_DATETIME_FORMAT),
    status='downloadable',
    is_passing=False,
)

# Expected learner completion data from the mock passing certificate
CERTIFICATE_PASSING_COMPLETION = dict(
    completed='true',
    timestamp=NOW_TIMESTAMP,
    grade=LearnerExporter.GRADE_PASSING,
)

# Expected learner completion data from the mock failing certificate
CERTIFICATE_FAILING_COMPLETION = dict(
    completed='false',
    timestamp=NOW_TIMESTAMP,
    grade=LearnerExporter.GRADE_FAILING,
)


@mark.django_db
class TestTransmitLearnerData(unittest.TestCase):
    """
    Test the transmit_learner_data management command.
    """

    def setUp(self):
        self.api_user = factories.UserFactory(username='staff_user', id=1)
        self.user = factories.UserFactory(id=2)
        self.course_id = COURSE_ID
        self.enterprise_customer = factories.EnterpriseCustomerFactory()
        self.identity_provider = FakerFactory.create().slug()  # pylint: disable=no-member
        factories.EnterpriseCustomerIdentityProviderFactory(
            provider_id=self.identity_provider,
            enterprise_customer=self.enterprise_customer
        )
        self.enterprise_customer_user = factories.EnterpriseCustomerUserFactory(
            user_id=self.user.id,
            enterprise_customer=self.enterprise_customer,
        )
        self.enrollment = factories.EnterpriseCourseEnrollmentFactory(
            enterprise_customer_user=self.enterprise_customer_user,
            course_id=self.course_id,
        )
        self.consent = factories.DataSharingConsentFactory(
            username=self.user.username,
            course_id=self.course_id,
            enterprise_customer=self.enterprise_customer
        )
        self.sapsf = factories.SAPSuccessFactorsEnterpriseCustomerConfigurationFactory(
            enterprise_customer=self.enterprise_customer,
            sapsf_base_url='http://enterprise.successfactors.com/',
            key='key',
            secret='secret',
        )
        super(TestTransmitLearnerData, self).setUp()

    def test_api_user_required(self):
        error = 'Error: argument --api_user is required'
        with raises(CommandError, message=error):
            call_command('transmit_learner_data')

    def test_api_user_must_exist(self):
        error = 'A user with the username bob was not found.'
        with raises(CommandError, message=error):
            call_command('transmit_learner_data', '--api_user', 'bob')

    def test_enterprise_customer_not_found(self):
        faker = FakerFactory.create()
        invalid_customer_id = faker.uuid4()  # pylint: disable=no-member
        error = 'Enterprise customer {} not found, or not active'.format(invalid_customer_id)
        with raises(CommandError, message=error):
            call_command('transmit_learner_data',
                         '--api_user', self.api_user.username,
                         enterprise_customer=invalid_customer_id)

    def test_invalid_integrated_channel(self):
        channel_code = 'abc'
        error = 'Invalid integrated channel: {}'.format(channel_code)
        with raises(CommandError, message=error):
            call_command('transmit_learner_data',
                         '--api_user', self.api_user.username,
                         enterprise_customer=self.enterprise_customer.uuid,
                         channel=channel_code)


# Helper methods used for the transmit_learner_data integration tests below.
@contextmanager
def transmit_learner_data_context(command_kwargs, certificate, self_paced, end_date, passed):
    """
    Sets up all the data and context wrappers required to run the transmit_learner_data management command.
    """
    # Borrow the test data from TestTransmitLearnerData
    testcase = TestTransmitLearnerData(methodName='setUp')
    testcase.setUp()

    # Activate the integrated channel
    testcase.sapsf.active = True
    testcase.sapsf.save()

    # Stub out the APIs called by the transmit_learner_data command
    stub_transmit_learner_data_apis(testcase, certificate, self_paced, end_date, passed)

    # Prepare the management command arguments
    command_args = ('--api_user', testcase.api_user.username)
    if 'enterprise_customer' in command_kwargs:
        command_kwargs['enterprise_customer'] = testcase.enterprise_customer.uuid

    # Mock the JWT authentication for LMS API calls
    with mock.patch('enterprise.api_client.lms.JwtBuilder', mock.Mock()):

        # Yield to the management command test, freezing time to the known NOW.
        with freeze_time(NOW):
            yield (command_args, command_kwargs)

    # Clean up the testcase data
    testcase.tearDown()


# Helper methods for the transmit_learner_data integration test below
def stub_transmit_learner_data_apis(testcase, certificate, self_paced, end_date, passed):
    """
    Stub out all of the API calls made during transmit_learner_data
    """

    # Third Party API remote_id response
    responses.add(
        responses.GET,
        urljoin(lms_api.ThirdPartyAuthApiClient.API_BASE_URL,
                "providers/{provider}/users?username={user}".format(provider=testcase.identity_provider,
                                                                    user=testcase.user.username)),
        match_querystring=True,
        json=dict(results=[
            dict(username=testcase.user.username, remote_id='remote-user-id'),
        ]),
    )

    # Course API course_details response
    responses.add(
        responses.GET,
        urljoin(lms_api.CourseApiClient.API_BASE_URL,
                "courses/{course}/".format(course=testcase.course_id)),
        json=dict(
            course_id=COURSE_ID,
            pacing="self" if self_paced else "instructor",
            end=end_date.isoformat() if end_date else None,
        ),
    )

    # Grades API course_grades response
    responses.add(
        responses.GET,
        urljoin(lms_api.GradesApiClient.API_BASE_URL,
                "course_grade/{course}/users/?username={user}".format(course=testcase.course_id,
                                                                      user=testcase.user.username)),
        match_querystring=True,
        json=[dict(
            username=testcase.user.username,
            course_id=COURSE_ID,
            passed=passed,
        )],
    )

    # Enrollment API enrollment response
    responses.add(
        responses.GET,
        urljoin(lms_api.EnrollmentApiClient.API_BASE_URL,
                "enrollment/{username},{course_id}".format(username=testcase.user.username,
                                                           course_id=testcase.course_id)),
        match_querystring=True,
        json=dict(
            mode="verified",
        ),
    )

    # Certificates API course_grades response
    if certificate:
        responses.add(
            responses.GET,
            urljoin(lms_api.CertificatesApiClient.API_BASE_URL,
                    "certificates/{user}/courses/{course}/".format(course=testcase.course_id,
                                                                   user=testcase.user.username)),
            json=certificate,
        )
    else:
        responses.add(
            responses.GET,
            urljoin(lms_api.CertificatesApiClient.API_BASE_URL,
                    "certificates/{user}/courses/{course}/".format(course=testcase.course_id,
                                                                   user=testcase.user.username)),
            status=404,
        )


def get_expected_output(**expected_completion):
    """
    Returns the expected JSON record logged by the transmit_learner_data command.
    """
    output_template = (
        '{{'
        '"completedTimestamp": {timestamp}, '
        '"courseCompleted": "{completed}", '
        '"courseID": "{course_id}", '
        '"grade": "{grade}", '
        '"providerID": "{provider_id}", '
        '"userID": "{user_id}"'
        '}}'
    )
    return output_template.format(
        user_id='remote-user-id',
        course_id=COURSE_ID,
        provider_id="EDX",
        **expected_completion
    )


@responses.activate
@mark.django_db
@mark.parametrize('command_kwargs,certificate,self_paced,end_date,passed,expected_completion', [
    # Certificate marks course completion
    (dict(), MOCK_PASSING_CERTIFICATE, False, None, False, CERTIFICATE_PASSING_COMPLETION),
    (dict(), MOCK_FAILING_CERTIFICATE, False, None, False, CERTIFICATE_FAILING_COMPLETION),
    # channel code is case-insensitive
    (dict(channel='sap'), MOCK_PASSING_CERTIFICATE, False, None, False, CERTIFICATE_PASSING_COMPLETION),
    (dict(channel='SAP'), MOCK_PASSING_CERTIFICATE, False, None, False, CERTIFICATE_PASSING_COMPLETION),
    (dict(channel='sap'), MOCK_FAILING_CERTIFICATE, False, None, False, CERTIFICATE_FAILING_COMPLETION),
    (dict(channel='SAP'), MOCK_FAILING_CERTIFICATE, False, None, False, CERTIFICATE_FAILING_COMPLETION),
    # enterprise_customer UUID gets filled in below
    (dict(enterprise_customer=None), MOCK_PASSING_CERTIFICATE, False, None, False, CERTIFICATE_PASSING_COMPLETION),
    (dict(enterprise_customer=None, channel='sap'), MOCK_PASSING_CERTIFICATE, False, None, False,
     CERTIFICATE_PASSING_COMPLETION),
    (dict(enterprise_customer=None), MOCK_FAILING_CERTIFICATE, False, None, False, CERTIFICATE_FAILING_COMPLETION),
    (dict(enterprise_customer=None, channel='sap'), MOCK_FAILING_CERTIFICATE, False, None, False,
     CERTIFICATE_FAILING_COMPLETION),

    # Instructor-paced course with no certificates issued yet results in incomplete course data
    (dict(), None, False, None, False, dict(completed='false', timestamp='null', grade='In Progress')),

    # Self-paced course with no end date send grade=Pass, or grade=In Progress, depending on current grade.
    (dict(), None, True, None, False, dict(completed='false', timestamp='null', grade='In Progress')),
    (dict(), None, True, None, True, dict(completed='true', timestamp=NOW_TIMESTAMP, grade='Pass')),

    # Self-paced course with future end date sends grade=Pass, or grade=In Progress, depending on current grade.
    (dict(), None, True, FUTURE, False, dict(completed='false', timestamp='null', grade='In Progress')),
    (dict(), None, True, FUTURE, True, dict(completed='true', timestamp=NOW_TIMESTAMP, grade='Pass')),

    # Self-paced course with past end date sends grade=Pass, or grade=Fail, depending on current grade.
    (dict(), None, True, PAST, False, dict(completed='false', timestamp=PAST_TIMESTAMP, grade='Fail')),
    (dict(), None, True, PAST, True, dict(completed='true', timestamp=PAST_TIMESTAMP, grade='Pass')),
])
@mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.get_oauth_access_token')
@mock.patch('integrated_channels.sap_success_factors.client.SAPSuccessFactorsAPIClient.send_completion_status')
def test_transmit_learner_data(
        send_completion_status,
        get_oauth_access_token_mock,
        caplog,
        command_kwargs,
        certificate,
        self_paced,
        end_date,
        passed,
        expected_completion
):
    """
    Test the log output from a successful run of the transmit_learner_data management command,
    using all the ways we can invoke it.
    """
    caplog.set_level(logging.INFO)

    # Mock the Open edX environment classes
    with transmit_learner_data_context(command_kwargs, certificate, self_paced, end_date, passed) as (args, kwargs):
        get_oauth_access_token_mock.return_value = "token", datetime.utcnow()
        send_completion_status.return_value = 200, '{}'
        # Call the management command
        call_command('transmit_learner_data', *args, **kwargs)

    # Ensure the correct learner_data record was logged
    assert len(caplog.records) == 1

    expected_output = get_expected_output(**expected_completion)
    assert expected_output in caplog.records[0].message
