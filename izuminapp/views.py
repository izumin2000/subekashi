import re
from django.shortcuts import redirect, render
from izuminapp.forms import FirstviewForm, PlayerForm
from izuminapp.model import Player, Citizen, Minister, Criminal, Gold, Tour, Town, Nation, Firstview, Analyze
import requests
from datetime import date
import json
from time import sleep


OUR_TOWN = "Juliaca"
OUR_NATION = "Inca_Empire"
EMC_API_URL = "https://earthmc-api.herokuapp.com/api/v1/nova/"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"
UPLOAD_URL = "uploadfiles/"
NUMBER_OF_FIRSTVIEWS = 5


# 成功時にAPIのjsonを出力。失敗すると空文字を出力。
def get_API(url, route) :
    sleep(2)
    try :
        get = requests.get(url + route)
    except :
        print("5xx Error", route)
        return ""

    if (get.status_code == 200) :
        try :
            get_dict = get.json()
        except :
            print("Not JSON Error", route)
            return ""

        if "error" in get_dict :     # dictのキーにerrorがあったら
            print("Invalid path Error", route)
            return ""
        else :
            print("OK", route)
            return get_dict

    else :
        print("not 2xx Error", route)
        return ""


# 国の情報を更新しDBに登録
def set_erea(nation, isnation): 
    ableAPI = True      # APIを取得できたかどうか

    # 国のデータを取得
    if isnation :
        nation_dict = get_API(EMC_API_URL, "nations/" + nation)
        if nation_dict :
            capital = nation_dict["capitalName"]
            king = nation_dict["king"]
        else :
            ableAPI = False

    # 首都のデータを取得
    if ableAPI :
        town_dict = get_API(EMC_API_URL, "towns/" + capital)
        if town_dict :
            mayor = town_dict["mayor"]
        else :
            ableAPI = False

    # 市長のデータを取得
    if ableAPI :
        ins_mayor, _ = Player.objects.get_or_create(name = mayor, defaults = {"name" : mayor})
        mayor_dict = get_API(EMC_API_URL, "allplayers/" + mayor)
        if not mayor_dict :
            ableAPI = False
    else :
        ins_mayor = None
    
    # 国王のデータを取得
    if ableAPI and isnation :
        ins_king, _ = Player.objects.get_or_create(name = king, defaults = {"name" : king})
        king_dict = get_API(EMC_API_URL, "allplayers/" + king)            
        if not king_dict :
            ableAPI = False
    else :
        ins_king = None

    # 首都のデータの登録
    if ableAPI :
        ins_capital, _ = Town.objects.get_or_create(name = capital, defaults = {"name" : capital})
        if not ins_capital.nickname :      # nicknameが空白のとき、nameと同じにする
            ins_capital.nickname = town_dict["name"]
        ins_capital.population = len(town_dict["residents"])
        ins_capital.area = town_dict["area"]
        ins_capital.x = town_dict["x"]
        ins_capital.z = town_dict["z"]
        ins_capital.mayor = ins_mayor
        ins_capital.save()
    else :
        ins_capital = None

    # 国のデータの登録
    if ableAPI and isnation :
        ins_nation, _ = Nation.objects.get_or_create(name = nation, defaults = {"name" : nation})
        if not ins_nation.nickname :      # nicknameが空白のとき、nameと同じにする
            ins_nation.nickname = nation_dict["name"]
        ins_nation.population = len(nation_dict["residents"])
        ins_nation.area = nation_dict["area"]
        ins_nation.capital = ins_capital
        ins_nation.x = nation_dict["capitalX"]
        ins_nation.z = nation_dict["capitalZ"]
        ins_nation.king = ins_king
        ins_nation.save()        
    else :
        ins_nation = None
    
    return ableAPI, ins_mayor, ins_king, ins_capital, ins_nation


