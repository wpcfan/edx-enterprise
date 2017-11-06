# -*- coding: utf-8 -*-
"""
Factoryboy factories.
"""

from __future__ import absolute_import, unicode_literals

from uuid import UUID

import factory
from consent.models import DataSharingConsent
from faker import Factory as FakerFactory
from integrated_channels.integrated_channel.models import (
    CatalogTransmissionAudit,
    EnterpriseCustomerPluginConfiguration,
    LearnerDataTransmissionAudit,
)
from integrated_channels.sap_success_factors.models import (
    SAPSuccessFactorsEnterpriseCustomerConfiguration,
    SAPSuccessFactorsGlobalConfiguration,
    SapSuccessFactorsLearnerDataTransmissionAudit,
)

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils import timezone

from enterprise.models import (
    EnterpriseCourseEnrollment,
    EnterpriseCustomer,
    EnterpriseCustomerCatalog,
    EnterpriseCustomerEntitlement,
    EnterpriseCustomerIdentityProvider,
    EnterpriseCustomerReportingConfiguration,
    EnterpriseCustomerUser,
    PendingEnrollment,
    PendingEnterpriseCustomerUser,
)

FAKER = FakerFactory.create()


# pylint: disable=no-member
# pylint: disable=invalid-name
class SiteFactory(factory.django.DjangoModelFactory):
    """
    Factory class for Site model.
    """

    class Meta(object):
        """
        Meta for ``SiteFactory``.
        """

        model = Site
        django_get_or_create = ("domain",)

    domain = factory.LazyAttribute(lambda x: FAKER.domain_name())
    name = factory.LazyAttribute(lambda x: FAKER.company())


class EnterpriseCustomerFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCustomer factory.

    Creates an instance of EnterpriseCustomer with minimal boilerplate - uses this class' attributes as default
    parameters for EnterpriseCustomer constructor.
    """

    class Meta(object):
        """
        Meta for EnterpriseCustomerFactory.
        """

        model = EnterpriseCustomer

    uuid = factory.LazyAttribute(lambda x: UUID(FAKER.uuid4()))
    name = factory.LazyAttribute(lambda x: FAKER.company())
    active = True
    site = factory.SubFactory(SiteFactory)
    catalog = factory.LazyAttribute(lambda x: FAKER.random_int(min=0, max=1000000))
    enable_data_sharing_consent = True
    enforce_data_sharing_consent = EnterpriseCustomer.AT_ENROLLMENT


class EnterpriseCustomerUserFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCustomer factory.

    Creates an instance of EnterpriseCustomerUser with minimal boilerplate - uses this class' attributes as default
    parameters for EnterpriseCustomerUser constructor.
    """

    class Meta(object):
        """
        Meta for EnterpriseCustomerFactory.
        """

        model = EnterpriseCustomerUser

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    user_id = factory.LazyAttribute(lambda x: FAKER.pyint())


class PendingEnterpriseCustomerUserFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCustomer factory.

    Creates an instance of EnterpriseCustomerUser with minimal boilerplate - uses this class' attributes as default
    parameters for EnterpriseCustomerUser constructor.
    """

    class Meta(object):
        """
        Meta for EnterpriseCustomerFactory.
        """

        model = PendingEnterpriseCustomerUser

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    user_email = factory.LazyAttribute(lambda x: FAKER.email())


class UserFactory(factory.DjangoModelFactory):
    """
    User factory.

    Creates an instance of User with minimal boilerplate - uses this class' attributes as default
    parameters for User constructor.
    """

    class Meta(object):
        """
        Meta for UserFactory.
        """

        model = User

    id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    email = factory.LazyAttribute(lambda x: FAKER.email())
    username = factory.LazyAttribute(lambda x: FAKER.user_name())
    first_name = factory.LazyAttribute(lambda x: FAKER.first_name())
    last_name = factory.LazyAttribute(lambda x: FAKER.last_name())
    is_staff = False
    is_active = False
    date_joined = factory.LazyAttribute(lambda x: FAKER.date_time_this_year(tzinfo=timezone.utc))


class EnterpriseCustomerIdentityProviderFactory(factory.django.DjangoModelFactory):
    """
    Factory class for EnterpriseCustomerIdentityProvider model.
    """

    class Meta(object):
        """
        Meta for ``EnterpriseCustomerIdentityProviderFactory``.
        """

        model = EnterpriseCustomerIdentityProvider
        django_get_or_create = ("provider_id",)

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    provider_id = factory.LazyAttribute(lambda x: FAKER.slug())


class PendingEnrollmentFactory(factory.django.DjangoModelFactory):
    """
    PendingEnrollment factory.

    Create an instance of PendingEnrollment with minimal boilerplate
    """

    class Meta(object):
        """
        Meta for ``PendingEnrollmentFactory``.
        """

        model = PendingEnrollment

    course_id = factory.LazyAttribute(lambda x: FAKER.slug())
    course_mode = 'audit'
    user = factory.SubFactory(PendingEnterpriseCustomerUserFactory)


class EnterpriseCustomerEntitlementFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCustomerEntitlement factory.

    Creates an instance of EnterpriseCustomerEntitlement with minimal boilerplate - uses this class' attributes as
    default parameters for EnterpriseCustomerBrandingFactory constructor.
    """

    class Meta(object):
        """
        Meta for EnterpriseCustomerEntitlementFactory.
        """

        model = EnterpriseCustomerEntitlement

    id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    entitlement_id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)


class EnterpriseCourseEnrollmentFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCourseEnrollment factory.

    Creates an instance of EnterpriseCourseEnrollment with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for EnterpriseCourseEnrollmentFactory.
        """

        model = EnterpriseCourseEnrollment

    id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    course_id = factory.LazyAttribute(lambda x: FAKER.slug())
    enterprise_customer_user = factory.SubFactory(EnterpriseCustomerUserFactory)


class EnterpriseCustomerCatalogFactory(factory.django.DjangoModelFactory):
    """
    EnterpriseCustomerCatalog factory.

    Creates an instance of EnterpriseCustomerCatalog with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for EnterpriseCustomerCatalog.
        """

        model = EnterpriseCustomerCatalog

    uuid = factory.LazyAttribute(lambda x: UUID(FAKER.uuid4()))
    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    content_filter = {}


class DataSharingConsentFactory(factory.django.DjangoModelFactory):
    """
    ``DataSharingConsent`` factory.

    Creates an instance of ``DataSharingConsent`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``DataSharingConsentFactory``.
        """

        model = DataSharingConsent

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    username = factory.LazyAttribute(lambda x: FAKER.user_name())
    course_id = factory.LazyAttribute(lambda x: FAKER.slug())
    granted = True


class EnterpriseCustomerReportingConfigFactory(factory.django.DjangoModelFactory):
    """
    ``EnterpriseCustomerReportingConfiguration`` factory.

    Creates an instance of EnterpriseCustomerReportingConfiguration with minimal boilerplate
    uses this class' attributes as default parameters for EnterpriseCustomerReportingConfiguration constructor.
    """

    class Meta(object):
        """
        Meta for ``EnterpriseCustomerReportingConfigFactory``.
        """

        model = EnterpriseCustomerReportingConfiguration

    id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    active = True
    email = factory.LazyAttribute(lambda x: FAKER.email())
    day_of_month = 1
    hour_of_day = 1
    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)


class EnterpriseCustomerPluginConfigurationFactory(factory.django.DjangoModelFactory):
    """
    ``EnterpriseCustomerPluginConfiguration`` factory.

    Creates an instance of ``EnterpriseCustomerPluginConfiguration`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``EnterpriseCustomerPluginConfigurationFactory``.
        """

        model = EnterpriseCustomerPluginConfiguration

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    active = True


class LearnerDataTransmissionAuditFactory(factory.django.DjangoModelFactory):
    """
    ``LearnerDataTransmissionAudit`` factory.

    Creates an instance of ``LearnerDataTransmissionAudit`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``LearnerDataTransmissionAuditFactory``.
        """

        model = LearnerDataTransmissionAudit

    enterprise_course_enrollment_id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    course_id = factory.LazyAttribute(lambda x: FAKER.slug())
    course_completed = True
    completed_timestamp = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    instructor_name = factory.LazyAttribute(lambda x: FAKER.name())
    grade = factory.LazyAttribute(lambda x: FAKER.bothify('?', letters='ABCDF') + FAKER.bothify('?', letters='+-'))
    status = factory.LazyAttribute(lambda x: FAKER.word())


class CatalogTransmissionAuditFactory(factory.django.DjangoModelFactory):
    """
    ``CatalogTransmissionAudit`` factory.

    Creates an instance of ``CatalogTransmissionAudit`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``CatalogTransmissionAuditFactory``.
        """

        model = CatalogTransmissionAudit

    enterprise_customer_uuid = factory.LazyAttribute(lambda x: UUID(FAKER.uuid4()))
    total_courses = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    status = factory.LazyAttribute(lambda x: FAKER.word())


class SAPSuccessFactorsGlobalConfigurationFactory(factory.django.DjangoModelFactory):
    """
    ``SAPSuccessFactorsGlobalConfiguration`` factory.

    Creates an instance of ``SAPSuccessFactorsGlobalConfiguration`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``SAPSuccessFactorsGlobalConfigurationFactory``.
        """

        model = SAPSuccessFactorsGlobalConfiguration

    completion_status_api_path = factory.LazyAttribute(lambda x: FAKER.file_path())
    course_api_path = factory.LazyAttribute(lambda x: FAKER.file_path())
    oauth_api_path = factory.LazyAttribute(lambda x: FAKER.file_path())


class SAPSuccessFactorsEnterpriseCustomerConfigurationFactory(factory.django.DjangoModelFactory):
    """
    ``SAPSuccessFactorsEnterpriseCustomerConfiguration`` factory.

    Creates an instance of ``SAPSuccessFactorsEnterpriseCustomerConfiguration`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``SAPSuccessFactorsEnterpriseCustomerConfigurationFactory``.
        """

        model = SAPSuccessFactorsEnterpriseCustomerConfiguration

    enterprise_customer = factory.SubFactory(EnterpriseCustomerFactory)
    active = True
    sapsf_base_url = factory.LazyAttribute(lambda x: FAKER.url())
    sapsf_company_id = factory.LazyAttribute(lambda x: FAKER.company())
    sapsf_user_id = factory.LazyAttribute(lambda x: FAKER.pyint())
    user_type = SAPSuccessFactorsEnterpriseCustomerConfiguration.USER_TYPE_USER


class SapSuccessFactorsLearnerDataTransmissionAuditFactory(factory.django.DjangoModelFactory):
    """
    ``SapSuccessFactorsLearnerDataTransmissionAudit`` factory.

    Creates an instance of ``SapSuccessFactorsLearnerDataTransmissionAudit`` with minimal boilerplate.
    """

    class Meta(object):
        """
        Meta for ``SapSuccessFactorsLearnerDataTransmissionAuditFactory``.
        """

        model = SapSuccessFactorsLearnerDataTransmissionAudit

    sapsf_user_id = factory.LazyAttribute(lambda x: FAKER.pyint())
    enterprise_course_enrollment_id = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    course_id = factory.LazyAttribute(lambda x: FAKER.slug())
    course_completed = True
    completed_timestamp = factory.LazyAttribute(lambda x: FAKER.random_int(min=1))
    instructor_name = factory.LazyAttribute(lambda x: FAKER.name())
    grade = factory.LazyAttribute(lambda x: FAKER.bothify('?', letters='ABCDF') + FAKER.bothify('?', letters='+-'))
    status = factory.LazyAttribute(lambda x: FAKER.word())
