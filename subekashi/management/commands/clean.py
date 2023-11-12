from django.core.management.base import BaseCommand
from subekashi.models import Song
from django.utils import timezone

def getIns(n) :
    return Song.objects.get(pk = n) if Song.objects.filter(pk = n) else False

def commaClean(s) :
    if s :
        s = s[1:] if s[0] == "," else s
        s = s[:-1] if s[-1] == "," else s
        return s
    else :
        return ""

def commaSplit(s) :
    return list(map(int, s.split(","))) if s else []

def addId(s, n) :
    if s :
        s = set(s.split(","))
        s.add(str(n))
        return ",".join(list(s))
    else :
        return str(n)

def deleteId(s, n) :
    s = set(s.split(","))
    s.remove(str(n))
    return ",".join(list(s)) if s else ""

def output(m) :
    print(m)
    return m

class Command(BaseCommand):
    def handle(self, *args, **options):
        msg = ""
        # 指定した曲の削除
        if options["d"] :
            for songId in options['d'] :
                songIns = getIns(songId)
                if songIns :
                    msg += output(f"{songIns.id}({songIns})を削除しました")
                    songIns.delete()

        for songIns in Song.objects.all() :
            # 模倣情報のチェック
            songImitate = songIns.imitate
            songImitateClean = commaClean(songImitate)
            if songImitate != songImitateClean :
                msg += output(f"{songIns.id}({songIns})の模倣情報のエラーを修正しました")
                songIns.imitate = songImitateClean
                songIns.save()
            
            # 被模倣情報のチェック
            songImitated = songIns.imitated
            songImitatedClean = commaClean(songImitated)
            if songImitated != songImitatedClean :
                msg += output(f"{songIns.id}({songIns})の被模倣情報のエラーを修正しました")
                songIns.imitated = songImitatedClean
                songIns.save()

            # 模倣情報から被模倣情報のチェック
            for imitateId in commaSplit(songIns.imitate) :
                imitateIns = getIns(imitateId)
                if imitateIns :
                    if songIns.id not in commaSplit(imitateIns.imitated) :
                        msg += output(f"{imitateIns.id}({imitateIns})の被模倣情報に{songIns.id}({songIns})を追加しました")
                        imitateIns.imitated = addId(imitateIns.imitated, songIns.id)
                        imitateIns.save()
                else :
                    msg += output(f"{songIns.id}({songIns})の被模倣情報から削除された曲{imitateId}を削除しました")
                    songIns.imitate = deleteId(songIns.imitate, imitateId)
                    songIns.save()

            # 模倣情報から被模倣情報のチェック  
            for imitatedId in commaSplit(songIns.imitated) :
                imitatedIns = getIns(imitatedId)
                if imitatedIns :
                    if songIns.id not in commaSplit(imitatedIns.imitate) :
                        msg += output(f"{imitatedIns.id}({imitatedIns})の模倣情報に{songIns.id}({songIns})を追加しました")
                        imitatedIns.imitate = addId(imitatedIns.imitate, songIns.id)
                        imitatedIns.save()
                else :
                    msg += output(f"{songIns.id}({songIns})の被模倣情報から削除された曲{imitatedId}を削除しました")
                    songIns.imitated = deleteId(songIns.imitated, imitatedId)
                    songIns.save()

            # posttimeの埋め込み
            if songIns.posttime == None :
                msg += output(f"{songIns.id}({songIns})のposttimeを更新しました。", songIns.id)
                songIns.posttime = timezone.now()
                songIns.save()
            
            # スラッシュの置換
            if "/" in songIns.title :
                msg += output(f"{songIns.id}({songIns})のスラッシュをリプレイスしました")
                songIns.title = songIns.title.replace("/", "╱")
                songIns.save()
        return msg

    def add_arguments(self, parser):
        parser.add_argument('-d', required=False, nargs='*')