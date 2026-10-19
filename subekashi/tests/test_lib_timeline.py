"""
lib/timeline.py のテスト（Google Sheets APIはモック化、#52）

parse_sheet: すべあな界隈年表の年ごとのシートの行を、列ごとの値に分けること、日付が空の行は直前の行の日付を引き継ぐこと、
見出しが想定と異なる場合はTimelineErrorを送出することを検証する。
get_timeline: シートが存在する年のみを読み取ること、読み取りのAPIのみを呼び出すこと（読み取り専用）、
APIの呼び出しに失敗した場合はAPIキーを含めずにTimelineErrorを送出することを検証する。
"""
import json
import socket
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from googleapiclient.errors import HttpError

from subekashi.lib.timeline import EXPECTED_HEADER, TimelineError, get_timeline, parse_sheet


def make_row(**cells):
    columns = {
        "date": 0, "premiere_rush": 1, "title": 2, "author": 3, "badge": 4, "category": 5, "motif1": 6, "motif2": 7,
        "url": 8, "url2": 9, "decode_date": 10, "decode_url": 11, "decode_url2": 12, "decode_url3": 13, "lyrics_url": 14,
        "distribution": 15, "distribution2": 16, "distribution_url": 17, "distribution_url2": 18, "distribution_url3": 19,
        "note": 20, "extra": 21,
    }
    row = [""] * (max(columns[key] for key in cells) + 1)
    for key, value in cells.items():
        row[columns[key]] = value
    return row


def make_http_error(status, reasons=()):
    content = {"error": {"code": status, "message": "error", "errors": [{"reason": reason} for reason in reasons]}}
    return HttpError(
        MagicMock(status=status, reason="error"),
        json.dumps(content).encode("utf-8"),
        uri="https://sheets.googleapis.com/v4/spreadsheets/sheet-id?key=dummy-key",
    )


