"""Goril maskotu: kurallar ve sabitler (Rıdvan, 16 Ekim 2026).

Hafta içi akşam özetinde (`post`) ve cumartesi haftalık özette (`hafta`) fiyatın sağında, değişime göre 5 hâlden
biri çıkar. Çizimler ve hareketleri templates/goril/<hâl>.svg ve .js; şablonlar `{% if maskot %}` ile içerir.

Yüzde: görseldeki okla aynı değer (2 ondalığa yuvarlanmış mutlak değişim).
  Akşam özeti (önceki iş gününe göre):
    özel gün (bot/baslik.py: yuvarlak eşik ilk kez aşıldı ya da en az 1 aylık en yüksek) → ozel (parti şapkalı)
    büyük hareket manşeti (%2; main.BUYUK_HAREKET_GUNLUK) → sevinen / uzulen
    %0,50 – %2 (iki yönde)  → gezinen
    %0,50'nin altı (sakin)  → istif
  Haftalık özet (önceki haftanın son değerine göre; özel gün yok):
    manşet (%5) → sevinen / uzulen · %1,25 – %5 → gezinen · %1,25'in altı → istif
Hâl manşetle aynı karardan (buyuk_hareket) türetilir; goril, rakam ve manşet hiç çelişmez.
İstifleyici yönden bağımsızdır (sakin gün); külçe dizmek fiyatın yönüne bağlanmaz.

Goril GORIL_BASLANGIC'ten itibaren çıkar (26–30 Ekim gorilsiz karşılaştırma haftası). Sabah Reels'i (ölçümde
kontrol grubu), aylık özet, rehber, kart ve pazar yorumunda goril yok; pazar yorumunda hiçbir zaman.
Açıklamaya yalnız sevinen hâlde 2. satır eklenir (SATIR); 1. satır (arama için fiyat satırı) değişmez.

Güvenlik: main.py gorilli görseli ayrı süreçte, SURE_SINIRI saniyede ve yerleşim denetimiyle üretir; herhangi
bir sorun olursa aynı paylaşım bugünkü gibi gorilsiz çıkar. Kapatmak için GORIL_ACIK = False.

Yalnızca standart kütüphane. Sınama: python bot/test_goril.py
"""
import os
from datetime import date

GORIL_ACIK = True
GORIL_BASLANGIC = date(2026, 11, 2)            # ilk akşam 2 Kasım, ilk cumartesi 7 Kasım
TURLER = ("post", "hafta")
SAKIN_ESIK = {"post": 0.5, "hafta": 1.25}      # %: bunun altı istifleyici
DURUMLAR = ("ozel", "sevinen", "istif", "gezinen", "uzulen")
SATIR = {"post": "🦍 Goril bugün sevinçli", "hafta": "🦍 Goril bu hafta sevinçli"}
YOK = {"goril": None, "maskot": None, "maskot_js": None, "goril_satiri": ""}
ETIKET_AYRAC = " · goril: "                    # takipci.md'deki paylaşım adına eklenir (bot/kayit.py)
SURE_SINIRI = 120                              # sn: gorilli üretim bu sürede bitmezse gorilsiz üretilir
YASAL_CUMLE = ("Paylaşımlardaki goril karakteri yalnızca o günün fiyat hareketini gösterir; "
               "alım ya da satım işareti değildir.")


def aktif_mi(gun):
    return GORIL_ACIK and gun >= GORIL_BASLANGIC


def durum(v, tur, gun):
    """Bu paylaşımın goril hâli ya da None (goril yok). v: main.veri_hazirla / haftalik_veri_hazirla çıktısı."""
    if tur not in TURLER or not aktif_mi(gun):
        return None
    if tur == "post" and gun.weekday() >= 5:
        return None
    if tur == "post" and v.get("ozel"):
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
    if z == "ozel" and (tur != "post" or not v.get("ozel")):
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