# プレイヤーの情報を更新しDBに登録
def set_player(player, isnested):
    ableAPI = True      # APIを取得できたかどうか
    ins_player, _ = Player.objects.get_or_create(name = player, defaults = {"name" : player})

    # オンラインのプレイヤーの情報を取得
    online_dict = get_API(EMC_API_URL, "onlineplayers/" + player)
    if online_dict :
        ins_player.nickname = online_dict["nickname"]
        ins_player.online = True
    else :
        ins_player.online = False
    
    # プレイヤーの情報を取得
    player_dict = get_API(EMC_API_URL, "allplayers/" + player)
    if player_dict :        
        # UUIDの取得と登録
        uuid_dict = get_API(UUID_API_URL, player)
        if uuid_dict :
            ins_player.uuid = uuid_dict["id"]
        else :
            ableAPI = False

        # プレイヤーの町と国の情報を登録
        nation = player_dict["nation"]
        if nation:      # 国なら
            ableAPIerea, ins_mayor, ins_king, ins_town, ins_nation = set_erea(nation, True)
            ableAPI &= ableAPIerea
            if ableAPI :
                ins_player.town = ins_town
                ins_player.nation = ins_nation
                if not isnested :       # 市長と国王のみフラグが立つ
                    set_player(ins_mayor.name, True)
                    set_player(ins_king.name, True)
            else :
                ins_player.town = None
                ins_player.nation = None
                ableAPI = False
        else :      # 町なら
            ableAPIerea, ins_mayor, _, ins_town, _ = set_erea(nation, False)
            ableAPI &= ableAPIerea
            if ableAPI :
                ins_player.town = ins_town
                ins_player.nation = None
                if not isnested :       # 市長と国王のみフラグが立つ
                    set_player(ins_mayor.name, True)
            else :
                ins_player.town = None
                ins_player.nation = None
                ableAPI = False
            
            # OUR_NATION市民の登録
            if nation == OUR_NATION :
                ins_citizen, _ = Citizen.get_or_create(name = player, defaults = {"name" : player})
                ins_citizen.player = ins_player
                ins_citizen.save()
    else :
        ins_player.town = None
        ins_player.nation = None
        ableAPI = False

    ins_player.save()
    return ableAPI

"""
# PV数のカウント
today = date.today()
insAnalyze, _ = Analyze.objects.get_or_create(date = today, defaults = {"date" : today})
insAnalyze.pv += 1
insAnalyze.save()
"""


def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    our_info = {}       # テンプレートに渡す辞書
    ableAPI = True

    # 大臣情報の取得と更新・OUR_NATIONの更新
    ministers = Minister.objects.all()

    ## 大臣が一人も居なかったら
    if not ministers.count() :
        ableAPI, _, _, _, _ = set_erea(OUR_NATION, True)

    ## 大臣の情報の更新
    our_info["ministers"] = ministers
    for minister in ministers :
        ableAPIplayer = set_player(minister, False)
        ableAPI &= ableAPIplayer

    # OUR_NATIONの情報の取得
    ## TODO リファクタリング
    our_nation = Nation.objects.filter(name = OUR_NATION)
    if our_nation.count() :     # DBにOUR_NATIONがあったら
        ins_captial = our_nation.first().capital        # 首都データを取得
        our_dict = our_nation.values()[0]
        our_info.update(our_dict)
        our_info.update({"capitalName":ins_captial.name})
    else :
        our_info.update({"population":"エラー", "area":"エラー", "king":"エラー", "capitalName":"エラー"})
        ableAPI = False

    # ファーストビューの処理
    # firstviews = Firstview.objects.filter(display = True).order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]     # ランダムにNUMBER_OF_FIRSTVIEWS個取り出す
    # firstviews = list(firstviews.values())
    # if len(firstviews) :
        # our_info["clTitle"] = [d.get('title') for d in firstviews]
        # our_info["clPlayers"] = [d.get('player') for d in firstviews]

    # APIが正常に処理できたかどうかの情報の登録
    our_info["ableAPI"] = ableAPI
    if not ableAPI :
        our_info["error"] = "EarthMCのデータが読み込まれなかった為、一部情報が存在しないか不正確です。"

    return render(request, 'inca/inca.html', our_info)

