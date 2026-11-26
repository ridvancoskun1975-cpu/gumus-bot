# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Kozmetik dokunuşlar (Rıdvan, 25 Kasım 2026 23:28: "mevcut kullanıcılar sıkılmaması terk etmemesi için paylaşımlarda
arayüzde ufak kozmetik değişimler yapalım"). Yalnız sabah Reels'i ve akşam özeti (görsel, video, kapak).

İki seçenek, her biri tek ayarla açılır, İKİSİ DE VARSAYILAN KAPALI (kapalıyken görseller bugünküyle bayt bayt aynı;
`python bot/test_kozmetik.py`). Hiçbir yazı, rakam, öğe ya da goril çizimi değişmez, küçülmez, yer değiştirmez.
  A  HAFTA_TONU   vurgu rengi (tarih, ₺, parite sayısı, Ag rozeti, nokta) ISO haftasına göre 4 ton arasında döner
                  (26 Kasım 2026 05:45 Rıdvan: "her hafta dört ton arasında dönsün").
  C  YON_ZEMINI   zemin, ayraç çizgileri ve üstte/altta yumuşak ışıma günün yönünde: yükselişte yeşil, düşüşte mavi
                  (kırmızı zemin yok); %0,5'in altındaki sakin günde bugünkü gibi. ZEMIN_DUZEYI 2 belirgin, 3 çok belirgin.
(Mevsim ayracı önizlendi, 26 Kasım 2026 Rıdvan: "mevsim işareti olmaz farklı anlaşılabilir"; kaldırıldı.)
Önizleme (yalnız --ornek ile): KOZMETIK_ZORLA=ton,zemin2 (ya da zemin3) python bot/main.py hazirla --tur post --ornek
--cikti <klasör>. Her hata "kozmetik yok" sayılır."""
import os

HAFTA_TONU = False
YON_ZEMINI = False
ZEMIN_DUZEYI = 2

ZEMIN = "#121418"        # templates/ortak.css → --zemin (bugünkü)
VURGU = "#C9D1DA"        # templates/ortak.css → --vurgu (bugünkü)

# A: hepsi bugünkü gümüş vurgudan en az onun kadar açık; yeşil ve kırmızıya kaçmaz (artış / düşüşle karışmasın).
TONLAR = [("buz mavisi", "#BCD8EE"), ("inci", "#E2D6BE"), ("lavanta", "#D4CDF0"), ("gümüş", VURGU)]

# C: düzey → yön → (zemin, çizgi, ışıma). Işıma sahnenin üstünde ve altında yön renginde yarı saydam elips.
SAKIN_ESIK = 0.5         # %: altında zemin bugünkü gibi (goril.SAKIN_ESIK ile aynı)
ZEMINLER = {
    2: {"artis": ("#0F1D16", "#2F5A45", "rgba(91, 201, 140, 0.13)"),
        "dusus": ("#10172A", "#33466E", "rgba(110, 150, 235, 0.15)")},
    3: {"artis": ("#12261C", "#3C7A5B", "rgba(91, 201, 140, 0.22)"),
        "dusus": ("#141E38", "#45609A", "rgba(110, 150, 235, 0.25)")},
}


def _parlaklik(renk):
    """WCAG göreli parlaklık (#RRGGBB)."""
    k = [int(renk[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    k = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in k]
    return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2]


def kontrast(a, b):
    la, lb = sorted((_parlaklik(a), _parlaklik(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _acik(ornek):
    """(ton açık mı, zemin düzeyi ya da 0)."""
    z = {s.strip() for s in os.environ.get("KOZMETIK_ZORLA", "").split(",")} if ornek else set()
    duzey = 3 if "zemin3" in z else 2 if "zemin2" in z else ZEMIN_DUZEYI if (YON_ZEMINI or "zemin" in z) else 0
    return HAFTA_TONU or "ton" in z, duzey


def sablon_verisi(veri, tur, gun, ornek=False):
    """Şablon alanı {"kozmetik": {"css": {değişken: renk}}}; hepsi kapalıysa {} (veri ve görsel bugünküyle aynı)."""
    if tur not in ("reels", "post"):
        return {}
    ton, duzey = _acik(ornek)
    css = {}
    if ton:
        css["vurgu"] = TONLAR[gun.isocalendar()[1] % len(TONLAR)][1]
    if duzey:
        d = veri["gram_deg"]
        if abs(d["yuzde"]) >= SAKIN_ESIK and d["yon"] in ZEMINLER[duzey]:
            css["zemin"], css["cizgi"], css["isima"] = ZEMINLER[duzey][d["yon"]]
    return {"kozmetik": {"css": css}} if css else {}
