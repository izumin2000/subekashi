from cgitb import reset
from unittest import result
from django.shortcuts import redirect, render
from xia.forms import PlayerForm, MinisterForm
from xia.model import Player, Minister, Criminal, Gold, Tour, Nation, Analyze
import requests
from datetime import date
import json
from time import sleep
import hashlib


OUR_NATION = "Xia"
EMC_API_URL = "https://emc-toolkit.vercel.app/api/aurora/"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"
UPLOAD_URL = "uploadfiles/"

# デバッグ用
ERROR_API_URL = "https://error"
# EMC_API_URL = ERROR_API_URL     # コメントアウトを外すとEMC APIを取得

#パスワード関連
SHA256a = "917d6bfe7c48bc2870732e241fc211f5a50816863aea945443e409610a7ca46a"
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


"""
# Tour DB上にnationが存在するか確認
def isExistDBTour(nation) :
    nation = nation.replace(" ", "")
    nation = nation.replace("_", "")
    nation = nation.lower()

    nation_dict = Tour.objects.all()
    for nation_ins in nation_dict :
        tour_nation = nation_ins.name
        tour_nation = tour_nation.replace("_", "")
        tour_nation = tour_nation.lower()
        if tour_nation == nation :     # Tour DB上にnationがあった場合
            return nation_ins
    return None
"""


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

    print(ableAPI, ins_ournation)
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
            result["title"] = name + "の情報が変更されました"
        else :
            result["error"] = True      # プレイヤー情報の作成に関するトーストの表示

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
            result["title"] = name + "の情報が変更されました"
        else :
            result["error"] = True

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


