# -*- coding: utf-8 -*-
"""
Generic learner data transmitter for integrated channels.
"""

from __future__ import absolute_import, unicode_literals

from integrated_channels.integrated_channel.client import IntegratedChannelApiClient
from integrated_channels.integrated_channel.transmitters import Transmitter


class LearnerTransmitter(Transmitter):
    """
    A generic learner data transmitter.

    It may be subclassed by specific integrated channel learner data transmitters for
    each integrated channel's particular learner data transmission requirements and expectations.

    TODO: Find any generic course metadata transmission logic across different integrated channels and put it here.
    """

    def __init__(self, enterprise_configuration, client=IntegratedChannelApiClient):
        """

        """
        super(LearnerTransmitter, self).__init__(
            enterprise_configuration=enterprise_configuration,
            client=client
        )

    def transmit(self, payload):
        """

        :param payload:
        :return:
        """
        pass
