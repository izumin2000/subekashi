from django.core.management.base import BaseCommand
from django.utils import timezone
from subekashi.models import Editor, History, Song 
from subekashi.lib.old_security import decrypt as old_dec
from subekashi.lib.security import encrypt as new_enc
from subekashi.lib.changes import md2changes
import json
import re
from datetime import datetime
from django.db import transaction


class Command(BaseCommand):
    help = "Import history data from new.json"

    def handle(self, *args, **options):
        old_editor_id = Editor.objects.all().count()
        historys = History.objects.all()
        for history in historys:
            changes = history.changes
            if changes:
                changes = "\n".join(changes.split("\n")[1:])
                changes = changes.replace("---:", "----").replace(":---", "----")
                history.changes = md2changes(changes)
            
            editor = history.editor
            new_ip = new_enc(old_dec(editor.ip))
            editor, is_created = Editor.objects.get_or_create(ip = new_ip)
            if is_created:
                editor.save()
            
            history.editor = editor
            history.save()
        
        Editor.objects.filter(id__lte=old_editor_id).delete()


        try:
            with open("./.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            for msg in data.get("messages", []):
                content = msg.get("content", "")
                
                if ":arrow_down:" in content:
                    break

                try:
                    with transaction.atomic():
                        if ("localhost:8000" in content) or ("izuminapp" in content):
                            continue

                        # ===== create_time =====
                        try:
                            if "==============================" in content:
                                create_time_str = re.search(r'==============================(.*?)==============================', content).group(1)
                                dt = datetime.strptime(create_time_str, "%Y年%m月%d日%H時%M分%S秒")
                            else:
                                create_time_str = msg['timestamp'][:19]
                                dt = datetime.strptime(create_time_str, "%Y-%m-%dT%H:%M:%S")
                            create_time = timezone.make_aware(dt, timezone.get_current_timezone())
                        except Exception as e:
                            raise ValueError(f"create_time: {e}")

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

                        # ===== history_type =====
                        if "新規作成されました" in content:
                            history_type = "new"
                        elif "編集されました" in content:
                            history_type = "edit"
                        else:
                            history_type = ""

                        # ===== title =====
                        try:
                            if content[81:83] == "**":
                                title = re.search(r'\*\*(.*?)\*\*\n', content).group(1)
                            elif "タイトル：" in content:
                                title = re.search(r'タイトル：(.*?)\n', content).group(1)
                            else:
                                raise ValueError(f"none")

                            if history_type == "new":
                                title_type = "新規追加"
                            elif history_type == "edit":
                                title_type = "編集"
                            else:
                                title_type = "新規追加か編集"
                                
                            title = f"{title}を{title_type}"
                        except Exception as e:
                            raise ValueError(f"title: {e}")

                        # ===== editor =====
                        try:
                            if "IP :" in content:
                                ip_enc = re.search(r'IP : (.*)"?\n?', content).group(1).replace("```", "")
                                ip = old_dec(ip_enc)
                                enc_ip = new_enc(ip)
                                editor, _ = Editor.objects.get_or_create(ip=enc_ip)
                            else:
                                editor, _ = Editor.objects.get_or_create(ip=new_enc("127.0.0.1"))
                        except Exception as e:
                            raise ValueError(f"editor: {e}")

                        # ===== 保存 =====
                        History.objects.create(
                            create_time=create_time,
                            song=song,
                            history_type=history_type,
                            title=title,
                            editor=editor
                        )

                except Exception as e:
                    print(f"{e}\n{msg['timestamp']}\n")

        except Exception as e:
            print(f"全体処理エラー: {e}")
            
        History.objects.filter(history_type="edit", changes="").delete()