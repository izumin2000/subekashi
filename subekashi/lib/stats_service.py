from datetime import datetime
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear
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


SONGRANGE_VALUES = {"all", "subeana", "xx"}


def resolve_songrange(request, base_qs):
    """GETパラメータのsongrangeを検証・正規化する

    総合統計ページ・authorごとの統計ページ共通のロジック。base_qsに
    is_subeana=True/Falseの両方が存在しない場合、"全て"は実在する方の結果と
    一致し選択肢としても表示されないため、実在する方に強制する
    """
    has_subeana, has_xx = get_songrange_availability(base_qs)
    show_all_songrange = has_subeana and has_xx

    songrange = request.GET.get("songrange", "all")
    if songrange not in SONGRANGE_VALUES:
        songrange = "all"
    if not show_all_songrange:
        songrange = "subeana" if has_subeana else "xx"

    return songrange, show_all_songrange


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


def _clean_base(qs):
    """qsのid一覧をサブクエリとして参照するJOIN無しのクリーンなQuerySetを返す

    songrange/upload_time等で既にJOINが乗ったqsに対しM2Mのannotate(Count)を
    直接重ねるとJOINのfan-outで値が狂うため、id一覧をサブクエリ化して
    作り直したqsを介して集計する。idをPythonリストに列挙しないため、
    SQLiteのバインド変数上限（曲数が増えてもid__inのIN句が肥大化しない）にも触れない
    """
    return Song.objects.filter(id__in=qs.values("id"))


def get_view_like_pairs(qs):
    """qs内の各曲のview/likeペアを列挙する（Noneは0として扱う）

    鍵歴（実績鍵盤）はSongごとに算出してから合計する仕様のため、
    集計済みのSumではなく曲ごとの値をそのまま使う
    """
    return [(view or 0, like or 0) for view, like in qs.values_list("view", "like")]


def compute_view_like_totals(qs):
    """曲数・総再生回数・総高評価数のみを返す（total_authors/total_imitatedsを含まない最小構成）

    鍵歴（実績鍵盤）の算出等、view/likeの合計だけが必要な呼び出し元で
    不要な追加集計クエリが発行されないよう、compute_base_statsから切り出した
    """
    base = _clean_base(qs)
    aggregates = base.aggregate(song_count=Count("id", distinct=True), v=Sum("view"), l=Sum("like"))
    return {
        "song_count": aggregates["song_count"] or 0,
        "total_view": aggregates["v"] or 0,
        "total_like": aggregates["l"] or 0,
    }


def compute_base_stats(qs):
    """総合統計ページ・authorごとの統計ページ共通の統計を返す（total_authorsは含まない）

    total_authorsの算出（compute_unique_author_count）はAuthorテーブル起点の
    追加クエリが必要になるため、それを使わないauthorごとの統計ページ
    （合作人数として別途算出するため総作者数自体は表示しない）で無駄なクエリが
    発行されないよう、compute_common_statsから切り出した
    """
    stats = compute_view_like_totals(qs)
    base = _clean_base(qs)
    stats["total_imitateds"] = base.annotate(c=Count("imitateds", distinct=True)).aggregate(s=Sum("c"))["s"] or 0
    return stats


def compute_common_stats(qs):
    """総合統計ページ・stats管理コマンドのみ: total_authorsを含む共通統計を返す"""
    stats = compute_base_stats(qs)
    stats["total_authors"] = compute_unique_author_count(qs)
    return stats


def build_stats_items(stats, items):
    """statsのsong_countが0（曲が無い＝データなし）なら統計カード全体を非表示にするため空リストを返す

    song_countが1件以上あれば、他の指標がたまたま0（模倣曲が無い等の実際の値）
    であってもそのまま表示する。「データなし」と「値が0」を区別するため
    """
    if stats["song_count"] == 0:
        return []
    return items


def compute_unique_author_count(qs):
    """範囲内の曲に紐づく重複なしの作者数（総作者数として使用）"""
    return Author.objects.filter(songs__in=qs).distinct().count()


def compute_total_imitates(qs):
    """authorごとの統計ページのみ: 範囲内の各曲が模倣している元曲数の総和"""
    base = _clean_base(qs)
    return base.annotate(c=Count("imitates", distinct=True)).aggregate(s=Sum("c"))["s"] or 0


