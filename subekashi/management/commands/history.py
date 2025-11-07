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
    
    
    def parse_table_html_to_2dlist(self, html_text):
        """
        html_text 内の最初の <table> を見つけて 2次元リストに変換して返す。
        <thead> の見出しを最初の行に、続けて tbody の各行を配列として返す。
        table が見つからなければ None を返す。

        修正点:
        - <br> を改行に変換してセル内改行を保持する
        - HTML エンティティ (&amp;, &#x1234; など) をデコードする
        - もし入力が JSON 文字列で中に "\\uXXXX" のようなエスケープが残っている場合は
        可能な限りデコードして元のユニコード文字列に戻す
        - 出力は Python の文字列（Unicode）として返す。JSON にシリアライズする際は
        json.dumps(rows, ensure_ascii=False) を使ってください（外部での扱いについての注意）
        """
        if not html_text or not isinstance(html_text, str):
            return None

        # JSONっぽければ試す（内部に \\uXXXX の生文字列がある場合は後でデコードする）
        html_text_stripped = html_text.strip()
        if html_text_stripped.startswith('[') or html_text_stripped.startswith('{'):
            try:
                parsed = json.loads(html_text_stripped)
                if isinstance(parsed, list):
                    # parsed 内の文字列に生のエスケープシーケンスがあればデコードして返す
                    def _decode_possible_escapes(obj):
                        if isinstance(obj, str):
                            s = obj
                            # HTML エンティティをデコード
                            s = html.unescape(s)
                            # 生の "\uXXXX" 等を含む場合は unicode_escape でデコードを試みる
                            if re.search(r'\\u[0-9a-fA-F]{4}', s) or re.search(r'\\x[0-9a-fA-F]{2}', s):
                                try:
                                    s = s.encode('utf-8').decode('unicode_escape')
                                except Exception:
                                    # 失敗しても元の文字列を使う
                                    pass
                            return s
                        if isinstance(obj, list):
                            return [_decode_possible_escapes(v) for v in obj]
                        if isinstance(obj, dict):
                            return {k: _decode_possible_escapes(v) for k, v in obj.items()}
                        return obj
                    return _decode_possible_escapes(parsed)
            except Exception:
                pass

        soup = BeautifulSoup(html_text, "html.parser")

        # 優先: div.change_table_wrapper 内の table を探す
        wrapper = soup.find("div", class_="change_table_wrapper")
        table = None
        if wrapper:
            table = wrapper.find("table")
        if not table:
            # とりあえずページ内の最初の table を使う
            table = soup.find("table")
        if not table:
            return None

        rows = []

        # helper: セル内のテキストをきれいに取得する
        def _clean_cell_text(cell):
            # <br> を改行文字に置き換える（BeautifulSoup の get_text では <br> が無視されることがあるため）
            for br in cell.find_all("br"):
                br.replace_with("\n")
            text = cell.get_text(separator="\n")
            # HTML エンティティをデコード
            text = html.unescape(text)
            # 標準的な改行を統一
            text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            # もし生の "\uXXXX" のようなシーケンスが残っていたら試しにデコード
            if re.search(r'\\u[0-9a-fA-F]{4}', text) or re.search(r'\\x[0-9a-fA-F]{2}', text):
                try:
                    text = text.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
            return text

        # thead の見出し
        thead = table.find("thead")
        if thead:
            ths = thead.find_all("th")
            if ths:
                header = [_clean_cell_text(th) for th in ths]
                rows.append(header)

        # tbody 行
        tbody = table.find("tbody")
        if tbody:
            tr_list = tbody.find_all("tr")
        else:
            # tbody 無くても tr を拾う
            tr_list = table.find_all("tr")
            # もし thead でヘッダー取れているなら、thead行は重複しないように除外する
            if thead:
                tr_list = [tr for tr in tr_list if not tr.find_parent("thead")]

        for tr in tr_list:
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue
            row = [_clean_cell_text(td) for td in tds]
            rows.append(row)

        if not rows:
            return None

        return rows

    
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


    def handle(self, *args, **options):
        histories = []
        for history in History.objects.exclude(history_type = "delete").exclude(changes = "").iterator():
            fixed_changes = self.fix_lyrics_row(history.changes)
            if fixed_changes != history.changes:
                history.changes = fixed_changes
                histories.append(history)
                
        
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
                
        self.stdout.write("Done.")