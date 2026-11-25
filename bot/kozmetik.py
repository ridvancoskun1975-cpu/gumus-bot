# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Kozmetik dokunuşlar (Rıdvan, 25 Kasım 2026 23:28: "mevcut kullanıcılar sıkılmaması terk etmemesi için paylaşımlarda
arayüzde ufak kozmetik değişimler yapalım"). Yalnız sabah Reels'i ve akşam özeti (görsel, video, kapak).

Üç seçenek, her biri tek ayarla açılır, HEPSİ VARSAYILAN KAPALI (kapalıyken görseller bugünküyle piksel piksel aynı;
`python bot/test_kozmetik.py`). Hiçbir yazı, rakam, öğe ya da goril çizimi değişmez, küçülmez, yer değiştirmez; yazı ile
zemin arasındaki kontrast bugünkünden düşmez (sınamada ölçülür).
  A  HAFTA_TONU     vurgu rengi (tarih, ₺, parite sayısı, Ag rozeti, nokta) haftaya göre 4 açık ton arasında döner
  B  MEVSIM_AYRACI  fiyatın üstündeki ayraç çizgisinin sağ ucunda küçük mevsim işareti (kış, ilkbahar, yaz,
                    sonbahar); goril balonlu paylaşımda çıkmaz
  C  YON_ZEMINI     zemin ve ayraç çizgileri günün yönüne göre çok hafif yeşilimsi (artış) / mavimsi (düşüş); sakin
                    günde bugünkü gibi
Önizleme (yalnız --ornek ile): KOZMETIK_ZORLA=ton,mevsim,zemin python bot/main.py hazirla --tur post --ornek --cikti <klasör>
(KOZMETIK_GUN=YYYY-AA-GG başka bir haftanın / mevsimin hâlini gösterir). Her hata "kozmetik yok" sayılır."""
import os
from datetime import date

HAFTA_TONU = False
MEVSIM_AYRACI = False
YON_ZEMINI = False

ZEMIN = "#121418"        # templates/ortak.css → --zemin (bugünkü)
VURGU = "#C9D1DA"        # templates/ortak.css → --vurgu (bugünkü)

# A: ISO hafta numarası % 4. Hepsi bugünkü gümüş vurgudan en az onun kadar açık (zeminle kontrast düşmez);
# yeşil ve kırmızıya kaçmaz (artış / düşüş renkleriyle karışmasın).
TONLAR = [("buz mavisi", "#BCD8EE"), ("inci", "#E2D6BE"), ("lavanta", "#D4CDF0"), ("gümüş", VURGU)]

# B: ay → mevsim (makrolar.html → mevsim_motifi)
MEVSIMLER = {12: "kis", 1: "kis", 2: "kis", 3: "ilkbahar", 4: "ilkbahar", 5: "ilkbahar",
             6: "yaz", 7: "yaz", 8: "yaz", 9: "sonbahar", 10: "sonbahar", 11: "sonbahar"}

# C: günün yönü (gram değişimi) → (zemin, çizgi). Zeminin her kanalı bugünkünden (18, 20, 24) büyük değil: yazının
# altındaki hiçbir yarı saydam kutuda da zemin açılmaz, kontrast düşmez.
SAKIN_ESIK = 0.5         # %: altında zemin bugünkü gibi (goril.SAKIN_ESIK ile aynı)
ZEMINLER = {"artis": ("#0A1410", "#28392F"), "dusus": ("#0A0E18", "#2A3247")}


def _parlaklik(renk):
    """WCAG göreli parlaklık (#RRGGBB)."""
    k = [int(renk[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    k = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in k]
    return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2]


def kontrast(a, b):
    la, lb = sorted((_parlaklik(a), _parlaklik(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _acik(ornek):
    z = {s.strip() for s in os.environ.get("KOZMETIK_ZORLA", "").split(",")} if ornek else set()
    return HAFTA_TONU or "ton" in z, MEVSIM_AYRACI or "mevsim" in z, YON_ZEMINI or "zemin" in z


def sablon_verisi(veri, tur, gun, ornek=False):
    """Şablon alanı {"kozmetik": {"css": …, "motif": …}}; hepsi kapalıysa {} (veri ve görsel bugünküyle aynı)."""
    if tur not in ("reels", "post"):
        return {}
    if ornek and os.environ.get("KOZMETIK_GUN", "").strip():
        gun = date.fromisoformat(os.environ["KOZMETIK_GUN"].strip())
    ton, mevsim, zemin = _acik(ornek)
    css, motif = {}, None
    if ton:
        css["vurgu"] = TONLAR[gun.isocalendar()[1] % len(TONLAR)][1]
    if mevsim:
        motif = MEVSIMLER[gun.month]
    if zemin:
        d = veri["gram_deg"]
        if abs(d["yuzde"]) >= SAKIN_ESIK and d["yon"] in ZEMINLER:
            css["zemin"], css["cizgi"] = ZEMINLER[d["yon"]]
    if not css and not motif:
        return {}
    return {"kozmetik": {"css": css, "motif": motif}}
