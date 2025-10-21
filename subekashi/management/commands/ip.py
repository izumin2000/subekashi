from django.core.management.base import BaseCommand
from subekashi.models import Editor
from subekashi.lib.security import decrypt


class Command(BaseCommand) :
    def handle(self, *args, **options):
        id = options['id']
        print(decrypt(Editor.objects.get(pk = id).ip))
        
    def add_arguments(self, parser):
        parser.add_argument('-id', type=int, help='editor_id')

