"""
Celery tasks for integrated channel management commands.
"""

from __future__ import absolute_import, unicode_literals

from celery import task
from celery.utils.log import get_task_logger
from integrated_channels.integrated_channel.management.commands import INTEGRATED_CHANNEL_CHOICES

from django.contrib.auth.models import User

LOGGER = get_task_logger(__name__)


@task(track_started=True)
def transmit_course_metadata(username, channel_code, channel_pk):
    """
    Task to send course data to each linked integrated channel

    Arguments:
        channel_code (str): Capitalized identifier for the integrated channel
        channel_pk (str): Primary key for identifying integrated channel

    """
    user = User.objects.get(username=username)
    channel = INTEGRATED_CHANNEL_CHOICES[channel_code].objects.get(pk=channel_pk)

    LOGGER.info('Processing courses for integrated channel using configuration: %s', channel)

    try:
        channel.transmit_course_data(user)
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


@task(track_started=True)
def transmit_learner_data(username, channel_code, channel_pk):
    """
    Allows each enterprise customer's integrated channel to collect and transmit data within its own celery task.
    """
    api_user = User.objects.get(username=username)
    integrated_channel = INTEGRATED_CHANNEL_CHOICES[channel_code].objects.get(pk=channel_pk)
    integrated_channel.transmit_learner_data(api_user)
