from django.core.management.base import BaseCommand
from subekashi.models import History
from bs4 import BeautifulSoup
from django.db import transaction
import json
import re
import html
import json


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
        p_joined = "".join(p_texts)

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
            lyrics_texts_br = "<br>".join(lyrics_texts)
            add_text = f"<br>{lyrics_texts_br}<br>{p_joined}"
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
    
    
    def parse_table_html_to_2dlist(self, html_text):
        html_text = html_text.replace("<br>", "\n").replace("<br/>", "\n")
        soup = BeautifulSoup(html_text, "html.parser")
        
        table = soup.find("table")
        if table is None:
            return None
        
        result = []
        
        # thead
        thead = table.find("thead")
        if thead:
            header_row = []
            for th in thead.find_all("th"):
                text = th.get_text(strip=True)
                header_row.append(text)
            result.append(header_row)
        
        # tbody
        tbody = table.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                row = []
                for td in tr.find_all("td"):
                    text = td.get_text(strip=True)
                    row.append(text)
                result.append(row)
        
        return result


    
    def parse_changes(self, html_text):
        """
        old_pattern / new_pattern を識別して ['理由', 内容] のリストを返す
        """
        soup = BeautifulSoup(html_text, "html.parser")

        # old_pattern: <p><strong>理由</strong>: ～～</p>
        strong_tag = soup.find("strong")
        if strong_tag and strong_tag.get_text(strip=True) == "理由":
            text = strong_tag.parent.get_text(strip=True)
            reason = text.split(":", 1)[-1].strip() if ":" in text else ""
            return ["理由", reason]

        # new_pattern: <h2>◯◯が削除申請されました</h2><b>理由</b>: ～～
        b_tag = soup.find("b")
        if b_tag and b_tag.get_text(strip=True) == "理由":
            # <b>理由</b>: の後ろのテキストを取得
            reason_text = b_tag.next_sibling
            reason = reason_text.strip() if isinstance(reason_text, str) else ""
            return ["理由", reason]

        return None

    
    def extract_urls(self, data):
        result = []
        for row in data:
            # 1列目が "URL" の行を処理
            if row[0] == "URL":
                new_row = ["URL"]
                for cell in row[1:]:
                    m = re.match(r'\[([^\]]*)\]', cell)
                    new_row.append(m.group(1) if m else cell)
                result.append(new_row)
            else:
                # それ以外の行はそのまま
                result.append(row)
        return result


    def handle(self, *args, **options):
        histories = []
        for history in History.objects.exclude(history_type = "delete").exclude(changes = "").iterator():
            fixed_changes = self.fix_lyrics_row(history.changes)
            if fixed_changes != history.changes:
                history.changes = fixed_changes
                histories.append(history)
                
        History.objects.bulk_update(histories, ["changes"])
        
        batch = 5000

        qs = History.objects.exclude(history_type = "delete").exclude(changes = "")
        to_update = []
        for hist in qs.iterator():
            parsed = None
            try:
                parsed = self.parse_table_html_to_2dlist(hist.changes)
            except Exception as e:
                self.stderr.write(f"Error parsing id={hist.id}: {e}")
                parsed = None

            if parsed is not None:
                hist.temp_changes = parsed
                to_update.append(hist)

            # バッチ更新
            if len(to_update) >= batch:
                with transaction.atomic():
                    for h in to_update:
                        h.save(update_fields=["temp_changes"])
                self.stdout.write(f"Saved batch up to id={to_update[-1].id}")
                to_update = []

        # 最後に残りを保存
        if to_update:
            with transaction.atomic():
                for h in to_update:
                    h.save(update_fields=["temp_changes"])
            self.stdout.write(f"Saved final batch up to id={to_update[-1].id}")

        History.objects.bulk_update(histories, ["changes"])
        
        for history in History.objects.filter(history_type = "delete"):
            html = history.changes.strip()
            parsed = self.parse_changes(html)
            if parsed:
                history.temp_changes = parsed
                history.save(update_fields=['temp_changes'])
        
        histories = []
        for history in History.objects.exclude(temp_changes = None):
            fixed_changes = self.extract_urls(history.temp_changes)
            if fixed_changes != history.temp_changes:
                history.temp_changes = fixed_changes
                histories.append(history)
                
        History.objects.bulk_update(histories, ["temp_changes"])
                
        self.stdout.write("Done.")