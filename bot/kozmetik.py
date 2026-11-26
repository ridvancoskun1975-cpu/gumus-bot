# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Kozmetik dokunuşlar (Rıdvan, 25 Kasım 2026 23:28: "mevcut kullanıcılar sıkılmaması terk etmemesi için paylaşımlarda
arayüzde ufak kozmetik değişimler yapalım"). Yalnız sabah Reels'i ve akşam özeti (görsel, video, kapak). Hiçbir yazı,
rakam, öğe ya da goril çizimi değişmez, küçülmez, yer değiştirmez. Rıdvan'ın 26 Kasım 2026 kararları: "kozmetik
lavanta iyi", "her hafta dört ton arasında dönsün", "mevsim işareti olmaz farklı anlaşılabilir" (kaldırıldı), "c2".
  HAFTA_TONU  vurgu rengi (tarih, ₺, parite sayısı, Ag rozeti, nokta) ISO haftasına göre 4 ton arasında döner.
  YON_ZEMINI  zemin, ayraç çizgileri ve üstte/altta yumuşak ışıma günün yönünde: yükselişte yeşil, düşüşte mavi
              (kırmızı zemin yok); %0,5'in altındaki sakin günde bugünkü gibi.
İkisi de False yapılınca görseller eski hâliyle bayt bayt aynı (`python bot/test_kozmetik.py` kanıtlar).
Her hata "kozmetik yok" sayılır (main.kozmetik_alanlari)."""
HAFTA_TONU = True
YON_ZEMINI = True

ZEMIN = "#121418"        # templates/ortak.css → --zemin (bugünkü)
VURGU = "#C9D1DA"        # templates/ortak.css → --vurgu (bugünkü)

# A: hepsi bugünkü gümüş vurgudan en az onun kadar açık; yeşil ve kırmızıya kaçmaz (artış / düşüşle karışmasın).
TONLAR = [("buz mavisi", "#BCD8EE"), ("inci", "#E2D6BE"), ("lavanta", "#D4CDF0"), ("gümüş", VURGU)]

# Yön zemini: yön → (zemin, çizgi, ışıma). Işıma sahnenin üstünde ve altında yön renginde yarı saydam elips.
SAKIN_ESIK = 0.5         # %: altında zemin bugünkü gibi (goril.SAKIN_ESIK ile aynı)
ZEMINLER = {"artis": ("#0F1D16", "#2F5A45", "rgba(91, 201, 140, 0.13)"),
            "dusus": ("#10172A", "#33466E", "rgba(110, 150, 235, 0.15)")}


def _parlaklik(renk):
    """WCAG göreli parlaklık (#RRGGBB)."""
    k = [int(renk[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    k = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in k]
    return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2]


def kontrast(a, b):
    la, lb = sorted((_parlaklik(a), _parlaklik(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sablon_verisi(veri, tur, gun):
    """Şablon alanı {"kozmetik": {"css": {değişken: renk}}}; ikisi de kapalıysa {} (veri ve görsel eski hâliyle aynı)."""
    if tur not in ("reels", "post"):
        return {}
    css = {}
    if HAFTA_TONU:
        css["vurgu"] = TONLAR[gun.isocalendar()[1] % len(TONLAR)][1]
    d = veri["gram_deg"]
    if YON_ZEMINI and abs(d["yuzde"]) >= SAKIN_ESIK and d["yon"] in ZEMINLER:
        css["zemin"], css["cizgi"], css["isima"] = ZEMINLER[d["yon"]]
    return {"kozmetik": {"css": css}} if css else {}