class ParseSheetTest(SimpleTestCase):
    def test_maps_cells_to_fields(self):
        values = [EXPECTED_HEADER, make_row(
            date="5/10", premiere_rush="年末プレラ", title="曲名", author="作者", badge="👤", category="曲",
            motif1="教育枠", motif2="→.👤", url="https://youtu.be/aaaaaaaaaaa", url2="https://www.nicovideo.jp/watch/sm1",
            decode_date="2021/8/29", decode_url="https://youtu.be/bbbbbbbbbbb", decode_url2="https://x.com/a/status/1",
            decode_url3="https://x.com/a/status/2", lyrics_url="https://lyrics.imicomweb.com/songs/1",
            distribution="アルバム", distribution2="シングル", distribution_url="https://fanlink.tv/a",
            distribution_url2="https://fanlink.tv/b", distribution_url3="https://fanlink.tv/c",
            note="備考", extra="見出しの無い列",
        )]
        row = parse_sheet(2018, values)[0]

        self.assertEqual(row.year, 2018)
        self.assertEqual(row.row, 2)
        self.assertEqual(row.date, date(2018, 5, 10))
        self.assertEqual(row.premiere_rush, "年末プレラ")
        self.assertEqual(row.title, "曲名")
        self.assertEqual(row.author, "作者")
        self.assertEqual(row.badge, "👤")
        self.assertEqual(row.category, "曲")
        self.assertEqual(row.motif1, "教育枠")
        self.assertEqual(row.motif2, "→.👤")
        self.assertEqual(row.urls, ["https://youtu.be/aaaaaaaaaaa", "https://www.nicovideo.jp/watch/sm1"])
        self.assertEqual(row.decode_date, "2021/8/29")
        # 見出しが空の列は直前の列（解読URL・配信URL）の続き
        self.assertEqual(row.decode_urls, ["https://youtu.be/bbbbbbbbbbb", "https://x.com/a/status/1", "https://x.com/a/status/2"])
        self.assertEqual(row.lyrics_url, "https://lyrics.imicomweb.com/songs/1")
        self.assertEqual(row.distribution, "アルバム")
        self.assertEqual(row.distribution2, "シングル")
        self.assertEqual(row.distribution_urls, ["https://fanlink.tv/a", "https://fanlink.tv/b", "https://fanlink.tv/c"])
        # 備考より右の見出しの無い列も備考として扱う
        self.assertEqual(row.notes, ["備考", "見出しの無い列"])

    def test_short_row_fills_missing_cells(self):
        # APIは行末の空のセルを返さない
        row = parse_sheet(2018, [EXPECTED_HEADER, ["5/10", "", "曲名"]])[0]

        self.assertEqual(row.title, "曲名")
        self.assertEqual(row.author, "")
        self.assertEqual(row.urls, [])
        self.assertEqual(row.decode_urls, [])
        self.assertEqual(row.distribution_urls, [])
        self.assertEqual(row.notes, [])

    def test_empty_cells_are_excluded_from_lists(self):
        row = parse_sheet(2018, [EXPECTED_HEADER, make_row(url2="https://youtu.be/aaaaaaaaaaa", decode_url3="https://x.com/a/status/1")])[0]

        self.assertEqual(row.urls, ["https://youtu.be/aaaaaaaaaaa"])
        self.assertEqual(row.decode_urls, ["https://x.com/a/status/1"])

    def test_strips_cells(self):
        row = parse_sheet(2018, [EXPECTED_HEADER, make_row(date=" 5/10 ", title=" 曲名\n", badge=" 🍁🍜\n🐬+ ")])[0]

        self.assertEqual(row.date, date(2018, 5, 10))
        self.assertEqual(row.title, "曲名")
        # セル内の改行は残す
        self.assertEqual(row.badge, "🍁🍜\n🐬+")

    def test_keeps_whitespace_only_title_and_author(self):
        # 全角スペースのみのタイトルなど、空白文字のみの値も曲のタイトル・作者として扱う
        row = parse_sheet(2024, [EXPECTED_HEADER, make_row(url="https://youtu.be/aaaaaaaaaaa", title="\u3000", author=" ", badge="\u3000")])[0]

        self.assertEqual(row.title, "\u3000")
        self.assertEqual(row.author, " ")
        self.assertEqual(row.badge, "")

    def test_blank_date_uses_previous_date(self):
        values = [
            EXPECTED_HEADER,
            make_row(date="1/1", title="曲1"),
            make_row(title="曲2"),
            # 全角スペースのみの日付も空として扱う
            make_row(date="\u3000", title="曲3"),
            make_row(date="1/3", title="曲4"),
            make_row(title="曲5"),
        ]
        rows = parse_sheet(2024, values)

        self.assertEqual([row.date for row in rows], [date(2024, 1, 1)] * 3 + [date(2024, 1, 3)] * 2)

    def test_rows_before_first_date_have_no_date(self):
        rows = parse_sheet(2024, [EXPECTED_HEADER, make_row(title="曲1"), make_row(date="1/1", title="曲2")])

        self.assertIsNone(rows[0].date)
        self.assertEqual(rows[1].date, date(2024, 1, 1))

    def test_invalid_date_is_none_and_carried_over(self):
        # 日付として読めない値の次の行も、直前の日付（読めなかった日付）を引き継ぐ
        values = [
            EXPECTED_HEADER,
            make_row(date="1/1", title="曲1"),
            make_row(date="不明", title="曲2"),
            make_row(title="曲3"),
            make_row(date="2/30", title="曲4"),
            make_row(date="2024/1/1", title="曲5"),
        ]
        rows = parse_sheet(2024, values)

        self.assertEqual([row.date for row in rows], [date(2024, 1, 1), None, None, None, None])

    def test_leap_day(self):
        self.assertEqual(parse_sheet(2024, [EXPECTED_HEADER, make_row(date="2/29")])[0].date, date(2024, 2, 29))
        self.assertIsNone(parse_sheet(2025, [EXPECTED_HEADER, make_row(date="2/29")])[0].date)

    def test_skips_empty_rows_and_keeps_row_numbers(self):
        values = [EXPECTED_HEADER, make_row(title="曲1"), [], ["", " ", "\u3000"], make_row(title="曲2")]
        rows = parse_sheet(2024, values)

        self.assertEqual([(row.title, row.row) for row in rows], [("曲1", 2), ("曲2", 5)])

    def test_header_only(self):
        self.assertEqual(parse_sheet(2024, [EXPECTED_HEADER]), [])

    def test_header_with_extra_columns(self):
        # 備考より右に列が増えても、既存の列の並びは変わらないため読み取る
        rows = parse_sheet(2024, [EXPECTED_HEADER + ["新しい列"], make_row(title="曲1")])

        self.assertEqual(rows[0].title, "曲1")

    def test_header_mismatch_raises_error(self):
        moved = EXPECTED_HEADER[:2] + EXPECTED_HEADER[3:4] + EXPECTED_HEADER[2:3] + EXPECTED_HEADER[4:]
        for header in [moved, EXPECTED_HEADER[:-1], ["日付", "作品名/出来事"]]:
            with self.subTest(header=header):
                with self.assertRaisesMessage(TimelineError, "2024年のシートの見出しが想定と異なります"):
                    parse_sheet(2024, [header, make_row(title="曲1")])

    def test_empty_sheet_raises_error(self):
        with self.assertRaises(TimelineError):
            parse_sheet(2024, [])


