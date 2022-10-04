from django.http import HttpResponse
from django.shortcuts import redirect, render
from xia.forms import PlayerForm, MinisterForm
from xia.model import Player, Minister, Criminal, Gold, Tour, Nation, Analyze
import requests
from datetime import date
import json
from time import sleep
from datetime import datetime
import hashlib


OUR_NATION = "Xia"
EMC_API_URL = "https://emc-toolkit.vercel.app/api/aurora/"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"

# デバッグ用
ERROR_API_URL = "https://error"
# EMC_API_URL = ERROR_API_URL     # コメントアウトを外すとEMC APIを取得

# ダミー用の辞書
dummy_dict = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10, 11:11, 12:12}

# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
# if hashlib.sha256(mypassword.encode()).hexdigest() == SHA256a :

# 成功時にAPIのjsonを出力。失敗すると空文字を出力。
def get_API(url, route) :
    if url == EMC_API_URL :
        sleep(1)

    try :
        get = requests.get(url + route)
    except :        # プロキシエラー等のエラーが発生したら
        print("5xx Error", route)
        return ""

    if (get.status_code == 200) :
        try :
            get_dict = get.json()
        except :        # JSON形式ではなかったら（メンテナンス等）
            print("Not JSON Error", get.status_code, route)
            return ""

        if "error" in get_dict :     # dictのキーにerrorがあったら
            print("Invalid path Error", get.status_code,  route)
            return ""
        
        if "message" in get_dict :     # dictのキーにerrorがあったら
            print("404 on json API", get.status_code,  route)
            
        else :      # 正常に取得できたら
            print("OK", get.status_code, route)
            return get_dict

    else :      # エラーステータスコードを受け取ったら（HEROKU error等）
        print("not 2xx", get.status_code, route)
        return ""


# Player DB上にplayerが存在するか確認
def isExistDBPlayer(nation) :
    ins_players = Player.objects.filter(name = nation)
    if ins_players :
        return ins_players.first()
    return None


# Nation DB上にnationが存在するか確認
def isExistDBNation(nation) :
    ins_nations = Nation.objects.filter(name = nation)
    if ins_nations :
        return ins_nations.first()
    return None


# 国の情報を更新しDBに登録
def set_nation(nation): 
    nation_dict = get_API(EMC_API_URL, "nations/" + nation)     # 国のデータを取得
    # 国のデータの登録
    if nation_dict :
        ins_nation, _ = Nation.objects.get_or_create(name = nation, defaults = {"name" : nation})

        ins_nation.population = len(nation_dict["residents"])
        ins_nation.area = nation_dict["area"]
        ins_nation.capital = nation_dict["capitalName"]
        ins_nation.x = nation_dict["capitalX"]
        ins_nation.z = nation_dict["capitalZ"]
        ins_nation.king = nation_dict["king"]
        ins_nation.save()

        ableAPI = True
    else :      # 今までにAPIの取得に失敗していたら
        ins_nation = isExistDBNation(nation)      # Nation DBからアーカイブを読み取り
        ableAPI = False
    
    return ableAPI, ins_nation


# プレイヤーの情報を取得
def get_player(player) :
    players_dict = get_API(EMC_API_URL, "allplayers/")
    if players_dict :
        for player_dict in players_dict :
            if player_dict["name"] == player :
                return player_dict
    return None
        

# プレイヤーの情報を更新しDBに登録
def set_player(player):
    ableAPI = True      # APIを取得できたかどうか

    player_dict = get_player(player)
    if player_dict :        # allplayers/の取得に成功したら
        ins_player, _ = Player.objects.get_or_create(name = player, defaults = {"name" : player})

        # ニックネーム・オンライン状況を取得
        online_dict = get_API(EMC_API_URL, "onlineplayers/" + player)
        if online_dict :        # onlineplayers/の取得に成功したら
            ins_player.nickname = online_dict["nickname"]
            ins_player.online = True
        else :      # onlineplayers/の取得に失敗したら
            ins_player.online = False
            if not ins_player.nickname :
                ins_player.nickname = player

        # UUIDの取得と登録
        uuid_dict = get_API(UUID_API_URL, player)
        if uuid_dict :      # APIの取得に成功したら
            ins_player.uuid = uuid_dict["id"]
        else :
            ableAPI = False
    
        ins_player.town = player_dict["town"]
        ins_player.nation = player_dict["nation"]
        ins_player.save()

    else :      # allplayers/の取得に失敗したら
        ins_player = isExistDBPlayer(player)
        ableAPI = False
    return ableAPI, ins_player


