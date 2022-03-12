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
    newNation, _ = Singleton.objects.get_or_create(name = "nations" , defaults = {"value" : ERROR_JSON})

    # ファーストビューの処理
    firstviews = Firstview.objects.order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]     # ランダムにNUMBER_OF_FIRSTVIEWS個取り出す
    firstviews = list(firstviews.values())
    inca_info["images"] = [d.get('image') for d in firstviews]
    inca_info["clTitle"] = [d.get('title') for d in firstviews]
    inca_info["clPlayers"] = [d.get('player') for d in firstviews]

    # APIの処理
    try :
        nations_get = requests.get(EMC_API_URL + "/nations/Inca_Empire")
    except :      # ProxyErrorなら
        # jsonアーカイブからのアーカイブを読み込み
        inca_info["ableAPI"] = False
        inca_info.update(dict(json.loads(newNation.value)))      # 辞書型の結合

    else :      #正常にAPIを取得できたら
        inca_info["ableAPI"] = True
        if nations_get.status_code == 200 :
            # nationデータの取得
            try :
                nations_json = dict(nations_get.json())
            except :
                inca_info["ableAPI"] = False
                inca_info.update(dict(json.loads(newNation.value)))      # 辞書型の結合
            else :
                nations_json["population"] = len(nations_json["residents"])     # 人口の取得
                
                inca_info.update(nations_json)      # 辞書型の結合

                # 国民の登録
                online_get = requests.get(EMC_API_URL + "/online")
                for player in nations_json["residents"] :
                    newPlayer, _ = Player.objects.get_or_create(name = player, defaults = {"name" : player})
                    if player in PRIMARIES.keys() :      # 大臣なら
                        newPlayer.primary = True
                        newPlayer.rank = PRIMARIES[player]
                    else :
                        newPlayer.primary = False
                        newPlayer.rank = "国民"

                    # UUIDの登録
                    if newPlayer.uuid == "" :
                        uuid_get = requests.get(UUID_API_URL + player)
                        if uuid_get.status_code == 200 :
                            try :
                                newPlayer.uuid = dict(uuid_get.json())["id"]
                            except :
                                inca_info["ableAPI"] = False

                    # onlineカラムの切り替え
                    if online_get.status_code == 200 :
                        online_json = online_get.json()
                        online_players = [d.get('name') for d in online_json]
                        if player in online_players :
                            newPlayer.online = True
                        else :
                            newPlayer.online = False
                    newPlayer.save()
            
                # 他の国に移住した国民の登録
                immigrants = set(Player.objects.values_list('name', flat = True)) - set(nations_json["residents"])
                for immigrant in immigrants :
                    immigrant_player = Player.objects.filter(name = immigrant)[0]
                    immigrant_player.leave = True
                    immigrant_player.save()

                # jsonのアーカイブ
                if newNation.value in ["", ERROR_JSON] :
                    newNation.value = json.dumps(nations_json)
                    newNation.save()

        # jsonアーカイブからのアーカイブを読み込み
        else :      # EMCサーバー側の問題なら
            inca_info["ableAPI"] = False
            inca_info.update(dict(json.loads(newNation.value)))      # 辞書型の結合

    inca_info["primaries"] = Player.objects.filter(primary = True)
    return render(request, 'inca/inca.html', inca_info)


def firstview(request) :
    result = {}

    if request.method == 'POST':
        newimage = request.POST["image"]
        newtitle = request.POST["title"]
        newPlayer = request.POST["player"]
        newimage = "firstview/" + newimage + ".png"
        insFirstview, _ = Firstview.objects.get_or_create(image = newimage, defaults = {"image" : newimage})
        insFirstview.title = newtitle
        insFirstview.player = newPlayer
        insFirstview.save()
        result["title"] = newtitle + "をアップロードしました"
    
    result["images"] = Firstview.objects.all()

    form = FirstviewForm()
    result["form"] = form
    return render(request, 'inca/firstview.html', result)

def firstviewdelete(request, imageid) :
    Firstview.objects.filter(pk = imageid).delete()

    result = {}
    result["images"] = Firstview.objects.all()
    form = FirstviewForm()
    result["form"] = form

    return render(request, 'inca/firstview.html', result)