"""
def emctour(request) :
    emctour_dict = {"nation" : "new"}

    if request.method == 'POST':

        # フォームの読み取り
        input_nation = request.POST['nation']

        # Tour DB上にinput_nationの国が存在するか確認
        ins_tour = isExistDBTour(input_nation)
        if ins_tour :     # input_nationがTour DBにあったら
            emctour_dict["jump"] = ins_tour.name
            emctour_dict["infomation"] = ins_tour.name + "の記事を読み込んでいます"
            return render(request, 'xia/emctour.html', emctour_dict)        # js側でリダイレクトの処理

        # input_nationがTour DBに無かった場合、EMC上にinput_nationの国が存在するか確認
        is_nation, ableAPI = isExistEMCNation(input_nation)
        if ableAPI :        # APIの取得に成功したら
            if is_nation :      # input_nationがEMC上にあったら
                emctour_dict["nation"] = is_nation
                emctour_dict["error"] = input_nation + "の記事が存在しません。"
                emctour_dict["noArticle"] = True        # 記事を作成しますか？トーストを表示する

            else :      # input_nationがEMC上に無かったら
                emctour_dict["error"] = input_nation + "はEarth MC上に存在しません。"

            return render(request, 'xia/emctour.html', emctour_dict)

        else :      # APIの取得に失敗したら
            # Tour DB からアーカイブがあるか確認
            ins_tour = isExistDBTour(input_nation)
            if ins_tour :       # Tour DBにアーカイブがあるのなら
                emctour_dict["error"] = "Earth MCからの情報の取得に失敗しました。"  
                emctour_dict["infomation"] = ins_tour.name + "のアーカイブ記事を表示します。"
                emctour_dict["jump"] = ins_tour.name        # リダイレクト先のnation    
                return render(request, 'xia/emctour.html', emctour_dict)
            else :          # Tour DBにアーカイブが無いのなら
                emctour_dict["error"] = "Earth MCからのデータの取得に失敗し、" + input_nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"
                return render(request, 'xia/emctour.html', emctour_dict)

    return render(request, 'xia/emctour.html', emctour_dict)


# 記事の作成・編集
def modarticle(request, nation) :
    modarticle_dict = {"nation" : nation}        # テンプレートに渡す辞書

    # 記事の登録
    if request.method == 'POST':
        # フォームの読み取り
        input_nation = request.POST['nation']
        input_info = request.POST['info']

        # EMC上にinput_nationの国が存在するか確認
        nation, ableAPI = isExistEMCNation(input_nation)
        if ableAPI :        # APIの取得に成功したら
            if nation :      # input_nationがEMC上にあったら

                # Tourレコードの作成・更新
                ableAPI, _, ins_nation = set_nation(nation, True)
                if ableAPI :        # APIの取得に成功したら
                    ins_tour, iscreated = Tour.objects.get_or_create(name = nation, defaults = {"name" : nation})
                    ins_nation.istour = True
                    ins_tour.nation = ins_nation
                    ins_tour.info = request.POST['info']
                    ins_tour.save()

                    if iscreated :
                        modarticle_dict["infomation"] = ins_nation + "の記事を作成しています"
                    else :
                        modarticle_dict["infomation"] = ins_nation + "の記事を更新しています"

                    modarticle_dict["info"] = ins_tour.info
                    modarticle_dict["jump"] = nation      # リダイレクト先のnation
                    return render(request, 'xia/modarticle.html', modarticle_dict)        # js側でリダイレクトの処理

            else :      # input_nationがEMC上に無かった場合
                modarticle_dict["error"] = input_nation + "はEarth MC上に存在しません。"
                modarticle_dict["info"] = input_info
                return render(request, 'xia/modarticle.html', modarticle_dict)

        if not ableAPI :      # 今までにAPIの取得に失敗したら
            # Tour DB からアーカイブがあるか確認
            ins_tour = isExistDBTour(input_nation)
            if ins_tour :       # Tour DBにアーカイブがあるのなら
                ins_tour.info = request.POST['info']
                ins_tour.save()

                modarticle_dict["error"] = "Earth MCからの情報の取得に失敗しました。"  
                modarticle_dict["infomation"] = nation + "のアーカイブ記事を表示します。"
                modarticle_dict["jump"] = nation        # リダイレクト先のnation    
                return render(request, 'xia/modarticle.html', modarticle_dict)
            else :          # Tour DBにアーカイブが無いのなら
                modarticle_dict["error"] = "Earth MCからのデータの取得に失敗し、" + input_nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"
                return render(request, 'xia/emctour.html', modarticle_dict)

    # infoの取得
    ins_tours = Tour.objects.filter(name = nation)
    if ins_tours.count() :     # Tour DBにnationがあったら
        ins_tour = ins_tours.first()
        modarticle_dict["info"] = ins_tour.info
    else:
        modarticle_dict["info"] = ""

    return render(request, 'xia/modarticle.html', modarticle_dict)


# 国の記事
def nation(request, nation) :
    nation_dict = {"nation" : nation}       # テンプレートに渡す辞書

    ins_tour = isExistDBTour(nation)
    if ins_tour :       # Tour DBにnationがあったら
        if request.method == "POST":
            inp_image = request.FILES.getlist('imagefile')      # 何故かNoneが返ってくる。
            # Screenshot.objects.create(image = inp_image, tour = ins_tour)
            nation_dict["infomation"] = "この機能はまだ実装してません"

        nation = ins_tour.name
        ableAPInation, ins_king, ins_nation = set_nation(nation, True)

        ableAPIplayer, _ = set_player(ins_king.name, False)
        ableAPI = ableAPInation & ableAPIplayer

        if ableAPI :        # APIを取得できたら
            # Tour レコードの登録
            ins_tour.nation = ins_nation
            ins_tour.save()

            ins_nation.istour = True
            ins_nation.save()

            uuid_dict = get_API(UUID_API_URL, ins_king.name)        # 何故か書かないと動かない
            if uuid_dict :      # APIの取得に成功したら
                ins_king.uuid = uuid_dict["id"]
                ins_king.save()

            nation_dict["tour"] = ins_tour
            nation_dict["king"] = ins_king
            nation_dict["mapzoom"] = mapzoom(ins_tour.nation.area)
            nation_dict["teleport"] = teleport(nation)
            nation_dict["km2"] = ins_tour.nation.area * 256 / 1000
            nation_dict["screenshots"] = ins_tour.screenshot_tour.all()
            nation_dict["ableAPI"] = ableAPI
            return render(request, 'xia/nation.html', nation_dict)
        
        else :      # APIの取得に失敗したら
            # Tour DB からアーカイブがあるか確認
            ins_tour = isExistDBTour(nation)
            if ins_tour :       # Tour DBにアーカイブがあるのなら
                nation_dict["error"] = "Earth MCからの情報の取得に失敗した為、アーカイブ記事を表示します。"  
                nation_dict["tour"] = ins_tour
                nation_dict["king"] = ins_king
                nation_dict["mapzoom"] = mapzoom(ins_tour.nation.area)
                nation_dict["teleport"] = teleport(nation)
                nation_dict["km2"] = ins_tour.nation.area * 256 / 1000
                nation_dict["screenshots"] = ins_tour.screenshot_tour.all()
                nation_dict["ableAPI"] = ableAPI 
                return render(request, 'xia/nation.html', nation_dict)
            else :          # Tour DBにアーカイブが無いのなら
                nation_dict["error"] = "Earth MCからのデータの取得にし、" + nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"      
                nation_dict["nation"] = "new"
                return render(request, 'xia/modarticle.html', nation_dict)

    else :      # Tour DBにnationが無かったら
        nation_dict["noArticle"] = True
        nation_dict["nation"] = nation
        nation_dict["error"] = nation + "の記事が存在しません。"
        return render(request, 'xia/emctour.html', nation_dict)


# 記事一覧
def nationlist(request, order) :
    nationlist_dict = {}
    order_item = ["name", "area", "population"]

    if not order in order_item :
        order = "name"

    nations = Nation.objects.filter(istour = True).order_by(order)

    if order != "name" :
        nations = nations.reverse()

    nationlist_dict["nations"] = nations
    nationlist_dict["order"] = order

    return render(request, 'xia/nationlist.html', nationlist_dict)
"""


# TODO ゼロ埋め 31レコード表示
def pv(request) :
    pv = Analyze.objects.values_list("pv", flat=True)
    pv = list(pv)
    allpv = sum(pv)
    axisxlist = list(range(len(pv)))

    result = {"pv" : pv, "allpv" : allpv, "axisxlist" : axisxlist}
    return render(request, 'xia/pv.html', result)