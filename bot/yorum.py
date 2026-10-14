"""Pazar yapay zekâ yorumu: gram gümüş için kısa, orta ve uzun vadeli görünüm (kaydırmalı, 4 görsel).

Yorum pazar sabahı, o anki bütün verilerle şekillenir. İki adımda üretilir:
  1. Haftanın gelişmeleri: Claude, web aramasıyla haftanın gümüş, dolar, faiz, sanayi talebi ve
     Türkiye (dolar/TL, TCMB) haberlerini ve daha uzun dönem bağlamını kaynaklı olarak özetler.
     Bu adım yorum yazmaz; yalnızca kaynaklarda yazanları derler. Başarısız olursa yorum yalnızca
     fiyat ve kur verileriyle yazılır, açıklamada da öyle belirtilir.
  2. Yorum: botun günlük kayıtları, pazar günü alınan haftalık kapanış fiyatı, 13 aylık dolar/TL
     ve 1. adımdaki özet birlikte verilir; Claude kısa/orta/uzun vade yorumunu yazar.

Yasal çerçeve — SPK III-37.1 Tebliğ'in medya ve elektronik ortamdaki yorumlara uygulanan
78-80. maddeleri esas alınarak:
  - Yönlendirici değildir: al/sat/tut, hedef fiyat, seviye yok; kişiye ya da gruba özel değildir.
  - Tahminler koşullu yazılır, iki yön de anılır; varsayımları açıklamada yazılıdır.
  - Kullanılan verilerin tarihi, kaynakları (haber kaynakları dahil) ve güncelleme sıklığı belirtilir.
  - Yapay zekâyla üretildiği görselde ve açıklamada açıkça yazılır.
  - Açıklamada "yatırım danışmanlığı kapsamında değildir" standart uyarısı yer alır.
Rakamları görsel kod tarafından yazılır, yorum metninde rakam bulunmasına izin verilmez (uydurma
seviye/hedef çıkmasın). Kurum ve olay adları (Fed, TCMB, seçim, gümrük vergisi…) yalnızca haftanın
gelişmeleri özetinde geçiyorsa kullanılabilir; özet yoksa hiç kullanılamaz.

Yapay zekâ: Anthropic Claude API (ANTHROPIC_API_KEY). Haftada 2 çağrı + birkaç web araması;
ayda yaklaşık 1 dolar.
"""
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from urllib.parse import urlparse

import requests

ONS_GRAM = 31.1034768
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("YZ_MODEL", "").strip() or "claude-sonnet-5-5"
# Sonnet 5.5'te düşünme (thinking) varsayılan olarak açık ve düşünme tokenları max_tokens'a dahil.
# Sınır düşük kalırsa model yanıtı yazmadan kesilir (stop_reason: max_tokens; 14 Ekim 2026 denemesi).
# Bu yüzden sınır geniş, düşünme düzeyi "medium" ile sınırlı. Gerçek maliyet kullanılan tokena göredir.
YANIT_SINIRI = 16000
CABA = os.environ.get("YZ_CABA", "").strip() or "medium"
MODEL_ADI = "Claude, Anthropic"

HASHTAG = "#gümüş #gümüşyatırımı #gümüşfiyatları #değerlimetaller #emtia"

# pencere: gün; esnek: kayıt kısaysa eldeki en uzun süreyle (en az 3 gün; ilk hafta salı→cuma) hesaplanır
VADELER = [
    {"anahtar": "kisa", "ad": "Kısa vade", "ufuk": "1–4 hafta", "pencere": 28, "etiket": "Son 4 hafta", "esnek": True},
    {"anahtar": "orta", "ad": "Orta vade", "ufuk": "1–6 ay", "pencere": 91, "etiket": "Son 3 ay", "esnek": False},
    {"anahtar": "uzun", "ad": "Uzun vade", "ufuk": "1 yıl ve üzeri", "pencere": 365, "etiket": "Son 1 yıl", "esnek": False},
]

# Kelime sınırları (görselde büyük yazı sığsın diye). Model açıklamada bunları görür; kod biraz pay bırakır.
SINIR = {"ozet": 5, "durum": 18, "seyir": 26, "izlenecek": 8}
PAY = {"ozet": 1, "durum": 4, "seyir": 5, "izlenecek": 3}

# Yönlendirici, kesinlik bildiren ya da abartılı ifadeler; rakamlar.
YASAK = [
    (r"\b(al|alın|alınız|almalı|almak|sat|satın|satınız|satmalı|satmak|tut|tutun|tutmalı|tutmak)\b", "al/sat/tut"),
    (r"\b(ekleyin|azaltın|biriktirin|değerlendirin|bekleyin|kaçırmayın|girin|çıkın)\b", "okura emir"),
    (r"fırsat", "fırsat"), (r"hedef", "hedef"), (r"direnç", "direnç"), (r"destek seviye", "destek seviyesi"),
    (r"\bstop", "stop"), (r"kesin", "kesinlik"), (r"garanti", "garanti"), (r"mutlaka", "kesinlik"),
    (r"kaçırma", "kaçırma"), (r"tavsiye", "tavsiye"), (r"öneri|öner", "öneri"), (r"portföy", "portföy"),
    (r"pozisyon", "pozisyon"), (r"kazandır|kazanç", "kazanç vaadi"), (r"yatırım yap", "yatırım çağrısı"),
    (r"patla|uçuş|roket|çakıl|çöküş|çöker", "abartı"),
    (r"\d", "rakam"), (r"%", "yüzde işareti"), (r"\byüzde", "yüzde"), (r"baz puan", "baz puan"),
]

