"""bot/program.py sınamaları: bilgi sayfasındaki takvim ve saatler farklı günlerde doğru mu?

Çalıştırma: python bot/test_program.py
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi  # noqa: E402
import program as prg  # noqa: E402

TR = prg.TR_SAAT
HIKAYE = {"post", "hafta", "ay"}
KAYIT_BAS = date(2026, 10, 13)


def kayitlar(bugun):
    g, sonuc = KAYIT_BAS, []
    while g < bugun:
        if g.weekday() < 5:
            sonuc.append(g)
        g += timedelta(days=1)
    return sonuc


def p(yil, ay, gun, saat=9, dakika=0, rehber_hikaye=False):
    an = datetime(yil, ay, gun, saat, dakika, tzinfo=TR)
    return prg.program(an, kayitlar(an.date()), HIKAYE, rehber_hikaye=rehber_hikaye)


def satir(pr, bas):
    return next(s for s in pr["satirlar"] if s["ne"].startswith(bas))


sonuc = []


def kontrol(ad, kosul, ayrinti=""):
    sonuc.append(bool(kosul))
    print(("TAMAM " if kosul else "HATA  ") + ad + ("" if kosul else f": {ayrinti}"))


# İş akışı okuma
c = dict((cron, tur) for cron, tur in prg.cronlar())
# 28 Ekim 2026'dan beri cron'lar hedef saatten ~45 dk önce (GitHub gecikmesi), bot hedefe kadar bekler.
kontrol("cron → tür eşlemesi", c.get("10 6 * * 1-5") == "reels" and c.get("10 16 * * 1-5") == "post"
        and c.get("10 10 * * 1-5") == "bilgi" and c.get("10 7 * * 0") == "yorum" and c.get("10 6 * * 6") == "hafta", c)
kontrol("gösterilen saat hedeften: ~10:00 / ~20:00 / ~14:00 / ~11:00",
        prg.yayin_saati("10 6 * * 1-5", "reels") == "~10:00" and prg.yayin_saati("10 16 * * 1-5", "post") == "~20:00"
        and prg.yayin_saati("10 10 * * 1-5", "bilgi") == "~14:00" and prg.yayin_saati("10 7 * * 0", "yorum") == "~11:00"
        and prg.yayin_saati("10 6 * * 6", "hafta") == "~10:00")
kontrol("hedefi olmayan tür için eski kural (cron + 10 dk)", prg.yayin_saati("50 8 * * 3,5", "kart") == "~12:00"
        and prg.yayin_saati("50 8 * * 3,5") == "~12:00")
kontrol("hedef saatler ile cron'lar uyumlu (10–60 dk önce)", prg.hedef_denetle() == [], prg.hedef_denetle())
kontrol("bütün zamanlı türlerin hedefi var", all(t in prg.HEDEF_SAATLERI for _, t in prg.cronlar()), prg.cronlar())
kontrol("cron günleri", prg.cron_coz("10 7 * * 0")[1] == {6} and prg.cron_coz("10 6 * * 6")[1] == {5}
        and prg.cron_coz("10 6 * * 1-5")[1] == set(range(5)))

# Bekleme (hedef saate kadar): sahte saat ve sahte uyku ile
uykular = []
def sahte_uyu(sn):
    uykular.append(sn)
def an(s, d, sn=0):
    return datetime(2026, 10, 29, s, d, sn, tzinfo=TR)
uykular.clear(); b = prg.bekle("post", an(19, 20), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("akşam 19:20'de başlayan post 35 dk bekler", b == 35 * 60 and sum(uykular) == 35 * 60 and max(uykular) <= 300, (b, uykular))
uykular.clear(); b = prg.bekle("reels", an(9, 12, 30), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("sabah 09:12:30'da başlayan reels 09:55'e kadar bekler", b == 42 * 60 + 30 and sum(uykular) == b, (b, uykular))
uykular.clear(); b = prg.bekle("post", an(20, 31), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("hedef geçmişse beklemez (bugünkü gibi geç başlayan çalışma)", b == 0 and uykular == [], (b, uykular))
uykular.clear(); b = prg.bekle("post", an(19, 55), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("tam hedefte beklemez", b == 0 and uykular == [])
uykular.clear(); b = prg.bekle("yasal", an(9, 0), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("hedefi olmayan tür (yasal) beklemez", b == 0 and uykular == [])
uykular.clear(); b = prg.bekle("post", an(17, 0), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("hedef 60 dk'dan uzaksa beklemez (yanlış ayar koruması)", b == 0 and uykular == [])
uykular.clear(); b = prg.bekle("bilgi", an(13, 10), uyu=sahte_uyu, yaz=lambda *_: None)
kontrol("rehber 13:10 → 13:55, aylık özet ve arşiv aynı hedef", b == 45 * 60
        and prg.bekleme_suresi("ay", an(13, 10)) == 45 * 60 and prg.bekleme_suresi("kisa", an(13, 10)) == 45 * 60)
kontrol("pazar yorumu 10:10 → 10:55, cumartesi 09:10 → 09:55", prg.bekleme_suresi("yorum", an(10, 10)) == 45 * 60
        and prg.bekleme_suresi("hafta", an(9, 10)) == 45 * 60)
def patlayan(_):
    raise RuntimeError("uyku bozuk")
kontrol("bekleme hatası paylaşımı durdurmaz (0 döner, hata fırlatmaz)",
        prg.bekle("post", an(19, 30), uyu=patlayan, yaz=lambda *_: None) == 0)
kontrol("UTC verilen 'şimdi' de doğru (16:20Z = 19:20 TR → 35 dk)",
        prg.bekleme_suresi("post", datetime(2026, 10, 29, 16, 20, tzinfo=__import__("datetime").timezone.utc)) == 35 * 60)
kontrol("gece yarısını geçen cron günü kayar", prg.cron_coz("30 22 * * 1")[1] == {1})   # pazartesi 22:30 UTC = salı 01:30 TR

# 14 Ekim sabah: ilk hafta her gün, sonra salı/perşembe; bugünkü bölüm listede
a = p(2026, 10, 14)
r = satir(a, "Gümüş rehberi")
kontrol("14 Ekim: rehber satırı ilk hafta + düzen",
        "14–19 Ekim hafta içi her gün, 26 Ekim haftasından itibaren çarşamba" in r["ek"], r)
# 18 Ekim (Rıdvan "1 uygun"): kalan ilk hafta günleri ve düzenli günlerin başladığı hafta açık yazılır
r18 = satir(p(2026, 10, 18), "Gümüş rehberi")
# 19 Ekim 2026 (Rıdvan): rehber 26 Ekim haftasından itibaren haftada 1, çarşamba; arşiv Reels'i de rehber günü
# 19 Ekim 2026 (Rıdvan "evet"): 20–21 Ekim rehber günleri kalktı; ilk hafta 19 Ekim'de biter
kontrol("18 Ekim: 19 Ekim tek gün, 26 Ekim haftasından çarşamba",
        r18["ek"][:2] == ["19 Ekim Pazartesi, 26 Ekim haftasından itibaren çarşamba",
                          "sıradaki: 19 ve 28 Ekim; 4 ve 11 Kasım"], r18)
kontrol("21 Ekim sabahı: yalnızca çarşamba", satir(p(2026, 10, 21), "Gümüş rehberi")["zaman"] == "Çarşamba ~14:00",
        satir(p(2026, 10, 21), "Gümüş rehberi"))
kontrol("aralık ay geçişi", prg.aralik_metni([date(2026, 10, 30), date(2026, 11, 2)]) == "30 Ekim–2 Kasım hafta içi her gün")
kontrol("14 Ekim: sıradaki bugünle başlar", "sıradaki: 14, 15, 16 ve 19 Ekim" in r["ek"], r)
kontrol("14 Ekim: haftalık ilki 17 Ekim (kısmi hafta), not yok", satir(a, "Haftalık")["ek"] == [], satir(a, "Haftalık"))
kontrol("ilk haftalık 17 Ekim (kayıtlar 13 Ekim'de başladı, önceki hafta boş)",
        prg.ilk_haftalik(date(2026, 10, 14), {KAYIT_BAS, date(2026, 10, 14)}) == date(2026, 10, 17))
kontrol("önceki haftalar kayıtlıyken boş hafta özet vermez",
        prg.ilk_haftalik(date(2026, 10, 14), {date(2026, 10, 1), date(2026, 10, 13), date(2026, 10, 14)}) == date(2026, 10, 24)
        and prg.ilk_haftalik(date(2026, 10, 14), {date(2026, 9, 30)}) == date(2026, 10, 24))
# Cumartesi kısa Reels'i 16 Ekim 2026'da kaldırıldı (Rıdvan); rehber günü sesli Reels + hikâye
kontrol("cumartesi kısa Reels satırı yok", not any(s_["ne"].startswith("Rehberden kısa") for s_ in a["satirlar"]))
kontrol("rehber satırı sesli Reels ve hikâye",
        satir(p(2026, 10, 14, rehber_hikaye=True), "Gümüş rehberi")["ne"] == "Gümüş rehberi (sesli Reels ve hikâye)")
kontrol("rehber Reels kapalıyken kaydırmalı", prg.program(datetime(2026, 10, 14, 9, tzinfo=TR), rehber_reels=False,
        rehber_hikaye=True)["satirlar"][1]["ne"] == "Gümüş rehberi (kaydırmalı gönderi ve hikâye)")
# Rehber arşivi Reels'i ayrı satır/not olarak yazılmaz (Rıdvan, 18 Ekim 2026 "5 çıkar"); 19 Ekim 2026'dan beri
# haftalık rehber sırasında olduğu için rehber günleri arasında görünür (28 Ekim)
kontrol("arşiv Reels'i ayrı not olarak yazılmaz",
        not any("önceki bölümlerin" in e or "#3" in e for e in satir(p(2026, 10, 17), "Gümüş rehberi")["ek"]))
kontrol("aylık satırında 'rehber varsa' notu yok", satir(p(2026, 10, 17), "Aylık")["ek"] == ["sıradaki: 2 Kasım Pazartesi"],
        satir(p(2026, 10, 17), "Aylık"))
kontrol("14 Ekim: aylık 2 Kasım", "2 Kasım Pazartesi" in " ".join(satir(a, "Aylık")["ek"]))
kontrol("14 Ekim: ECB ~17:00 (yaz saati)", a["ecb"]["saat"] == "~17:00", a["ecb"])
# Rıdvan, 21 Ekim 2026 ("1"): "bazı günler" yerine günler yazılır
# (günler ayarlardan: rehber hikâyesi otomatik değilse rehber günü 4'ü aşmaz, yazılmaz)
_oz = satir(p(2026, 10, 21, rehber_hikaye=True), "Günün özeti")
kontrol("akşam özeti: rehber günü ve ayın ilk iş günü hikâyesiz (günlük sınır, 19 Ekim 2026)",
        _oz["ek"] == ["rehber günü (çarşamba) ve ayın ilk iş günü hikâyesiz"], _oz)
kontrol("akşam özeti: rehber hikâyesi kapalıyken yalnız ayın ilk iş günü",
        satir(a, "Günün özeti")["ek"] == ["ayın ilk iş günü hikâyesiz"], satir(a, "Günün özeti"))
kontrol("güncelleme saatleri", a["guncelleme"] == "Hafta içi ~10:00 ve ~20:00" and a["son_deger_saati"] == "~20:00")
kontrol("ECB kullanım cümlesi", a["ecb"]["kullanim"] == "~10:00 değeri önceki iş gününün, ~20:00 değeri o günün kurunu kullanır")

# 14 Ekim 15:00: bugünün bölümü artık sıradaki değil
b = p(2026, 10, 14, 15)
kontrol("14 Ekim öğleden sonra: sıradaki 15 Ekim'le başlar", "sıradaki: 15, 16, 19 ve 28 Ekim" in satir(b, "Gümüş rehberi")["ek"],
        satir(b, "Gümüş rehberi"))

# 22 Ekim: yalnızca çarşamba (haftada 1; Rıdvan, 19 Ekim 2026), arşiv Reels'i günleri dahil
d = p(2026, 10, 22)
r = satir(d, "Gümüş rehberi")
kontrol("22 Ekim: zaman 'Çarşamba ~14:00'", r["zaman"] == "Çarşamba ~14:00", r)
kontrol("22 Ekim: sıradaki 28 Ekim; 4, 11, 18 Kasım", "sıradaki: 28 Ekim; 4, 11 ve 18 Kasım" in r["ek"], r)
kontrol("22 Ekim: haftalık notu yok (24 Ekim gelecek cumartesi)", satir(d, "Haftalık")["ek"] == [], satir(d, "Haftalık"))

# 26 Ekim: kış saati, ECB ~18:00 (20:00 yine o günün kurunu kullanır)
e = p(2026, 10, 26)
kontrol("26 Ekim: ECB ~18:00 (kış saati)", e["ecb"]["saat"] == "~18:00", e["ecb"])
kontrol("26 Ekim: kullanım aynı", e["ecb"]["kullanim"].startswith("~10:00 değeri önceki iş gününün, ~20:00 değeri o günün"), e["ecb"])

# Hafta sonu: ECB saati sıradaki iş gününe göre
f = p(2026, 10, 24)
kontrol("cumartesi: ECB saati pazartesiye göre (26 Ekim → ~18:00)", f["ecb"]["saat"] == "~18:00", f["ecb"])

# 13 Kasım: haftada 1 hızla bölümler sürüyor
g = p(2026, 11, 13)
r = satir(g, "Gümüş rehberi")
kontrol("13 Kasım: sıradaki 18, 25 Kasım; 2, 9 Aralık", "sıradaki: 18 ve 25 Kasım; 2 ve 9 Aralık" in r["ek"], r)
# Son hazır bölümün ertesi günü: hazır bölüm kalmadı (aylık paket eklemediyse). Tarih sabit yazılmaz; yeni bölümler
# (aylık paket, 20 Ekim 2026 ön paketi) eklendikçe son gün ileri kayar.
_son = max(g for g, _ in bilgi.yayim_listesi()) + timedelta(days=1)
g = p(_son.year, _son.month, _son.day)
r = satir(g, "Gümüş rehberi")
kontrol(f"{_son:%d.%m.%Y} (son bölümün ertesi günü): 'şimdilik sıradaki bölüm yok'",
        "şimdilik sıradaki bölüm yok" in r["ek"], r)


# Rehber hikâyesi otomatik kapalıyken (14 Ekim'den beri) sayfa hikâye/öne çıkan yazmaz; açıksa yazar
r_kapali = satir(a, "Gümüş rehberi")
kontrol("otomatik kapalı: 'hikâye' ve 'Öne çıkanlar' yok", "hikâye" not in r_kapali["ne"]
        and not any("Öne çıkanlar" in e for e in r_kapali["ek"]) and a["rehber_hikaye"] is False, r_kapali)
r_acik = satir(p(2026, 10, 14, rehber_hikaye=True), "Gümüş rehberi")
kontrol("otomatik açık: 've hikâye' var, 'Öne çıkanlar' notu yok (18 Ekim)", "ve hikâye" in r_acik["ne"]
        and not any("Öne çıkanlar" in e for e in r_acik["ek"]), r_acik)
import main as bot  # noqa: E402
bot_etiket = lambda g: bot.HASHTAG_HAFTA.index(bot.hashtag_sec("hafta", g))
# Haftalık özetin etiket sırası (Rıdvan 14 Ekim 2026: ilk özet 17 Ekim yatırım ağırlıklı 1. setle)
kontrol("17 Ekim haftalık 1. set, 24 Ekim 2. set",
        bot_etiket(date(2026, 10, 17)) == 0 and bot_etiket(date(2026, 10, 24)) == 1 and bot_etiket(date(2026, 10, 31)) == 0)
kontrol("main'deki ayar okunuyor", prg.program(datetime(2026, 10, 14, 9, tzinfo=TR), [], HIKAYE)["rehber_hikaye"]
        == bot.REHBER_HIKAYE_OTOMATIK)

# Pazar yorumu 15 Ekim 2026'dan beri Reels ve hikâye olarak da gider; sayfa bunu botun ayarından yazar
y_acik = satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE, yorum_reels=True, pazar_hikaye=True), "Kısa ve orta vade")
y_hikayesiz = satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE, yorum_reels=True, pazar_hikaye=False), "Kısa ve orta vade")
kontrol("pazar hikâyesi kapalıyken 'kaydırmalı gönderi ve Reels'", y_hikayesiz["ne"].endswith("(kaydırmalı gönderi ve Reels)"), y_hikayesiz)
y_kapali = satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE, yorum_reels=False), "Kısa ve orta vade")
kontrol("pazar yorumu Reels açıkken 'kaydırmalı gönderi, Reels ve hikâye'",
        y_acik["ne"].endswith("(kaydırmalı gönderi, Reels ve hikâye)"), y_acik)
kontrol("pazar yorumu Reels kapalıyken yalnızca 'kaydırmalı gönderi'", y_kapali["ne"].endswith("(kaydırmalı gönderi)"), y_kapali)
kontrol("main'deki YORUM_REELS ve PAZAR_HIKAYE okunuyor", ("Reels" in satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [],
        HIKAYE), "Kısa ve orta vade")["ne"]) == bool(bot.YORUM_REELS)
        and ("hikâye" in satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE), "Kısa ve orta vade")["ne"])
        == bool(bot.PAZAR_HIKAYE))

# Satırlar sıralı ve hepsinin adı var
kontrol("satır sırası", [s["zaman"].split(" ~")[0] for s in a["satirlar"]][:2] == ["Hafta içi", "Rehber günleri"], a["satirlar"])
kontrol("bilinmeyen tür yok", all(not s["ne"][:1].islower() for s in a["satirlar"]))
kontrol("alt bilgi", a["fiyat_ozet"] == "hafta içi her gün")

print(f"\n{sum(sonuc)}/{len(sonuc)} sınama geçti")
sys.exit(0 if all(sonuc) else 1)
