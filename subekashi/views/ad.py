from django.shortcuts import render, redirect
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.security import *
from subekashi.lib.discord import *


def ad(request) :
    dataD = {
        "metatitle" : "宣伝",
    }
    check = ""
    urlForms = []
    for i in range(1, 4) :
        url = request.COOKIES.get(f"ad{i}") if request.COOKIES.get(f"ad{i}") else ""
        dataD[f"url{i}"] = url
        dataD[f"ad{i}"] = url
        check += url
        urlForms.append(url)
        
    dataD["sha256"] = sha256(check)
    
    if request.method == "POST" :
        checkPOST = ""
        urlForms = []
        adForms = []
        for i in range(1, 4) :
            urlForm = format_yt_url(request.POST.get(f"url{i}", ""))
            adForm = format_yt_url(request.POST.get(f"ad{i}", ""))
            sha256Form = request.POST.get("sha256")
            
            checkPOST += adForm
            urlForms.append(urlForm)
            adForms.append(adForm)
        
        if sha256Form != sha256(checkPOST) :
            dataD["error"] = "不正なパラメータが含まれています"
            return render(request, "subekashi/ad.html", dataD)
        
        for i, urlForm, adForm in zip(range(1, 4), urlForms, adForms) :
            if urlForm == adForm :
                continue
            
            adIns = Ad.objects.filter(url = adForm).first()
            if (adIns == None) and (adForm != "") :
                dataD["error"] = "内部エラーが発生しました"
                return render(request, "subekashi/ad.html", dataD)
            elif adForm != "" :
                adIns.dup -= 1
                adIns.save()
            
            if urlForm == "" :
                continue
        
            if not(is_yt_url(urlForm)) and (urlForm != "") :
                dataD["error"] = "YouTubeのURLを入力してください"
                dataD[f"ad{i}"] = ""
                dataD[f"url{i}"] = ""
                urlForms[i - 1] = ""
                dataD["sha256"] = sha256("".join(urlForms))
                return render(request, "subekashi/ad.html", dataD)
            
            adIns, isCreate = Ad.objects.get_or_create(url = urlForm)
            adIns.dup += 1
            adIns.save()
            if isCreate :
                sendDiscord(DSP_DISCORD_URL, f"{urlForm}, {adIns.id}")
        
        return redirect("subekashi:ad_complete")
                
    ads = set()
    for urlForm in urlForms :
        if urlForm == "" : 
            continue
        adIns = Ad.objects.filter(url = urlForm).first()
        if not adIns :
            continue
            
        ads.add(adIns)
    
    dataD["ads"] = list(ads)
    
    return render(request, "subekashi/ad.html", dataD)