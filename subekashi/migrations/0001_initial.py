# Generated by Django 4.0 on 2024-02-17 00:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(default='', max_length=100)),
                ('view', models.IntegerField(default=0)),
                ('click', models.IntegerField(default=0)),
                ('dup', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('still', '未審査'), ('pass', '公開中'), ('fail', '未通過')], default='still', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Ai',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lyrics', models.CharField(default='', max_length=100)),
                ('score', models.IntegerField(default=0)),
                ('genetype', models.CharField(default='', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Singleton',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(default='', max_length=100)),
                ('value', models.CharField(default='', max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='Song',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='', max_length=500)),
                ('channel', models.CharField(default='', max_length=500)),
                ('url', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('lyrics', models.CharField(blank=True, default='', max_length=10000, null=True)),
                ('imitate', models.CharField(blank=True, default='', max_length=1000, null=True)),
                ('imitated', models.CharField(blank=True, default='', max_length=1000, null=True)),
                ('posttime', models.DateTimeField(blank=True, null=True)),
                ('uploaddata', models.DateField(blank=True, null=True)),
                ('isoriginal', models.BooleanField(default=False)),
                ('isjoke', models.BooleanField(default=False)),
                ('isdeleted', models.BooleanField(default=False)),
                ('isarchived', models.BooleanField(default=True)),
                ('isdraft', models.BooleanField(default=False)),
                ('isinst', models.BooleanField(default=False)),
                ('issubeana', models.BooleanField(default=True)),
                ('ip', models.CharField(default='', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('before', models.CharField(default='', max_length=10000)),
                ('after', models.CharField(default='', max_length=10000)),
                ('editedtime', models.DateTimeField(blank=True, null=True)),
                ('ip', models.CharField(default='', max_length=100)),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='subekashi.song')),
            ],
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=100)),
                ('ismain', models.BooleanField(default=True)),
                ('isnickname', models.BooleanField(default=True)),
                ('subs', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='main', to='subekashi.channel')),
            ],
        ),
    ]