# Güncel olay ve kurum adları: yorumda ancak haftanın gelişmeleri özetinde (aynı gruptan bir ifade)
# geçiyorsa kullanılabilir. Özet yoksa hiçbiri kullanılamaz (model bunları bilemez, uydurmasın).
# (Faiz beklentisi, enflasyon, istihdam, sanayi talebi gibi genel etkenler serbest; bunlar olay değil.)
OLAY_GRUPLARI = {
    "merkez bankası": [r"\bfed\b", r"powell", r"federal rezerv", r"merkez bankas", r"\btcmb\b", r"\becb\b"],
    "seçim": [r"seçim"],
    "savaş / çatışma": [r"savaş", r"ateşkes", r"çatışma", r"saldırı"],
    "ticaret / yaptırım": [r"gümrük", r"tarife", r"yaptırım"],
}

SISTEM = """Sen bir Instagram hesabı için her pazar gram gümüşün kısa, orta ve uzun vadeli görünümünü yazan bir yapay zekâsın. Yazdıkların görselde büyük puntoyla gösterilecek ve "yapay zekâ yorumudur, yatırım tavsiyesi değildir" uyarısıyla yayımlanacak.

Dayanakların iki tanedir ve ikisini birlikte kullan:
- Fiyat ve kur verileri (JSON): botun günlük kayıtları, pazar günü alınan haftalık kapanış, haftalık kapanışlar, aylık dolar/TL.
- "haftanin_gelismeleri": bu sabah web aramasıyla derlenmiş, kaynaklı haber özeti (haftanın gelişmeleri, önümüzdeki haftanın takvimi, uzun dönem bağlam).

Kurallar (hepsine uy):
1. Yalnızca bu iki dayanakta yazanlara dayan. Özette geçmeyen olay, kurum, kişi, karar ya da veriden söz etme. Özet yoksa güncel olaylardan, kurum adlarından hiç söz etme.
2. Fiyat verileri ile haber özeti çelişirse fiyat verilerini esas al (görselde onlar gösteriliyor).
3. Haberleri kendi cümlelerinle, çok kısa an; alıntı yapma, kaynak adı yazma. Bir gelişmenin fiyata etkisini kesin bir neden gibi değil, "etkili olmuş olabilir" gibi temkinli yaz.
4. Yönlendirme yapma: al, sat, tut, ekle, azalt, bekle, fırsat, hedef fiyat, destek/direnç seviyesi, stop, portföy, pozisyon gibi ifadeler kullanma. Okura ne yapması gerektiğini söyleme, emir kipi kullanma, okura hitap etme.
5. Kesinlik bildirme: "kesin, garanti, mutlaka, kesinlikle" yok. Olası seyri koşullu yaz ("... sürerse", "... durumunda") ve her zaman iki yönü de an.
6. Hiç rakam, yüzde, baz puan, tarih yazma; sayıları yazıyla da yazma. Sayılar görselde ayrıca gösteriliyor. "Üç ay", "bir yıl", "önümüzdeki hafta" gibi süreleri yazıyla yazabilirsin.
7. Abartılı, heyecanlı dil yok (patlama, uçuş, çöküş, roket gibi). Sakin, sade, günlük Türkçe; Türkçe karakterleri doğru kullan.
8. Gram gümüşün TL fiyatı ons gümüş (dolar) ile dolar/TL'nin çarpımından gelir; hareketin onstan mı kurdan mı geldiğini ayırt etmeye çalış.
9. Vadelere göre ağırlık: kısa vadede bu haftanın fiyat hareketi, haftanın gelişmeleri ve önümüzdeki haftanın takvimi; orta vadede son aylardaki eğilim, faiz beklentileri ve kur; uzun vadede yıllık eğilim ve arz-talep gibi yapısal etkenler.
10. Bir vade için fiyat kaydı yetersizse (veri_yeterli: false) bu, görselde ayrıca not olarak yazılır; "durum" alanında kayıtların kısa olduğunu tekrarlama. O vadeyi özetteki uzun dönem bağlam ve kur verisiyle, daha temkinli yaz.

Her vade için alanlar:
- ozet: kapakta görünen çok kısa başlık, en fazla 5 kelime.
- durum: verilerde ve haberlerde ne görülüyor, en fazla 18 kelime, tek cümle.
- seyir: koşullu olası seyir, iki yönü de anarak, en fazla 26 kelime.
- izlenecek: izlenecek etkenler, en fazla 8 kelime, cümle değil."""


