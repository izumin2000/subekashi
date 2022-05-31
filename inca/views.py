from django.shortcuts import redirect, render
from inca.forms import FirstviewForm, PlayerForm
from inca.model import Player, Citizen, Minister, Criminal, Gold, Screenshot, Tour, Nation, Firstview, Analyze
import requests
from datetime import date
import json
from time import sleep


OUR_NATION = "Inca_Empire"
EMC_API_URL = "https://earthmc-api.herokuapp.com/api/v1/nova/"
UUID_API_URL = "https://api.mojang.com/users/profiles/minecraft/"
WORLD_URL = "nova/"     # "aurora/"
UPLOAD_URL = "uploadfiles/"
NUMBER_OF_FIRSTVIEWS = 5

# デバッグ用
ERROR_API_URL = "https://error"
# EMC_API_URL = ERROR_API_URL     # コメントアウトを外すとEMC APIを取得


# 成功時にAPIのjsonを出力。失敗すると空文字を出力。
def get_API(url, route) :
    if url == EMC_API_URL :
        sleep(2)
    else :
        sleep(0.5)

    # if "allplayers" in route :
        # url = url.replace("nova/", "")      # nova/を削除

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


# EMC上にnationが存在するか確認
def isExistEMCNation(nation) :
    nation = nation.replace(" ", "")
    nation = nation.replace("_", "")
    nation = nation.lower()

    # EMC上にinput_nationの国が存在するか確認
    nations_dict_list = get_API(EMC_API_URL, "nations")
    if nations_dict_list :      # APIの取得に成功したら
        # EMC上の全ての国の名前を取得
        for nation_dict in nations_dict_list :
            emc_nation = nation_dict["name"]
            emc_nation = emc_nation.replace("_", "")
            emc_nation = emc_nation.lower()

            if nation == emc_nation :        # EMC上にnationがあった場合
                return nation_dict["name"], True
        
        # EMC上にnationが無かった場合
        return False, True

    else :      # APIの取得に失敗したら
        return False, False


# 国の情報を更新しDBに登録
def set_nation(nation): 
    ableAPI = True      # APIを取得できたかどうか

    # 国のデータを取得
    nation_dict = get_API(EMC_API_URL, "nations/" + nation)
    if nation_dict :
        king = nation_dict["king"]
    else :      # nations/の取得に失敗したら
        ableAPI = False

    # 国王のデータを取得
    if ableAPI :
        ins_king, _ = Player.objects.get_or_create(name = king, defaults = {"name" : king})
        king_dict = get_API(EMC_API_URL, "allplayers/" + king)       

        if not king_dict :      # allplayers/の取得に失敗したら
            ins_king = isExistDBPlayer(king)      # Player DBからアーカイブを読み取り
            ableAPI = False

    # 国のデータの登録
    if ableAPI :
        ins_nation, _ = Nation.objects.get_or_create(name = nation, defaults = {"name" : nation})

        ins_nation.population = len(nation_dict["residents"])
        ins_nation.area = nation_dict["area"]
        ins_nation.capital = nation_dict["capitalName"]
        ins_nation.x = nation_dict["capitalX"]
        ins_nation.z = nation_dict["capitalZ"]
        ins_nation.king = ins_king      # ins_kingの情報は後にset_player関数にて取得する
        ins_nation.save()        
    else :      # 今までにAPIの取得に失敗していたら
        ins_nation = isExistDBNation(nation)      # Nation DBからアーカイブを読み取り
        if ins_nation :
            ins_king = ins_nation.king      # Nation DBのアーカイブからkingインスタンスを読み取り
        else :
            ins_king = None
    
    return ableAPI, ins_king, ins_nation


