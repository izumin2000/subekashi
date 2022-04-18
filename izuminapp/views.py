from django.shortcuts import render
from izuminapp.forms import FirstviewForm, PlayerForm
from izuminapp.model import Player, Firstview, Singleton, Analyze
import requests
from datetime import date
import json

EMC_API_URL = "https://earthmc-api.herokuapp.com/api/v1"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"
UPLOAD_URL = "uploadfiles/"
NUMBER_OF_FIRSTVIEWS = 5
ERROR_JSON = '{"population":"error","area":"error","king":"error","capitalName":"error","skin":"error"}'


def updateinfo() : 
    inca_info = {}

    # シングルトンインスタンスの生成
    insSingleton, _ = Singleton.objects.get_or_create(name = "nations" , defaults = {"value" : ERROR_JSON})

    # APIの処理
    try :
        nations_get = requests.get(EMC_API_URL + "/nations/Inca_Empire")
    except :      # ProxyErrorなら
        # jsonアーカイブからのアーカイブを読み込み
        inca_info["ableAPI"] = False
        inca_info.update(dict(json.loads(insSingleton.value)))      # 辞書型の結合

    else :      #正常にAPIを取得できたら
        inca_info["ableAPI"] = True
        if nations_get.status_code == 200 :
            # nationデータの取得
            try :
                nations_json = dict(nations_get.json())
            except :
                inca_info["ableAPI"] = False
                inca_info.update(dict(json.loads(insSingleton.value)))      # 辞書型の結合
            else :
                nations_json["population"] = len(nations_json["residents"])     # 人口の取得
                
                inca_info.update(nations_json)      # 辞書型の結合

                # 国民の登録
                online_get = requests.get(EMC_API_URL + "/online")
                for player in nations_json["residents"] :
                    insPlayer, _ = Player.objects.get_or_create(name = player, defaults = {"name" : player})

                    # UUIDの登録
                    if insPlayer.uuid == "" :
                        uuid_get = requests.get(UUID_API_URL + player)
                        if uuid_get.status_code == 200 :
                            try :
                                insPlayer.uuid = dict(uuid_get.json())["id"]
                            except :
                                inca_info["ableAPI"] = False

                    # onlineカラムの切り替え
                    if online_get.status_code == 200 :
                        online_json = online_get.json()
                        online_players = [d.get('name') for d in online_json]
                        if player in online_players :
                            insPlayer.online = True
                        else :
                            insPlayer.online = False
                    insPlayer.save()
            
                # 他の国に移住した国民の登録
                immigrants = set(Player.objects.values_list('name', flat = True))
                immigrants -= set(nations_json["residents"])        # 現在所属している国民は除外
                immigrants -= set(Player.objects.filter(primary = True))       # 大臣を除く
                for immigrant in immigrants :
                    immigrant_player = Player.objects.filter(name = immigrant)[0]
                    immigrant_player.leave = True
                    immigrant_player.rank = "元国民"
                    immigrant_player.save()

                # jsonのアーカイブ
                if insSingleton.value in ["", ERROR_JSON] :
                    insSingleton.value = json.dumps(nations_json)
                    insSingleton.save()

        # jsonアーカイブからのアーカイブを読み込み
        else :      # EMCサーバー側の問題なら
            inca_info["ableAPI"] = False
            inca_info.update(dict(json.loads(insSingleton.value)))      # 辞書型の結合
        
        # PV数のカウント
        today = date.today()
        insAnalyze, _ = Analyze.objects.get_or_create(date = today, defaults = {"date" : today})
        insAnalyze.pv += 1
        insAnalyze.save()

    return inca_info


def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    inca_info = updateinfo()

    # ファーストビューの処理
    insFirstviews = Firstview.objects.filter(display = True).order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]     # ランダムにNUMBER_OF_FIRSTVIEWS個取り出す
    insFirstviews = list(insFirstviews.values())
    inca_info["names"] = [d.get('name') for d in insFirstviews]
    inca_info["clTitle"] = [d.get('title') for d in insFirstviews]
    inca_info["clPlayers"] = [d.get('player') for d in insFirstviews]
    inca_info["primaries"] = Player.objects.filter(primary = True)

    return render(request, 'inca/inca.html', inca_info)

def abroad(request) :
    return render(request, 'inca/abroad.html')


def firstview(request) :
    result = {}

    if request.method == 'POST':
        name = request.POST.get("name")       # form.pyにおいてid冒頭のid_はidに含まない
        title = request.POST.get("title")
        player = request.POST.get("player")
        displayon = request.POST.get("displayon")
        displayoff = request.POST.get("displayoff")
        delete = request.POST.get("delete")
        password = request.POST.get("password")
        print(type(name), type(title), type(player), type(displayon), type(displayoff), type(delete))
        if password == "incagold" :
            filename = name.replace("firstview/", "").replace(".png", "")
            name = "firstview/" + filename + ".png"
            insFirstview, created = Firstview.objects.get_or_create(name = name, defaults = {"name" : name})
            if delete :        # 削除する場合は
                if not created :        #   Firstviewレコードが新規作成された場合は
                    deleted_path = insFirstview.name
                    insFirstview.delete()
                    result["title"] = deleted_path + "を削除しました"
            else :
                if title != "" :
                    insFirstview.title = title
                if player != "" :
                    insFirstview.player = player
                if displayon :
                    insFirstview.display = True
                if displayoff :
                    insFirstview.display = False
                insFirstview.save()

                result["title"] = filename + "をアップロードしました"
                    
        else :
            result["title"] = "パスワードが違います"
    
    result["images"] = Firstview.objects.all()

    form = FirstviewForm()
    result["form"] = form
    return render(request, 'inca/firstview.html', result)


def editplayer(request) :
    result = {}

    name = request.POST.get("name")
    rank = request.POST.get("rank")
    primary = request.POST.get("primary")
    crime = request.POST.get("crime")
    info = request.POST.get("info")
    password = request.POST.get("password")
    if password == "incagold" :
        insPlayer, _ = Player.objects.get_or_create(name = name, defaults = {"name" : name})
        if rank != "" :
            insPlayer.rank = rank
        insPlayer.primary = bool(primary)
        insPlayer.crime = bool(crime)
        insPlayer.info = info
        insPlayer.save()
        result["title"] = name + "の情報が変更されました"
    else :
        result["title"] = "パスワードが違います"

    form = PlayerForm()
    result["form"] = form
    result["players"] = Player.objects.all()
    return render(request, 'inca/editplayer.html', result)

def pv(request) :
    pv = Analyze.objects.values_list("pv", flat=True)
    pv = list(pv)
    allpv = sum(pv)
    axisxlist = list(range(len(pv)))

    result = {"pv" : pv, "allpv" : allpv, "axisxlist" : axisxlist}
    print(result)
    return render(request, 'inca/pv.html', result)