def emctour(request) :
    emctour_dict = {"nation" : "new"}
    if request.method == 'POST':
        input_nation_raw = request.POST['nation']
        input_nation = input_nation_raw.replace(" ", "")
        input_nation = input_nation.replace("_", "")
        input_nation = input_nation.lower()

        # EMC上にinput_nationの国が存在するか確認
        nations_dict_list = get_API(EMC_API_URL, "nations")
        emc_nations = []
        for nation_dict in nations_dict_list :
            nation_name = nation_dict["name"]
            nation_name = nation_name.replace("_", "")
            nation_name = nation_name.lower()
            emc_nations.append(nation_name)

        if input_nation in emc_nations :        # EMC上にinput_nationの国があった場合

            # TourDB上にinput_nationの国が存在するか確認
            nation_dict = Tour.objects.all()
            for nation_ins in nation_dict :
                nation_name = nation_ins.name
                nation_name = nation_name.replace("_", "")
                nation_name = nation_name.lower()
                if nation_name == input_nation :     # TourDB上にinput_nationの国があった場合
                    emctour_dict["jump"] = nation_ins.name      # リダイレクト先のnation
                    return render(request, 'inca/emctour.html', emctour_dict)        # js側でリダイレクトの処理
            
            # TourDB上にinput_nationの国が無かった場合
            if input_nation_raw :
                emctour_dict["nation"] = input_nation_raw
                emctour_dict["error"] = input_nation_raw + "の記事が存在しません。"
                emctour_dict["noArticle"] = True

            return render(request, 'inca/emctour.html', emctour_dict)

        # EMC上にinput_nationの国が無かった場合
        else :
            print("!!!!!!!!")
            emctour_dict["error"] = input_nation_raw + "はEMC上に存在しません。"
            return render(request, 'inca/emctour.html', emctour_dict)

    return render(request, 'inca/emctour.html', emctour_dict)


# 記事の作成・編集
def modarticle(request, nation) :
    modarticle_dict = {"nation" : nation}        # テンプレートに渡す辞書

    # 記事の登録
    if request.method == 'POST':
        ableAPI, _, _, _, ins_nation = set_erea(nation, True)
        if ableAPI :
            ins_tour, _ = Tour.objects.get_or_create(name = nation, defaults = {"name" : nation})
            ins_tour.nation = ins_nation
            ins_tour.info = request.POST['info']
            ins_tour.save()
            modarticle_dict["info"] = ins_tour.info
            modarticle_dict["jump"] = nation      # リダイレクト先のnation
            return render(request, 'inca/modarticle.html', modarticle_dict)        # js側でリダイレクトの処理
        else :
            modarticle_dict["error"] = "APIの取得に失敗しました。再度時間を置いて登録してください。"
            return render(request, 'inca/emctour.html', modarticle_dict)

    # infoの取得
    ins_tours = Tour.objects.filter(name = nation)
    if ins_tours.count() :     # DBにOnationがあったら
        ins_tour = ins_tours.first()
        modarticle_dict["info"] = ins_tour.info
    else:
        modarticle_dict["info"] = ""

    return render(request, 'inca/modarticle.html', modarticle_dict)


# 国の記事
def nation(request, nation) :
    nation_dict = {}        # テンプレートに渡す辞書

    ins_tours = Tour.objects.filter(name = nation)
    if ins_tours.count() :     # Tour DBにnationがあったら
        ins_tour = ins_tours.first()
        ableAPInation, _, ins_king, _, ins_nation = set_erea(nation, True)
        if ableAPInation :
            ableAPIplayer = set_player(ins_king.name, False)

        ins_tour.nation = ins_nation
        ins_tour.save()
        nation_dict["tour"] = ins_tour
        nation_dict["king"] = ins_king
        if ableAPInation :
            nation_dict["ableAPI"] = ableAPIplayer
        else :
            nation_dict["ableAPI"] = False
        
        if not nation_dict["ableAPI"] :
            nation_dict["error"] = "APIの取得に失敗しました。再度時間を置いて登録してください。"
            nation_dict["nation"] = "new"
            return render(request, 'inca/emctour.html', nation_dict)

        return render(request, 'inca/nation.html', nation_dict)
    else :
        nation_dict["error"] = nation + "はEMC上に存在しません。"
        return render(request, 'inca/emctour.html', nation_dict)


"""
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
"""


# TODO ゼロ埋め 31レコード表示
def pv(request) :
    pv = Analyze.objects.values_list("pv", flat=True)
    pv = list(pv)
    allpv = sum(pv)
    axisxlist = list(range(len(pv)))

    result = {"pv" : pv, "allpv" : allpv, "axisxlist" : axisxlist}
    return render(request, 'inca/pv.html', result)