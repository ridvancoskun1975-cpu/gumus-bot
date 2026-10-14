"""bot/sinir.py sınamaları (ağ yok). Çalıştır: python bot/test_sinir.py"""
import contextlib
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sinir  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


def is_(ad, durum, sonuc=None, bas=None, bit=None):
    return {"name": ad, "status": durum, "conclusion": sonuc, "started_at": bas, "completed_at": bit}


# 14 Ekim 2026 10:30 TR = 07:30 UTC
SIMDI = datetime(2026, 10, 14, 7, 30, tzinfo=timezone.utc)

# ---------------------------------------------------------------- sayım
calistirmalar = [{"id": i} for i in range(1, 9)]
isler = {
    # dün 22:30 TR paylaşıldı → sayılmaz
    1: [is_("kontrol", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-13T19:30:00Z")],
    # bugün 00:10 TR (13 Ekim 21:10 UTC) paylaşıldı → sayılır (gün TR'ye göre)
    2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:10:00Z")],
    # bugün 04:51 TR rehber hikâyesi → sayılır (bir çalıştırma = bir paylaşım, 5 kare de olsa)
    3: [is_("uret", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-14T01:51:28Z")],
    # deneme: yayinla atlandı → sayılmaz
    4: [is_("uret", "completed", "success"), is_("yayinla", "completed", "skipped", bit="2026-10-14T02:00:00Z")],
    # paylaşım hata verdi → sayılmaz
    5: [is_("yayinla", "completed", "failure", bit="2026-10-14T03:00:00Z")],
    # başka çalıştırma şu an paylaşıyor → sayılır
    6: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:00Z")],
    # bu çalıştırma → sayılmaz
    7: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:30Z")],
    # sınırda durdurulmuş çalıştırma (kontrol hata) → sayılmaz
    8: [is_("kontrol", "completed", "failure")],
}
say = sinir.paylasim_sayisi(calistirmalar, isler, SIMDI, bu_calistirma=7)
esit([c for c, _, _ in say], [2, 3, 6], "sayılan çalıştırmalar")
esit([d for _, _, d in say], ["paylaşıldı", "paylaşıldı", "sürüyor"], "durumlar")
esit(len(sinir.paylasim_sayisi([], {}, SIMDI, 0)), 0, "boş gün")
gy = {1: [is_("yayinla", "completed", "success", bit="2026-10-13T20:59:59Z")],   # 23:59:59 TR dün
      2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:00:00Z")]}   # 00:00 TR bugün
esit([c for c, _, _ in sinir.paylasim_sayisi([{"id": 1}, {"id": 2}], gy, SIMDI, 0)], [2], "gece yarısı")


# ---------------------------------------------------------------- karar (GitHub okuması sahte)
def sahte(n):
    return lambda simdi=None, **kw: [(i, SIMDI, "paylaşıldı") for i in range(n)]


def hata(simdi=None, **kw):
    raise sinir.SayilamadiHatasi("bağlantı yok")


def karar(sayici, yayin, onay):
    sinir.say = sayici
    with contextlib.redirect_stdout(io.StringIO()):
        return sinir.kontrol(yayin, onay, "bilgi", "3", simdi=SIMDI)


asil_say, asil_gun = sinir.say, sinir.GUN_SINIRI
sinir.GUN_SINIRI = {}   # sınamalar gerçek gün istisnalarından bağımsız
#        sayı  yayın  onay   beklenen (0 devam, 1 dur)
# günde en fazla 4 (14 Ekim 2026 21:23'ten beri): 4. geçer, 5. onaysız durur
for n, yayin, onay, bek in [(0, True, False, 0), (3, True, False, 0), (4, True, False, 1), (6, True, False, 1),
                            (4, True, True, 0), (6, True, True, 0), (4, False, False, 0), (9, False, False, 0)]:
    esit(karar(sahte(n), yayin, onay), bek, f"n={n} yayın={yayin} onay={onay}")
esit(karar(hata, True, False), 1, "sayılamazsa onaysız durur")
esit(karar(hata, True, True), 0, "sayılamazsa onaylı devam")
esit(karar(hata, False, False), 0, "sayılamazsa deneme devam (paylaşım yok)")

esit(sinir.GUNLUK_SINIR, 4, "günlük sınır 4")
# gün istisnası: Rıdvan o gün için 5'e izin verdiyse 5. geçer, 6. durur; ertesi gün yine 4
sinir.GUN_SINIRI = {"2026-10-14": 5}
esit(karar(sahte(4), True, False), 0, "istisna günü 5. geçer")
esit(karar(sahte(5), True, False), 1, "istisna günü 6. durur")
esit(sinir.bugunun_siniri(datetime(2026, 10, 15).date()), 4, "ertesi gün 4")
sinir.GUN_SINIRI = asil_gun
sinir.say = asil_say
for gun, n in sinir.GUN_SINIRI.items():   # gerçek istisnalar geçerli tarih ve makul sayı olmalı
    esit(datetime.fromisoformat(gun).date().isoformat(), gun, f"istisna tarihi {gun}")
    esit(isinstance(n, int) and sinir.GUNLUK_SINIR < n <= 10, True, f"istisna sayısı {gun}")

print(f"Tamam: {gecen} sınama geçti.")