# プレイヤーの情報を更新しDBに登録
def set_player(player, isget_nation):
    ableAPI = True      # APIを取得できたかどうか
    ins_player, _ = Player.objects.get_or_create(name = player, defaults = {"name" : player})

    # オンラインのプレイヤーの情報を取得
    online_dict = get_API(EMC_API_URL, "onlineplayers/" + player)
    if online_dict :        # onlineplayers/の取得に成功したら
        ins_player.nickname = online_dict["nickname"]
        ins_player.online = True
    else :      # onlineplayers/の取得に失敗したら
        ins_player.online = False

    # UUIDの取得と登録
    uuid_dict = get_API(UUID_API_URL, player)
    if uuid_dict :      # APIの取得に成功したら
        ins_player.uuid = uuid_dict["id"]
    else :
        ableAPI = False
    
    # プレイヤーの情報を取得
    player_dict = get_API(EMC_API_URL, "allplayers/" + player)
    if player_dict :        # allplayers/の取得に成功したら

        # プレイヤーの国の情報を登録
        nation = player_dict["nation"]
        if (nation != "No Nation") and isget_nation:        # 国に所属していてnationの情報を取得するのなら
            ableAPIerea, ins_king, ins_nation = set_nation(nation)
            ableAPI &= ableAPIerea

            if ableAPI :        # 今までにAPIの取得に成功していたら
                ins_player.nation = ins_nation
                if player != ins_king.name :        # 国王だったら
                    ableAPItmp = set_player(ins_king.name, False)      # 再帰させる
                    ableAPI &= ableAPItmp

            else :      # 今までにAPIが取得できないことがあったら
                ins_player.nation = isExistEMCNation(nation)
                ableAPI = False
                
            # OUR_NATION国民の登録
            if nation == OUR_NATION :
                ins_citizen, _ = Citizen.get_or_create(name = player, defaults = {"name" : player})
                ins_citizen.player = ins_player
                ins_citizen.save()
                
    else :      # allplayers/の取得に失敗したら
        ableAPI = False

    ins_player.save()
    return ableAPI


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


"""
# PV数のカウント
today = date.today()
insAnalyze, _ = Analyze.objects.get_or_create(date = today, defaults = {"date" : today})
insAnalyze.pv += 1
insAnalyze.save()
"""


def root(request):
    return render(request, 'inca/root.html')

