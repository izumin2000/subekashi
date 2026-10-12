"""
changes テンプレートタグのテスト

render_changes(): 編集の変更履歴のみ、編集前と編集後の差分をJS（editor.js）で表示する
diff-tableクラスが付くことを検証する（#608）。
"""
from django.test import TestCase

from subekashi.models import Editor, History, Song
from subekashi.templatetags.changes import render_changes


class RenderChangesTest(TestCase):
    """render_changes() のテスト"""

    def setUp(self):
        self.editor = Editor.objects.create(ip="127.0.0.10")
        self.song = Song.objects.create(title="変更履歴テスト曲")

    def create_history(self, history_type, changes):
        return History.create_for_song(
            song=self.song, title="変更履歴", history_type=history_type, changes=changes, editor=self.editor,
        )

    def test_edit_changes_has_diff_table(self):
        history = self.create_history("edit", [["種類", "編集前", "編集後"], ["タイトル", "旧タイトル", "新タイトル"]])
        result = render_changes(history)
        self.assertIn('<table class="diff-table">', result)
        self.assertIn("<td>旧タイトル</td>", result)
        self.assertIn("<td>新タイトル</td>", result)

    def test_old_edit_changes_saved_as_new_has_diff_table(self):
        # 2026/4/11以前は編集もhistory_type="new"で保存されていたため、changesの見出しで判定する
        history = self.create_history("new", [["種類", "編集前", "編集後"], ["タイトル", "旧タイトル", "新タイトル"]])
        self.assertIn('<table class="diff-table">', render_changes(history))

    def test_new_changes_has_no_diff_table(self):
        history = self.create_history("new", [["種類", "内容"], ["タイトル", "新規曲"]])
        result = render_changes(history)
        self.assertIn("<table>", result)
        self.assertNotIn("diff-table", result)

    def test_delete_changes_has_no_diff_table(self):
        history = self.create_history("delete", ["理由", "削除理由"])
        result = render_changes(history)
        self.assertIn('<table class="delete-table">', result)
        self.assertNotIn("diff-table", result)

    def test_no_changes_renders_nothing(self):
        history = self.create_history("edit", None)
        self.assertNotIn("<table", render_changes(history))

    def test_edit_cell_is_escaped_with_linebreaks(self):
        # JSはセルのテキストと<br>から編集前と編集後の文字列を取り出すため、改行は<br>・HTMLはエスケープして出力する
        history = self.create_history("edit", [["種類", "編集前", "編集後"], ["歌詞", "<b>1行目\n2行目", "1行目\r\n2行目"]])
        result = render_changes(history)
        self.assertIn("<td>&lt;b&gt;1行目<br>2行目</td>", result)
        self.assertIn("<td>1行目<br>2行目</td>", result)
        self.assertNotIn("<b>", result)
