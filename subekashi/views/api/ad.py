from subekashi.models import Ad
from rest_framework import viewsets, serializers
from ...serializer import AdSerializer


class AdAPI(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    
    def create(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドCREATEは受け付けていません")
    
    def update(self, request, *args, **kwargs):
        if set(request.data.keys()) - {'view', 'click'}:
            raise serializers.ValidationError("フィールドviewとフィールドclick以外の変更は受け付けていません")
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドDELETEは受け付けていません")