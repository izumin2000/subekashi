from django.utils import timezone
from django.db import models


# すべかしへの問い合わせとその回答の情報
class Contact(models.Model):
    detail = models.TextField(max_length = 10000)
    post_time = models.DateField()
    answer = models.TextField(blank = True, null = True, max_length = 10000)

    def __str__(self):
        return self.detail[:30]

    @classmethod
    def get_answered(cls):
        return cls.objects.filter(answer__isnull=False).order_by("-id")
    
    @classmethod
    def create_contact(detail):
        return Contact.objects.create(
            detail=detail,
            post_time=timezone.localdate(),
        )