from config.settings import BASE_DIR
from django.core.management.base import BaseCommand
from django.core import management
import os

class Command(BaseCommand):
    help = "定数ファイルの生成。すでにあるファイルは上書きしない。"
    
    def handle(self, *args, **options) :
        CONST_INFO = {
            'ai.py': 'SEND_DISCORD_AI_RESULT = True',
            'ban.py': 'BAN_LIST = []',
            'gpt.txt': '',
            'word.json': '[]',
            'version.json': '{\n\t"VERSION": "dev"\n}',
            'reject.py': 'REJECT_LIST = []',
            'maintenance.json': '{\n\t"IS_MAINTENANCE": false,\n\t"MAINTENANCE_MESSAGE": "<p>メンテナンス中です</p>"\n}',
        }
        for file_name, text in CONST_INFO.items():
            const_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic', file_name)
            if os.path.exists(const_path):
                continue
            
            file = open(const_path, 'w', encoding='utf-8')
            file.write(text)
            file.close()
            self.stdout.write(self.style.SUCCESS(f"ファイル{file_name}を作成しました。"))
        
        management.call_command("sitemap")