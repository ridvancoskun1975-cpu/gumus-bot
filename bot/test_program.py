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


def p(yil, ay, gun, saat=9, dakika=0):
    an = datetime(yil, ay, gun, saat, dakika, tzinfo=TR)
    return prg.program(an, kayitlar(an.date()), HIKAYE)


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
kontrol("14 Ekim: haftalık ilki 24 Ekim", "ilki 24 Ekim Cumartesi" in " ".join(satir(a, "Haftalık")["ek"]), satir(a, "Haftalık"))
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

# Satırlar sıralı ve hepsinin adı var
kontrol("satır sırası", [s["zaman"].split(" ~")[0] for s in a["satirlar"]][:2] == ["Hafta içi", "Rehber günleri"], a["satirlar"])
kontrol("bilinmeyen tür yok", all(not s["ne"][:1].islower() for s in a["satirlar"]))
kontrol("alt bilgi", a["fiyat_ozet"] == "hafta içi her gün")

print(f"\n{sum(sonuc)}/{len(sonuc)} sınama geçti")
sys.exit(0 if all(sonuc) else 1)
