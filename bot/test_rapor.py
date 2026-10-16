"""bot/rapor.py sınamaları (ağ yok, sahte Instagram). Çalıştır: python bot/test_rapor.py"""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rapor  # noqa: E402

TR = rapor.TR_SAAT
gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


def icinde(parca, metin, ad):
    global gecen
    assert parca in metin, f"{ad}: {parca!r} yok"
    gecen += 1


# biçim
esit(rapor.sayi(1234), "1.234", "binlik ayraç")
esit(rapor.sayi(2.5), "2,5", "ondalık virgül")
esit(rapor.sayi(None), "—", "boş")
esit(rapor.yuzde(1, 3), "%33", "yüzde")
esit(rapor.yuzde(1, 0), "—", "sıfıra bölme yok")
esit(rapor.saniye(4250), "4,2 sn", "izlenme süresi")


def medya(gun, saat, tur, **ist):
    z = datetime(2026, 10, gun, *saat, tzinfo=TR)
    return {"id": f"{gun}{saat}", "media_product_type": tur, "_zaman": z, "caption": "",
            "permalink": f"https://www.instagram.com/p/{gun}{saat[0]}/", "_ist": ist}


# kayıt üretimde, gönderiden birkaç dakika önce düşer; aynı saatte birden çok kayıt olabilir
satirlar = [("2026-10-12", "20:01", "Günlük özet", 4), ("2026-10-13", "09:58", "Reels", 6),
            ("2026-10-13", "09:59", "Rehber (deneme)", 6), ("2026-10-13", "19:50", "Günlük özet", 9),
            ("2026-10-14", "09:56", "Reels", 15), ("2026-10-14", "21:45", "Rehber Reels", 18),
            ("2026-10-14", "21:55", "Rehber", 20)]
ms = [medya(13, (10, 1), "REELS", reach=300, views=500, likes=20, comments=1, saved=3, shares=2,
            ig_reels_avg_watch_time=4200),
      medya(13, (20, 0), "FEED", reach=100, views=150, likes=8, comments=0, saved=1, shares=0, follows=2),
      medya(14, (10, 0), "REELS", reach=500, views=900, likes=30, comments=2, saved=6, shares=5,
            ig_reels_avg_watch_time=5100),
      medya(14, (21, 58), "FEED", reach=50, views=60, likes=2, comments=0, saved=4, shares=1, follows=0)]

# eşleme: deneme satırı atlanır, kayıt paylaşımdan birkaç dakika sonra düşer
rapor.paylasim_adlari(ms, satirlar)
esit([m["_ad"] for m in ms], ["Fiyat Reels'i", "Günlük özet", "Fiyat Reels'i", "Rehber"], "paylaşım adları")
m = medya(15, (9, 0), "REELS")   # öncesinde kayıt yok
m["caption"] = "Gram gümüş 88 ₺\nGüncel gümüş fiyatları · 15.10.2026"
rapor.paylasim_adlari([m], satirlar)
esit(m["_ad"], "Fiyat Reels'i", "açıklamadan ad")
m = medya(16, (11, 3), "REELS")
m["caption"] = "…\nYorumun 4 sayfası profildeki kaydırmalı gönderide de var →"
rapor.paylasim_adlari([m], [])
esit(m["_ad"], "Pazar yorumu Reels", "pazar Reels'i açıklamadan")

# günlük takipçi: dönem öncesi son kayıt başlangıç olur
g = rapor.gunluk_takipci(satirlar, date(2026, 10, 13), date(2026, 10, 15))
esit(g, [(date(2026, 10, 13), 9, 5), (date(2026, 10, 14), 20, 11)], "günlük takipçi")
esit(rapor._ort([{"_ist": {"r": 138}}, {"_ist": {"r": 139}}, {"_ist": {"r": 139}}], "r"), 139, "ortalama yuvarlama")

hesap = {"reach": 700, "reach:FOLLOWER": 70, "reach:NON_FOLLOWER": 630, "reach:REEL": 600, "reach:POST": 120,
         "views": 1800, "views:NON_FOLLOWER": 1500, "accounts_engaged": 40, "profile_links_taps": 3}
metin = rapor.rapor_yaz(ms, hesap, satirlar, date(2026, 10, 9), date(2026, 10, 15), "@gunlukgumus",
                        ["Hesap geneli x alınamadı (HTTP 400, kod 100)."], True, datetime(2026, 10, 15, 18, 30, tzinfo=TR))
