from datetime import datetime
from django.db.models import Count, Q, Sum
from django.utils import timezone
from subekashi.models import Author, Song


def parse_int_or_none(value):
    """valueをintに変換できればその値を、できなければNoneを返す

    GETパラメータ(year/month)はint変換できない任意の文字列になり得るため、
    ValueError/TypeErrorで500にならないようビュー側のバリデーションで使う
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def now_local():
    """現在時刻をDjangoの設定タイムゾーン(Asia/Tokyo)に変換して返す

    サーバーOSのタイムゾーン設定に依存する素のdatetime.now()は使わない
    """
    return timezone.localtime(timezone.now())


def apply_songrange_filter(qs, songrange):
    """songrange(all/subeana/xx)の設定に応じてis_subeanaで絞り込んだQuerySetを返す"""
    if songrange == "subeana":
        return qs.filter(is_subeana=True)
    if songrange == "xx":
        return qs.filter(is_subeana=False)
    return qs


def get_songrange_availability(qs):
    """qs内にis_subeana=True/Falseの曲がそれぞれ存在するかを(has_subeana, has_xx)で返す

    どちらか一方しか存在しない場合、"全て"の選択肢は存在する方の結果と一致するため不要になる
    """
    return qs.filter(is_subeana=True).exists(), qs.filter(is_subeana=False).exists()


def apply_upload_time_filter(qs, year, month):
    """year("all"または数値文字列)/month("all"または数値文字列)でupload_timeを絞り込んだQuerySetを返す

    yearとmonthは独立して指定できる（例: yearが"all"でもmonthだけ指定すれば、
    年を問わずその月にアップロードされた曲に絞り込める）。
    upload_timeがNoneの曲は年/月を指定した場合は対象外になる（SQLのNULL比較により自動的に除外される）
    """
    if year and year != "all":
        qs = qs.filter(upload_time__year=int(year))
    if month and month != "all":
        qs = qs.filter(upload_time__month=int(month))
    return qs


def _by_ids(qs):
    """M2Mフィルタ・distinct済みのqsから素のid一覧を経由してクリーンなQuerySetを作り直す

    既にauthors__id等のM2M JOINが乗ったqsに対してさらにCount('authors')等の
    別M2Mをannotateすると、JOINのfan-outで値が重複・肥大化するため、
    集計のたびにid一覧経由でSong.objects.filter(id__in=...)を作り直す
    """
    song_ids = list(qs.values_list("id", flat=True))
    return Song.objects.filter(id__in=song_ids), song_ids


def compute_common_stats(qs):
    """総合統計ページ・authorごとの統計ページ共通の統計を返す"""
    base, song_ids = _by_ids(qs)
    view_like = base.aggregate(v=Sum("view"), l=Sum("like"))
    return {
        "song_count": len(song_ids),
        "total_view": view_like["v"] or 0,
        "total_like": view_like["l"] or 0,
        "total_authors": compute_unique_author_count(qs),
        "total_imitateds": base.annotate(c=Count("imitateds", distinct=True)).aggregate(s=Sum("c"))["s"] or 0,
    }


def compute_unique_author_count(qs):
    """範囲内の曲に紐づく重複なしの作者数（総作者数として使用）"""
    return Author.objects.filter(songs__in=qs).distinct().count()


def compute_total_imitates(qs):
    """authorごとの統計ページのみ: 範囲内の各曲が模倣している元曲数の総和"""
    base, _ = _by_ids(qs)
    return base.annotate(c=Count("imitates", distinct=True)).aggregate(s=Sum("c"))["s"] or 0


def compute_collaborator_count(qs, author_id):
    """authorごとの統計ページのみ: 範囲内の各曲について、author_id本人を除いた作者数の総和（合作人数）"""
    base, _ = _by_ids(qs)
    return base.annotate(
        c=Count("authors", filter=~Q(authors__id=author_id), distinct=True)
    ).aggregate(s=Sum("c"))["s"] or 0


def compute_unique_collaborator_count(qs, author_id):
    """authorごとの統計ページのみ: 範囲内の曲に紐づく作者からauthor_id本人を除いたユニーク数（ユニーク合作人数）"""
    return Author.objects.filter(songs__in=qs).exclude(id=author_id).distinct().count()


def get_year_choices():
    """upload_timeが最小の年〜今年のリストを返す（upload_time付きの曲が1件もなければ空リスト）

    DBにはUTCで保存されているため、年の判定はローカルタイムゾーンに変換してから行う
    """
    first = Song.objects.exclude(upload_time__isnull=True).order_by("upload_time").first()
    if first is None:
        return []
    first_year = timezone.localtime(first.upload_time).year
    return list(range(first_year, now_local().year + 1))


def get_month_choices(year, current_year):
    """yearが今年ならその年の1月〜現在月、それ以外なら1〜12月のリストを返す"""
    if year == current_year:
        return list(range(1, now_local().month + 1))
    return list(range(1, 13))


MONTHLY_STATS_FIELDS = ["song_count", "total_view", "total_like", "total_authors", "total_imitateds"]


def with_monthly_deltas(rows):
    """年月昇順の累積値の行リストに、各フィールドの単月差分(<field>_delta)を追加して返す

    先頭行の差分は直前の月が無いため累積値そのものを使う。累積値と差分を両方
    保持したまま返すため、後段でyear/monthによる表示範囲の絞り込みを行っても
    差分値がずれない（絞り込み前の全期間から差分を計算しているため）
    """
    result = []
    prev = None
    for row in rows:
        row = dict(row)
        for field in MONTHLY_STATS_FIELDS:
            row[f"{field}_delta"] = row[field] if prev is None else row[field] - prev[field]
        result.append(row)
        prev = row
    return result


def filter_monthly_series_by_year_month(rows, year, month):
    """year("all"または数値文字列)/month("all"または数値文字列)で表示する行を絞り込む"""
    if year and year != "all":
        rows = [row for row in rows if row["year"] == int(year)]
        if month and month != "all":
            rows = [row for row in rows if row["month"] == int(month)]
    return rows


def next_year_month(year, month):
    """(year, month)の次の月を(year, month)タプルで返す"""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def month_start(year, month):
    """year年month月1日0時0分のタイムゾーン付きdatetimeを返す"""
    return timezone.make_aware(datetime(year, month, 1))
