from django.core.management.base import BaseCommand
from django.utils import timezone
from subekashi.models import Editor, History, Song 
from subekashi.lib.security import encrypt, decrypt
import json
import re
from datetime import datetime
from django.db import transaction


class Command(BaseCommand):
    help = "Import history data from new.json"

    def handle(self, *args, **options):
        try:
            with open("./.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            for msg in data.get("messages", []):
                content = msg.get("content", "")

                try:
                    with transaction.atomic():
                        if ("localhost:8000" in content) or ("izuminapp" in content):
                            continue

                        # ===== edited_time =====
                        try:
                            if "==============================" in content:
                                edited_time_str = re.search(r'==============================(.*?)==============================', content).group(1)
                                dt = datetime.strptime(edited_time_str, "%Y年%m月%d日%H時%M分%S秒")
                            else:
                                edited_time_str = msg['timestamp'][:19]
                                dt = datetime.strptime(edited_time_str, "%Y-%m-%dT%H:%M:%S")
                            edited_time = timezone.make_aware(dt, timezone.get_current_timezone())
                        except Exception as e:
                            raise ValueError(f"edited_time: {e}")

                        # ===== song =====
                        try:
                            if "lyrics.imicomweb.com" in content:
                                song_id = re.search(r'https://lyrics.imicomweb.com/songs?/(.*?)\n', content).group(1)
                            elif "id : " in content:
                                song_id = re.search(r'id : (.*?)\n', content).group(1)
                            else:
                                raise ValueError(f"id none")
                            
                            song = Song.objects.filter(id=song_id).first()
                        except Exception as e:
                            raise ValueError(f"song: {e}")

                        # ===== edit_type =====
                        if "新規作成されました" in content:
                            edit_type = "new"
                        elif "編集されました" in content:
                            edit_type = "edit"
                        else:
                            edit_type = ""

                        # ===== title =====
                        try:
                            if content[81:83] == "**":
                                title = re.search(r'\*\*(.*?)\*\*\n', content).group(1)
                            elif "タイトル：" in content:
                                title = re.search(r'タイトル：(.*?)\n', content).group(1)
                            else:
                                raise ValueError(f"none")

                            if edit_type == "new":
                                title_type = "新規追加しました"
                            elif edit_type == "edit":
                                title_type = "編集しました"
                            else:
                                title_type = "新規追加か編集しました"
                                
                            title = f"{title}を{title_type}"
                        except Exception as e:
                            raise ValueError(f"title: {e}")

                        # ===== editor =====
                        try:
                            if "IP :" in content:
                                ip_enc = re.search(r'IP : (.*)"?\n?', content).group(1).replace("```", "")
                                ip = decrypt(ip_enc)
                                enc_ip = encrypt(ip)
                                editor, _ = Editor.objects.get_or_create(ip=enc_ip)
                            else:
                                editor, _ = Editor.objects.get_or_create(ip=encrypt("127.0.0.1"))
                        except Exception as e:
                            raise ValueError(f"editor: {e}")

                        # ===== 保存 =====
                        History.objects.create(
                            edited_time=edited_time,
                            song=song,
                            edit_type=edit_type,
                            title=title,
                            editor=editor
                        )

                except Exception as e:
                    print(f"{e}\n{msg['timestamp']}\n")

        except Exception as e:
            print(f"全体処理エラー: {e}")