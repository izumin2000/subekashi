
from recruit.models import Users
from rest_framework import viewsets
from .serializer import UsersSerializer
import json
from django.http.response import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

class UsersViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.all()
    serializer_class = UsersSerializer

@ensure_csrf_cookie
def signup(request):
    datas = json.loads(request.body)
    requires = set(["user_id", "password"])
    UserDisct = {}
    for k, v in datas.items() :
        requires -= set([k])
        if k != "password" :
            UserDisct[k] = v
    isRequiredOK = not(len(requires))
    isLengthOK = (6 <= datas["user_id"] <= 20) and (8 <= datas["password"] <= 20)
    isPatternOK = datas["password"].isascii()
    if isRequiredOK :
        if len(Users.objects.filter("user_id" == datas["user_id"])) :
            response = {"message" : "Account creation failed", "cause" : "already same user_id is used"}
            status = 400

        elif not(isPatternOK) :
            #TODO 要リファクタリング
            if len(requires) == 2 :
                cause = "required user_id and password"
            else :
                cause = "required " + requires.pop()
            response = {"message" : "Account creation failed", "cause" : cause}
            status = 400
        elif not(isLengthOK) :
            response = {"message" : "Account successfully created", "user" : "pattern(s) don't match"}
            status = 200
        else :
            user_ins = Users.objects.create()
            user_ins.user_id = datas["user_id"]
            user_ins.password = datas["password"]
            user_ins.save()
            response = {"message" : "Account successfully created", "user" : UserDisct}
            status = 200

    return JsonResponse(response, status = status)

@ensure_csrf_cookie
def close(request) :
    return JsonResponse({"message":"hoge"})