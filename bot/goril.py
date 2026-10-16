"""Goril maskotu: kurallar ve sabitler (Rıdvan, 16 Ekim 2026).

Hafta içi sabah Reels'inde (`reels`, 19 Ekim 2026'dan; Rıdvan 16 Ekim 22:25 "sabaha şimdi koy"), akşam özetinde
(`post`) ve cumartesi haftalık özette (`hafta`) fiyatın sağında, değişime göre 5 hâlden biri çıkar. Çizimler ve hareketleri templates/goril/<hâl>.svg ve .js; şablonlar `{% if maskot %}` ile içerir.

Yüzde: görseldeki okla aynı değer (2 ondalığa yuvarlanmış mutlak değişim).
  Sabah Reels'i ve akşam özeti (önceki iş gününe göre; ikisinde aynı kural):
    özel gün (bot/baslik.py: yuvarlak eşik ilk kez aşıldı ya da en az 1 aylık en yüksek) → ozel (parti şapkalı)
    büyük hareket manşeti (%2; main.BUYUK_HAREKET_GUNLUK) → sevinen / uzulen
    %0,50 – %2 (iki yönde)  → gezinen
    %0,50'nin altı (sakin)  → istif
  Haftalık özet (önceki haftanın son değerine göre; özel gün yok):
    manşet (%5) → sevinen / uzulen · %1,25 – %5 → gezinen · %1,25'in altı → istif
Hâl manşetle aynı karardan (buyuk_hareket) türetilir; goril, rakam ve manşet hiç çelişmez.
İstifleyici yönden bağımsızdır (sakin gün); külçe dizmek fiyatın yönüne bağlanmaz.

Goril GORIL_BASLANGIC'ten itibaren her gün çıkar (Rıdvan, 16 Ekim 2026 12:3x: "daha erken başlayalım", ölçüm
"her gün goril"; gorilsiz kıyas 13–15 Ekim akşamları). Sabah Reels'i 16 Ekim'e kadar karşılaştırma grubuydu
(gorilsiz sabahlar 13–16 Ekim); Rıdvan 16 Ekim 22:25'te sabaha da istedi. Aylık özet, rehber, kart ve pazar
yorumunda goril yok; pazar yorumunda hiçbir zaman.
Açıklamaya yalnız sevinen hâlde 2. satır eklenir (SATIR); 1. satır (arama için fiyat satırı) değişmez. Sabah
satırında "bugün" yok (gün daha başlamadı; parite cümlesindeki kararla aynı).

Güvenlik: main.py gorilli görseli ayrı süreçte, SURE_SINIRI saniyede üretir; hata ya da süre aşımında aynı
paylaşım bugünkü gibi gorilsiz çıkar. Yerleşim denetimi goril bir yazıyla üst üste binerse paylaşımı durdurmaz:
goril kalır, günlüğe "Goril üst üste biniyor" uyarısı düşer ve gece kontrolü Rıdvan'a bildirir (Rıdvan, 16 Ekim
2026 22:43). Kapatmak için GORIL_ACIK = False.

Yalnızca standart kütüphane. Sınama: python bot/test_goril.py
"""
import os
from datetime import date

GORIL_ACIK = True
GORIL_BASLANGIC = date(2026, 10, 16)           # ilk akşam 16 Ekim, ilk cumartesi 17 Ekim
TURLER = ("reels", "post", "hafta")
GUNLUK = ("reels", "post")                     # hafta içi, önceki iş gününe göre; özel gün hâli var
SAKIN_ESIK = {"reels": 0.5, "post": 0.5, "hafta": 1.25}   # %: bunun altı istifleyici
DURUMLAR = ("ozel", "sevinen", "istif", "gezinen", "uzulen")
SATIR = {"reels": "🦍 Goril bu sabah sevinçli", "post": "🦍 Goril bugün sevinçli", "hafta": "🦍 Goril bu hafta sevinçli"}
YOK = {"goril": None, "maskot": None, "maskot_js": None, "goril_satiri": ""}
ETIKET_AYRAC = " · goril: "                    # takipci.md'deki paylaşım adına eklenir (bot/kayit.py)
SURE_SINIRI = 120                              # sn: gorilli üretim bu sürede bitmezse gorilsiz üretilir


def aktif_mi(gun):
    return GORIL_ACIK and gun >= GORIL_BASLANGIC


def durum(v, tur, gun):
    """Bu paylaşımın goril hâli ya da None (goril yok). v: main.veri_hazirla / haftalik_veri_hazirla çıktısı."""
    if tur not in TURLER or not aktif_mi(gun):
        return None
    if tur in GUNLUK and gun.weekday() >= 5:
        return None
    if tur in GUNLUK and v.get("ozel"):
        return "ozel"
    b = v.get("buyuk_hareket")
    if b:
        return "sevinen" if b["yon"] == "artis" else "uzulen"
    yuzde = round(abs(v["gram_deg"]["yuzde"]), 2)
    return "gezinen" if yuzde >= SAKIN_ESIK[tur] else "istif"


def _zorlanan(v, tur, ornek):
    """Önizleme için hâl: GORIL_ZORLA (yalnız --ornek ile) ya da GORIL_DENEME (iş akışının paylaşmayan elle deneme
    çalıştırması verir). Tarih sınırını aşar. Özel gün hâli yalnız gerçekten özel gün verisi varken zorlanır."""
    z = (os.environ.get("GORIL_ZORLA", "").strip() if ornek else "") or os.environ.get("GORIL_DENEME", "").strip()
    if tur not in TURLER or z not in DURUMLAR:
        return None
    if z == "ozel" and (tur not in GUNLUK or not v.get("ozel")):
        return None
    return z


def sablon_verisi(v, tur, gun, ornek=False):
    """Şablona ve açıklamaya giden alanlar (goril, maskot, maskot_js, goril_satiri)."""
    d = _zorlanan(v, tur, ornek) or durum(v, tur, gun)
    if not d:
        return dict(YOK)
    return {"goril": d, "maskot": f"goril/{d}.svg", "maskot_js": f"goril/{d}.js",
            "goril_satiri": (SATIR[tur] + "\n") if d == "sevinen" else ""}


def etiket_ekle(etiket, durum_):
    return f"{etiket}{ETIKET_AYRAC}{durum_}" if durum_ in DURUMLAR else etiket


def etiket_ayir(etiket):
    """'Günlük özet · goril: istif (deneme)' → ('Günlük özet (deneme)', 'istif'); goril yoksa (etiket, None)."""
    if ETIKET_AYRAC not in etiket:
        return etiket, None
    bas, son = etiket.split(ETIKET_AYRAC, 1)
    d, _, kalan = son.partition(" ")
    return (bas + (" " + kalan if kalan else "")), (d if d in DURUMLAR else None)
