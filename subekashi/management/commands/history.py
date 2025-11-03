from django.core.management.base import BaseCommand
from subekashi.models import History
from bs4 import BeautifulSoup


class Command(BaseCommand):
    def fix_lyrics_row(self, html):
        COLUMNS = ["タイトル", "チャンネル名", "URL", "オリジナル", "削除済み", "ネタ曲", "インスト曲", "すべあな模倣曲", "下書き", "模倣", "歌詞"]

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr")

        # 後ろの<p>を処理
        p_texts = []
        for p in soup.find_all("p"):
            txt = p.get_text().replace("\n", "<br>").rstrip("|")
            p_texts.append(txt)
        p_joined = "<br>".join(p_texts)

        # "歌詞"行とCOLUMNSに基づく処理
        new_rows = []
        collecting = False
        lyrics_texts = []
        lyrics_target = None

        for i, tr in enumerate(rows):
            tds = tr.find_all("td")
            if not tds:
                continue
            first = tds[0].get_text(strip=True)
            if first == "歌詞":
                collecting = True
                lyrics_target = tds[2]
                new_rows.append(tr)
                continue
            if collecting:
                if first in COLUMNS and first != "歌詞":
                    collecting = False
                else:
                    # 歌詞の次から対象範囲の文字を収集
                    lyrics_texts.append(tds[0].decode_contents())
                    continue
            # COLUMNSに含まれる行のみ残す
            if first in COLUMNS:
                new_rows.append(tr)

        # 収集した文字と<p>の文字を結合
        if lyrics_target:
            add_text = "<br>".join(lyrics_texts + [p_joined])
            lyrics_target.append(BeautifulSoup(add_text, "html.parser"))

        # テーブルのtbodyを置き換え
        tbody = table.find("tbody")
        tbody.clear()
        for r in new_rows:
            tbody.append(r)
            
        for tag in soup.find_all('div'):
            for element in list(tag.next_siblings):
                element.extract()

        return str(soup)

    def handle(self, *args, **options):
        histories = []
        for history in History.objects.iterator():
            fixed_changes = self.fix_lyrics_row(history.changes)
            if fixed_changes != history.changes:
                history.changes = fixed_changes
                histories.append(history)

        History.objects.bulk_update(histories, ["changes"])
