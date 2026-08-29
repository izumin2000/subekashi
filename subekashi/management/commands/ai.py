import random

from django.core.management.base import BaseCommand
from subekashi.models import Ai, Song, Word
from subekashi.lib.lyric_tokenizer import tokenize_lyrics_with_index, REPLACEABLE_HINSHIS


class Command(BaseCommand):
    help = "既存のSong.lyricsの単語をランダムに入れ替えて、genetype='janome'のAiレコードをシードする。"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1000, help='作成するAiレコード数の目安')

    def handle(self, *args, **options):
        target_count = options['count']

        lyrics_list = list(
            Song.objects.filter(is_joke=False, is_questionable=False)
            .exclude(lyrics='')
            .exclude(lyrics__isnull=True)
            .values_list('lyrics', flat=True)
        )
        random.shuffle(lyrics_list)

        # 置き換え可能かどうかをトークンごとにDB問い合わせすると
        # 曲数×行数×トークン数だけクエリが発生し非常に遅くなるため、
        # (word, hinshi) の組を先に一括取得してメモリ上で判定する
        # （tokenize_ai_instances()と同じN+1回避パターン）
        replaceable_pairs = set(Word.objects.values_list('word', 'hinshi').distinct())

        # 候補もhinshi・katsuyouの組ごとにキャッシュし、同じ組み合わせに対する
        # 重複クエリを避ける
        candidates_cache = {}

        def get_candidates(hinshi, katsuyou):
            key = (hinshi, katsuyou)
            if key not in candidates_cache:
                candidates_cache[key] = list(
                    Word.objects.filter(hinshi=hinshi, katsuyou=katsuyou)
                    .values_list('candidate', flat=True)
                    .distinct()
                )
            return candidates_cache[key]

        # 既存のAiレコードおよび今回の実行内での重複を避ける
        existing_lyrics = set(Ai.objects.filter(genetype=Ai.GENETYPE_JANOME).values_list('lyrics', flat=True))

        MIN_LYRICS_LENGTH = 7
        MAX_LYRICS_LENGTH = 20
        new_lyrics_list = []

        for song_lyrics in lyrics_list:
            if len(new_lyrics_list) >= target_count:
                break

            lines = [line for line in song_lyrics.split('\n') if line.strip()]
            random.shuffle(lines)

            for line in lines:
                tokens = tokenize_lyrics_with_index(line)
                eligible = [
                    token for token in tokens
                    if token['hinshi'] in REPLACEABLE_HINSHIS
                    and (token['surface'], token['hinshi']) in replaceable_pairs
                ]
                if not eligible:
                    continue

                token = random.choice(eligible)
                candidates = [
                    c for c in get_candidates(token['hinshi'], token['katsuyou'])
                    if c != token['surface']
                ]
                if not candidates:
                    continue
                candidate = random.choice(candidates)

                new_lyrics = ''.join(
                    candidate if t['index'] == token['index'] else t['surface']
                    for t in tokens
                )
                if not (MIN_LYRICS_LENGTH <= len(new_lyrics) <= MAX_LYRICS_LENGTH):
                    continue
                if new_lyrics in existing_lyrics:
                    # この行・候補の組み合わせは重複するが、同じ曲の別の行なら
                    # 重複しないユニークな結果を作れる可能性があるため、
                    # 曲ごと諦めず次の行を試す
                    continue

                existing_lyrics.add(new_lyrics)
                new_lyrics_list.append(new_lyrics)
                break

        Ai.objects.bulk_create([
            Ai(lyrics=lyrics, genetype=Ai.GENETYPE_JANOME, score=0) for lyrics in new_lyrics_list
        ])

        self.stdout.write(self.style.SUCCESS(
            f"新規Aiレコード数：{len(new_lyrics_list)}件（対象{len(lyrics_list)}曲中）"
        ))