icinde("# Haftalık Instagram raporu · @gunlukgumus", metin, "başlık")
icinde("9 Ekim – 15 Ekim 2026", metin, "dönem")
icinde("örnek (deneme)", metin, "deneme işareti")
icinde("**Takipçi:** 4 → **20** (+16)", metin, "takipçi özeti")
icinde("takip etmeyen: **630** (%90)", metin, "takip etmeyen payı")
icinde("Reels'ler ortalamada gönderilerin **5,3 katı**", metin, "Reels/gönderi oranı")
icinde("| Reels | 2 | 400 | 700 | 25 | 9 | 7 |", metin, "Reels satırı")
icinde("| Gönderi | 2 | 75 | 105 | 5 | 5 | 1 |", metin, "gönderi satırı")
icinde("En çok kaydedilen: [Fiyat Reels'i · Çar 14.10 10:00]", metin, "en çok kaydedilen")
icinde("| 4,2 sn |", metin, "izlenme süresi hücresi")
icinde("| 2 takip |", metin, "takip hücresi")
icinde("| Çar 14 Ekim | 20 | +11 |", metin, "takipçi günü")
icinde("- Hesap geneli x alınamadı", metin, "uyarı notlarda")
esit("## Goril" in metin, True, "akşam özeti varsa goril bölümü (gorilsiz karşılaştırma için)")
icinde("| goril yok | 1 | 150 | 100 | 0,30 | 0,33 |", metin, "gorilsiz akşam: sabaha oran")


# ---- goril: takipci.md'deki hâl eki, günüyle eşleme, hâl tablosu
def ozet(gun, saat, tur_adi, **ist):
    m = medya(gun, saat, "REELS", **ist)
    m["caption"] = ("Gümüş bugün %3,4 yükseldi: gram gümüş fiyatı 98,44 ₺\n🦍 Goril bugün sevinçli\nGünün gümüş özeti · …"
                    if tur_adi == "Günlük özet" else "Gram gümüş fiyatı bu hafta: …\nHaftalık gümüş özeti · 02–06 Kasım 2026")
    return m


satirlar = [("2026-10-19", "09:57", "Reels", 30), ("2026-10-19", "19:55", "Günlük özet · goril: sevinen", 31),
            ("2026-10-20", "09:56", "Reels", 31), ("2026-10-20", "19:56", "Günlük özet · goril: istif", 32),
            ("2026-10-20", "21:00", "Günlük özet · goril: gezinen (deneme)", 32),
            ("2026-10-21", "09:55", "Reels", 33), ("2026-10-21", "19:54", "Günlük özet", 33),
            ("2026-10-24", "09:55", "Haftalık özet · goril: uzulen", 34)]
ms = [medya(19, (10, 0), "REELS", reach=200, views=400, ig_reels_avg_watch_time=4000),
      ozet(19, (22, 25), "Günlük özet", reach=150, views=300, saved=2, shares=1, ig_reels_avg_watch_time=6000),  # 150 dk gecikme
      medya(20, (9, 59), "REELS", reach=100, views=200),
      ozet(20, (20, 0), "Günlük özet", reach=50, views=100),
      medya(21, (9, 58), "REELS", reach=100, views=100),
      ozet(21, (19, 58), "Günlük özet", reach=50, views=50),
      ozet(24, (10, 0), "Haftalık özet", reach=80, views=120, ig_reels_avg_watch_time=5500)]
rapor.paylasim_adlari(ms, satirlar)
esit([(m["_ad"], m["_goril"]) for m in ms],
     [("Fiyat Reels'i", None), ("Günlük özet", "sevinen"), ("Fiyat Reels'i", None), ("Günlük özet", "istif"),
      ("Fiyat Reels'i", None), ("Günlük özet", None), ("Haftalık özet", "uzulen")],
     "günüyle eşleme, 150 dk gecikme, deneme satırı atlanır, hâl eki ayrılır")
metin = rapor.rapor_yaz(ms, {}, satirlar, date(2026, 10, 19), date(2026, 10, 25), "@gunlukgumus", [], False,
                        datetime(2026, 10, 26, 9, 5, tzinfo=TR))
icinde("| goril yok | 1 | 50 | 50 | 0,50 | 0,50 |", metin, "gorilsiz akşam satırı")
icinde("| istifleyici | 1 | 100 | 50 | 0,50 | 0,50 |", metin, "istifleyici satırı")
icinde("| sevinen | 1 | 300 | 150 | 0,75 | 0,75 | 6,0 sn | 2 | 1 |", metin, "sevinen satırı")
icinde("| gorilli (hepsi) | 2 | 200 | 100 | 0,62 | 0,62 |", metin, "gorilli toplam satırı")
icinde("| Cmt 24.10 10:00 | üzülen | 120 | 80 | 5,5 sn |", metin, "haftalık özet satırı")
icinde("[Günlük özet · goril: sevinen]", metin, "tek tek tabloda hâl")
icinde("| Paylaşım | Adet |", metin, "paylaşım türü tablosu duruyor")
icinde("| Günlük özet | 3 |", metin, "hâl eki türü bölmez")
m = medya(22, (10, 0), "REELS", reach=1)
rapor.paylasim_adlari([m], satirlar)
esit("## Goril" in rapor.rapor_yaz([m], {}, satirlar, date(2026, 10, 22), date(2026, 10, 22), "", [], False,
                                   datetime(2026, 10, 23, 9, 5, tzinfo=TR)), False, "özet yoksa goril bölümü yok")

print(f"test_rapor: {gecen} sınama geçti")
