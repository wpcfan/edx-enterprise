"""
Celery tasks for integrated channel management commands.
"""

from __future__ import absolute_import, unicode_literals

from celery import task
from celery.utils.log import get_task_logger
from integrated_channels.integrated_channel.management.commands import INTEGRATED_CHANNEL_CHOICES

from django.contrib.auth.models import User

LOGGER = get_task_logger(__name__)


@task
def transmit_course_metadata(username, channel_code, channel_pk):
    """
    Task to send course metadata to each linked integrated channel.

    Arguments:
        username (str): The username of the User to be used for making API requests for course metadata.
        channel_code (str): Capitalized identifier for the integrated channel
        channel_pk (str): Primary key for identifying integrated channel

    """
    api_user = User.objects.get(username=username)
    integrated_channel = INTEGRATED_CHANNEL_CHOICES[channel_code].objects.get(pk=channel_pk)
    LOGGER.info('Processing courses for integrated channel using configuration: %s', integrated_channel)
    try:
        integrated_channel.transmit_course_data(api_user)
    except Exception:  # pylint: disable=broad-except
        exception_message = (
            'Transmission of course metadata failed for user "{username}" and for integrated '
            'channel with code "{channel_code}" and id "{channel_pk}".'.format(
                username=username,
                channel_code=channel_code,
                channel_pk=channel_pk,
            )
        )
        LOGGER.exception(exception_message)


@task
def transmit_learner_data(username, channel_code, channel_pk):
    """
    Task to send learner data to each linked integrated channel.

    Arguments:
        username (str): The username of the User to be used for making API requests for learner data.
        channel_code (str): Capitalized identifier for the integrated channel
        channel_pk (str): Primary key for identifying integrated channel

    """
    api_user = User.objects.get(username=username)
    integrated_channel = INTEGRATED_CHANNEL_CHOICES[channel_code].objects.get(pk=channel_pk)
    LOGGER.info('Processing learners for integrated channel using configuration: %s', integrated_channel)
    try:
        integrated_channel.transmit_learner_data(api_user)
    except Exception:  # pylint: disable=broad-except
        exception_message = (
            'Transmission of learner data failed for user "{username}" and for integrated '
            'channel with code "{channel_code}" and id "{channel_pk}".'.format(
                username=username,
                channel_code=channel_code,
                channel_pk=channel_pk,
            )
        )
        LOGGER.exception(exception_message)
