# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""İnsan dokunuşu (#33): fiyat paylaşımlarına seyrek, küçük eklemeler (Rıdvan, 11 Kasım 2026).

Rıdvan, 10:15: "sayfayı daha insancıl, daha popüler ve insanların takip etmekten sıkılmayacağı bir hale sokmak
istiyorum"; 10:23: "1 2 3 görelim. Ama çok sık olmamalı." Karar notu Projede claude/insan-dokunusu.md.

Üç ekleme var; yeni paylaşım yok, günlük sınır değişmez. Bir paylaşımda en fazla bir kart ve bir balon olur:

1. Hesap kartı (akşam özeti; Rıdvan 10:30 "1 bin liraya kaç gram gümüş alınır … Uygun"): salı ve perşembe akşamı
   "1.000 ₺ ile bugün X gram gümüş alınır". Hesap kodla yapılır, yapay zekâ yok. Görselin altında ve açıklamada
   "piyasa fiyatıyla; işçilik ve makas hariç" notu. Haftada en çok 2 kart (hesap + neden birlikte sayılır): o hafta
   önceden %2+ hareket günü olduysa neden kartı hesap kartının yerine geçmiş sayılır.
2. Neden kartı (akşam özeti; Rıdvan 10:30 "3 neden yükseldiğinin detayı Uygun"): gram gümüşün %2 ve üstü oynadığı
   akşam, haberlerden tek cümlelik neden (web araması, güvenilir siteler; kaynak açıklamada). Tavsiye, tahmin,
   rakam, kişi ve parti adı yok; denetimden geçmeyen cümle kullanılmaz. Süre sınırlı: yetişmezse ya da bir hata olursa
   kart çıkmaz, paylaşım bugünkü gibi gider (taahhüt: hafta içi her gün 2 kez fiyat). Türkiye'de oy gününde çıkmaz.
