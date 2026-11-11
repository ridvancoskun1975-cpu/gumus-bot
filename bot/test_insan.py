# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""İnsan dokunuşu (bot/insan.py) sınaması. Ağ ve API yok. Çalıştırma: python bot/test_insan.py"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insan  # noqa: E402

hatalar = []


def bekle(kosul, ad):
    if not kosul:
        hatalar.append(ad)
        print("HATA:", ad)


def deg(yuzde):
    return {"yuzde": yuzde, "yon": "dusus" if yuzde < 0 else "artis"}


def veri(yuzde=0.3, goril="istif", gram=100.0, **ek):
    v = {"gram_deg": deg(yuzde), "dolar_deg": deg(0.05), "goril": goril, "gram_sayi": gram,
         "buyuk_hareket": None, "gun_baslik": None, "ozel": None}
    v.update(ek)
    return v


def seri(gun, degerler):
    """degerler: bugünden geriye iş günlerinin kayıtları (en yakın gün ilk)."""
    s, d = {}, gun
    for x in degerler:
        d -= timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        s[d.isoformat()] = x
    return s


for k in ("INSAN_ZORLA", "INSAN_DENEME", "DENEME", "KONU", "ANTHROPIC_API_KEY"):
    os.environ.pop(k, None)

PZT = date(2026, 11, 23)                       # BASLANGIC'tan sonraki ilk tam hafta
SAL, CAR, PER, CUM = (PZT + timedelta(days=i) for i in (1, 2, 3, 4))
bekle(PZT.weekday() == 0 and CUM.weekday() == 4, "tarih düzeni")

# --- cümleler: onay tablosundaki 33 cümle, iki satıra sığar
bekle(sum(len(x) for x in insan.BALON.values()) == 33, "33 onaylı cümle")
bekle(all(len(c) <= insan.BALON_EN_UZUN for x in insan.BALON.values() for c in x), "balon cümleleri kısa")
bekle(all("  " not in c and c == c.strip() for x in insan.BALON.values() for c in x), "fazla boşluk yok")

# --- başlangıçtan önce hiçbir şey yok
erken = insan.BASLANGIC - timedelta(days=insan.BASLANGIC.weekday() - 1 if insan.BASLANGIC.weekday() > 1 else 6)
bekle(insan.sablon_verisi(veri(), {}, "post", insan.BASLANGIC - timedelta(days=7)) == insan.YOK, "başlangıç öncesi yok")

# --- 3. goril balonu
g = seri(PZT, [100.0] * 8)
bekle(insan.goril_balonu(veri(0.3, "istif"), g, "reels", PZT) in insan.BALON[("pazartesi", "istif")], "pzt sabah sakin")
bekle(insan.goril_balonu(veri(1.1, "gezinen"), g, "reels", PZT) in insan.BALON[("pazartesi", "gezinen")], "pzt sabah hareketli")
bekle(insan.goril_balonu(veri(0.3), g, "post", PZT) is None, "pzt akşam balon yok")
bekle(insan.goril_balonu(veri(0.3), g, "reels", SAL) is None, "salı sabah balon yok")
# düşüş günü: en küçük düşüşte bile yok (Rıdvan, 11 Kasım 2026 14:18)
bekle(insan.goril_balonu(veri(-0.01, "istif"), g, "reels", PZT) is None, "düşüşte balon yok (sabah)")
bekle(insan.goril_balonu(veri(-0.8, "gezinen"), g, "reels", PZT) is None, "düşüşte balon yok (gezinen)")
bekle(insan.goril_balonu(veri(-0.004, "istif"), g, "reels", PZT) is None, "görselde ▼ %0,00 de düşüş sayılır")
bekle(insan.goril_balonu(veri(0.0, "istif"), g, "reels", PZT) is not None, "değişmeyen gün balon var")
# sevinen / üzülen / manşet / başlık / özel gün: yok
bekle(insan.goril_balonu(veri(3.0, "sevinen", buyuk_hareket={"yon": "artis"}), g, "reels", PZT) is None, "manşette yok")
bekle(insan.goril_balonu(veri(0.3, "istif", gun_baslik={"metin": "x"}), g, "reels", PZT) is None, "başlıkta yok")
bekle(insan.goril_balonu(veri(0.3, "istif", ozel={"x": 1}), g, "reels", PZT) is None, "özel günde yok")
bekle(insan.goril_balonu(veri(0.3, None), g, "reels", PZT) is None, "gorilsiz balon yok")
# cuma: gün ve hafta artıda olmalı
hafta_arti = seri(CUM, [100.0, 100.0, 100.0, 100.0, 98.0, 98.0])      # geçen cuma 98 → bugün 100
hafta_eksi = seri(CUM, [100.0, 100.0, 100.0, 100.0, 103.0, 103.0])    # geçen cuma 103 → bugün 100
bekle(insan.goril_balonu(veri(0.2, "istif"), hafta_arti, "post", CUM) in insan.BALON[("cuma", "istif")], "cuma akşam sakin")
bekle(insan.goril_balonu(veri(0.2, "istif"), hafta_eksi, "post", CUM) is None, "cuma: hafta düşüşte balon yok")
bekle(insan.goril_balonu(veri(0.2, "istif"), {}, "post", CUM) is None, "cuma: haftalık kayıt yoksa balon yok")
bekle(insan.goril_balonu(veri(-0.2, "istif"), hafta_arti, "post", CUM) is None, "cuma: gün düşüşte balon yok")
bekle(insan.goril_balonu(veri(0.2), hafta_arti, "reels", CUM) is None, "cuma sabah balon yok")
# dönüş: art arda haftalarda farklı cümle, aynı hafta içinde sabit
c1 = insan.balon_cumlesi("pazartesi", "istif", PZT)
c2 = insan.balon_cumlesi("pazartesi", "istif", PZT + timedelta(days=7))
bekle(c1 != c2, "haftaya göre dönüyor")
tum = {insan.balon_cumlesi("cuma", "istif", CUM + timedelta(days=7 * i)) for i in range(7)}
bekle(len(tum) == 7, "7 haftada 7 farklı cuma cümlesi")