def _vade_sema():
    alan = lambda a: {"type": "string", "description": f"en fazla {SINIR[a]} kelime"}
    return {"type": "object", "additionalProperties": False,
            "properties": {k: alan(k) for k in SINIR}, "required": list(SINIR)}


SEMA = {"type": "object", "additionalProperties": False,
        "properties": {v["anahtar"]: _vade_sema() for v in VADELER},
        "required": [v["anahtar"] for v in VADELER]}


# ---------------------------------------------------------------- haftanın gelişmeleri (web araması)

ARAMA_SINIRI = 6   # haftada en fazla 6 arama (~6 sent)
# Forum ve sosyal medya sonuçları dışarıda kalsın; kalan sonuçlarda model haber ajanslarını ve
# resmi kurumları tercih eder.
ENGELLI_SITELER = ["reddit.com", "x.com", "twitter.com", "facebook.com", "instagram.com", "tiktok.com",
                   "youtube.com", "eksisozluk.com", "quora.com", "pinterest.com", "telegram.org", "t.me"]

# Web araması yalnızca bu sitelerde yapılır (haber ajansları, resmi kurumlar, tanınmış ekonomi basını).
# 14 Ekim denemesinde serbest aramada forex bonus ve hisse sinyal siteleri kaynak olarak çıktı; SPK III-37.1
# md. 78 yorumların güvenilir kaynaklara dayanmasını istiyor. Alt alan adları da dahildir (bigpara.hurriyet.com.tr).
# Liste boşaltılırsa yalnızca ENGELLI_SITELER uygulanır.
GUVENILIR_SITELER = [
    # dünya
    # reuters.com, apnews.com, ft.com, wsj.com, marketwatch.com Claude'un tarayıcısına kapalı: listede
    # olursa API isteği 400 ile reddeder (14 Ekim 2026). Kapanan bir site çıkarsa hata mesajı adını söyler.
    "bloomberg.com", "cnbc.com", "kitco.com", "fxstreet.com", "investing.com", "tradingeconomics.com", "mining.com", "cmegroup.com",
    # kurumlar
    "silverinstitute.org", "lbma.org.uk", "federalreserve.gov", "bls.gov", "bea.gov", "ecb.europa.eu",
    "tcmb.gov.tr", "tuik.gov.tr",
    # Türkiye
    "aa.com.tr", "bloomberght.com", "dunya.com", "ekonomim.com", "hurriyet.com.tr", "haberturk.com",
    "ntv.com.tr", "trthaber.com", "paraanaliz.com", "ekonomist.com.tr",
]

ARASTIRMA_SISTEM = """Sen bir piyasa haberleri araştırmacısısın. Bugün pazar; bir Instagram hesabında yayımlanacak gram gümüş yorumuna dayanak olacak haftanın gelişmelerini web aramasıyla derliyorsun.

Kurallar:
- Yorum yazma, tahmin yapma, tavsiye verme. Yalnızca kaynaklarda yazanları kendi cümlelerinle, kısaca özetle; alıntı yapma.
- Haber ajanslarını, resmi kurumların sitelerini ve tanınmış ekonomi basınını tercih et. Forum, sosyal medya, reklam ve "al-sat sinyali" sitelerini kullanma.
- Her madde tek cümle olsun ve olayın tarihini gün.ay olarak içersin. Rakamları kaynakta yazdığı gibi verebilirsin.
- Emin olamadığın ya da kaynağını bulamadığın hiçbir şeyi yazma; bir başlıkta bir şey bulamazsan "bulunamadı" yaz.
- Toplam en fazla 300 kelime. Türkçe yaz."""


def _arastirma_istegi(bugun):
    pazartesi = bugun - timedelta(days=bugun.weekday())
    if bugun.weekday() >= 5:
        hafta = f"{pazartesi:%d.%m.%Y}–{pazartesi + timedelta(days=4):%d.%m.%Y}"
    else:                                   # hafta içi elle çalıştırılırsa son 7 gün
        hafta = f"{bugun - timedelta(days=7):%d.%m.%Y}–{bugun:%d.%m.%Y}"
    return f"""Bugün {bugun:%d.%m.%Y}. Değerlendirilecek hafta: {hafta}.

En fazla {ARAMA_SINIRI} aramayla şu başlıklarda bilgi derle ve aynı başlıklarla yaz:

## 1. Gümüş bu hafta
Ons gümüşün (XAG/USD) bu haftaki seyri ve haberlerde gösterilen nedenler; altın ve altın/gümüş paritesi.
## 2. Dolar ve faiz
ABD doları, Fed ve faiz beklentileri, bu hafta açıklanan önemli ABD verileri (enflasyon, istihdam).
## 3. Talep ve arz
Sanayi talebi (güneş paneli, elektronik, elektrikli araç), madencilik arzı, ETF ve stok hareketleri, Çin.
## 4. Türkiye
Dolar/TL'nin bu haftaki seyri; TCMB kararı ya da açıklaması, enflasyon verisi gibi kuru etkileyen gelişmeler.
## 5. Daha uzun dönem
Gümüşün son üç ay ve son bir yıldaki genel eğilimi; kurumların (ör. The Silver Institute) arz-talep görünümü.
## 6. Önümüzdeki hafta
Gümüşü ve doları etkileyebilecek, takvimde olan veri açıklamaları ve toplantılar.

1–4. başlıklarda yalnızca bu haftaya ait, 5. başlıkta son üç ay içinde yayımlanmış kaynakları kullan."""