def compute_collaborator_count(qs, author_id):
    """authorごとの統計ページのみ: 範囲内の各曲について、author_id本人を除いた作者数の総和（合作人数）"""
    base = _clean_base(qs)
    return base.annotate(
        c=Count("authors", filter=~Q(authors__id=author_id), distinct=True)
    ).aggregate(s=Sum("c"))["s"] or 0


def compute_unique_collaborator_count(qs, author_id):
    """authorごとの統計ページのみ: 範囲内の曲に紐づく作者からauthor_id本人を除いたユニーク数（ユニーク合作人数）"""
    return Author.objects.filter(songs__in=qs).exclude(id=author_id).distinct().count()


def get_year_choices(qs=None):
    """qs（省略時はSong.objects.all()）内で実際にupload_timeが存在する年のみを昇順で返す

    "最古年〜今年"の連続レンジではなく、get_month_choicesと同様に実際に曲が
    存在する年のみを返す（間の年に投稿が無ければその年は選択肢に出さない。
    選んでも0件になる組み合わせを避けるため）。qsにauthorやsongrangeの絞り込みを
    渡せば、その範囲で実際に選択可能な年のみに絞った選択肢になる（例: author
    ページではその作者自身の投稿年のみ、songrange選択中はその範囲に該当する
    年のみを候補にできる）。ExtractYearはDjangoのタイムゾーン設定に従って
    変換されるため、DBがUTC保存でもローカルタイムゾーン基準で年が判定される
    """
    if qs is None:
        qs = Song.objects.all()
    years = qs.annotate(year=ExtractYear("upload_time")).values_list("year", flat=True).distinct()
    return sorted(y for y in years if y is not None)


def get_month_choices(qs, year=None):
    """qs内で実際にupload_timeが存在する月のみを1〜12の昇順で返す

    yearを指定すればその年のみ、Noneなら年を問わず全期間が対象（"全ての年"時、
    月だけの絞り込みで実際にヒットする月のみを選択肢にする）。曲が存在しない
    月は選択肢に出さない（選んでも0件になる組み合わせを避けるため）。
    ExtractMonthはDjangoのタイムゾーン設定に従って変換されるため、DBがUTC
    保存でもローカルタイムゾーン基準で月が判定される
    """
    if year is not None:
        qs = qs.filter(upload_time__year=year)
    months = qs.annotate(month=ExtractMonth("upload_time")).values_list("month", flat=True).distinct()
    return sorted(m for m in months if m is not None)


def resolve_year_month(request, year_choice_qs=None):
    """GETパラメータのyear/monthを検証・正規化する

    総合統計ページ・authorごとの統計ページ共通のロジック。ゼロ埋め等の非正規な
    文字列表現でもint変換後の値で選択肢と照合し、正規化した文字列を返す
    （テンプレート上の選択状態比較や500エラー防止のため）。
    year_choice_qsを渡せば、その範囲（author自身の曲・選択中のsongrange等）で
    実際に選択可能な年・月のみに選択肢を絞り込める
    """
    if year_choice_qs is None:
        year_choice_qs = Song.objects.all()
    year_choices = get_year_choices(year_choice_qs)

    year = request.GET.get("year", "all")
    year_int = parse_int_or_none(year)
    if year_int not in year_choices:
        year, year_int = "all", None
    else:
        year = str(year_int)

    month_choices = get_month_choices(year_choice_qs, year_int)
    month = request.GET.get("month", "all")
    month_int = parse_int_or_none(month)
    month = str(month_int) if month_int in month_choices else "all"

    return year, month, year_choices, month_choices


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
    """year("all"または数値文字列)/month("all"または数値文字列)で表示する行を絞り込む

    yearが指定されている場合はその年のみに絞り込み、monthによる絞り込みは行わない
    （year・monthを両方指定すると棒グラフが1本だけになり意味を成さないため、
    その場合はmonthを無視してその年の全期間を表示する。コードレビュー指摘対応）。
    yearが"all"の場合はmonthのみで絞り込める（年をまたいだ同月比較として意味を成す）
    """
    if year and year != "all":
        return [row for row in rows if row["year"] == int(year)]
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
