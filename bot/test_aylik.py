"""Aylık özetin "Son 1 yıl" satırı (Rıdvan, 1 Kasım 2026: "3 Uygun bence").

Çalıştırma: python bot/test_aylik.py
Ağ kullanmaz: MetalCharts ve ECB geçmişi sınamada elle verilir.
"""
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402

sonuc = []


def kontrol(kosul, ad, ayrinti=""):
    sonuc.append(bool(kosul))
    print(("TAMAM " if kosul else "HATA  ") + ad + ("" if kosul else f": {ayrinti}"))


SON = date(2026, 10, 30)

# 1) Kendi kaydı varsa o kullanılır (Ekim 2027'den itibaren), ağa gidilmez
gecmis = {date(2025, 10, 30): {"gram": 64.0}, date(2025, 10, 27): {"gram": 60.0}}
b = main.yillik_baz(gecmis, SON, metal={"XAG": {}}, kur={})
kontrol(b == {"tarih": "2025-10-30", "gram": 64.0, "kaynak": "kayit"}, "kendi kaydı: aynı gün", b)

gecmis = {date(2025, 10, 27): {"gram": 60.0}}       # 30 Ekim 2025 kaydı yok, 3 gün öncesi var (tolerans 4)
b = main.yillik_baz(gecmis, SON, metal={"XAG": {}}, kur={})
kontrol(b and b["tarih"] == "2025-10-27" and b["kaynak"] == "kayit", "kendi kaydı: en yakın önceki gün", b)

gecmis = {date(2025, 10, 20): {"gram": 60.0}}       # tolerans dışında → kendi kaydı sayılmaz
b = main.yillik_baz(gecmis, SON, metal={"XAG": {}}, kur={})
kontrol(b is None, "tolerans dışındaki eski kayıt kullanılmaz, MetalCharts da yoksa satır yok", b)

# 2) Kendi kaydı yoksa MetalCharts kapanışı × ECB kuru
metal = {"XAG": {date(2025, 10, 30): 48.0, date(2025, 10, 29): 47.0}}
kur = {date(2025, 10, 30): 42.0, date(2025, 10, 29): 41.9}
b = main.yillik_baz({}, SON, metal=metal, kur=kur)
beklenen = 48.0 * 42.0 / main.ONS_GRAM
kontrol(b and b["kaynak"] == "metalcharts" and b["tarih"] == "2025-10-30" and abs(b["gram"] - beklenen) < 1e-9,
        "MetalCharts × ECB, aynı gün", b)

metal = {"XAG": {date(2025, 10, 31): 49.0, date(2025, 10, 28): 47.5}}   # 31 Ekim hedeften sonra: alınmaz
kur = {date(2025, 10, 27): 41.8}                                         # kur 1 gün önceki
b = main.yillik_baz({}, SON, metal=metal, kur=kur)
kontrol(b and b["tarih"] == "2025-10-28" and b["kur_tarihi"] == "2025-10-27", "hedeften sonraki gün alınmaz; kur en yakın önceki", b)

kontrol(main.yillik_baz({}, SON, metal=None, kur={}) is None, "MetalCharts planı yok (None) → satır yok")
kontrol(main.yillik_baz({}, SON, metal={"XAG": {date(2025, 10, 30): 48.0}}, kur={}) is None, "kur yok → satır yok")


class Patlayan(dict):
    def get(self, *a):
        raise RuntimeError("bozuk")


kontrol(main.yillik_baz({}, SON, metal=Patlayan(), kur={}) is None, "hata satırı düşürür, fırlatmaz")
kontrol(main._yil_once(date(2028, 2, 29)) == date(2027, 2, 28), "29 Şubat → bir yıl önce 28 Şubat")

# 3) Görsel ve açıklama alanları
f = {"gram": 79.07, "yil": {"tarih": "2025-10-30", "gram": 65.12, "kaynak": "metalcharts"}}
a = main.yil_alanlari(f)
kontrol(a["yil_deg"] == {"yon": "artis", "isaret": "▲", "metin": "%21,4"}, "artış: ▲ %21,4 yeşil", a)
kontrol(a["yil_satiri"] == "Son 1 yıl: ▲ %21,4 (30 Ekim 2025: 65,12 ₺)", "açıklama satırı", a["yil_satiri"])
kontrol("MetalCharts günlük kapanışı" in a["yil_notu"] and "30 Ekim 2025" in a["yil_notu"], "kaynak notu", a["yil_notu"])
a = main.yil_alanlari({"gram": 60.0, "yil": {"tarih": "2025-10-30", "gram": 65.12, "kaynak": "kayit"}})
kontrol(a["yil_deg"]["yon"] == "dusus" and a["yil_deg"]["isaret"] == "▼", "düşüş de olduğu gibi yazılır (kırmızı ▼)", a)
kontrol("kaydına göredir" in a["yil_notu"], "kendi kaydında not", a["yil_notu"])
kontrol(main.yil_alanlari({"gram": 79.07, "yil": None}) == {}, "yıl yoksa alan yok")
kontrol(main.yil_alanlari({"gram": 79.07, "yil": {"tarih": "bozuk", "gram": 1}}) == {}, "bozuk veri satırı düşürür")

# 4) Örnek aylık özetin açıklaması: satır yerinde, uzunluk sınırı, satır yokken eskisiyle aynı
fo = main.ornek_aylik(kismi=True)
fo.update({"ons": 49.1, "ons_once": 58.9})            # gerçekte olduğu gibi "Ayın kaynağı" satırı da çıksın
v = main.aylik_veri_hazirla(fo, "gunlukgumus")
ack = main.aciklama_yaz(v, "ay")
satirlar = ack.splitlines()
i_kaynak = next(i for i, s in enumerate(satirlar) if s.startswith("Ayın kaynağı"))
kontrol(satirlar[i_kaynak + 1].startswith("Son 1 yıl: "), "açıklamada 'Ayın kaynağı'nın hemen altında", satirlar[:6])
kontrol(len(ack) <= 2200, "açıklama ≤ 2200 karakter", len(ack))
os.environ["ORNEK_YIL"] = "0"
fo0 = main.ornek_aylik(kismi=True)
fo0.update({"ons": 49.1, "ons_once": 58.9})
v0 = main.aylik_veri_hazirla(fo0, "gunlukgumus")
ack0 = main.aciklama_yaz(v0, "ay")
os.environ.pop("ORNEK_YIL")
kontrol("Son 1 yıl" not in ack0 and not v0.get("yil_deg"), "yıl yoksa açıklamada ve görselde yok")
kontrol(ack.replace(v["yil_satiri"] + "\n", "").replace(" " + v["yil_notu"], "") == ack0,
        "yıl satırı ve notu dışında açıklama aynı")

print(f"\ntest_aylik: {sum(sonuc)}/{len(sonuc)} sınama geçti")
sys.exit(0 if all(sonuc) else 1)