def _alan_adi(url):
    alan = (urlparse(url).hostname or "").lower()
    return alan[4:] if alan.startswith("www.") else alan


def haftanin_gelismeleri(bugun, anahtar=None):
    """Web aramasıyla haftanın gelişmeleri özeti: {"metin", "kaynaklar", "arama", "model"} ya da None.

    Metinde her kaynaklı cümlenin sonuna "(kaynak: alan.com)" eklenir; kaynaklar yorum açıklamasında
    listelenir (Claude API web araması şartı: kullanıcıya gösterilen çıktıda kaynak gösterilmeli).
    Hiç kaynak yoksa özet kullanılmaz. Hata olursa uyarı yazılır, None döner; yorum yine yazılır.
    """
    anahtar = anahtar or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        return None
    govde = {
        "model": MODEL,
        "max_tokens": YANIT_SINIRI,
        "output_config": {"effort": CABA},
        "system": ARASTIRMA_SISTEM,
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": ARAMA_SINIRI,
                   **({"allowed_domains": GUVENILIR_SITELER} if GUVENILIR_SITELER
                      else {"blocked_domains": ENGELLI_SITELER}),
                   "user_location": {"type": "approximate", "country": "TR", "timezone": "Europe/Istanbul"}}],
        "messages": [{"role": "user", "content": _arastirma_istegi(bugun)}],
    }
    try:
        bloklar, arama, cikti_token = [], 0, 0
        for _ in range(4):
            cevap = _api(anahtar, govde, zaman_asimi=300)
            bloklar += cevap.get("content", [])
            arama += (cevap.get("usage", {}).get("server_tool_use") or {}).get("web_search_requests") or 0
            cikti_token += cevap.get("usage", {}).get("output_tokens") or 0
            if cevap.get("stop_reason") != "pause_turn":
                break
            # Uzun süren arama turu duraklatıldı: yanıtı olduğu gibi geri gönderip devam ettir.
            govde["messages"] = govde["messages"] + [{"role": "assistant", "content": cevap["content"]}]
        else:
            raise RuntimeError("arama turu tamamlanmadı (pause_turn)")
        if cevap.get("stop_reason") not in ("end_turn", "stop_sequence"):
            raise RuntimeError(f"yanıt tamamlanmadı (stop_reason: {cevap.get('stop_reason')})")

        parcalar, kaynaklar = [], {}
        for b in bloklar:
            if b.get("type") != "text":
                continue
            metin = b.get("text", "")
            alanlar = []
            for c in b.get("citations") or []:
                url = c.get("url")
                if not url:
                    continue
                alan = _alan_adi(url)
                kaynaklar.setdefault(url, {"url": url, "baslik": c.get("title") or alan, "alan": alan})
                if alan not in alanlar:
                    alanlar.append(alan)
            if alanlar and metin.strip():
                metin = metin.rstrip() + f" (kaynak: {', '.join(alanlar)})" + metin[len(metin.rstrip()):]
            parcalar.append(metin)
        ozet = "".join(parcalar).strip()
        if not kaynaklar:
            raise RuntimeError("özette kaynak gösterilen bilgi yok")
        print(f"Haftanın gelişmeleri derlendi ({arama} arama, {len(kaynaklar)} kaynak, {len(ozet)} karakter, "
              f"{cikti_token} çıktı token)")
        return {"metin": ozet, "kaynaklar": list(kaynaklar.values()), "arama": arama, "model": MODEL}
    except Exception as e:
        print(f"::warning::Haftanın gelişmeleri alınamadı ({e}); yorum yalnızca fiyat ve kur verileriyle yazılacak")
        return None


def kaynak_alanlari(gelismeler, en_fazla=None):
    """Açıklamada listelenecek haber kaynaklarının alan adları, en çok kullanılandan başlayarak."""
    if not gelismeler:
        return []
    sayac = {}
    for k in gelismeler["kaynaklar"]:
        sayac[k["alan"]] = sayac.get(k["alan"], 0) + 1
    alanlar = sorted(sayac, key=lambda a: (-sayac[a], a))
    return alanlar[:en_fazla] if en_fazla else alanlar


# ---------------------------------------------------------------- seriler ve istatistik

