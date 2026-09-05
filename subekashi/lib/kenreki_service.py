VIEW_THRESHOLDS = [
    1, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000,
    200000, 500000, 1000000, 2000000, 5000000, 10000000, 20000000, 50000000, 100000000,
]
LIKE_THRESHOLDS = [
    1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000,
    20000, 50000, 100000, 200000, 500000, 1000000, 2000000, 5000000,
]

MAX_KEYS = 88  # 鍵盤ビジュアルに描画する本数の上限（現実のピアノの鍵盤数に合わせる）
# オーバーフロー色スペクトルの上限鍵盤数。鍵歴はSongごとに算出したpt合計をそのまま
# 鍵盤本数として扱う（#1099で2pt=鍵盤1本の換算を廃止）ため、廃止前の実データ最大値
# (1,506、2pt=1鍵盤換算時)のpt換算後のおおよその最大値に対して、十分な伸びしろを
# 持たせた固定値（DBを都度クエリしない）
MAX_POSSIBLE_KEY_COUNT = 5000


MAX_TOTAL_POINTS = len(VIEW_THRESHOLDS) + len(LIKE_THRESHOLDS)

WHITE_KEY_WIDTH = 12
BLACK_KEY_WIDTH = 8
# 1オクターブ(12半音)の白鍵/黒鍵パターン。ラ(A)から開始: A, A#, B, C, C#, D, D#, E, F, F#, G, G#
CHROMATIC_IS_WHITE = [True, False, True, True, False, True, False, True, True, False, True, False]


def compute_threshold_points(value, thresholds):
    """valueが到達した段階数をそのままptとして返す

    例: thresholdsが[1, 20, 50, ...]でvalue=55なら、1・20・50の3段階に到達しているため3pt
    """
    return sum(1 for threshold in thresholds if value >= threshold)


def compute_song_points(view, like):
    """1曲分のview/likeから鍵歴ptを算出する（鍵歴はSongごとに求め、authorや総合統計では
    その総和を表示する仕様のため、この曲単位の算出が全ての起点になる）
    """
    return compute_threshold_points(view, VIEW_THRESHOLDS) + compute_threshold_points(like, LIKE_THRESHOLDS)


def _kenreki_from_points(points):
    """合計ptから鍵歴（オーバーフロー色等）を算出する

    ptは合計をそのまま鍵盤本数として扱う（#1099で2pt=鍵盤1本の換算を廃止したため、
    鍵盤ビジュアル用の別フィールドは持たない）。カンストはさせず実際の達成数を
    そのまま返す（鍵盤ビジュアルの描画本数のみMAX_KEYSを上限とし、呼び出し側で
    min()して渡す）。ptがMAX_KEYS(88)以上になった時点で、黒鍵の色（虹色の
    グラデーション、MAX_POSSIBLE_KEY_COUNTに対する到達度で連続的に変化）を返す
    """
    overflow_color = None
    overflow_ratio = None
    if points >= MAX_KEYS:
        overflow_ratio = min(1.0, (points - MAX_KEYS) / (MAX_POSSIBLE_KEY_COUNT - MAX_KEYS))
        hue = round(overflow_ratio * 270)
        overflow_color = f"hsl({hue}, 75%, 45%)"

    return {
        "points": points,
        "overflow_color": overflow_color,
        "overflow_ratio": overflow_ratio,
        "overflow_lower_bound": MAX_KEYS,
        "overflow_upper_bound": MAX_POSSIBLE_KEY_COUNT if overflow_ratio is not None else None,
    }


def compute_kenreki(view, like):
    """1曲分のview/likeから鍵歴（実績鍵盤）のpt・オーバーフロー色を算出して返す"""
    return _kenreki_from_points(compute_song_points(view, like))


def compute_kenreki_for_songs(view_like_pairs):
    """複数曲分の(view, like)ペアそれぞれについて鍵歴ptを算出し、合計してから鍵歴を返す

    authorごとの統計・総合統計ページで表示する「Songごとの鍵歴の総和」を算出する
    """
    total_points = sum(compute_song_points(view, like) for view, like in view_like_pairs)
    return _kenreki_from_points(total_points)


def build_keyboard_geometry(key_count, black_key_color=None):
    """key_count個分の鍵盤（白鍵・黒鍵の両方を含む実際の鍵の総数）を、標準的な鍵盤配列
    （ラ(A)から開始する12半音の繰り返し）で並べた白鍵・黒鍵の位置一覧を返す

    key_countは白鍵の本数（度数）ではなく、黒鍵も含めた実際の鍵の総数として扱う。
    black_key_colorが指定されていれば全ての黒鍵をその色で塗る（鍵歴の上限超過表現用）
    """
    white_count = 0
    black_keys = []
    last_is_black = False
    for i in range(key_count):
        if CHROMATIC_IS_WHITE[i % len(CHROMATIC_IS_WHITE)]:
            white_count += 1
            last_is_black = False
        else:
            left = white_count * WHITE_KEY_WIDTH - BLACK_KEY_WIDTH // 2
            black_keys.append({"left": left, "color": black_key_color})
            last_is_black = True

    width = white_count * WHITE_KEY_WIDTH
    if last_is_black:
        width += BLACK_KEY_WIDTH // 2

    return {
        "white_key_count": white_count,
        "white_keys": range(white_count),
        "black_keys": black_keys,
        "width": width,
    }
