# Generated by Django 5.2.4 on 2025-07-21 14:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mr_tracker', '0006_category_assigned_support_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='merchanttask',
            name='task_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='merchant_tasks', to='mr_tracker.tasktemplate'),
        ),
    ]
