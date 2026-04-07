from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0034_remove_song_imitate_remove_song_imitated'),
    ]

    operations = [
        migrations.RenameField(model_name='song', old_name='isoriginal', new_name='is_original'),
        migrations.RenameField(model_name='song', old_name='isjoke', new_name='is_joke'),
        migrations.RenameField(model_name='song', old_name='isdeleted', new_name='is_deleted'),
        migrations.RenameField(model_name='song', old_name='isdraft', new_name='is_draft'),
        migrations.RenameField(model_name='song', old_name='isinst', new_name='is_inst'),
        migrations.RenameField(model_name='song', old_name='issubeana', new_name='is_subeana'),
        migrations.RenameField(model_name='song', old_name='isspecial', new_name='is_special'),
        migrations.RenameField(model_name='song', old_name='islock', new_name='is_lock'),
        migrations.RenameField(model_name='song', old_name='islimited', new_name='is_limited'),
    ]
