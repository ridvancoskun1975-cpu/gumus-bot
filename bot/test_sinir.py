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
# tahminler: sabah Reels'i hikâyesiz 1; akşam özeti, haftalık, aylık, rehber 2; pazar yorumu 3
esit((sinir.TAHMIN["reels"], sinir.TAHMIN["post"], sinir.TAHMIN["bilgi"], sinir.TAHMIN["yorum"],
      sinir.TAHMIN["kisa"]), (1, 2, 2, 3, 1), "tür tahminleri")


# ---------------------------------------------------------------- karar (GitHub okuması sahte)
def sahte(n):
    """Bugün n içerik gösterilmiş (n tane 1'lik çalıştırma)."""
    return lambda simdi=None, **kw: [(i, SIMDI, "paylaşıldı", "reels", 1) for i in range(n)]


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
        cikti = open(yol, encoding="utf-8").read().strip()
    finally:
        os.environ.pop("GITHUB_OUTPUT", None)
        os.unlink(yol)
    return kod, cikti.removeprefix("hikaye=")


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
    ("yorum", 0, True, False, (0, "tam")),     # pazar: 3
    ("yorum", 2, True, False, (0, "yok")),     # 2 + 3 = 5 → hikâyesiz 4
    ("yorum", 3, True, False, (1, "tam")),     # hikâyesiz de 5 → durur
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
sinir.GUN_SINIRI = asil_gun
sinir.say = asil_say
for gun, n in sinir.GUN_SINIRI.items():   # gerçek istisnalar geçerli tarih ve makul sayı olmalı
    esit(datetime.fromisoformat(gun).date().isoformat(), gun, f"istisna tarihi {gun}")
    esit(isinstance(n, int) and sinir.GUNLUK_SINIR < n <= 10, True, f"istisna sayısı {gun}")

print(f"Tamam: {gecen} sınama geçti.")
