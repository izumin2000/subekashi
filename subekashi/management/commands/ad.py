from django.core.management.base import BaseCommand
from subekashi.models import Ad

class Command(BaseCommand):
    def handle(self, *args, **options):
        ac = options['ac'] if options['ac'] else []
        for ad_id in ac:
            try:
                ad = Ad.objects.get(id=ad_id)
                ad.status = "pass"
                ad.save()
                self.stdout.write(self.style.SUCCESS(f"Successfully updated status of Ad with ID {ad_id}"))
            except Ad.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Ad with ID {ad_id} does not exist"))

        wa = options['wa'] if options['wa'] else []
        for ad_id in wa:
            try:
                ad = Ad.objects.get(id=ad_id)
                ad.status = "fail"
                ad.save()
                self.stdout.write(self.style.SUCCESS(f"Successfully updated status of Ad with ID {ad_id}"))
            except Ad.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Ad with ID {ad_id} does not exist"))
                
    def add_arguments(self, parser):
        parser.add_argument('-ac', nargs='+', type=int, help='List of ac')
        parser.add_argument('-wa', nargs='+', type=int, help='List of wa')