@patch("subekashi.lib.timeline.GOOGLE_SHEETS_SPREADSHEET_ID", "sheet-id")
@patch("subekashi.lib.timeline.GOOGLE_SHEETS_API_KEY", "dummy-key")
@patch("subekashi.lib.timeline.build")
class GetTimelineTest(SimpleTestCase):
    def get_spreadsheets(self, mock_build):
        return mock_build.return_value.spreadsheets.return_value

    def set_response(self, mock_build, titles, value_ranges=None, error=None):
        spreadsheets = self.get_spreadsheets(mock_build)
        spreadsheets.get.return_value.execute.return_value = {"sheets": [{"properties": {"title": title}} for title in titles]}
        execute = spreadsheets.values.return_value.batchGet.return_value.execute
        if error:
            execute.side_effect = error
        else:
            execute.return_value = {"valueRanges": value_ranges or []}

    def test_returns_rows_by_year(self, mock_build):
        self.set_response(mock_build, ["はじめに", "2018年", "2019年"], [
            {"range": "'2018年'!A1:AH5396", "values": [EXPECTED_HEADER, make_row(date="5/10", title="曲1")]},
            {"range": "'2019年'!A1:AJ5396", "values": [EXPECTED_HEADER, make_row(date="1/1", title="曲2"), make_row(title="曲3")]},
        ])
        timeline = get_timeline([2018, 2019])

        self.assertEqual(list(timeline), [2018, 2019])
        self.assertEqual([row.title for row in timeline[2018]], ["曲1"])
        self.assertEqual([(row.title, row.date) for row in timeline[2019]], [("曲2", date(2019, 1, 1)), ("曲3", date(2019, 1, 1))])

        spreadsheets = self.get_spreadsheets(mock_build)
        spreadsheets.get.assert_called_once_with(spreadsheetId="sheet-id", fields="sheets.properties.title")
        spreadsheets.values.return_value.batchGet.assert_called_once_with(spreadsheetId="sheet-id", ranges=["'2018年'", "'2019年'"])

    def test_uses_only_api_key(self, mock_build):
        # APIキーでは公開されているスプレッドシートの読み取りしかできない
        self.set_response(mock_build, ["2018年"], [{"values": [EXPECTED_HEADER]}])
        get_timeline([2018])

        mock_build.assert_called_once_with("sheets", "v4", developerKey="dummy-key", cache_discovery=False)

    def test_does_not_call_write_apis(self, mock_build):
        self.set_response(mock_build, ["2018年"], [{"values": [EXPECTED_HEADER, make_row(title="曲1")]}])
        get_timeline([2018])

        spreadsheets = self.get_spreadsheets(mock_build)
        values = spreadsheets.values.return_value
        for method in [spreadsheets.batchUpdate, spreadsheets.create, values.update, values.append, values.clear,
                       values.batchUpdate, values.batchClear]:
            method.assert_not_called()

    def test_skips_years_without_sheet(self, mock_build):
        self.set_response(mock_build, ["2018年", "2020年"], [
            {"values": [EXPECTED_HEADER, make_row(title="曲1")]},
            {"values": [EXPECTED_HEADER, make_row(title="曲2")]},
        ])
        timeline = get_timeline([2018, 2019, 2020])

        self.assertEqual(list(timeline), [2018, 2020])
        self.get_spreadsheets(mock_build).values.return_value.batchGet.assert_called_once_with(
            spreadsheetId="sheet-id", ranges=["'2018年'", "'2020年'"]
        )

    def test_no_sheets_returns_empty_without_batch_get(self, mock_build):
        self.set_response(mock_build, ["はじめに"])

        self.assertEqual(get_timeline([2018]), {})
        self.get_spreadsheets(mock_build).values.return_value.batchGet.assert_not_called()

    def test_empty_sheet_values(self, mock_build):
        # 見出しも無い空のシートはvaluesが返らない
        self.set_response(mock_build, ["2018年"], [{"range": "'2018年'!A1:Z1000"}])

        with self.assertRaisesMessage(TimelineError, "2018年のシートの見出しが想定と異なります"):
            get_timeline([2018])

    def test_mismatched_value_ranges_raises_error(self, mock_build):
        self.set_response(mock_build, ["2018年", "2019年"], [{"values": [EXPECTED_HEADER]}])

        with self.assertRaisesMessage(TimelineError, "レスポンスを解析できませんでした"):
            get_timeline([2018, 2019])

    def test_http_error_raises_timeline_error_without_api_key(self, mock_build):
        for status, reasons in [(400, ["badRequest"]), (403, ["forbidden"]), (404, []), (500, [])]:
            with self.subTest(status=status):
                self.set_response(mock_build, ["2018年"], error=make_http_error(status, reasons))

                with self.assertRaises(TimelineError) as cm:
                    get_timeline([2018])

                message = str(cm.exception)
                self.assertIn(f"HTTP {status}", message)
                for reason in reasons:
                    self.assertIn(reason, message)
                self.assertNotIn("dummy-key", message)
                # トレースバックにAPIキーを含むURLが出力されないよう、例外を連鎖させない
                self.assertIsNone(cm.exception.__cause__)
                self.assertTrue(cm.exception.__suppress_context__)

    def test_http_error_on_get(self, mock_build):
        self.get_spreadsheets(mock_build).get.return_value.execute.side_effect = make_http_error(404)

        with self.assertRaisesMessage(TimelineError, "HTTP 404"):
            get_timeline([2018])
        self.get_spreadsheets(mock_build).values.return_value.batchGet.assert_not_called()

    def test_network_error_raises_timeline_error(self, mock_build):
        error = socket.timeout("timed out")
        self.set_response(mock_build, ["2018年"], error=error)

        with self.assertRaises(TimelineError) as cm:
            get_timeline([2018])

        # 調査しやすいよう、元の例外のクラス名をメッセージに含める
        self.assertIn(type(error).__name__, str(cm.exception))
        self.assertIsNone(cm.exception.__cause__)
        self.assertTrue(cm.exception.__suppress_context__)

    def test_missing_settings_raises_error_without_calling_api(self, mock_build):
        for setting in ["GOOGLE_SHEETS_API_KEY", "GOOGLE_SHEETS_SPREADSHEET_ID"]:
            with self.subTest(setting=setting), patch(f"subekashi.lib.timeline.{setting}", ""):
                with self.assertRaisesMessage(TimelineError, "設定されていません"):
                    get_timeline([2018])
        mock_build.assert_not_called()
