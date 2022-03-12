from django.shortcuts import render
from izuminapp.settings import BASE_DIR, DEBUG
from izuminapp.forms import FirstviewForm, PlayerForm
from izuminapp.model import Player, Firstview, Singleton, Analyze
import requests
import datetime
import json

EMC_API_URL = "https://earthmc-api.herokuapp.com/api/v1"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"
UPLOAD_URL = "uploadfiles/"
NUMBER_OF_FIRSTVIEWS = 5
ERROR_JSON = '{"population":"error","area":"error","king":"error","capitalName":"error","skin":"error"}'
PRIMARIES = {"Ryo5Syo5":"国王", "RyoK3":"財務大臣", "KANATA2000":"メディア大臣", "sakira1996":"外交大臣 副国王", "hiroshi4872":"国土交通大臣", "ramuate":"法務大臣"}


def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    inca_info = {}

    # シングルトンインスタンスの生成
    insSingleton, _ = Singleton.objects.get_or_create(name = "nations" , defaults = {"value" : ERROR_JSON})

    # ファーストビューの処理
    insFirstviews = Firstview.objects.filter(display = True).order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]     # ランダムにNUMBER_OF_FIRSTVIEWS個取り出す
    insFirstviews = list(insFirstviews.values())
    inca_info["names"] = [d.get('name') for d in insFirstviews]
    inca_info["clTitle"] = [d.get('title') for d in insFirstviews]
    inca_info["clPlayers"] = [d.get('player') for d in insFirstviews]

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
                    if player in PRIMARIES.keys() :      # 大臣なら
                        insPlayer.primary = True
                        insPlayer.rank = PRIMARIES[player]
                    else :
                        insPlayer.primary = False
                        insPlayer.rank = "国民"

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
                immigrants = set(Player.objects.values_list('name', flat = True)) - set(nations_json["residents"])
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

    inca_info["primaries"] = Player.objects.filter(primary = True)
    return render(request, 'inca/inca.html', inca_info)


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
    form = PlayerForm()
    result["form"] = form
    result["players"] = Player.objects.all()
    return render(request, 'inca/editplayer.html', result)