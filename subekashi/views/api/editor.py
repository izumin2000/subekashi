# editors/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from subekashi.models import Editor
from subekashi.serializer import IsOpenSerializer
from subekashi.lib.security import SYMBOLS


class EditorIsOpenView(APIView):
    """PUT -> {'ip': '1.2.3.4'} を受け取り encrypt(ip) をキーに DB 検索する"""

    def _validate_ip(self, ip_str):
        # 長さチェック
        if not (20 <= len(ip_str) <= 100):
            return False

        # 使用文字チェック
        if not all(ch in SYMBOLS for ch in ip_str):
            return False

        return True

    def put(self, request, *args, **kwargs):
        serializer = IsOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = serializer.validated_data.get('ip')
        if not self._validate_ip(ip):
            return Response({'detail': 'IPアドレスの形式がおかしいです。'}, status=status.HTTP_400_BAD_REQUEST)

        is_open = serializer.validated_data.get('is_open')
        if is_open is None:
            return Response({'detail': 'is_openキーが必要です。'}, status=status.HTTP_400_BAD_REQUEST)

        editor = get_object_or_404(Editor, ip=ip)
        editor.is_open = is_open
        editor.save()

        return Response({'is_open': bool(editor.is_open)}, status=status.HTTP_200_OK)