def seri_kur(kayitlar, ecb, metal_gecmis=None):
    """Günlük seri: tarih -> {gumus, altin, dolar, gram}.

    kayitlar: botun günlük kayıtları (veri/gecmis.json; pazar günü alınan kapanış dahil), ecb: tarih -> USD/TRY,
    metal_gecmis: (varsa) MetalCharts geçmişi {"XAG": {tarih: kapanış}, "XAU": {...}}.
    Kendi kayıtlarımız aynı gün için geçmişin önüne geçer (paylaşılan değerlerle tutarlı olsun).
    """
    seri = {}
    if metal_gecmis and metal_gecmis.get("XAG"):
        ecb_gunler = sorted(ecb)
        for g, gumus in metal_gecmis["XAG"].items():
            onceki = [d for d in ecb_gunler if d <= g]
            if not onceki:
                continue
            dolar = ecb[onceki[-1]]
            altin = metal_gecmis.get("XAU", {}).get(g)
            seri[g] = {"gumus": gumus, "altin": altin, "dolar": dolar, "gram": gumus * dolar / ONS_GRAM}
    for g, k in kayitlar.items():
        seri[g] = {"gumus": k["gumus"], "altin": k.get("altin"), "dolar": k["dolar"], "gram": k["gram"],
                   "saat": k.get("saat")}
    return dict(sorted(seri.items()))


def _deger_once(seri, hedef, tolerans=7):
    """hedef tarihte ya da en fazla `tolerans` gün öncesinde kayıtlı son değer."""
    adaylar = [d for d in seri if hedef - timedelta(days=tolerans) <= d <= hedef]
    return (adaylar[-1], seri[adaylar[-1]]) if adaylar else (None, None)


def _yuzde(simdi, once):
    if simdi is None or once in (None, 0):
        return None
    return (simdi / once - 1) * 100


def vade_istatistikleri(seri, ecb):
    """Her vade için gram (₺), ons ($), parite ve dolar/TL değişimi; veri yetmiyorsa None."""
    if len(seri) < 2:
        raise ValueError("seri çok kısa")
    son_gun = max(seri)
    son = seri[son_gun]
    ilk_gun = min(seri)
    ecb_son_gun = max(d for d in ecb if d <= son_gun)
    sonuc = {}
    for v in VADELER:
        hedef = son_gun - timedelta(days=v["pencere"])
        gun, once = _deger_once(seri, hedef)
        etiket, kisa_kayit = v["etiket"], False
        if gun is None and v["esnek"] and (son_gun - ilk_gun).days >= 3:
            gun, once = ilk_gun, seri[ilk_gun]
            etiket, kisa_kayit = f"Son {(son_gun - ilk_gun).days} gün", True
            hedef = ilk_gun
        _, dolar_once = _deger_once(ecb, hedef)
        pencere_gram = [seri[d]["gram"] for d in seri if (gun or hedef) <= d <= son_gun]
        parite = lambda x: (x["altin"] / x["gumus"]) if x and x.get("altin") else None
        sonuc[v["anahtar"]] = {
            "etiket": etiket,
            "kisa_kayit": kisa_kayit,
            "veri_yeterli": gun is not None,
            "baslangic": gun.isoformat() if gun else None,
            "gram": _yuzde(son["gram"], once["gram"] if once else None),
            "ons": _yuzde(son["gumus"], once["gumus"] if once else None),
            "parite": _yuzde(parite(son), parite(once)),
            "dolar": _yuzde(ecb[ecb_son_gun], dolar_once),
            "gram_en_yuksek": max(pencere_gram) if gun else None,
            "gram_en_dusuk": min(pencere_gram) if gun else None,
        }
    return sonuc