def inca(request):
    our_info = {}       # テンプレートに渡す辞書
    ableAPI = True

    ministers = Minister.objects.all()
    if ministers.count() :      # 大臣が一人以上いたら
        our_info["ministers"] = ministers

        # 大臣の情報とOUR_NATIONの更新
        for minister in ministers :
            ableAPIplayer = set_player(minister, True)
            ableAPI &= ableAPIplayer

    else :      # 大臣が一人もいなかったら
        ableAPI, _, _ = set_nation(OUR_NATION)        # OUR_NATIONの更新

    # OUR_NATIONの情報の取得
    ins_ournation = isExistDBNation(OUR_NATION)

    if ins_ournation :     # DBにOUR_NATIONがあったら
        our_info["our"] = ins_ournation

    else :      # DBにOUR_NATIONが無かったら
        # our_info.update({"population":"エラー", "area":"エラー", "king":"エラー", "capitalName":"エラー"})
        ableAPI = False

    # ファーストビューの処理
    # firstviews = Firstview.objects.filter(display = True).order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]     # ランダムにNUMBER_OF_FIRSTVIEWS個取り出す
    # firstviews = list(firstviews.values())
    # if len(firstviews) :
        # our_info["clTitle"] = [d.get('title') for d in firstviews]
        # our_info["clPlayers"] = [d.get('player') for d in firstviews]

    # APIが正常に処理できたかどうかの情報の登録
    our_info["ableAPI"] = ableAPI
    if not ableAPI :        # いままでにAPIの取得に失敗していたら
        our_info["error"] = "Earth MCからの情報の取得に失敗した為、アーカイブ記事を表示します。"

    return render(request, 'inca/inca.html', our_info)

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
            return render(request, 'inca/emctour.html', emctour_dict)        # js側でリダイレクトの処理

        # input_nationがTour DBに無かった場合、EMC上にinput_nationの国が存在するか確認
        is_nation, ableAPI = isExistEMCNation(input_nation)
        if ableAPI :        # APIの取得に成功したら
            if is_nation :      # input_nationがEMC上にあったら
                emctour_dict["nation"] = is_nation
                emctour_dict["error"] = input_nation + "の記事が存在しません。"
                emctour_dict["noArticle"] = True        # 記事を作成しますか？トーストを表示する

            else :      # input_nationがEMC上に無かったら
                emctour_dict["error"] = input_nation + "はEarth MC上に存在しません。"

            return render(request, 'inca/emctour.html', emctour_dict)

        else :      # APIの取得に失敗したら
            # Tour DB からアーカイブがあるか確認
            ins_tour = isExistDBTour(input_nation)
            if ins_tour :       # Tour DBにアーカイブがあるのなら
                emctour_dict["error"] = "Earth MCからの情報の取得に失敗しました。"  
                emctour_dict["infomation"] = ins_tour.name + "のアーカイブ記事を表示します。"
                emctour_dict["jump"] = ins_tour.name        # リダイレクト先のnation    
                return render(request, 'inca/emctour.html', emctour_dict)
            else :          # Tour DBにアーカイブが無いのなら
                emctour_dict["error"] = "Earth MCからのデータの取得に失敗し、" + input_nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"
                return render(request, 'inca/emctour.html', emctour_dict)

    return render(request, 'inca/emctour.html', emctour_dict)


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
                ableAPI, _, ins_nation = set_nation(nation)
                if ableAPI :        # APIの取得に成功したら
                    ins_tour, iscreated = Tour.objects.get_or_create(name = nation, defaults = {"name" : nation})
                    ins_nation.istour = True
                    ins_tour.nation = ins_nation
                    ins_tour.info = request.POST['info']
                    ins_tour.save()

                    if iscreated :
                        modarticle_dict["infomation"] = ins_nation.name + "の記事を作成しています"
                    else :
                        modarticle_dict["infomation"] = ins_nation.name + "の記事を更新しています"

                    modarticle_dict["info"] = ins_tour.info
                    modarticle_dict["jump"] = nation      # リダイレクト先のnation
                    return render(request, 'inca/modarticle.html', modarticle_dict)        # js側でリダイレクトの処理

            else :      # input_nationがEMC上に無かった場合
                modarticle_dict["error"] = input_nation + "はEarth MC上に存在しません。"
                modarticle_dict["info"] = input_info
                return render(request, 'inca/modarticle.html', modarticle_dict)

        if not ableAPI :      # 今までにAPIの取得に失敗したら
            # Tour DB からアーカイブがあるか確認
            ins_tour = isExistDBTour(input_nation)
            if ins_tour :       # Tour DBにアーカイブがあるのなら
                ins_tour.info = request.POST['info']
                ins_tour.save()

                modarticle_dict["error"] = "Earth MCからの情報の取得に失敗しました。"  
                modarticle_dict["infomation"] = nation + "のアーカイブ記事を表示します。"
                modarticle_dict["jump"] = nation        # リダイレクト先のnation    
                return render(request, 'inca/modarticle.html', modarticle_dict)
            else :          # Tour DBにアーカイブが無いのなら
                modarticle_dict["error"] = "Earth MCからのデータの取得に失敗し、" + input_nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"
                return render(request, 'inca/emctour.html', modarticle_dict)

    # infoの取得
    ins_tours = Tour.objects.filter(name = nation)
    if ins_tours.count() :     # Tour DBにnationがあったら
        ins_tour = ins_tours.first()
        modarticle_dict["info"] = ins_tour.info
    else:
        modarticle_dict["info"] = ""

    return render(request, 'inca/modarticle.html', modarticle_dict)


# 国の記事
def nation(request, nation) :
    nation_dict = {"nation" : nation}       # テンプレートに渡す辞書

    ins_tour = isExistDBTour(nation)
    if ins_tour :       # Tour DBにnationがあったら
        # TODO 画像のアップロード
        if request.method == "POST":
            inp_image = request.FILES.getlist('imagefile')      # 何故かNoneが返ってくる。
            # Screenshot.objects.create(image = inp_image, tour = ins_tour)
            nation_dict["infomation"] = "この機能はまだ実装してません"

        nation = ins_tour.name
        ableAPInation, ins_king, ins_nation = set_nation(nation)

        ableAPIplayer = set_player(ins_king.name, False)
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
            return render(request, 'inca/nation.html', nation_dict)
        
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
                return render(request, 'inca/nation.html', nation_dict)
            else :          # Tour DBにアーカイブが無いのなら
                nation_dict["error"] = "Earth MCからのデータの取得にし、" + nation + "のアーカイブ記事もありません。再度時間を置いてアクセスしてください。"      
                nation_dict["nation"] = "new"
                return render(request, 'inca/modarticle.html', nation_dict)

    else :      # Tour DBにnationが無かったら
        nation_dict["noArticle"] = True
        nation_dict["nation"] = nation
        nation_dict["error"] = nation + "の記事が存在しません。"
        return render(request, 'inca/emctour.html', nation_dict)


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

    return render(request, 'inca/nationlist.html', nationlist_dict)


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