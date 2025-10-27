from django.core.management.base import BaseCommand
from subekashi.models import History
from bs4 import BeautifulSoup


class Command(BaseCommand):
    def fix_lyrics_row(self, html):
        COLUMNS = ["タイトル", "チャンネル名", "URL", "オリジナル", "削除済み", "ネタ曲", "インスト曲", "すべあな模倣曲", "下書き", "模倣", "歌詞"]
        
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            return html

        rows = table.find_all("tr")
        # find index of the row whose first cell text == "歌詞"
        karaoke_idx = None
        for idx, row in enumerate(rows):
            first_cell = row.find(['td', 'th'])
            if first_cell and first_cell.get_text(strip=True) == "歌詞":
                karaoke_idx = idx
                break
        if karaoke_idx is None:
            return str(soup)  # "歌詞" row not found, return unchanged

        # determine range: from next row until (but not including) a row whose first cell text equals any element of COLUMNS
        start = karaoke_idx + 1
        end = start
        while end < len(rows):
            first = rows[end].find(['td', 'th'])
            first_text = first.get_text(strip=True) if first else ""
            if first_text in COLUMNS:
                break
            end += 1

        # concatenate inner HTML (preserve <br> etc.) of first column cells in [start, end)
        parts = []
        for i in range(start, end):
            first = rows[i].find(['td', 'th'])
            if first:
                parts.append(first.decode_contents())  # preserves tags like <br>

        concat_html = "".join(parts)

        # append to the end of the 3rd cell of the "歌詞" row (create cells if needed)
        lyric_row = rows[karaoke_idx]
        cells = lyric_row.find_all(['td', 'th'])
        # ensure there are at least 3 cells
        while len(cells) < 3:
            new_td = soup.new_tag("td")
            lyric_row.append(new_td)
            cells = lyric_row.find_all(['td', 'th'])

        third_cell = cells[2]
        if concat_html:
            # parse the concat_html fragment and append its contents into the third cell
            frag = BeautifulSoup(concat_html, "html.parser")
            for node in frag.contents:
                third_cell.append(node)

        # remove rows whose first-column text is NOT in COLUMNS (keep rows where first-col is in COLUMNS)
        # (this will keep the "歌詞" row if "歌詞" is in COLUMNS as per requirement)
        for row in table.find_all("tr"):
            first = row.find(['td', 'th'])
            first_text = first.get_text(strip=True) if first else ""
            if first_text not in COLUMNS:
                row.decompose()

        return str(soup)

    
    def handle(self, *args, **options):
        histories = []
        for history in History.objects.iterator():
            fixed_changes = self.fix_lyrics_row(history.changes)
            if fixed_changes != history.changes:
                history.changes = fixed_changes
                histories.append(history)

        History.objects.bulk_update(histories, ["changes"])