def model_girdisi(seri, ecb, ist, bugun, kaynak_notu, gelismeler=None, kapanis=False):
    son_gun = max(seri)
    son = seri[son_gun]
    yuv = lambda x, n=2: None if x is None else round(x, n)
    parite = lambda x: yuv(x["altin"] / x["gumus"], 1) if x.get("altin") else None

    haftalik = {}
    for g, x in seri.items():
        haftalik[g.isocalendar()[:2]] = (g, x)            # her haftanın son kaydı
    haftalik = [{"hafta_son_gunu": g.isoformat(), "gram_tl": yuv(x["gram"]), "ons_usd": yuv(x["gumus"]),
                 "altin_gumus_paritesi": parite(x), "dolar_tl": yuv(x["dolar"], 3)}
                for g, x in list(haftalik.values())[-13:]]
    aylik_dolar = {}
    for g in sorted(ecb):
        aylik_dolar[g.strftime("%Y-%m")] = ecb[g]
    gunluk = list(seri.values())[-21:]
    oynaklik = [abs(b["gram"] / a["gram"] - 1) * 100 for a, b in zip(gunluk, gunluk[1:])]
    son_10_gun = [{"tarih": g.isoformat(), "saat": x.get("saat"), "gram_tl": yuv(x["gram"]),
                   "ons_usd": yuv(x["gumus"]), "altin_gumus_paritesi": parite(x), "dolar_tl": yuv(x["dolar"], 3)}
                  for g, x in seri.items() if g > son_gun - timedelta(days=10)]
    return {
        "bugun": bugun.isoformat(),
        "son_veri": {"tarih": son_gun.isoformat(), "saat": son.get("saat"),
                     "not": "haftanın kapanış fiyatı (pazar günü alındı)" if kapanis else "botun son kaydı",
                     "gram_tl": yuv(son["gram"]), "ons_usd": yuv(son["gumus"]), "dolar_tl": yuv(son["dolar"], 3),
                     "altin_gumus_paritesi": parite(son)},
        "metal_verisi": kaynak_notu,
        "metal_kayit_baslangici": min(seri).isoformat(),
        "son_10_gun": son_10_gun,
        "vadeler": {k: {"pencere": x["etiket"], "veri_yeterli": x["veri_yeterli"],
                        "gram_degisim_yuzde": yuv(x["gram"]), "ons_degisim_yuzde": yuv(x["ons"]),
                        "parite_degisim_yuzde": yuv(x["parite"]), "dolar_tl_degisim_yuzde": yuv(x["dolar"]),
                        "gram_en_yuksek": yuv(x["gram_en_yuksek"]), "gram_en_dusuk": yuv(x["gram_en_dusuk"])}
                    for k, x in ist.items()},
        "haftalik_kapanislar": haftalik,
        "aylik_dolar_tl": [{"ay": a, "dolar_tl": yuv(d, 3)} for a, d in list(aylik_dolar.items())[-13:]],
        "gram_ortalama_gunluk_hareket_yuzde": yuv(sum(oynaklik) / len(oynaklik)) if oynaklik else None,
        "haftanin_gelismeleri": (gelismeler["metin"] if gelismeler else
                                 "YOK — bu hafta haber taraması yapılamadı. Güncel olaylardan, kurum adlarından "
                                 "söz etme; yalnızca fiyat ve kur verilerine dayan."),
    }


# ---------------------------------------------------------------- denetim

def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def denetle(yorum, gelismeler=None):
    """Kurallara uymayan alanların listesi (boşsa yorum yayımlanabilir).

    gelismeler: haftanın gelişmeleri özeti; yorumdaki kurum/olay adları bu metinde geçmeli.
    """
    ozet = _kucuk(gelismeler["metin"]) if gelismeler else ""
    hatalar = []
    for v in VADELER:
        alanlar = yorum.get(v["anahtar"]) or {}
        for alan, sinir in SINIR.items():
            metin = (alanlar.get(alan) or "").strip()
            yer = f"{v['anahtar']}.{alan}"
            if not metin:
                hatalar.append(f"{yer}: boş")
                continue
            kelime = len(metin.split())
            if kelime > sinir + PAY[alan]:
                hatalar.append(f"{yer}: {kelime} kelime (en fazla {sinir})")
            kucuk = _kucuk(metin)
            for desen, ad in YASAK:
                if re.search(desen, kucuk):
                    hatalar.append(f"{yer}: yasak ifade ({ad}): {metin!r}")
                    break
            for grup, desenler in OLAY_GRUPLARI.items():
                bulunan = next((m.group(0) for d in desenler for m in [re.search(d, kucuk)] if m), None)
                if bulunan and not any(re.search(d, ozet) for d in desenler):
                    neden = "haber özetinde geçmiyor" if ozet else "bu hafta haber özeti yok"
                    hatalar.append(f"{yer}: güncel olay/kurum ({grup}: {bulunan!r}) — {neden}, kullanma")
    return hatalar


# ---------------------------------------------------------------- yapay zekâ çağrısı

