# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sap_success_factors', '0008_historicalsapsuccessfactorsenterprisecustomerconfiguration_history_change_reason'),
    ]

    database_operations = [
        # This table literally just moves apps, so just rename it to prefix it with `integrated_channel_`.
        migrations.AlterModelTable('CatalogTransmissionAudit', 'integrated_channel_catalogtransmissionaudit'),
    ]

    state_operations = [
        # See `integrated_channel.migrations.0003` for the migration that adds this model to the other app's state.
        migrations.DeleteModel(name='CatalogTransmissionAudit')
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations
        ),
        migrations.RenameModel('LearnerDataTransmissionAudit', 'SapSuccessFactorsLearnerDataTransmissionAudit')
    ]