# --- 1. hesap kartı
bos = seri(SAL, [100.0])
k = insan.hesap_karti(veri(gram=103.79), bos, "post", SAL)
bekle(k and k["metin"] == "1.000 ₺ ile bugün 9,63 gram gümüş alınır", f"hesap metni: {k and k['metin']}")
bekle(k and k["alt"] == insan.HESAP_NOTU and "işçilik ve makas hariç" in k["aciklama"], "hesap notu")
bekle(insan.hesap_karti(veri(), bos, "post", CAR) is None, "çarşamba hesap yok")
bekle(insan.hesap_karti(veri(), bos, "reels", SAL) is None, "sabah hesap yok")
bekle(insan.hesap_karti(veri(ozel={"x": 1}), bos, "post", SAL) is None, "özel günde hesap yok")
# haftada en çok 2 kart: salı hesap + çarşamba %2+ (neden) → perşembe hesap yok
iki = seri(PER, [103.0, 100.5, 100.4, 100.0])         # çar 103 (salıya göre +%2,49), sal 100.5
bekle(insan.buyuk_gunler(iki, PER) == [CAR], f"büyük gün: {insan.buyuk_gunler(iki, PER)}")
bekle(insan.onceki_kart_sayisi(iki, PER) == 2, f"kart sayısı: {insan.onceki_kart_sayisi(iki, PER)}")
bekle(insan.hesap_karti(veri(), iki, "post", PER) is None, "haftalık 2 kart sınırı")
tek = seri(PER, [100.0, 100.4, 100.5, 100.0])          # yalnız salı hesap
bekle(insan.hesap_karti(veri(), tek, "post", PER) is not None, "perşembe hesap (1 kart sonrası)")
# başlangıçtan önceki günler kart sayılmaz (sınama BASLANGIC'ı bir salıya koyar, sonra geri alır)
_eski = insan.BASLANGIC
insan.BASLANGIC = date(2026, 11, 17)                             # salı
once = {"2026-11-13": 100.0, "2026-11-16": 103.0,              # 16 Kas pazartesi +%3 (başlangıçtan önce)
        "2026-11-17": 103.1}                                     # 17 Kas salı (hesap)
bekle(insan.onceki_kart_sayisi(once, date(2026, 11, 19)) == 1, f"başlangıç öncesi sayılmaz: {insan.onceki_kart_sayisi(once, date(2026, 11, 19))}")
insan.BASLANGIC = _eski
# canlı başlangıç: 12 Kas perşembe; aynı hafta pazartesi–çarşamba %2+ olsa da kart sayılmaz, perşembe hesap kartı çıkar
bekle(insan.BASLANGIC == date(2026, 11, 12), "başlangıç 12 Kasım (Rıdvan: ilk paylaşımda başla)")
ilk = {"2026-11-06": 80.0, "2026-11-09": 82.0, "2026-11-10": 79.0, "2026-11-11": 84.05}
bekle(insan.onceki_kart_sayisi(ilk, date(2026, 11, 12)) == 0, "ilk hafta: başlangıç öncesi günler sayılmaz")
bekle(insan.hesap_karti(veri(), ilk, "post", date(2026, 11, 12)) is not None, "12 Kas perşembe akşamı hesap kartı")
bekle(insan.goril_balonu(veri(0.3, "istif"), ilk, "reels", date(2026, 11, 12)) is None, "perşembe sabahı balon yok")
# zorla: gün sınırını aşar
bekle(insan.hesap_karti(veri(), bos, "post", CAR, zorla="hesap") is not None, "zorla hesap")

