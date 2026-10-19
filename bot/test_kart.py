"""bot/kart.py sınamaları (ağ yok, tarayıcı yok). Çalıştır: python bot/test_kart.py"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kart  # noqa: E402
import main  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


CARSAMBA, PERSEMBE, CUMA = date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)

# ---------------------------------------------------------------- taahhüt: hafta içi her gün 2 kez gram fiyatı
# Rıdvan (15 Ekim 2026): "Hafta içi her gün 2 kere gümüş gram fiyatı verilecek." Kart Reels'in ya da özetin
# yerine geçmez; ayrı bir zamanlı çalışmadır.
import program  # noqa: E402
zamanlar = program.cronlar()
turler = {c: t for c, t in zamanlar}
esit(turler.get("50 6 * * 1-5"), "reels", "taahhüt: hafta içi her gün ~10:00 Reels")
esit(turler.get("50 16 * * 1-5"), "post", "taahhüt: hafta içi her gün ~20:00 özet")
esit(sum(1 for _, t in zamanlar if t in ("reels", "post")), 2, "fiyat paylaşımları yalnızca bu ikisi")
kart_cron = [c for c, t in zamanlar if t == "kart"]
# Rıdvan, 19 Ekim 2026: kartlar takvimden kaldırıldı (takipçiyi bıktırmamak için paylaşım sayısı azaltıldı);
# kod duruyor, yalnızca elle (Run workflow → tür: kart).
esit(kart_cron, [], "kartın zamanlı çalışması yok (19 Ekim 2026'da kaldırıldı)")
esit(re.search(r"options: \[[^\]]*\bkart\b", program.IS_AKISI.read_text(encoding="utf-8")) is not None, True,
     "elle çalıştırma seçeneklerinde kart duruyor")
esit(program.KAYIT_TURLERI, ("reels", "post"), "günlük fiyat kaydını yalnızca Reels ve özet yazar")

# ---------------------------------------------------------------- hangi gün kart
esit(kart.bugunun_karti(CARSAMBA), "gram", "çarşamba Kaç gram eder?")
esit(kart.bugunun_karti(CUMA), "parite", "cuma altın–gümüş")
esit(kart.bugunun_karti(PERSEMBE), None, "perşembe kart yok")
esit(kart.bugunun_karti(date(2026, 10, 19)), None, "pazartesi kart yok")
esit(kart.bugunun_karti(date(2026, 10, 16)), None, "başlangıçtan (21 Ekim) önce kart yok")
esit(kart.bugunun_karti(date(2026, 10, 14)), None, "başlangıçtan önceki çarşamba da yok")

# ---------------------------------------------------------------- Kaç gram eder?
v = kart.gram_karti({"gram": 96.42}, main.tr_sayi)
esit([s["tl"] for s in v["tl_tablo"]], ["1.000", "5.000", "10.000"], "TL tutarları")
esit([s["gram"] for s in v["tl_tablo"]], ["10,37", "51,86", "103,71"], "TL → gram")
esit([(s["ad"], s["tl"]) for s in v["gram_tablo"]], [("100 gram", "9.642"), ("1 kilogram", "96.420")], "gram → TL")

v = kart.gram_karti({"gram": 88.9993}, main.tr_sayi)
esit(v["gram_tablo"][-1]["tl"], "89.000", "kilogram yazan gram fiyatıyla tutarlı (89,00 ₺ → 89.000 ₺)")

# ---------------------------------------------------------------- haftalık kapanış paritesi
kayit = {  # iş günlerinin son kaydı; bu hafta (19–23 Ekim) sayılmaz
    "2026-10-13": 84.0, "2026-10-14": 84.5, "2026-10-16": 85.1,        # 42. hafta: kapanış 16 Ekim
    "2026-10-05": 83.0, "2026-10-09": 83.6,                            # 41. hafta: kapanış 9 Ekim
    "2026-10-19": 86.0, "2026-10-21": 86.2,                            # bu hafta
}
h = kart.haftalik_pariteler(kayit, CUMA)
esit(h, [(date(2026, 10, 9), 83.6), (date(2026, 10, 16), 85.1)], "her haftanın son kaydı, bu hafta hariç")
on_hafta = {(date(2026, 8, 7) + timedelta(weeks=i)).isoformat(): 80.0 + i for i in range(10)}   # 10 cuma
esit([v for _, v in kart.haftalik_pariteler(on_hafta, CUMA, en_cok=6)], [84.0, 85.0, 86.0, 87.0, 88.0, 89.0],
     "en çok 6 hafta, en yeniler")
esit(kart.haftalik_pariteler({}, CUMA), [], "kayıt yoksa boş")

# ---------------------------------------------------------------- altın–gümüş kartı
f = {"gram": 96.42, "parite": 85.6, "gecmis_parite": kayit}
v = kart.parite_karti(f, main.tr_sayi, main.degisim, CUMA)
esit([s["ad"] for s in v["haftalar"]], ["9 Eki", "16 Eki", "Bugün"], "satırlar eskiden yeniye, sonda bugün")
esit(v["haftalar"][-1]["oran"], 100.0, "en büyük değer tam çubuk")
esit(all(0 < s["oran"] <= 100 for s in v["haftalar"]), True, "çubuklar 0–100 arası")
esit(v["gecen_hafta"], "16 Eki", "karşılaştırma geçen haftanın kapanışıyla")
esit(v["parite_hafta_deg"]["metin"], "%0,59", "geçen haftaya göre değişim")
esit(v["gram_altin"], "8.254", "gram altın = gram gümüş × parite")
v = kart.parite_karti({"gram": 96.42, "parite": 85.6, "gecmis_parite": {}}, main.tr_sayi, main.degisim, CUMA)
esit((v["hafta_yok"], v["parite_hafta_deg"], len(v["haftalar"])), (True, None, 1), "önceki hafta yoksa yalnız bugün")

# ---------------------------------------------------------------- açıklama
v = {**kart.gram_karti({"gram": 96.42}, main.tr_sayi), "tarih": "21 Ekim 2026", "saat": "12:03", "gram": "96,42",
     "gram_deg": main.degisim(96.42, 96.0)}
a = kart.aciklama(v, "KAYNAKLAR")
esit(a.splitlines()[0], "1.000 ₺ kaç gram gümüş eder? Bugün 10,37 gram (gram gümüş 96,42 ₺, ▲ %0,44)",
     "ilk satır aranan soru ve rakam")
esit(a.splitlines()[1], "Kaç gram eder? · 21 Ekim 2026 · 12:03", "ikinci satır kart adı")
esit("Bilgi amaçlıdır, yatırım tavsiyesi değildir." in a, True, "uyarı var")
esit(a.endswith(kart.HASHTAG["gram"]), True, "etiketler sonda")
esit(len(kart.HASHTAG["gram"].split()), 5, "en çok 5 etiket (gram)")
esit(len(kart.HASHTAG["parite"].split()), 5, "en çok 5 etiket (parite)")
esit(len(a) < 2200, True, "açıklama 2200 karakterin altında")
v = {**kart.parite_karti(f, main.tr_sayi, main.degisim, CUMA), "tarih": "23 Ekim 2026", "saat": "12:03", "gram": "96,42"}
a = kart.aciklama(v, "KAYNAKLAR")
esit(a.splitlines()[0], "1 gram altın kaç gram gümüş eder? Bugün 85,6 gram (gram altın 8.254 ₺, gram gümüş 96,42 ₺)",
     "ilk satır (altın–gümüş)")
esit("1 gram altın ≈ 85,6 gram gümüş" in a, True, "parite satırı")
esit("16 Eki kapanışına göre ▲ %0,59" in a, True, "geçen haftaya göre")
esit("Önceki haftaların kapanışı: 9 Eki 83,6 · 16 Eki 85,1" in a, True, "önceki haftalar")
for yasak in ("al ", "sat ", "tavsiye ederiz", "fırsat", "hedef"):
    esit(yasak in a.lower().replace("alış-satış", ""), False, f"yönlendirici ifade yok: {yasak.strip()}")

print(f"Tamam: {gecen} sınama geçti.")
