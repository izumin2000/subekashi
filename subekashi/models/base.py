class GetOrNoneMixin:
    @classmethod
    def get_or_none(cls, pk):
        try:
            return cls.objects.get(pk=pk)
        except cls.DoesNotExist:
            return None
