from django.db import migrations

# 動詞・形容詞・名詞は実際のトークナイズ結果として katsuyou が常に非空になるため、
# katsuyou="" のまま残っている行は、katsuyou 導入前の word.json を取り込んだ
# 旧データ（新方式では二度と一致しない）とみなせる。
# 副詞・連体詞はもともと katsuyou="" が正当な値のため対象外とする
NON_CONJUGATING_HINSHIS = ("副詞", "連体詞")


def delete_stale_rows(apps, schema_editor):
    Word = apps.get_model('subekashi', 'Word')
    Word.objects.filter(katsuyou="").exclude(hinshi__in=NON_CONJUGATING_HINSHIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0044_remove_word_unique_word_hinshi_candidate_and_more'),
    ]

    operations = [
        migrations.RunPython(delete_stale_rows, migrations.RunPython.noop),
    ]
