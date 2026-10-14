"""bot/kart.py sınamaları (ağ yok, tarayıcı yok). Çalıştır: python bot/test_kart.py"""
import os
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


os.environ.pop("KART", None)
CARSAMBA, PERSEMBE, CUMA = date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)
olagan = {"ozel": None, "buyuk_hareket": None}

# ---------------------------------------------------------------- hangi gün kart
esit(kart.kart_turu(CARSAMBA, olagan), "gram", "çarşamba Kaç gram eder?")
esit(kart.kart_turu(CUMA, olagan), "parite", "cuma altın–gümüş")
esit(kart.kart_turu(PERSEMBE, olagan), None, "perşembe kart yok")
esit(kart.kart_turu(date(2026, 10, 19), olagan), None, "pazartesi kart yok")
esit(kart.kart_turu(CARSAMBA, {"ozel": {"tur": "esik"}, "buyuk_hareket": None}), None, "özel günde kart atlanır")
esit(kart.kart_turu(CUMA, {"ozel": None, "buyuk_hareket": {"metin": "x"}}), None, "büyük harekette kart atlanır")
os.environ["KART"] = "parite"
esit(kart.kart_turu(PERSEMBE, olagan), "parite", "KART ortam değişkeni günü ezer")
os.environ["KART"] = "yok"
esit(kart.kart_turu(CARSAMBA, olagan), None, "KART=yok kartı kapatır")
os.environ.pop("KART")

# ---------------------------------------------------------------- Kaç gram eder?
v = kart.gram_karti({"gram": 96.42}, main.tr_sayi)
esit([s["tl"] for s in v["tl_tablo"]], ["1.000", "5.000", "10.000"], "TL tutarları")
esit([s["gram"] for s in v["tl_tablo"]], ["10,37", "51,86", "103,71"], "TL → gram")
esit([(s["ad"], s["tl"]) for s in v["gram_tablo"]], [("100 gram", "9.642"), ("1 kilogram", "96.420")], "gram → TL")

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
v = {**kart.gram_karti({"gram": 96.42}, main.tr_sayi), "tarih": "21 Ekim 2026", "saat": "10:03", "gram": "96,42"}
a = kart.aciklama(v, "Gram gümüş fiyatı bugün: 96,42 ₺ (▲ %0,44)", "KAYNAKLAR")
esit(a.splitlines()[0], "Gram gümüş fiyatı bugün: 96,42 ₺ (▲ %0,44)", "ilk satır öteki paylaşımlarla aynı")
esit(a.splitlines()[1], "Kaç gram eder? · 21 Ekim 2026 · 10:03", "ikinci satır kart adı")
esit("Bilgi amaçlıdır, yatırım tavsiyesi değildir." in a, True, "uyarı var")
esit(a.endswith(kart.HASHTAG["gram"]), True, "etiketler sonda")
esit(len(kart.HASHTAG["gram"].split()), 5, "en çok 5 etiket (gram)")
esit(len(kart.HASHTAG["parite"].split()), 5, "en çok 5 etiket (parite)")
esit(len(a) < 2200, True, "açıklama 2200 karakterin altında")
v = {**kart.parite_karti(f, main.tr_sayi, main.degisim, CUMA), "tarih": "23 Ekim 2026", "saat": "10:03", "gram": "96,42"}
a = kart.aciklama(v, "Gram gümüş fiyatı bugün: 96,42 ₺ (▲ %0,44)", "KAYNAKLAR")
esit("1 gram altın ≈ 85,6 gram gümüş" in a, True, "parite satırı")
esit("16 Eki kapanışına göre ▲ %0,59" in a, True, "geçen haftaya göre")
esit("Önceki haftaların kapanışı: 9 Eki 83,6 · 16 Eki 85,1" in a, True, "önceki haftalar")
for yasak in ("al ", "sat ", "tavsiye ederiz", "fırsat", "hedef"):
    esit(yasak in a.lower().replace("alış-satış", ""), False, f"yönlendirici ifade yok: {yasak.strip()}")

print(f"Tamam: {gecen} sınama geçti.")
