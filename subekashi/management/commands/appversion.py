from config.settings import BASE_DIR
from django.core.management.base import BaseCommand
from datetime import date
from subekashi.constants.constants import *
import subprocess
import os
import json


class Command(BaseCommand):
    help = "最終更新日のアップデート"

    def handle(self, *args, **options) :
        today = date.today().strftime("%Y-%m-%d")
        v = options['v']
        commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'main']).strip().decode('utf8')
        sub_version = v if v else commit_count
        version = f"{today}(ver.{sub_version})"
        version_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/version.json')
        if os.path.exists(version_path):
            file = open(version_path, 'w', encoding='utf-8')
            json.dump({"VERSION": version}, file, indent=4)
            file.close()
            massage = f"バージョン：{version}"
            self.stdout.write(self.style.SUCCESS(massage))
        else :
            massage = CONST_ERROR
            self.stdout.write(self.style.ERROR(massage))
        return
    
    def add_arguments(self, parser):
        parser.add_argument('--v', required=False, type=str)