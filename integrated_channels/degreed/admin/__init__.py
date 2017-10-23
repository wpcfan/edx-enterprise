# -*- coding: utf-8 -*-
"""
Django admin integration for configuring degreed app to communicate with Degreed systems.
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from config_models.admin import ConfigurationModelAdmin
from requests import RequestException

from integrated_channels.degreed.models import (
    DegreedEnterpriseCustomerConfiguration, DegreedGlobalConfiguration
)
from integrated_channels.degreed.client import DegreedAPIClient


@admin.register(DegreedGlobalConfiguration)
class DegreedGlobalConfigurationAdmin(ConfigurationModelAdmin):
    """
    Django admin model for DegreedGlobalConfiguration.
    """
    list_display = (
        "completion_status_api_path",
        "course_api_path",
        "oauth_api_path",
        "provider_id",
    )

    class Meta(object):
        model = DegreedGlobalConfiguration


@admin.register(DegreedEnterpriseCustomerConfiguration)
class DegreedEnterpriseCustomerConfigurationAdmin(admin.ModelAdmin):
    """
    Django admin model for DegreedEnterpriseCustomerConfiguration.
    """

    list_display = (
        "enterprise_customer_name",
        "active",
        "degreed_base_url",
        "key",
        "secret",
        "degreed_company_id",
        "degreed_user_id",
        "has_access_token",
    )

    readonly_fields = (
        "enterprise_customer_name",
        "has_access_token",
    )

    list_filter = ("active",)
    search_fields = ("enterprise_customer_name",)

    class Meta(object):
        model = DegreedEnterpriseCustomerConfiguration

    def enterprise_customer_name(self, obj):
        """
        Returns: the name for the attached EnterpriseCustomer.

        Args:
            obj: The instance of DegreedEnterpriseCustomerConfiguration
                being rendered with this admin form.
        """
        return obj.enterprise_customer.name

    def has_access_token(self, obj):
        """
        Confirms the presence and validity of the access token for the Degreed client instance

        Returns: a bool value indicating the presence of the access token

        Args:
            obj: The instance of DegreedEnterpriseCustomerConfiguration
                being rendered with this admin form.
        """
        try:
            access_token, expires_at = DegreedAPIClient.get_oauth_access_token(
                obj.degreed_base_url,
                obj.key,
                obj.secret,
                obj.degreed_company_id,
                obj.degreed_user_id,
                obj.user_type
            )
        except (RequestException, ValueError):
            return False
        return bool(access_token and expires_at)

    has_access_token.boolean = True