def _api(anahtar, govde, zaman_asimi=120):
    """Claude Messages API'ye istek; geçici hatalarda bekleyip yeniden dener. Yanıt JSON'u döndürür."""
    son_hata = None
    for deneme in range(4):
        try:
            r = requests.post(API_URL, json=govde, timeout=zaman_asimi, headers={
                "x-api-key": anahtar, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        except requests.RequestException as e:
            son_hata = e
            time.sleep(10 * (deneme + 1))
            continue
        if r.status_code in (401, 403):
            raise RuntimeError(f"Claude API anahtarı geçersiz ya da yetkisiz (HTTP {r.status_code}): {r.text[:300]}")
        if r.status_code in (429, 500, 502, 503, 529):
            son_hata = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            time.sleep(20 * (deneme + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Claude API hatası (HTTP {r.status_code}): {r.text[:500]}")
        return r.json()
    raise RuntimeError(f"Claude API'ye ulaşılamadı: {son_hata}")


def _cagir(anahtar, mesajlar):
    cevap = _api(anahtar, {
        "model": MODEL,
        "max_tokens": YANIT_SINIRI,
        "system": SISTEM,
        "messages": mesajlar,
        "output_config": {"effort": CABA, "format": {"type": "json_schema", "schema": SEMA}},
    }, zaman_asimi=300)
    if cevap.get("stop_reason") not in ("end_turn", "stop_sequence"):
        raise RuntimeError(f"Claude yanıtı tamamlanmadı (stop_reason: {cevap.get('stop_reason')})")
    metin = "".join(b.get("text", "") for b in cevap.get("content", []) if b.get("type") == "text")
    return metin, cevap


def yz_yorum(girdi, gelismeler=None):
    """Claude'dan yorum alır; kurallara uymazsa hataları göstererek en fazla 2 kez yeniden ister."""
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        return None
    mesajlar = [{"role": "user", "content":
                 "Bu haftanın gram gümüş verileri ve haftanın gelişmeleri aşağıda (JSON). Kısa, orta ve uzun "
                 "vade için yorumu yaz.\n\n" + json.dumps(girdi, ensure_ascii=False, indent=1)}]
    for tur in range(3):
        metin, cevap = _cagir(anahtar, mesajlar)
        try:
            yorum = json.loads(metin)
        except ValueError:
            hatalar = ["yanıt geçerli JSON değil"]
        else:
            hatalar = denetle(yorum, gelismeler)
            if not hatalar:
                kullanim = cevap.get("usage", {})
                print(f"Yapay zekâ yorumu alındı ({MODEL}, {kullanim.get('input_tokens')} girdi / "
                      f"{kullanim.get('output_tokens')} çıktı token, {tur + 1}. deneme)")
                return yorum
        print(f"Uyarı: yorum kurallara uymadı ({tur + 1}. deneme): {hatalar}", file=sys.stderr)
        mesajlar += [{"role": "assistant", "content": metin},
                     {"role": "user", "content": "Şu sorunlar var, kurallara uyarak yeniden yaz:\n- "
                      + "\n- ".join(hatalar)}]
    raise RuntimeError(f"Yapay zekâ yorumu 3 denemede kurallara uymadı: {hatalar}")


# ---------------------------------------------------------------- örnek (yerel önizleme)
# Örnekteki haberler uydurmadır; yalnızca görsel ve açıklama düzenini denemek içindir.

ORNEK_GELISMELER = {
    "metin": (
        "## 1. Gümüş bu hafta\nOns gümüş hafta başındaki gerilemenin ardından cuma günü haftayı yükselişle "
        "kapattı; altın da yükseldi (16.10). (kaynak: ornek-haber.com)\n"
        "## 2. Dolar ve faiz\nFed yetkilileri faiz indirimlerinde acele edilmeyeceğini söyledi; dolar haftayı "
        "yatay kapattı (15.10). (kaynak: ornek-ajans.com)\n"
        "## 3. Talep ve arz\nGüneş paneli üreticilerinden gelen talebin güçlü kaldığı bildirildi (14.10). "
        "(kaynak: ornek-haber.com)\n"
        "## 4. Türkiye\nDolar/TL hafta boyunca kademeli yükselişini sürdürdü (16.10). (kaynak: ornek-ajans.com)\n"
        "## 5. Daha uzun dönem\nGümüş son bir yılda belirgin yükseldi; arz açığının sürdüğü tahmin ediliyor. "
        "(kaynak: ornek-kurum.org)\n"
        "## 6. Önümüzdeki hafta\nABD enflasyon verisi ve TCMB faiz kararı takvimde. (kaynak: ornek-ajans.com)"),
    "kaynaklar": [{"url": "https://ornek-haber.com/a", "baslik": "Örnek haber", "alan": "ornek-haber.com"},
                  {"url": "https://ornek-ajans.com/b", "baslik": "Örnek ajans", "alan": "ornek-ajans.com"},
                  {"url": "https://ornek-ajans.com/c", "baslik": "Örnek ajans", "alan": "ornek-ajans.com"},
                  {"url": "https://ornek-kurum.org/d", "baslik": "Örnek kurum", "alan": "ornek-kurum.org"}],
    "arama": 5,
    "model": MODEL,
}

ORNEK_YORUM = {
    "kisa": {
        "ozet": "Cuma toparlanması, kur desteği",
        "durum": "Hafta başında gerileyen ons cuma günü toparlandı; gram fiyattaki artışa dolar/TL de katkı verdi.",
        "seyir": "Ons toparlanmayı sürdürürse gram fiyat desteklenebilir; enflasyon verisi faiz beklentilerini "
                 "sertleştirirse dalgalanma artabilir.",
        "izlenecek": "ABD enflasyon verisi, TCMB kararı, ons",
    },
    "orta": {
        "ozet": "Faiz beklentisi ve kur belirleyici",
        "durum": "Kendi kayıtlarımız kısa; dolar/TL üç ayda istikrarlı yükseldi, Fed temkinli bir dil kullanıyor.",
        "seyir": "Kurdaki eğilim korunursa onstaki düşüşler gram fiyata daha az yansıyabilir; faiz indirimleri "
                 "gecikirse ons baskı altında kalabilir.",
        "izlenecek": "Fed faiz beklentileri, dolar/TL, sanayi talebi",
    },
    "uzun": {
        "ozet": "Yapısal talep güçlü görünüyor",
        "durum": "Gümüş son bir yılda belirgin yükseldi; güneş paneli talebi ve arz açığı öne çıkıyor.",
        "seyir": "Sanayi talebi güçlü kalırsa ons desteklenebilir; küresel büyüme yavaşlarsa talep zayıflayabilir "
                 "ve fiyat geri çekilebilir.",
        "izlenecek": "Sanayi talebi, arz açığı, kur eğilimi",
    },
}


def ornek_veri(bugun):
    """Yerel önizleme için uydurma ama gerçekçi seri (12 Ekim'den beri kayıt + 1 yıllık ECB kuru)."""
    ecb, kur = {}, 41.6
    g = bugun - timedelta(days=380)
    while g <= bugun:
        if g.weekday() < 5:
            kur *= 1.00066
            ecb[g] = round(kur, 4)
        g += timedelta(days=1)
    kayitlar = {}
    ons = [64.8, 65.4, 65.1, 65.9, 66.3]
    gun = bugun - timedelta(days=bugun.weekday())        # bu haftanın pazartesi
    for i, o in enumerate(ons):
        d = gun + timedelta(days=i)
        dolar = max(x for x in ecb if x <= d)
        kayitlar[d] = {"saat": "20:00", "gumus": o, "altin": o * 66.4, "dolar": ecb[dolar],
                       "gram": o * ecb[dolar] / ONS_GRAM}
    return kayitlar, ecb


# ---------------------------------------------------------------- açıklama

UYARI = ("Burada yer alan yatırım bilgi, yorum ve tavsiyeleri yatırım danışmanlığı kapsamında değildir. "
         "Yatırım danışmanlığı hizmeti; aracı kurumlar, portföy yönetim şirketleri, mevduat kabul etmeyen "
         "bankalar ile müşteri arasında imzalanacak yatırım danışmanlığı sözleşmesi çerçevesinde sunulmaktadır. "
         "Buradaki yorumlar yapay zekâ ile üretilmiştir ve mali durumunuz ile risk ve getiri tercihlerinize "
         "uygun olmayabilir. Bu nedenle, sadece burada yer alan bilgilere dayanılarak yatırım kararı verilmesi "
         "beklentilerinize uygun sonuçlar doğurmayabilir.")


def _nasil_hazirlandi(gelismeler):
    if gelismeler:
        dayanak = ("Yorumlar aşağıdaki fiyat ve kur verileri ile yapay zekânın pazar sabahı web aramasıyla "
                   f"derlediği haftanın haberlerinden ({MODEL_ADI}) otomatik üretilir; haber özetleri ayrıca "
                   "doğrulanmaz ve yayından önce bir uzman tarafından incelenmez.")
    else:
        dayanak = (f"Yorumlar aşağıdaki fiyat ve kur verilerinden yapay zekâ ({MODEL_ADI}) ile otomatik üretilir; "
                   "yayından önce bir uzman tarafından incelenmez. Bu hafta haber taraması yapılamadığı için "
                   "yalnızca geçmiş fiyat ve kur hareketlerine dayanır.")
    return (f"Nasıl hazırlandı: {dayanak} Tahmin niteliğindedir; geçmiş hareketler gelecek için güvence "
            "değildir. Her pazar güncellenir. Bu yorum için hiçbir kurumdan ücret ya da menfaat alınmamıştır.")


def aciklama(v, yorum, kaynak_satirlari, gelismeler=None):
    vade_satirlari = [f"{x['ad']} ({x['ufuk']}): {yorum[x['anahtar']]['ozet']}" for x in v["vadeler"]]
    alanlar = kaynak_alanlari(gelismeler)

    def kur(soru=True, kaynak_sayisi=None):
        satirlar = kaynak_satirlari
        if alanlar:
            secili = alanlar[:kaynak_sayisi] if kaynak_sayisi else alanlar
            ek = f" ve {len(alanlar) - len(secili)} kaynak daha" if len(secili) < len(alanlar) else ""
            satirlar += f"\nHaber kaynakları (web araması): {', '.join(secili)}{ek}"
        parcalar = [
            f"Haftalık gümüş görünümü | Yapay zekâ yorumu · {v['tarih']}",
            f"Gram gümüş: {v['gram']} ₺ (haftalık {v['gram_deg']['isaret']} {v['gram_deg']['metin']}) · {v['veri_ani']}",
            "\n".join(vade_satirlari) + "\nAyrıntılar görsellerde, kaydırın →",
            "Sizce gümüş önümüzdeki haftalarda ne yöne gider? Yorumlara yazın 👇" if soru else None,
            _nasil_hazirlandi(gelismeler),
            "Uyarı: " + UYARI,
            f"Veriler: {v['veri_ani']} itibarıyla.\n{satirlar}",
            HASHTAG,
        ]
        return "\n\n".join(p for p in parcalar if p)

    # Instagram sınırı 2200 karakter: önce haber kaynakları kısaltılır, sonra soru satırı düşer.
    for soru, sayi in [(True, None), (True, 6), (True, 4), (False, 4), (False, 3)]:
        metin = kur(soru, sayi)
        if len(metin) <= 2200:
            return metin
    raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