# オンラインプレイヤーの取得
def get_online() :
    online_dict_list = get_API(EMC_API_URL, "onlineplayers/")
    online_players = []
    for online_dict in online_dict_list :
        online_players.append(online_dict["name"])
    return online_players


# レイド情報の取得
def get_reid() :
    players_dict = get_API(EMC_API_URL, "allplayers/")
    towns_dict = {}
    for player_dict in players_dict :
        town = player_dict["town"]
        if "lastOnline" in player_dict :
            lastOnline = int(player_dict["lastOnline"])
            if town in towns_dict :
                if towns_dict[town] < lastOnline :
                    towns_dict[town] = lastOnline
            else :
                towns_dict[town] = lastOnline
    return towns_dict


# dynmapの拡大率
def mapzoom(erea) :
    zoom = 8 - int(erea**0.22)
    if zoom > 8 :
        zoom = 8
    if zoom < 1 :
        zoom = 1
    
    return zoom


# テンプレートに渡す用のテレポートコマンドの生成
def teleport(nation) :
    if len(nation) > 5 :
        nation = nation[:3] + "..."
    
    return "/n spawn " + nation


# PV数のカウント
def pv_increment() :
    today = date.today()
    insAnalyze, _ = Analyze.objects.get_or_create(date = today, defaults = {"date" : today})
    insAnalyze.pv += 1
    insAnalyze.save()


# トップ
def top(request):
    our_info = {}       # テンプレートに渡す辞書
    ableAPI = True

    # 大臣の情報とOUR_NATIONの更新
    ministers = Minister.objects.all()
    if ministers.count() :
        online_players = get_online()
        for minister in ministers :
            if minister.player.name in online_players :
                minister.player.online = True
            else :
                minister.player.online = False
            minister.save()

    our_info["ministers"] = ministers

    ableAPI, ins_ournation = set_nation(OUR_NATION)       # OUR_NATIONの情報の取得

    if ins_ournation :     # DBにOUR_NATIONがあったら
        our_info["our"] = ins_ournation
        if not ableAPI :
            our_info["error"] = "Earth MCからの情報の取得に失敗した為、アーカイブ記事を表示します。"
    else :      # DBにOUR_NATIONが無かったら
        our_info.update({"population":"エラー", "area":"エラー", "king":"エラー", "capitalName":"エラー"})
        our_info["error"] = "今までに一度も情報を取得できたことが無い為、記事を表示できません。"

    # APIが正常に処理できたかどうかの情報の登録
    our_info["ableAPI"] = ableAPI

    pv_increment()

    return render(request, 'xia/top.html', our_info)


# プレイヤーの編集
def editplayer(request) :
    result = {}

    if request.method == "POST":
        name = request.POST.get("name")
        info = request.POST.get("info")
        _, ins_player = set_player(name)

        if ins_player :
            ins_player.info = info
            ins_player.save()
            result["title"] = name + "の情報が更新されました"
        else :
            result["error"] = True      # プレイヤー情報の作成に関するトーストの表示
            result["name"] = name

    form = PlayerForm()
    result["form"] = form
    result["players"] = Player.objects.all()
    return render(request, 'xia/editplayer.html', result)


# プレイヤーの情報の削除
def editplayerdelete(request, player_id) :
    result = {}
    ins_player = Player.objects.get(id = player_id)

    result["title"] = ins_player.name + "の情報の削除しました"
    ins_player.delete()

    form = PlayerForm()
    result["form"] = form
    result["players"] = Player.objects.all()
    return render(request, 'xia/editplayer.html', result)


