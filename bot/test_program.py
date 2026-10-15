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
kontrol("cron → tür eşlemesi", c.get("50 6 * * 1-5") == "reels" and c.get("50 16 * * 1-5") == "post"
        and c.get("50 10 * * 1-5") == "bilgi" and c.get("50 7 * * 0") == "yorum", c)
kontrol("cron saati TR + gecikme", prg.yayin_saati("50 6 * * 1-5") == "~10:00" and prg.yayin_saati("50 16 * * 1-5") == "~20:00")
kontrol("cron günleri", prg.cron_coz("50 7 * * 0")[1] == {6} and prg.cron_coz("50 6 * * 6")[1] == {5}
        and prg.cron_coz("50 6 * * 1-5")[1] == set(range(5)))
kontrol("gece yarısını geçen cron günü kayar", prg.cron_coz("30 22 * * 1")[1] == {1})   # pazartesi 22:30 UTC = salı 01:30 TR

# 14 Ekim sabah: ilk hafta her gün, sonra salı/perşembe; bugünkü bölüm listede
a = p(2026, 10, 14)
r = satir(a, "Gümüş rehberi")
kontrol("14 Ekim: rehber satırı ilk hafta + düzen", "21 Ekim'e kadar hafta içi her gün, sonra salı ve perşembe" in r["ek"], r)
kontrol("14 Ekim: sıradaki bugünle başlar", "sıradaki: 14, 15, 16 ve 19 Ekim" in r["ek"], r)
kontrol("14 Ekim: haftalık ilki 17 Ekim (kısmi hafta), not yok", satir(a, "Haftalık")["ek"] == [], satir(a, "Haftalık"))
kontrol("ilk haftalık 17 Ekim (kayıtlar 13 Ekim'de başladı, önceki hafta boş)",
        prg.ilk_haftalik(date(2026, 10, 14), {KAYIT_BAS, date(2026, 10, 14)}) == date(2026, 10, 17))
kontrol("önceki haftalar kayıtlıyken boş hafta özet vermez",
        prg.ilk_haftalik(date(2026, 10, 14), {date(2026, 10, 1), date(2026, 10, 13), date(2026, 10, 14)}) == date(2026, 10, 24)
        and prg.ilk_haftalik(date(2026, 10, 14), {date(2026, 9, 30)}) == date(2026, 10, 24))
kontrol("14 Ekim: kısa Reels 17 Ekim #3", "17 Ekim Cumartesi (rehber #3)" in " ".join(satir(a, "Rehberden kısa")["ek"]))
kontrol("14 Ekim: aylık 2 Kasım", "2 Kasım Pazartesi" in " ".join(satir(a, "Aylık")["ek"]))
kontrol("14 Ekim: ECB ~17:00 (yaz saati)", a["ecb"]["saat"] == "~17:00", a["ecb"])
kontrol("güncelleme saatleri", a["guncelleme"] == "Hafta içi ~10:00 ve ~20:00" and a["son_deger_saati"] == "~20:00")
kontrol("ECB kullanım cümlesi", a["ecb"]["kullanim"] == "~10:00 değeri önceki iş gününün, ~20:00 değeri o günün kurunu kullanır")

# 14 Ekim 15:00: bugünün bölümü artık sıradaki değil
b = p(2026, 10, 14, 15)
kontrol("14 Ekim öğleden sonra: sıradaki 15 Ekim'le başlar", "sıradaki: 15, 16, 19 ve 20 Ekim" in satir(b, "Gümüş rehberi")["ek"],
        satir(b, "Gümüş rehberi"))

# 22 Ekim: yalnızca salı/perşembe
d = p(2026, 10, 22)
r = satir(d, "Gümüş rehberi")
kontrol("22 Ekim: zaman 'Salı ve perşembe ~14:00'", r["zaman"] == "Salı ve perşembe ~14:00", r)
kontrol("22 Ekim: sıradaki 27, 29 Ekim; 3, 5 Kasım", "sıradaki: 27 ve 29 Ekim; 3 ve 5 Kasım" in r["ek"], r)
kontrol("22 Ekim: haftalık notu yok (24 Ekim gelecek cumartesi)", satir(d, "Haftalık")["ek"] == [], satir(d, "Haftalık"))

# 26 Ekim: kış saati, ECB ~18:00 (20:00 yine o günün kurunu kullanır)
e = p(2026, 10, 26)
kontrol("26 Ekim: ECB ~18:00 (kış saati)", e["ecb"]["saat"] == "~18:00", e["ecb"])
kontrol("26 Ekim: kullanım aynı", e["ecb"]["kullanim"].startswith("~10:00 değeri önceki iş gününün, ~20:00 değeri o günün"), e["ecb"])

