# Generated by Django 4.0 on 2022-12-07 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0004_rename_points_ai_score'),
    ]

    operations = [
        migrations.AlterField(
            model_name='song',
            name='imitated',
            field=models.CharField(blank=True, default='', max_length=1000, null=True),
        ),
    ]