# --- 2. neden kartı: denetim
iyi = "ABD’de faiz indirimi beklentisi güçlendi, dolar zayıfladı; ons gümüş yükseldi."
bekle(insan.neden_denetle(iyi, ["bloomberght.com"]) == [], f"iyi cümle: {insan.neden_denetle(iyi, ['x.com'])}")
bekle(insan.neden_denetle("Fed'in faiz kesintisi beklentisi doları zayıflattı.", ["a.com"]) == [], "faiz kesintisi serbest")
bekle("kaynak yok" in insan.neden_denetle(iyi, []), "kaynaksız")
bekle(insan.neden_denetle("YOK", ["a.com"]) == ["neden yok"], "YOK")
bekle("rakam" in insan.neden_denetle("Fed faizi 25 baz puan indirdi, dolar zayıfladı.", ["a.com"]), "rakam")
bekle("gelecek zaman" in insan.neden_denetle("Dolar zayıfladı, gümüş yükselmeye devam edecek gibi.", ["a.com"]), "gelecek")
bekle("olasılık" in insan.neden_denetle("Dolar zayıfladı; bu durum gümüşü destekleyebilir.", ["a.com"]), "olasılık")
bekle("al/sat/tut" in insan.neden_denetle("Yatırımcılar gümüş al çağrısıyla harekete geçti, talep arttı.", ["a.com"]), "al")
bekle("kişi/parti adı" in insan.neden_denetle("Trump'ın gümrük vergisi açıklaması doları zayıflattı.", ["a.com"]), "ad")
bekle(any("uzunluk" in s for s in insan.neden_denetle("Dolar düştü.", ["a.com"])), "çok kısa")
# neden kartı: örnek veriyle (API yok), büyük hareket günü
v_b = veri(3.2, "sevinen", buyuk_hareket={"yon": "artis", "metin": "Gümüş bugün %3,2 yükseldi"})
k = insan.neden_karti(v_b, "post", SAL, ornek=True)
bekle(k and k["etiket"] == "BUGÜN NEDEN YÜKSELDİ?" and k["kaynaklar"], "neden örnek kartı")
bekle(k and "kaynak: bloomberght.com" in k["aciklama"], "neden açıklama satırı")
v_d = veri(-3.2, "uzulen", buyuk_hareket={"yon": "dusus", "metin": "Gümüş bugün %3,2 düştü"})
bekle(insan.neden_karti(v_d, "post", SAL, ornek=True)["etiket"] == "BUGÜN NEDEN DÜŞTÜ?", "düşüş etiketi")
bekle(insan.neden_karti(veri(1.0), "post", SAL, ornek=True) is None, "küçük harekette neden yok")
bekle(insan.neden_karti(v_b, "reels", SAL, ornek=True) is None, "sabah neden yok")
bekle(insan.neden_karti(v_b, "post", SAL) is None, "anahtar yoksa neden yok (API'ye gitmez)")
bekle(insan.neden_karti(v_b, "post", SAL, kalan_sn=60, anahtar="x") is None, "bütçe azsa arama yok")
# neden kartı varken aynı gün hesap kartı yok (salı + büyük hareket)
os.environ["INSAN_ZORLA"] = ""
s = insan.sablon_verisi(v_b, bos, "post", SAL, ornek=True)
bekle(s["gunun_notu"] and s["gunun_notu"]["tur"] == "neden", "salı büyük hareket: neden kartı öncelikli")
s = insan.sablon_verisi(veri(0.4), bos, "post", SAL)
bekle(s["gunun_notu"] and s["gunun_notu"]["tur"] == "hesap" and s["goril_balon"] is None, "olağan salı: yalnız hesap")
bekle(insan.sablon_verisi(veri(0.4), bos, "post", SAL + timedelta(days=4)) == insan.YOK, "cumartesi hiçbir şey yok")

# --- zorlama: yalnız --ornek ile INSAN_ZORLA; denemede konu "insan:x"
os.environ["INSAN_ZORLA"] = "balon"
bekle(insan.zorlanan(ornek=False) is None and insan.zorlanan(ornek=True) == "balon", "INSAN_ZORLA yalnız örnekte")
os.environ.pop("INSAN_ZORLA")
os.environ.update({"DENEME": "true", "KONU": "insan:hesap"})
bekle(insan.zorlanan() == "hesap", "deneme konusu")
os.environ["DENEME"] = "false"
bekle(insan.zorlanan() is None, "paylaşan çalışmada zorlama yok")
os.environ.pop("DENEME"); os.environ.pop("KONU")
# zorlanan balon da düşüş kuralını aşmaz
bekle(insan.goril_balonu(veri(-0.5, "gezinen"), g, "reels", CAR, zorla="balon") is None, "zorla balon düşüşte de yok")

print(f"\n{'TAMAM' if not hatalar else f'{len(hatalar)} HATA'}: test_insan")
sys.exit(1 if hatalar else 0)