# Hafta sonu: ECB saati sıradaki iş gününe göre
f = p(2026, 10, 24)
kontrol("cumartesi: ECB saati pazartesiye göre (26 Ekim → ~18:00)", f["ecb"]["saat"] == "~18:00", f["ecb"])

# 13 Kasım: hazır bölüm kalmadı
g = p(2026, 11, 13)
r = satir(g, "Gümüş rehberi")
kontrol("13 Kasım: 'şimdilik sıradaki bölüm yok'", "şimdilik sıradaki bölüm yok" in r["ek"], r)
kontrol("13 Kasım: kısa Reels sürüyor (14 Kasım #7)", "14 Kasım Cumartesi (rehber #7)" in " ".join(satir(g, "Rehberden kısa")["ek"]))

# 3 Ocak 2027: kısa Reels de bitti
h = p(2027, 1, 3)
kontrol("3 Ocak 2027: kısa Reels bitti", "yeni rehber bölümleri eklenince devam eder" in satir(h, "Rehberden kısa")["ek"])

# Rehber hikâyesi otomatik kapalıyken (14 Ekim'den beri) sayfa hikâye/öne çıkan yazmaz; açıksa yazar
r_kapali = satir(a, "Gümüş rehberi")
kontrol("otomatik kapalı: 'hikâye' ve 'Öne çıkanlar' yok", "hikâye" not in r_kapali["ne"]
        and not any("Öne çıkanlar" in e for e in r_kapali["ek"]) and a["rehber_hikaye"] is False, r_kapali)
r_acik = satir(p(2026, 10, 14, rehber_hikaye=True), "Gümüş rehberi")
kontrol("otomatik açık: 've hikâye' ve 'Öne çıkanlar' var", "ve hikâye" in r_acik["ne"]
        and any("Öne çıkanlar" in e for e in r_acik["ek"]), r_acik)
import main as bot  # noqa: E402
bot_etiket = lambda g: bot.HASHTAG_HAFTA.index(bot.hashtag_sec("hafta", g))
# Haftalık özetin etiket sırası (Rıdvan 14 Ekim 2026: ilk özet 17 Ekim yatırım ağırlıklı 1. setle)
kontrol("17 Ekim haftalık 1. set, 24 Ekim 2. set",
        bot_etiket(date(2026, 10, 17)) == 0 and bot_etiket(date(2026, 10, 24)) == 1 and bot_etiket(date(2026, 10, 31)) == 0)
kontrol("main'deki ayar okunuyor", prg.program(datetime(2026, 10, 14, 9, tzinfo=TR), [], HIKAYE)["rehber_hikaye"]
        == bot.REHBER_HIKAYE_OTOMATIK)

# Pazar yorumu 15 Ekim 2026'dan beri Reels ve hikâye olarak da gider; sayfa bunu botun ayarından yazar
y_acik = satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE, yorum_reels=True), "Kısa, orta")
y_kapali = satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [], HIKAYE, yorum_reels=False), "Kısa, orta")
kontrol("pazar yorumu Reels açıkken 'kaydırmalı gönderi, Reels ve hikâye'",
        y_acik["ne"].endswith("(kaydırmalı gönderi, Reels ve hikâye)"), y_acik)
kontrol("pazar yorumu Reels kapalıyken yalnızca 'kaydırmalı gönderi'", y_kapali["ne"].endswith("(kaydırmalı gönderi)"), y_kapali)
kontrol("main'deki YORUM_REELS okunuyor", ("Reels ve hikâye" in satir(prg.program(datetime(2026, 10, 16, 9, tzinfo=TR), [],
        HIKAYE), "Kısa, orta")["ne"]) == bool(bot.YORUM_REELS))

# Satırlar sıralı ve hepsinin adı var
kontrol("satır sırası", [s["zaman"].split(" ~")[0] for s in a["satirlar"]][:2] == ["Hafta içi", "Rehber günleri"], a["satirlar"])
kontrol("bilinmeyen tür yok", all(not s["ne"][:1].islower() for s in a["satirlar"]))
kontrol("alt bilgi", a["fiyat_ozet"] == "hafta içi her gün")

print(f"\n{sum(sonuc)}/{len(sonuc)} sınama geçti")
sys.exit(0 if all(sonuc) else 1)
