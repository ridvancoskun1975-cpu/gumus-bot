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
# 19 Ekim 2026'dan beri takipçinin gördüğü her şey sayılır (akış + Reels + hikâye): gerçek sayı "gorunen-…"
# eserinden, yoksa türüne göre tahmin (sinir.TAHMIN; tür "onizleme-<tür>" eserinden).
calistirmalar = [{"id": i} for i in range(1, 11)]
isler = {
    # dün 22:30 TR paylaşıldı → sayılmaz
    1: [is_("kontrol", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-13T19:30:00Z")],
    # bugün 00:10 TR (13 Ekim 21:10 UTC) sabah Reels'i gibi: eser yok, tür reels → 1
    2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:10:00Z")],
    # bugün 04:51 TR elle rehber hikâyesi: gerçek sayı eserde, 3 video → 3
    3: [is_("uret", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-14T01:51:28Z")],
    # deneme: yayinla atlandı → sayılmaz
    4: [is_("uret", "completed", "success"), is_("yayinla", "completed", "skipped", bit="2026-10-14T02:00:00Z")],
    # paylaşım hata verdi, hiçbir şey paylaşmadı (eser yok) → sayılmaz
    5: [is_("yayinla", "completed", "failure", bit="2026-10-14T03:00:00Z")],
    # başka çalıştırma şu an paylaşıyor (akşam özeti) → tahmin 2
    6: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:00Z")],
    # bu çalıştırma → sayılmaz
    7: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:30Z")],
    # sınırda durdurulmuş çalıştırma (kontrol hata) → sayılmaz
    8: [is_("kontrol", "completed", "failure")],
    # paylaşım işi hata verdi ama 1 şey paylaştı (eser gorunen-1-1) → 1, "yarım"
    9: [is_("yayinla", "completed", "failure", bit="2026-10-14T04:00:00Z")],
    # yeniden çalıştırılmış iş: iki denemenin sayısı toplanır (1 + 2) → 3
    10: [is_("yayinla", "completed", "success", bit="2026-10-14T05:00:00Z")],
}
eserler = {
    2: ["github-pages", "onizleme-reels"],
    3: ["onizleme-hikaye", "gorunen-1-3"],
    5: ["onizleme-post"],
    6: ["onizleme-post"],
    9: ["onizleme-bilgi", "gorunen-1-1"],
    10: ["onizleme-yorum", "gorunen-1-1", "gorunen-2-2"],
}
say = sinir.paylasim_sayisi(calistirmalar, isler, SIMDI, 7, eserler)
esit([x[0] for x in say], [2, 3, 9, 10, 6], "sayılan çalıştırmalar")
esit([x[2] for x in say], ["paylaşıldı", "paylaşıldı", "yarım", "paylaşıldı", "sürüyor"], "durumlar")
esit([x[4] for x in say], [1, 3, 1, 3, 2], "her çalıştırmanın gösterdiği içerik")
esit(sinir.toplam(say), 10, "toplam")
esit(len(sinir.paylasim_sayisi([], {}, SIMDI, 0)), 0, "boş gün")
gy = {1: [is_("yayinla", "completed", "success", bit="2026-10-13T20:59:59Z")],   # 23:59:59 TR dün
      2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:00:00Z")]}   # 00:00 TR bugün
esit([x[0] for x in sinir.paylasim_sayisi([{"id": 1}, {"id": 2}], gy, SIMDI, 0)], [2], "gece yarısı")
# eser okunamazsa (eski çalıştırma, tür bilinmiyor) güvenli taraf: 2 sayılır
esit(sinir.paylasim_sayisi([{"id": 2}], {2: gy[2]}, SIMDI, 0)[0][4], 2, "tür bilinmiyorsa 2")
# tahminler: sabah Reels'i hikâyesiz 1; akşam özeti, haftalık, aylık, rehber 2; pazar yorumu 2 (25 Ekim 2026'dan beri hikâyesiz)
esit((sinir.TAHMIN["reels"], sinir.TAHMIN["post"], sinir.TAHMIN["bilgi"], sinir.TAHMIN["yorum"],
      sinir.TAHMIN["kisa"]), (1, 2, 2, 2, 1), "tür tahminleri")


# ---------------------------------------------------------------- karar (GitHub okuması sahte)
def sahte(n):
    """Bugün n içerik gösterilmiş (n tane 1'lik çalıştırma). Tür "hikaye": çift paylaşım kilidinin dışında, böylece
    sınır sınamaları kilide takılmaz (kilit aşağıda ayrıca sınanır)."""
    return lambda simdi=None, **kw: [(i, SIMDI, "paylaşıldı", "hikaye", 1) for i in range(n)]


def hata(simdi=None, **kw):
    raise sinir.SayilamadiHatasi("bağlantı yok")


def karar(sayici, yayin, onay, tur="bilgi"):
    """(çıkış kodu, hikaye çıktısı)"""
    import os
    import tempfile
    sinir.say = sayici
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        yol = f.name
    os.environ["GITHUB_OUTPUT"] = yol
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            kod = sinir.kontrol(yayin, onay, tur, "3", simdi=SIMDI)
        cikti = dict(x.split("=", 1) for x in open(yol, encoding="utf-8").read().split())
    finally:
        os.environ.pop("GITHUB_OUTPUT", None)
        os.unlink(yol)
    return kod, cikti.get("hikaye")


asil_say, asil_gun = sinir.say, sinir.GUN_SINIRI
sinir.GUN_SINIRI = {}   # sınamalar gerçek gün istisnalarından bağımsız
# tür, bugün gösterilen, yayın, onay → (0 devam / 1 dur, hikâye tam / yok)
for tur, n, yayin, onay, bek in [
    ("reels", 0, True, False, (0, "tam")),     # sabah Reels'i
    ("bilgi", 1, True, False, (0, "tam")),     # rehber: 1 + 2 = 3
    ("post", 3, True, False, (0, "yok")),      # rehber günü akşamı: 3 + 2 = 5 → hikâyesiz 4
    ("post", 1, True, False, (0, "tam")),      # olağan akşam: 1 + 2 = 3
    ("post", 2, True, False, (0, "tam")),      # 2 + 2 = 4 sınırda, tam
    ("post", 4, True, False, (1, "tam")),      # hikâyesiz de 5 → onaysız durur
    ("post", 4, True, True, (0, "tam")),       # onaylı: tam gider
    ("yorum", 0, True, False, (0, "tam")),     # pazar: 2 (kaydırmalı + Reels)
    ("yorum", 2, True, False, (0, "tam")),     # 2 + 2 = 4 sınırda
    ("yorum", 3, True, False, (1, "tam")),     # 3 + 2 = 5, bırakılacak hikâye yok → durur
    ("ay", 1, True, False, (0, "tam")),        # aylık özet günü 14:00: 1 + 2 = 3
    ("hafta", 0, True, False, (0, "tam")),
    ("kisa", 3, True, False, (0, "tam")),      # 3 + 1 = 4
    ("kisa", 4, True, False, (1, "tam")),      # hikâyesi olmayan tür: durur
    ("hikaye", 4, True, False, (1, "tam")),    # elle hikâye bırakılamaz: durur
    ("reels", 9, False, False, (0, "tam")),    # deneme: sınır yok
]:
    esit(karar(sahte(n), yayin, onay, tur), bek, f"{tur} n={n} yayın={yayin} onay={onay}")
esit(karar(hata, True, False), (1, "tam"), "sayılamazsa onaysız durur")
esit(karar(hata, True, True), (0, "tam"), "sayılamazsa onaylı devam")
esit(karar(hata, False, False), (0, "tam"), "sayılamazsa deneme devam (paylaşım yok)")

esit(sinir.GUNLUK_SINIR, 4, "günlük sınır 4")
# Olağan haftanın hiçbir günü onaysız 4'ü aşmaz (Rıdvan, 19 Ekim 2026): gün sırasıyla çalıştırmalar
gunler = {
    "pazartesi": ["reels", "post"], "rehber günü (çarşamba)": ["reels", "bilgi", "post"],
    "aylık özet günü": ["reels", "ay", "post"], "cumartesi": ["hafta"], "pazar": ["yorum"],
    "arşiv Reels'i günü": ["reels", "kisa", "post"],
}
for ad, sira in gunler.items():
    gosterilen = 0
    for tur in sira:
        kod, hk = karar(sahte(gosterilen), True, False, tur)
        esit(kod, 0, f"{ad}: {tur} onaysız gider")
        gosterilen += sinir.HIKAYESIZ[tur] if hk == "yok" else sinir.TAHMIN[tur]
    esit(gosterilen <= 4, True, f"{ad}: {gosterilen} ≤ 4")
# gün istisnası: Rıdvan o gün için 5'e izin verdiyse 5. geçer, 6. durur; ertesi gün yine 4
sinir.GUN_SINIRI = {"2026-10-14": 5}
esit(karar(sahte(4), True, False, "reels"), (0, "tam"), "istisna günü 5. geçer")
esit(karar(sahte(5), True, False, "reels"), (1, "tam"), "istisna günü 6. durur")
esit(sinir.bugunun_siniri(datetime(2026, 10, 15).date()), 4, "ertesi gün 4")
# ---------------------------------------------------------------- çift paylaşım kilidi (Rıdvan, 3 Kasım 2026)
# "çift paylaşım da olmasın lütfen": bu tür bugün paylaşıldıysa yedek cron, nöbetçi ya da geç gelen zamanlı
# çalışma paylaşmadan, hata vermeden biter (tekrar=evet). Yalnız onay=true kilidi aşar.
def tekrar_ciktisi(sayici, yayin, onay, tur, konu=""):
    import os
    import tempfile
    sinir.say = sayici
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        yol = f.name
    os.environ["GITHUB_OUTPUT"] = yol
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            kod = sinir.kontrol(yayin, onay, tur, konu, SIMDI)
        cikti = dict(s.split("=", 1) for s in Path(yol).read_text().split())
    finally:
        os.environ.pop("GITHUB_OUTPUT", None)
    return kod, cikti.get("tekrar", "hayir"), cikti.get("hikaye")


def bugun(*kayitlar):
    return lambda simdi=None, **kw: list(kayitlar)


sabah = (101, SIMDI, "paylaşıldı", "reels", 1)
yarim = (102, SIMDI, "yarım", "post", 1)
suren = (103, SIMDI, "sürüyor", "reels", 1)
esit(tekrar_ciktisi(bugun(sabah), True, False, "reels"), (0, "evet", "tam"), "kilit: Reels bugün gitti, ikinci durur")
esit(tekrar_ciktisi(bugun(sabah), True, False, "post"), (0, "hayir", "tam"), "kilit: başka tür (akşam) etkilenmez")
esit(tekrar_ciktisi(bugun(sabah), True, True, "reels"), (0, "hayir", "tam"), "kilit: onay=true aşar")
esit(tekrar_ciktisi(bugun(sabah), False, False, "reels"), (0, "hayir", "tam"), "kilit: deneme etkilenmez")
esit(tekrar_ciktisi(bugun(yarim), True, False, "post"), (0, "evet", "tam"), "kilit: yarım kalan (bir şey paylaşan) da sayılır")
esit(tekrar_ciktisi(bugun(suren), True, False, "reels"), (0, "hayir", "tam"), "kilit: süren çalıştırma sayılmaz")
esit(tekrar_ciktisi(bugun((104, SIMDI, "paylaşıldı", "hikaye", 1)), True, False, "hikaye"), (0, "hayir", "tam"),
     "kilit: elle rehber hikâyesi kapsam dışı")
esit(tekrar_ciktisi(bugun(), True, False, "reels"), (0, "hayir", "tam"), "kilit: bugün bir şey yoksa paylaşır")
# kilit, sınırdan önce gelir: gün dolu olsa bile ikinci Reels hata vermeden (kırmızı olmadan) atlanır
dolu = [(200 + i, SIMDI, "paylaşıldı", "hikaye", 1) for i in range(3)] + [sabah]
esit(tekrar_ciktisi(bugun(*dolu), True, False, "reels"), (0, "evet", "tam"), "kilit: gün doluyken de sessiz atlar")
esit(sinir.TEKIL >= {"reels", "post", "hafta", "ay", "yorum", "bilgi", "kisa"}, True, "zamanlı türlerin hepsi kilitli")
pazar = (104, SIMDI, "paylaşıldı", "yorum", 2)
esit(tekrar_ciktisi(bugun(pazar), True, False, "yorum"), (0, "evet", "tam"), "kilit: pazar yorumu ikinci kez gitmez")
esit(tekrar_ciktisi(bugun(pazar), True, False, "yorum", "reels-tekrar"), (0, "hayir", "tam"),
     "kilit: pazar Reels'ini yeniden gönderme (konu reels-tekrar) onaysız geçer")
# ikinci kilit (Instagram) paylaşmadan bitirdiyse: eser "gorunen-1-0" → gün artmaz ama tür paylaşılmış sayılır
atlanan = sinir.paylasim_sayisi(
    [{"id": 301}], {301: [is_("yayinla", "completed", "success", bit="2026-10-14T07:00:00Z")]}, SIMDI, 0,
    {301: ["gorunen-1-0", "onizleme-reels"]})
esit([(x[2], x[3], x[4]) for x in atlanan], [("paylaşıldı", "reels", 0)], "atlanan çalıştırma 0 sayılır")
hatali = sinir.paylasim_sayisi(
    [{"id": 302}], {302: [is_("yayinla", "completed", "failure", bit="2026-10-14T07:00:00Z")]}, SIMDI, 0,
    {302: ["gorunen-1-0", "onizleme-post"]})
esit(hatali, [], "hiçbir şey paylaşmadan hata veren çalıştırma sayılmaz (yeniden denenebilir)")

# ---------------------------------------------------------------- gece yarısı kuralı (4 Kasım 2026)
# GitHub 3 Kasım 19:10 TR zamanlı çalışmasını 4 Kasım 00:43'te başlattı; kilit onu 4 Kasım'ın özeti sanıp 00:44'te
# ikinci özeti attı. (1) Geç kalan zamanlı çalışma paylaşmaz; (2) kilit 00:00–05:00 arası paylaşımı o güne saymaz.
def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


# son_tetik: cron'un asıl tetik anı
esit(sinir.son_tetik("10 16 * * 1-5", utc(2026, 11, 3, 21, 43)), utc(2026, 11, 3, 16, 10), "son tetik: 3 Kasım akşamı")
esit(sinir.son_tetik("37 16 * * 1-5", utc(2026, 11, 3, 21, 54)), utc(2026, 11, 3, 16, 37), "son tetik: yedek cron")
esit(sinir.son_tetik("10 6 * * 1-5", utc(2026, 11, 2, 5, 0)), utc(2026, 10, 30, 6, 10), "son tetik: pazartesi sabahı → cuma")
esit(sinir.son_tetik("10 7 * * 0", utc(2026, 11, 1, 7, 40)), utc(2026, 11, 1, 7, 10), "son tetik: pazar (0)")
esit(sinir.son_tetik("10 6 * * 6", utc(2026, 10, 31, 6, 10)), utc(2026, 10, 31, 6, 10), "son tetik: tam anında")
esit(sinir.son_tetik("bozuk", utc(2026, 11, 3, 21, 43)), None, "okunamayan cron → None")
esit(sinir.son_tetik("", utc(2026, 11, 3, 21, 43)), None, "boş cron → None")
# gec_kalmis
esit(sinir.gec_kalmis("10 16 * * 1-5", "post", utc(2026, 11, 3, 21, 43)) is not None, True,
     "3 Kasım 19:10 çalışması 00:43'te: paylaşmaz (gün değişti)")
esit(sinir.gec_kalmis("10 16 * * 1-5", "post", utc(2026, 11, 3, 16, 55)), None, "45 dk gecikme: paylaşır")
esit(sinir.gec_kalmis("10 16 * * 1-5", "post", utc(2026, 11, 3, 19, 29)), None, "akşam 22:29: paylaşır")
esit(sinir.gec_kalmis("10 16 * * 1-5", "post", utc(2026, 11, 3, 19, 30)) is not None, True, "akşam 22:30: paylaşmaz")
esit(sinir.gec_kalmis("10 6 * * 1-5", "reels", utc(2026, 11, 3, 15, 30)) is not None, True,
     "sabah Reels'i 18:30'da gelirse paylaşmaz")
esit(sinir.gec_kalmis("10 6 * * 1-5", "reels", utc(2026, 11, 3, 8, 0)), None, "sabah Reels'i 11:00'de: paylaşır")
esit(sinir.gec_kalmis("10 10 * * 1-5", "bilgi", utc(2026, 11, 3, 17, 47)) is not None, True,
     "13:10 rehber çalışması 20:47'de: paylaşmaz (son saat 18:30)")
esit(sinir.gec_kalmis("", "post", utc(2026, 11, 3, 21, 43)), None, "elle / nöbetçi (cron yok): etkilenmez")
for t in sinir.SON_SAAT:
    esit(t in sinir.TEKIL, True, f"son saat türü kilitli: {t}")


def gec_ciktisi(cron, simdi, tur="post", yayin=True, kayitlar=()):
    import os
    import tempfile
    sinir.say = bugun(*kayitlar)
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        yol = f.name
    os.environ["GITHUB_OUTPUT"] = yol
    try:
        with contextlib.redirect_stdout(io.StringIO()) as o:
            kod = sinir.kontrol(yayin, False, tur, "", simdi, cron=cron)
        cikti = dict(x.split("=", 1) for x in Path(yol).read_text().split())
    finally:
        os.environ.pop("GITHUB_OUTPUT", None)
    return kod, cikti.get("tekrar", "hayir"), o.getvalue()


k, t, yazi = gec_ciktisi("10 16 * * 1-5", utc(2026, 11, 3, 21, 43))
esit((k, t), (0, "evet"), "kontrol: 00:43'teki geç zamanlı çalışma hata vermeden paylaşmadan biter")
esit("Geç kalan zamanlı çalışma" in yazi, True, "kontrol: nedeni günlüğe yazar")
esit(gec_ciktisi("10 16 * * 1-5", utc(2026, 11, 3, 21, 43), yayin=False)[:2], (0, "hayir"), "deneme etkilenmez")
esit(gec_ciktisi("10 16 * * 1-5", utc(2026, 11, 3, 16, 55))[:2], (0, "hayir"), "zamanında zamanlı çalışma paylaşır")
# Kilit: 4 Kasım 00:47'de giden (dünün gecikmiş) özet, 4 Kasım akşamki özeti durdurmaz
gecikmis = (41724390910, utc(2026, 11, 3, 21, 47), "paylaşıldı", "post", 2)
esit(sinir.bugun_paylasildi([gecikmis], "post", utc(2026, 11, 4, 16, 55)), None,
     "kilit: 00:47'deki özet o günün akşam özetini durdurmaz")
esit(sinir.bugun_paylasildi([gecikmis], "post", utc(2026, 11, 3, 22, 30)) is not None, True,
     "kilit: gece 01:30'da gelen ikinci özet 00:47'dekini görür ve gitmez (gece çift paylaşım yok)")
esit(gec_ciktisi("10 16 * * 1-5", utc(2026, 11, 4, 16, 55), kayitlar=[gecikmis])[:2], (0, "hayir"),
     "4 Kasım akşam özeti 00:47'deki yüzünden durmaz")
sabah_05 = (7, utc(2026, 11, 4, 2, 0), "paylaşıldı", "reels", 1)   # 05:00 TR
esit(sinir.bugun_paylasildi([sabah_05], "reels", utc(2026, 11, 4, 7, 0)) is not None, True,
     "kilit: 05:00 ve sonrası sayılır")
k, t, _ = gec_ciktisi("", utc(2026, 11, 3, 22, 30), kayitlar=[gecikmis])
esit((k, t), (0, "evet"), "kontrol: gece elle başlatılan ikinci özet kilide takılır")
esit(sinir.toplam(sinir.paylasim_sayisi([{"id": 9}], {9: [is_("yayinla", "completed", "success",
     bit="2026-11-03T21:47:45Z")]}, utc(2026, 11, 4, 16, 55), 0, {9: ["gorunen-1-2", "onizleme-post"]})), 2,
     "günlük sınır: gece giden de takipçi gördüğü için sayılır")
sys.path.insert(0, str(Path(__file__).parent))
import nobetci  # noqa: E402
esit(nobetci.SON_SAAT is sinir.SON_SAAT, True, "nöbetçi ve zamanlı çalışma aynı son saat penceresi")

sinir.GUN_SINIRI = asil_gun
sinir.say = asil_say
for gun, n in sinir.GUN_SINIRI.items():   # gerçek istisnalar geçerli tarih ve makul sayı olmalı
    esit(datetime.fromisoformat(gun).date().isoformat(), gun, f"istisna tarihi {gun}")
    esit(isinstance(n, int) and sinir.GUNLUK_SINIR < n <= 10, True, f"istisna sayısı {gun}")

print(f"Tamam: {gecen} sınama geçti.")
