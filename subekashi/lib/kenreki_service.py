VIEW_THRESHOLDS = [
    1, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000,
    200000, 500000, 1000000, 2000000, 5000000, 10000000, 20000000, 50000000, 100000000,
]
LIKE_THRESHOLDS = [
    1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000,
    20000, 50000, 100000, 200000, 500000, 1000000, 2000000, 5000000,
]

POINTS_PER_KEY = 2
MAX_KEYS = 100
KENREKI_CAP_POINTS = POINTS_PER_KEY * MAX_KEYS


def _triangular(n):
    return n * (n + 1) // 2


MAX_TOTAL_POINTS = _triangular(len(VIEW_THRESHOLDS)) + _triangular(len(LIKE_THRESHOLDS))

WHITE_KEY_WIDTH = 12
BLACK_KEY_WIDTH = 8
# 1オクターブ内の白鍵(C~B、7音)のうち直後に黒鍵を持つもの（E-F、B-C間には黒鍵が無い）
OCTAVE_HAS_BLACK_AFTER = [True, True, False, True, True, True, False]


def compute_threshold_points(value, thresholds):
    """valueが到達した段階数を求め、1〜その段階数までの合計（三角数）を返す

    各段階は到達順に1, 2, 3, ...ptが割り当てられ、到達した段階のptを全て合計する
    """
    reached = sum(1 for threshold in thresholds if value >= threshold)
    return _triangular(reached)


def compute_kenreki(total_view, total_like):
    """再生数・高評価数から鍵歴（実績鍵盤）の鍵盤数・オーバーフロー色を算出して返す

    2pt = 鍵盤1本として100本を上限とし、上限を超えた分（points > KENREKI_CAP_POINTS）は
    黒鍵の色（赤→紫のグラデーション、達成しうる全段階のptの合計に対する到達度で連続的に変化）で表現する
    """
    points = compute_threshold_points(total_view, VIEW_THRESHOLDS) + compute_threshold_points(total_like, LIKE_THRESHOLDS)
    key_count = min(MAX_KEYS, points // POINTS_PER_KEY)

    overflow_color = None
    overflow_ratio = None
    if points > KENREKI_CAP_POINTS:
        overflow_ratio = min(1.0, (points - KENREKI_CAP_POINTS) / (MAX_TOTAL_POINTS - KENREKI_CAP_POINTS))
        hue = round(overflow_ratio * 270)
        overflow_color = f"hsl({hue}, 75%, 45%)"

    return {
        "points": points,
        "key_count": key_count,
        "overflow_color": overflow_color,
        "overflow_ratio": overflow_ratio,
    }


def build_keyboard_geometry(key_count, black_key_color=None):
    """key_count本の白鍵と、標準的な鍵盤配列に基づく黒鍵の位置一覧を返す

    黒鍵は隣り合う白鍵の間（最後の白鍵の後ろは除く）に配置され、
    black_key_colorが指定されていれば全ての黒鍵をその色で塗る（鍵歴の上限超過表現用）
    """
    black_keys = []
    for i in range(key_count - 1):
        octave_pos = i % 7
        if OCTAVE_HAS_BLACK_AFTER[octave_pos]:
            left = (i + 1) * WHITE_KEY_WIDTH - BLACK_KEY_WIDTH // 2
            black_keys.append({"left": left, "color": black_key_color})

    return {
        "white_key_count": key_count,
        "white_keys": range(key_count),
        "black_keys": black_keys,
        "width": key_count * WHITE_KEY_WIDTH,
    }
