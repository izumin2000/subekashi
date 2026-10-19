from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import GOOGLE_SHEETS_API_KEY, GOOGLE_SHEETS_SPREADSHEET_ID
from subekashi.lib.youtube import get_error_reasons
from dataclasses import dataclass
from datetime import date
import re


# すべあな界隈年表の読み取り・解析に失敗した
class TimelineError(Exception):
    pass


# 年ごとのシートがある最初の年
FIRST_YEAR = 2018

# 年ごとのシートの見出し。見出しが空の列は直前の列の続き（2つ目以降の解読URL・配信URL）
EXPECTED_HEADER = [
    "日付", "プ", "作品名/出来事", "作者", "バッジ", "カテゴリ", "モチーフ1", "モチーフ2", "URL", "URL2",
    "解読日", "解読URL", "", "", "歌詞", "配信", "配信2", "配信URL", "", "", "備考",
]

DATE_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})")


@dataclass
class TimelineRow:
    year: int
    row: int
    date: date | None
    premiere_rush: str
    title: str
    author: str
    badge: str
    category: str
    motif1: str
    motif2: str
    urls: list[str]
    decode_date: str
    decode_urls: list[str]
    lyrics_url: str
    distribution: str
    distribution2: str
    distribution_urls: list[str]
    notes: list[str]


def get_sheet_title(year):
    return f"{year}年"


def get_cell(cells, index):
    return cells[index] if index < len(cells) else ""


# 見出しの無い列（備考より右の列）も備考として扱うため、endを省略すると行の最後までを返す
def get_cells(cells, start, end=None):
    return [cell for cell in cells[start:end] if cell]


# 「月/日」形式でない、または存在しない日付ならNoneを返す
def parse_date(year, text):
    match = DATE_PATTERN.fullmatch(text)
    if not match:
        return None
    try:
        return date(year, int(match[1]), int(match[2]))
    except ValueError:
        return None


# 列の並びが変わったまま読み取ると別の列の値が入るため、見出しが想定と異なる場合はTimelineErrorを送出する
def parse_sheet(year, values):
    if not values or [cell.strip() for cell in values[0][:len(EXPECTED_HEADER)]] != EXPECTED_HEADER:
        raise TimelineError(f"{get_sheet_title(year)}のシートの見出しが想定と異なります")

    rows = []
    current_date = None
    # 1行目は見出しのため、2行目から読み取る
    for row_number, raw_cells in enumerate(values[1:], start=2):
        cells = [cell.strip() for cell in raw_cells]
        if not any(cells):
            continue

        # 日付が空の行は、直前の行と同じ日付
        if cells[0]:
            current_date = parse_date(year, cells[0])

        rows.append(TimelineRow(
            year=year,
            row=row_number,
            date=current_date,
            premiere_rush=get_cell(cells, 1),
            # 全角スペースのみのタイトルなど、空白文字のみの値も曲のタイトル・作者として扱うため、そのまま残す
            title=get_cell(cells, 2) or get_cell(raw_cells, 2),
            author=get_cell(cells, 3) or get_cell(raw_cells, 3),
            badge=get_cell(cells, 4),
            category=get_cell(cells, 5),
            motif1=get_cell(cells, 6),
            motif2=get_cell(cells, 7),
            urls=get_cells(cells, 8, 10),
            decode_date=get_cell(cells, 10),
            decode_urls=get_cells(cells, 11, 14),
            lyrics_url=get_cell(cells, 14),
            distribution=get_cell(cells, 15),
            distribution2=get_cell(cells, 16),
            distribution_urls=get_cells(cells, 17, 20),
            notes=get_cells(cells, 20),
        ))

    return rows


# yearsの年のシートを読み取り、{年: TimelineRowのリスト}を返す。シートが無い年は含めない
# APIキーでは公開されているスプレッドシートの読み取りしかできないため、スプレッドシートを書き換えることはない
# 元の例外の文字列にはAPIキーを含むURLが入るため、例外は連鎖させず（from None）、メッセージにはAPIキーを含まない情報のみを入れる
def get_timeline(years):
    if GOOGLE_SHEETS_API_KEY == "" or GOOGLE_SHEETS_SPREADSHEET_ID == "":
        raise TimelineError("GOOGLE_SHEETS_API_KEYまたはGOOGLE_SHEETS_SPREADSHEET_IDが設定されていません")

    try:
        spreadsheets = build("sheets", "v4", developerKey=GOOGLE_SHEETS_API_KEY, cache_discovery=False).spreadsheets()
        spreadsheet = spreadsheets.get(
            spreadsheetId=GOOGLE_SHEETS_SPREADSHEET_ID,
            fields="sheets.properties.title"
        ).execute()
        sheet_titles = {sheet["properties"]["title"] for sheet in spreadsheet.get("sheets", [])}

        target_years = [year for year in years if get_sheet_title(year) in sheet_titles]
        if not target_years:
            return {}

        response = spreadsheets.values().batchGet(
            spreadsheetId=GOOGLE_SHEETS_SPREADSHEET_ID,
            ranges=[f"'{get_sheet_title(year)}'" for year in target_years]
        ).execute()

    except HttpError as e:
        detail = " ".join([f"HTTP {e.status_code}", *get_error_reasons(e)])
        raise TimelineError(f"Google Sheets APIの呼び出しに失敗しました（{detail}）") from None
    except Exception as e:
        raise TimelineError(f"Google Sheets APIの呼び出しに失敗しました（{type(e).__name__}）") from None

    # valueRangesはrangesと同じ順で返る
    value_ranges = response.get("valueRanges", [])
    if len(value_ranges) != len(target_years):
        raise TimelineError("Google Sheets APIのレスポンスを解析できませんでした")

    return {
        year: parse_sheet(year, value_range.get("values", []))
        for year, value_range in zip(target_years, value_ranges)
    }