3. Goril balonu (Rıdvan 14:18 "goril cümleleri tamam"): pazartesi sabah Reels'i ve cuma akşam özetinde gorilin
   üstünde konuşma balonu. Doğaçlama yok: yalnız Rıdvan'ın onay tablosunda işaretlediği cümleler (BALON), haftaya
   göre sırayla döner. **Düşüş gününde balon çıkmaz** (Rıdvan, 14:18: "goril yorum balonları gümüş düştüğü zaman
   çıkmaması lazım. morali bozuk bir insana espiri yapamayız. !!! dalga geçiyor gibi anlaşılabilir."): gram önceki iş
   gününe göre en küçük düşüşte bile; cuma akşamı haftalık değişim düşüşteyse de (cuma cümleleri haftadan söz ediyor).
   Manşetli, günün başlıklı ya da özel gün paylaşımında, sevinen/üzülen gorilde balon yok (yüzdenin ve başlığın
   üstüne biniyor). Goril yoksa balon da yok (şablon `maskot and goril_balon`).

Hiçbir hata paylaşımı durdurmaz: main.insan_alanlari her hatada eklemesiz devam eder. Kapatmak için ACIK = False.
Yalnızca standart kütüphane (neden kartı anthropic'i yalnız gerektiğinde yükler). Sınama: python bot/test_insan.py
"""
import os
import re
import threading
from datetime import date, timedelta

ACIK = True
# Canlıya alma (Claude önerisi: 16 Kasım reklamsız hafta raporundan sonra; Rıdvan'ın onayıyla değişir).
BASLANGIC = date(2026, 11, 17)

YOK = {"gunun_notu": None, "goril_balon": None}

# ---------------------------------------------------------------- 1. hesap kartı

HESAP_GUNLERI = {1, 3}            # salı, perşembe (akşam özeti)
HESAP_TL = 1000
HESAP_ETIKET = "BUGÜNÜN HESABI"
HESAP_NOTU = "Hesap piyasa fiyatıyla; işçilik ve makas hariç."
HAFTALIK_KART_SINIRI = 2          # hesap + neden kartı birlikte, haftada en çok
BUYUK_ESIK = 2.0                  # % (main.BUYUK_HAREKET_GUNLUK ile aynı: manşet ve neden kartı)

# ---------------------------------------------------------------- 2. neden kartı

NEDEN_MODEL = os.environ.get("INSAN_MODEL", "").strip() or "claude-sonnet-5-5"
NEDEN_SURE_SN = 60                # sn: haber araması en çok bu kadar beklenir, sonra kartsız devam
NEDEN_BUTCE_PAYI_SN = 120         # sn: üretim bütçesinde bundan az kalacaksa arama hiç başlatılmaz
NEDEN_ARAMA = 3                   # en çok arama sayısı
NEDEN_EN_KISA, NEDEN_EN_UZUN = 25, 95   # karakter: kart iki satıra sığsın
NEDEN_ETIKET = {"artis": "BUGÜN NEDEN YÜKSELDİ?", "dusus": "BUGÜN NEDEN DÜŞTÜ?"}
NEDEN_NOTU = "Neden satırı: haberlerden yapay zekâ özeti; kaynak açıklamada."
NEDEN_ACIKLAMA_NOTU = "Neden satırı haber kaynaklarından yapay zekâyla özetlenmiştir."
# Gelecek zaman ve olasılık: neden geçmişte olmuş bir olaydır, tahmin değil.
NEDEN_YASAK = [
    (r"\w(ecek|acak)(tır|tir|lar|ler)?\b", "gelecek zaman"), (r"\w(ebilir|abilir)", "olasılık"),
    (r"\bbeklen(iyor|mektedir)\b.*\b(yüksel|düş|art|geril)", "tahmin"),
]

NEDEN_SISTEM = """Sen bir Instagram gümüş fiyatı hesabı için, gram gümüşün bugünkü sert hareketinin nedenini haberlerden tek cümleyle özetleyen bir araştırmacısın. Cümle görselde "Bugün neden yükseldi/düştü?" başlığının altında gösterilecek.

Kurallar:
- Yalnızca bugün ve dün yayımlanmış haberlere dayan; kaynağını bulamadığın hiçbir şeyi yazma.
- Olanı yaz: tahmin, yorum ve tavsiye yok. Gelecek zaman ve "olabilir" gibi olasılık sözleri kullanma.
- Al, sat, tut, fırsat, hedef, destek, direnç, kesin, garanti, kazanç, portföy, pozisyon gibi sözcükleri kullanma.
- Rakam, yüzde ve tarih yazma.
- Kişi ve parti adı yazma; kurum adı yaz ("Fed", "ABD yönetimi", "TCMB"). Siyasi değerlendirme yapma.
- Tek cümle, en çok 90 karakter, Türkçe, sade ve anlaşılır. Okura hitap etme.
- Neden bulamazsan ya da haberler çelişkiliyse yalnızca "NEDEN: YOK" yaz."""

ORNEK_NEDEN = {"metin": "ABD’de faiz indirimi beklentisi güçlendi, dolar zayıfladı; ons gümüş yükseldi.",
               "kaynaklar": ["bloomberght.com"]}

# ---------------------------------------------------------------- 3. goril balonu
# Rıdvan'ın onay tablosunda (https://claude.ai/artifact/32r87SxehVXXjYqkxMrHrZ, 11 Kasım 2026 14:18) işaretlediği
# cümleler, onun düzelttiği hâliyle. İşaretlenmeyen 7 cümle (7, 17, 24, 26, 29, 34, 36) yok. Yeni cümle yalnız onay
# tablosundan gelir; doğaçlama yazılmaz.
BALON = {
    ("pazartesi", "istif"): [
        "Yeni hafta, yeni külçeler!",
        "Hafta sakin başladı...",
        "Pazartesi sabahı: önce çay.",
        "Sakin bir başlangıç.",
        "Günaydın! Hafta sessiz sedasız açıldı.",
        "Günaydın!",
        "Sabah sabah külçe saymak gibisi yok.",
        "Hafta başladı, ben yerimdeyim.",
        "Günaydın! Yeni haftaya sakin bir merhaba.",
    ],
    ("pazartesi", "gezinen"): [
        "Hafta hareketli başladı, takipteyim!",
        "Pazartesi ve gümüş yerinde durmuyor.",
        "Yeni hafta, yeni rakamlar. Gözüm ekranda!",
        "Günaydın! Gümüş haftaya hareketli girdi.",
        "Hafta başı hareketli, yakından izliyorum.",
        "Henüz pazartesi sabah, hareket başladı bile!",
        "Hafta canlı başladı, gözüm fiyatta.",
        "Gümüşü izlerken çayımı unuttum!",
        "Günaydın! Bugün volta günü.",
    ],
    ("cuma", "istif"): [
        "Sakin bir cuma.",
        "Haftayı sakin kapattık. İyi hafta sonları!",
        "Yarın haftalık özette görüşürüz!",
        "Sakin bir haftanın sonu. Dinlenme vakti!",
        "İyi hafta sonları!",
        "Sakin günler de güzel. Yarın özetteyiz.",
        "Hafta sonu. Herkese iyi dinlenmeler!",
    ],
    ("cuma", "gezinen"): [
        "Hareketli bir haftayı geride bıraktık.",
        "Cuma da boş geçmedi! İyi hafta sonları.",
        "Haftanın tamamı yarın özette!",
        "Hafta hareketli bitti, şimdi dinlenme vakti.",
        "Cuma akşamı ama gümüş hâlâ hareketli.",
        "Hareketli bir cuma. İyi hafta sonları!",
        "Bu haftayı yarın birlikte özetleyelim.",
        "Volta bitti, hafta sonu dinleniyorum.",
    ],
}
BALON_EN_UZUN = 46                # karakter: balon (400 px, 30 px yazı) iki satırı geçmesin
ZORLA = ("hesap", "balon", "neden")


def _tr(x, basamak=2):
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _seri(gecmis_gram):
    return sorted((date.fromisoformat(k), v) for k, v in (gecmis_gram or {}).items() if v)


def zorlanan(ornek=False):
    """Önizleme: INSAN_ZORLA (yalnız --ornek ile) ya da INSAN_DENEME (paylaşmayan elle deneme; paylas.yml konu
    "insan:<tür>"). Gün ve başlangıç tarihi sınırını aşar; düşüş günü ve manşet kuralını aşmaz."""
    z = (os.environ.get("INSAN_ZORLA", "").strip() if ornek else "") or os.environ.get("INSAN_DENEME", "").strip()
    konu = os.environ.get("KONU", "").strip()
    if not z and os.environ.get("DENEME", "").strip().lower() == "true" and konu.startswith("insan:"):
        z = konu.split(":", 1)[1].strip()
    return z if z in ZORLA else None


def aktif_mi(gun):
    return ACIK and gun >= BASLANGIC


# ---------------------------------------------------------------- 1. hesap kartı

def buyuk_gunler(gecmis_gram, gun, esik=BUYUK_ESIK):
    """Bu hafta (pazartesiden dünkü güne) %esik ve üstü hareketin olduğu iş günleri; her gün önceki kaydına göre
    (en çok 6 gün geriye; daha eski kayıtla kıyas yapılmaz)."""
    seri = _seri(gecmis_gram)
    pzt = gun - timedelta(days=gun.weekday())
    sonuc = []
    for (d0, v0), (d1, v1) in zip(seri, seri[1:]):
        if pzt <= d1 < gun and d1 - d0 <= timedelta(days=6):
            if round(abs((v1 / v0 - 1) * 100), 2) >= esik:
                sonuc.append(d1)
    return sonuc


def onceki_kart_sayisi(gecmis_gram, gun):
    """Bu hafta bugünden önce çıkmış sayılan kart: %2+ günleri (neden kartı) + kaydı olan salı/perşembe (hesap)."""
    buyuk = set(buyuk_gunler(gecmis_gram, gun))
    pzt = gun - timedelta(days=gun.weekday())
    kayitli = {d for d, _ in _seri(gecmis_gram) if pzt <= d < gun and d >= BASLANGIC}   # kart başlangıçtan önce yoktu
    buyuk = {d for d in buyuk if d >= BASLANGIC}
    hesap = {d for d in kayitli if d.weekday() in HESAP_GUNLERI and d not in buyuk}
    return len(buyuk) + len(hesap)


def hesap_metni(gram):
    return f"{_tr(HESAP_TL, 0)} ₺ ile bugün {_tr(HESAP_TL / gram, 2)} gram gümüş alınır"


def hesap_karti(v, gecmis_gram, tur, gun, zorla=None):
    if tur != "post" or v.get("ozel"):
        return None
    if zorla != "hesap":
        if not aktif_mi(gun) or gun.weekday() not in HESAP_GUNLERI:
            return None
        if onceki_kart_sayisi(gecmis_gram, gun) >= HAFTALIK_KART_SINIRI:
            return None
    gram = v.get("gram_sayi")
    if not gram or gram <= 0:
        return None
    return {"tur": "hesap", "etiket": HESAP_ETIKET, "metin": hesap_metni(gram), "alt": HESAP_NOTU,
            "aciklama": f"💡 {hesap_metni(gram)} (piyasa fiyatıyla; işçilik ve makas hariç)"}


# ---------------------------------------------------------------- 2. neden kartı

def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def neden_denetle(cumle, kaynaklar):
    """Sorun listesi; boşsa cümle kullanılabilir."""
    sorunlar = []
    c = (cumle or "").strip()
    if not c or c.upper().startswith("YOK"):
        return ["neden yok"]
    if not (NEDEN_EN_KISA <= len(c) <= NEDEN_EN_UZUN):
        sorunlar.append(f"uzunluk {len(c)}")
    if not kaynaklar:
        sorunlar.append("kaynak yok")
    if "\n" in c:
        sorunlar.append("birden çok satır")
    try:
        import yorum
        # Pazar yorumunun yasak listesi; yalnız "kesin" daraltılır: "faiz kesintisi" bir nedendir, kesinlik değil.
        yasak = [(k, a) for k, a in yorum.YASAK if k != r"kesin"] + [(r"\bkesin(likle|lik)?\b", "kesinlik")]
        adlar = yorum.SIYASI_ADLAR
    except Exception:
        yasak, adlar = [(r"\d", "rakam"), (r"%", "yüzde işareti")], []
    k = _kucuk(c)
    for kalip, ad in list(yasak) + NEDEN_YASAK:
        if re.search(kalip, k):
            sorunlar.append(ad)
    for kalip in adlar:
        if re.search(kalip, k):
            sorunlar.append("kişi/parti adı")
            break
    return sorunlar


def _neden_istegi(v, gun):
    g, d = v["gram_deg"], v.get("dolar_deg") or {"yuzde": 0.0}
    yon = "yükseldi" if g["yon"] == "artis" else "düştü"
    ons = ((1 + g["yuzde"] / 100) / (1 + d["yuzde"] / 100) - 1) * 100
    kaynak = "ons gümüşün (dolar fiyatının)" if abs(ons) >= abs(d["yuzde"]) else "dolar/TL kurunun"
    return (f"Bugün {gun:%d.%m.%Y}. Gram gümüş (TL) bugün önceki iş gününe göre %{_tr(abs(g['yuzde']), 1)} {yon}. "
            f"Aynı sürede dolar/TL %{_tr(abs(d['yuzde']), 2)} {'yükseldi' if d['yuzde'] >= 0 else 'düştü'}; "
            f"ons gümüş yaklaşık %{_tr(abs(ons), 1)} {'yükseldi' if ons >= 0 else 'düştü'}. Hareketin büyük kısmı "
            f"{kaynak} hareketinden geliyor.\n\n"
            f"En fazla {NEDEN_ARAMA} aramayla bu hareketin haberlerde gösterilen nedenini bul. Cevabının son satırı "
            "tam olarak şöyle olsun (başka bir şey ekleme):\nNEDEN: <tek cümle>")


def _alan(url):
    from urllib.parse import urlparse
    a = (urlparse(url).hostname or "").lower()
    return a[4:] if a.startswith("www.") else a


def _neden_iste(anahtar, v, gun, sonuc):
    """Ayrı iş parçacığında çalışır; sonucu sonuc sözlüğüne yazar (zaman aşımında kimse beklemez)."""
    try:
        import anthropic
        import yorum
        istemci = anthropic.Anthropic(api_key=anahtar, max_retries=1, timeout=NEDEN_SURE_SN)
        govde = {
            "model": NEDEN_MODEL, "max_tokens": 4000, "system": NEDEN_SISTEM,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": NEDEN_ARAMA,
                       "allowed_domains": yorum.GUVENILIR_SITELER,
                       "user_location": {"type": "approximate", "country": "TR", "timezone": "Europe/Istanbul"}}],
            "messages": [{"role": "user", "content": _neden_istegi(v, gun)}],
        }
        cevap = istemci.messages.create(**govde).model_dump(mode="json", exclude_none=True)
        yorum._harcama_ekle(cevap.get("model") or NEDEN_MODEL, cevap.get("usage"))
        metin, alanlar = "", []
        for b in cevap.get("content", []):
            if b.get("type") != "text":
                continue
            metin += b.get("text", "")
            for c in b.get("citations") or []:
                if c.get("url") and _alan(c["url"]) not in alanlar:
                    alanlar.append(_alan(c["url"]))
        satir = re.findall(r"NEDEN:\s*(.+)", metin)
        sonuc["metin"] = satir[-1].strip().strip('"“”') if satir else ""
        sonuc["kaynaklar"] = alanlar
    except Exception as e:  # noqa: BLE001 — neden kartı hiçbir durumda paylaşımı durdurmaz
        sonuc["hata"] = f"{type(e).__name__}: {str(e)[:200]}"


def neden_karti(v, tur, gun, ornek=False, zorla=None, kalan_sn=None, anahtar=None):
    if tur != "post" or v.get("ozel") or not v.get("buyuk_hareket"):
        if not (zorla == "neden" and tur == "post"):     # önizleme: büyük hareket olmayan günde de dener
            return None
    if zorla != "neden" and not aktif_mi(gun):
        return None
    try:
        import yorum
        if gun in yorum.SECIM_GUNLERI:
            print("İnsan dokunuşu: oy günü, neden kartı yok.")
            return None
    except Exception:
        pass
    yon = v["gram_deg"]["yon"]
    if ornek:
        bulunan = dict(ORNEK_NEDEN)
    else:
        anahtar = anahtar or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not anahtar:
            print("::warning::Neden kartı: Claude API anahtarı yok, kartsız devam ediliyor.")
            return None
        if kalan_sn is not None and kalan_sn < NEDEN_SURE_SN + NEDEN_BUTCE_PAYI_SN:
            print(f"::warning::Neden kartı: üretim bütçesinde {kalan_sn:.0f} sn kaldı, arama başlatılmadı.")
            return None
        bulunan = {}
        is_ = threading.Thread(target=_neden_iste, args=(anahtar, v, gun, bulunan), daemon=True)
        is_.start()
        is_.join(NEDEN_SURE_SN + 5)
        if is_.is_alive():
            print(f"::warning::Neden kartı: haber araması {NEDEN_SURE_SN} sn'de bitmedi, kartsız devam ediliyor.")
            return None
        if bulunan.get("hata"):
            print(f"::warning::Neden kartı alınamadı ({bulunan['hata']}); kartsız devam ediliyor.")
            return None
    metin, kaynaklar = bulunan.get("metin", ""), bulunan.get("kaynaklar") or []
    sorunlar = neden_denetle(metin, kaynaklar)
    if sorunlar:
        print(f"::warning::Neden kartı kullanılmadı ({', '.join(sorunlar)}): {metin!r}")
        return None
    print(f"Neden kartı: {metin} (kaynak: {', '.join(kaynaklar)})")
    return {"tur": "neden", "etiket": NEDEN_ETIKET[yon], "metin": metin, "alt": NEDEN_NOTU,
            "kaynaklar": kaynaklar[:2],
            "aciklama": f"📰 Neden: {metin} (kaynak: {', '.join(kaynaklar[:2])})"}


# ---------------------------------------------------------------- 3. goril balonu

def haftalik_degisim(gecmis_gram, gun, gram):
    """Önceki haftanın son kaydına göre % değişim; kayıt yoksa None (o zaman cuma balonu çıkmaz)."""
    pzt = gun - timedelta(days=gun.weekday())
    onceki = [(d, x) for d, x in _seri(gecmis_gram) if pzt - timedelta(days=7) <= d < pzt]
    if not onceki or not gram:
        return None
    return (gram / onceki[-1][1] - 1) * 100


def balon_cumlesi(an, hal, gun):
    liste = BALON.get((an, hal)) or []
    return liste[(gun.toordinal() // 7) % len(liste)] if liste else None


def goril_balonu(v, gecmis_gram, tur, gun, zorla=None):
    if zorla != "balon":
        if not aktif_mi(gun):
            return None
        if tur == "reels" and gun.weekday() == 0:
            pass
        elif tur == "post" and gun.weekday() == 4:
            pass
        else:
            return None
    an = "pazartesi" if tur == "reels" else "cuma"
    hal = v.get("goril")
    if hal not in ("istif", "gezinen"):
        return None
    if v.get("buyuk_hareket") or v.get("gun_baslik") or v.get("ozel"):
        return None
    # Düşüş günü: espri yok (Rıdvan, 11 Kasım 2026 14:18). En küçük düşüş de sayılır: görseldeki ok kırmızı ▼ ise
    # (main.degisim: yüzde < 0, "%0,00" yazsa bile) balon yok.
    if v["gram_deg"]["yon"] == "dusus" or v["gram_deg"]["yuzde"] < 0:
        return None
    if an == "cuma":
        h = haftalik_degisim(gecmis_gram, gun, v.get("gram_sayi"))
        if h is None or h < 0:
            return None
    return balon_cumlesi(an, hal, gun)


# ---------------------------------------------------------------- hepsi

def sablon_verisi(v, gecmis_gram, tur, gun, ornek=False, kalan_sn=None):
    """Şablona ve açıklamaya giden alanlar: gunun_notu (kart ya da None), goril_balon (cümle ya da None)."""
    z = zorlanan(ornek)
    if tur not in ("reels", "post") or (not aktif_mi(gun) and not z) or gun.weekday() >= 5:
        return dict(YOK)
    kart = None
    if tur == "post" and (v.get("buyuk_hareket") or z == "neden"):
        kart = neden_karti(v, tur, gun, ornek=ornek, zorla=z, kalan_sn=kalan_sn)
    if kart is None and z != "neden":
        kart = hesap_karti(v, gecmis_gram, tur, gun, zorla=z)
    return {"gunun_notu": kart, "goril_balon": goril_balonu(v, gecmis_gram, tur, gun, zorla=z)}
