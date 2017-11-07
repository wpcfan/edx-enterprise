# -*- coding: utf-8 -*-
"""
Class for transmitting course metadata to SuccessFactors.
"""

from __future__ import absolute_import, unicode_literals

from integrated_channels.integrated_channel.transmitters.course_metadata import CourseTransmitter
from integrated_channels.sap_success_factors.client import SAPSuccessFactorsAPIClient


class SapSuccessFactorsCourseTransmitter(CourseTransmitter):
    """
    This transmitter transmits a course metadata export to SAPSF.
    """

    def __init__(self, enterprise_configuration, client=SAPSuccessFactorsAPIClient):
        """
        Ensure by default that the client used for SAPSF Course Metadata transmission is ``SAPSuccessFactorsAPIClient``.
        """
        super(SapSuccessFactorsCourseTransmitter, self).__init__(
            enterprise_configuration=enterprise_configuration,
            client=client
        )