# プレイヤーの情報をjsonに関わらず強制的に作成
def editplayerforce(request, name) :
    result = {"title" : name + "の情報を登録しました。国と町の情報は登録できませんでした。"}
    
    ins_player, _ = Player.objects.get_or_create(name = name, defaults = {"name" : name})
    ins_player.nation = "No Nation"
    ins_player.town = "No Town"
    ins_player.save()

    form = PlayerForm()
    result["form"] = form
    result["players"] = Player.objects.all()
    return render(request, 'xia/editplayer.html', result)


# 大臣の情報の編集
def editminister(request) :
    result = {}

    if request.method == "POST":
        name = request.POST.get("name")
        title = request.POST.get("title")
        _, ins_player = set_player(name)
        if ins_player :
            insMinister, _ = Minister.objects.get_or_create(player = ins_player, defaults = {"player" : ins_player})
            insMinister.title = title
            insMinister.isminister = True
            insMinister.save()
            result["title"] = name + "の情報が更新されました"
        else :
            result["error"] = True
            result["name"] = name

    form = MinisterForm()
    result["form"] = form
    result["ministers"] = Minister.objects.all()
    return render(request, 'xia/editminister.html', result)


# 大臣の情報の削除
def editministerdelete(request, minister_id) :
    result = {}
    insMinister = Minister.objects.get(id = minister_id)

    result["title"] = insMinister.player.name + "大臣の情報の削除しました"
    insMinister.delete()

    form = MinisterForm()
    result["form"] = form
    result["ministers"] = Minister.objects.all()
    return render(request, 'xia/editminister.html', result)


# 大臣情報をjsonに関わらず強制的に作成
def editministerforce(request, name) :
    result = {"title" : name + "大臣の情報を登録しました。国と町の情報は登録できませんでした。"}

    ins_player, _ = Player.objects.get_or_create(name = name, defaults = {"name" : name})
    ins_player.nation = "No Nation"
    ins_player.town = "No Town"
    ins_player.save()
    insMinister, _ = Minister.objects.get_or_create(player = ins_player, defaults = {"player" : ins_player})
    insMinister.save()

    form = MinisterForm()
    result["form"] = form
    result["ministers"] = Minister.objects.all()
    return render(request, 'xia/editminister.html', result)


# レイド
def raid(request) :
    pv_increment()
    result = {"locked" : True, "towns" : dummy_dict}

    if request.method == "POST":
        password = request.POST.get("password")
        if hashlib.sha256(password.encode()).hexdigest() == SHA256a :
            result["locked"] = False

            towns_dict = get_reid()
            towns_tuple = sorted(towns_dict.items(), key = lambda town : town[1])     # ソート

            today = datetime.today()
            towns = []
            for name, unixt in towns_tuple :
                lastOnline = (today - datetime.fromtimestamp(unixt)).days
                if lastOnline < 45 :
                    towns.append((name, lastOnline))

            result["towns"] = towns

            if len(towns) :
                result["get"] = True
            else :
                result["towns"] = dummy_dict
                result["locked"] = True
                result["error"] = True

    return render(request, 'xia/raid.html', result)


# BOTによるレイド自動取得
def raidbot(request) :
    towns_dict = get_reid()
    return HttpResponse("OK")


# レイドからdynmapへリダイレクト
def raidmap(request, town) :
    town_dict = get_API(EMC_API_URL, "towns/" + town)
    if town_dict :
        x = town_dict["x"]
        z = town_dict["z"]
        area = town_dict["area"]
        return redirect(f"https://earthmc.net/map/aurora/?worldname=earth&mapname=flat&zoom={mapzoom(area)}&x={x}&y=64&z={z}")
    return raid(request)

def pv(request) :
    pv = list(Analyze.objects.values_list("pv", flat=True))
    date = Analyze.objects.values_list("date", flat=True)
    date = [f"{d.month}月{d.day}日" for d in date]
    allpv = sum(pv)

    result = {"pv" : pv, "allpv" : allpv, "axisxlist" : ",".join(date)}
    return render(request, 'xia/pv.html', result)