"""Pazar yapay zekâ yorumu: gram gümüş için kısa, orta ve uzun vadeli görünüm (kaydırmalı, 4 görsel).

Yasal çerçeve — SPK III-37.1 Tebliğ'in medya ve elektronik ortamdaki yorumlara uygulanan
78-80. maddeleri esas alınarak:
  - Yönlendirici değildir: al/sat/tut, hedef fiyat, seviye yok; kişiye ya da gruba özel değildir.
  - Tahminler koşullu yazılır, iki yön de anılır; varsayımları açıklamada yazılıdır.
  - Kullanılan verilerin tarihi, kaynakları ve güncelleme sıklığı belirtilir.
  - Yapay zekâyla üretildiği görselde ve açıklamada açıkça yazılır.
  - Açıklamada "yatırım danışmanlığı kapsamında değildir" standart uyarısı yer alır.
Model yalnızca verilen fiyat ve kur verilerini görür, internete çıkmaz; rakamları görsel kod
tarafından yazılır, model metninde rakam bulunmasına izin verilmez (uydurma seviye/hedef çıkmasın).

Yapay zekâ: Anthropic Claude API (ANTHROPIC_API_KEY). Haftada 1 çağrı, birkaç kuruş.
"""
import json
import os
import re
import sys
import time
from datetime import date, timedelta

import requests

ONS_GRAM = 31.1034768
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("YZ_MODEL", "").strip() or "claude-sonnet-5-5"
MODEL_ADI = "Claude, Anthropic"

HASHTAG = "#gümüş #gümüşyatırımı #gümüşfiyatları #değerlimetaller #emtia"

# pencere: gün; esnek: kayıt kısaysa eldeki en uzun süreyle (en az 4 gün) hesaplanır
VADELER = [
    {"anahtar": "kisa", "ad": "Kısa vade", "ufuk": "1–4 hafta", "pencere": 28, "etiket": "Son 4 hafta", "esnek": True},
    {"anahtar": "orta", "ad": "Orta vade", "ufuk": "1–6 ay", "pencere": 91, "etiket": "Son 3 ay", "esnek": False},
    {"anahtar": "uzun", "ad": "Uzun vade", "ufuk": "1 yıl ve üzeri", "pencere": 365, "etiket": "Son 1 yıl", "esnek": False},
]

# Kelime sınırları (görselde büyük yazı sığsın diye). Model açıklamada bunları görür; kod biraz pay bırakır.
SINIR = {"ozet": 5, "durum": 18, "seyir": 26, "izlenecek": 8}
PAY = {"ozet": 1, "durum": 4, "seyir": 5, "izlenecek": 3}

# Yönlendirici, kesinlik bildiren, abartılı ya da modelin bilemeyeceği güncel olaylara değinen ifadeler.
YASAK = [
    (r"\b(al|alın|alınız|almalı|almak|sat|satın|satınız|satmalı|satmak|tut|tutun|tutmalı|tutmak)\b", "al/sat/tut"),
    (r"\b(ekleyin|azaltın|biriktirin|değerlendirin|bekleyin|kaçırmayın|girin|çıkın)\b", "okura emir"),
    (r"fırsat", "fırsat"), (r"hedef", "hedef"), (r"direnç", "direnç"), (r"destek seviye", "destek seviyesi"),
    (r"\bstop", "stop"), (r"kesin", "kesinlik"), (r"garanti", "garanti"), (r"mutlaka", "kesinlik"),
    (r"kaçırma", "kaçırma"), (r"tavsiye", "tavsiye"), (r"öneri|öner", "öneri"), (r"portföy", "portföy"),
    (r"pozisyon", "pozisyon"), (r"kazandır|kazanç", "kazanç vaadi"), (r"yatırım yap", "yatırım çağrısı"),
    (r"patla|uçuş|roket|çakıl|çöküş|çöker", "abartı"),
    (r"\bfed|merkez bankası|tcmb|ecb|seçim|savaş|gümrük vergisi", "güncel olay"),
    (r"\d", "rakam"), (r"%", "yüzde işareti"),
]

SISTEM = """Sen bir Instagram hesabı için her pazar gram gümüşün kısa, orta ve uzun vadeli görünümünü yazan bir yapay zekâsın. Yazdıkların görselde büyük puntoyla gösterilecek ve "yapay zekâ yorumudur, yatırım tavsiyesi değildir" uyarısıyla yayımlanacak.

Kurallar (hepsine uy):
1. Yalnızca kullanıcının verdiği verilere dayan. Verilerde olmayan güncel olaylardan, haberlerden, kurum ya da kişi adlarından, faiz kararlarından, seçim, savaş gibi gelişmelerden söz etme. Bunları bilmiyorsun.
2. Dolar, faiz beklentileri, sanayi talebi, küresel büyüme, dolar/TL gibi genel bilinen etkenleri yalnızca "izlenecek etken" ya da koşul olarak anabilirsin; şu an ne durumda olduklarını iddia etme.
3. Yönlendirme yapma: al, sat, tut, ekle, azalt, bekle, fırsat, hedef fiyat, destek/direnç seviyesi, stop, portföy, pozisyon gibi ifadeler kullanma. Okura ne yapması gerektiğini söyleme, emir kipi kullanma, okura hitap etme.
4. Kesinlik bildirme: "kesin, garanti, mutlaka, kesinlikle" yok. Olası seyri koşullu yaz ("... sürerse", "... durumunda") ve her zaman iki yönü de an.
5. Hiç rakam, yüzde, tarih yazma. Sayılar görselde ayrıca gösteriliyor. "Üç ay", "bir yıl" gibi süreleri yazıyla yazabilirsin.
6. Abartılı, heyecanlı dil yok (patlama, uçuş, çöküş, roket gibi). Sakin, sade, günlük Türkçe; Türkçe karakterleri doğru kullan.
7. Bir vade için veri yetersizse (veri_yeterli: false) "durum" alanında bunu açıkça söyle; o vadeyi genel etkenler üzerinden ve daha temkinli yaz.
8. Gram gümüşün TL fiyatı ons gümüş (dolar) ile dolar/TL'nin çarpımından gelir; hareketin onstan mı kurdan mı geldiğini ayırt etmeye çalış.

Her vade için alanlar:
- ozet: kapakta görünen çok kısa başlık, en fazla 5 kelime.
- durum: verilerde ne görülüyor, en fazla 18 kelime, tek cümle.
- seyir: koşullu olası seyir, iki yönü de anarak, en fazla 26 kelime.
- izlenecek: izlenecek etkenler, en fazla 8 kelime, cümle değil."""


def _vade_sema():
    alan = lambda a: {"type": "string", "description": f"en fazla {SINIR[a]} kelime"}
    return {"type": "object", "additionalProperties": False,
            "properties": {k: alan(k) for k in SINIR}, "required": list(SINIR)}


SEMA = {"type": "object", "additionalProperties": False,
        "properties": {v["anahtar"]: _vade_sema() for v in VADELER},
        "required": [v["anahtar"] for v in VADELER]}


# ---------------------------------------------------------------- seriler ve istatistik

def seri_kur(kayitlar, ecb, metal_gecmis=None):
    """Günlük seri: tarih -> {gumus, altin, dolar, gram}.

    kayitlar: botun günlük kayıtları (veri/gecmis.json), ecb: tarih -> USD/TRY,
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
        if gun is None and v["esnek"] and (son_gun - ilk_gun).days >= 4:
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


def model_girdisi(seri, ecb, ist, bugun, kaynak_notu):
    son_gun = max(seri)
    son = seri[son_gun]
    yuv = lambda x, n=2: None if x is None else round(x, n)

    haftalik = {}
    for g, x in seri.items():
        haftalik[g.isocalendar()[:2]] = (g, x)            # her haftanın son kaydı
    haftalik = [{"hafta_son_gunu": g.isoformat(), "gram_tl": yuv(x["gram"]), "ons_usd": yuv(x["gumus"]),
                 "dolar_tl": yuv(x["dolar"], 3)} for g, x in list(haftalik.values())[-13:]]
    aylik_dolar = {}
    for g in sorted(ecb):
        aylik_dolar[g.strftime("%Y-%m")] = ecb[g]
    gunluk = list(seri.values())[-21:]
    oynaklik = [abs(b["gram"] / a["gram"] - 1) * 100 for a, b in zip(gunluk, gunluk[1:])]
    return {
        "bugun": bugun.isoformat(),
        "son_veri": {"tarih": son_gun.isoformat(), "saat": son.get("saat"), "gram_tl": yuv(son["gram"]),
                     "ons_usd": yuv(son["gumus"]), "dolar_tl": yuv(son["dolar"], 3),
                     "altin_gumus_paritesi": yuv(son["altin"] / son["gumus"], 1) if son.get("altin") else None},
        "metal_verisi": kaynak_notu,
        "metal_kayit_baslangici": min(seri).isoformat(),
        "vadeler": {k: {"pencere": x["etiket"], "veri_yeterli": x["veri_yeterli"],
                        "gram_degisim_yuzde": yuv(x["gram"]), "ons_degisim_yuzde": yuv(x["ons"]),
                        "parite_degisim_yuzde": yuv(x["parite"]), "dolar_tl_degisim_yuzde": yuv(x["dolar"]),
                        "gram_en_yuksek": yuv(x["gram_en_yuksek"]), "gram_en_dusuk": yuv(x["gram_en_dusuk"])}
                    for k, x in ist.items()},
        "haftalik_kapanislar": haftalik,
        "aylik_dolar_tl": [{"ay": a, "dolar_tl": yuv(d, 3)} for a, d in list(aylik_dolar.items())[-13:]],
        "gram_ortalama_gunluk_hareket_yuzde": yuv(sum(oynaklik) / len(oynaklik)) if oynaklik else None,
    }


# ---------------------------------------------------------------- denetim

def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def denetle(yorum):
    """Kurallara uymayan alanların listesi (boşsa yorum yayımlanabilir)."""
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
    return hatalar


# ---------------------------------------------------------------- yapay zekâ çağrısı

def _cagir(anahtar, mesajlar):
    govde = {
        "model": MODEL,
        "max_tokens": 1500,
        "system": SISTEM,
        "messages": mesajlar,
        "output_config": {"format": {"type": "json_schema", "schema": SEMA}},
    }
    son_hata = None
    for deneme in range(4):
        try:
            r = requests.post(API_URL, json=govde, timeout=120, headers={
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
        cevap = r.json()
        if cevap.get("stop_reason") not in ("end_turn", "stop_sequence"):
            raise RuntimeError(f"Claude yanıtı tamamlanmadı (stop_reason: {cevap.get('stop_reason')})")
        metin = "".join(b.get("text", "") for b in cevap.get("content", []) if b.get("type") == "text")
        return metin, cevap
    raise RuntimeError(f"Claude API'ye ulaşılamadı: {son_hata}")


def yz_yorum(girdi):
    """Claude'dan yorum alır; kurallara uymazsa hataları göstererek en fazla 2 kez yeniden ister."""
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        return None
    mesajlar = [{"role": "user", "content":
                 "Bu haftanın gram gümüş verileri aşağıda (JSON). Kısa, orta ve uzun vade için yorumu yaz.\n\n"
                 + json.dumps(girdi, ensure_ascii=False, indent=1)}]
    for tur in range(3):
        metin, cevap = _cagir(anahtar, mesajlar)
        try:
            yorum = json.loads(metin)
        except ValueError:
            hatalar = ["yanıt geçerli JSON değil"]
        else:
            hatalar = denetle(yorum)
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

ORNEK_YORUM = {
    "kisa": {
        "ozet": "Kur destekli, ons dalgalı",
        "durum": "Son günlerde gram gümüşteki artışın bir kısmı dolar/TL'den geldi; ons dar bir aralıkta dalgalandı.",
        "seyir": "Kur artışı aynı hızda sürerse gram fiyat desteklenebilir; onsta satış baskısı artarsa bu destek "
                 "zayıflayabilir ve oynaklık yükselebilir.",
        "izlenecek": "Haftalık ons hareketi ve kurun hızı",
    },
    "orta": {
        "ozet": "Belirleyici olan kur",
        "durum": "Üç aylık dönemde dolar/TL istikrarlı yükseldi; ons için bu süreyi kapsayan kayıt henüz yok.",
        "seyir": "Kurdaki eğilim korunursa onstaki düşüşler gram fiyata daha az yansıyabilir; kur yatay kalırsa "
                 "yön büyük ölçüde onsa bağlı olur.",
        "izlenecek": "Dolar endeksi, faiz beklentileri, sanayi talebi",
    },
    "uzun": {
        "ozet": "Veri birikiyor, temkinli bakış",
        "durum": "Bir yılda dolar/TL belirgin yükseldi; ons için bir yıllık kayıt olmadığından değerlendirme sınırlı.",
        "seyir": "Uzun vadede gram fiyatı ons ile kurun ortak seyri belirler; sanayi talebi güçlü kalırsa ons "
                 "desteklenebilir, küresel talep zayıflarsa baskı artabilir.",
        "izlenecek": "Sanayi talebi, küresel büyüme, kur eğilimi",
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


def aciklama(v, yorum, kaynak_satirlari):
    vade_satirlari = [f"{x['ad']} ({x['ufuk']}): {yorum[x['anahtar']]['ozet']}" for x in v["vadeler"]]
    parcalar = [
        f"Haftalık gümüş görünümü | Yapay zekâ yorumu · {v['tarih']}",
        f"Gram gümüş: {v['gram']} ₺ (haftalık {v['gram_deg']['isaret']} {v['gram_deg']['metin']}) · {v['veri_ani']}",
        "\n".join(vade_satirlari) + "\nAyrıntılar görsellerde, kaydırın →",
        "Sizce gümüş önümüzdeki haftalarda ne yöne gider? Yorumlara yazın 👇",
        "Nasıl hazırlandı: Yorumlar aşağıdaki fiyat ve kur verilerinden yapay zekâ "
        f"({MODEL_ADI}) ile otomatik üretilir; yayından önce bir uzman tarafından incelenmez. Tahmin "
        "niteliğindedir ve yalnızca geçmiş fiyat ve kur hareketlerine dayanır; haberler, faiz kararları ve "
        "diğer gelişmeler değerlendirmeye alınmaz. Geçmiş hareketler gelecek için güvence değildir. "
        "Her pazar güncellenir. Bu yorum için hiçbir kurumdan ücret ya da menfaat alınmamıştır.",
        "Uyarı: " + UYARI,
        f"Veriler: {v['veri_ani']} itibarıyla.\n{kaynak_satirlari}",
        HASHTAG,
    ]
    metin = "\n\n".join(parcalar)
    if len(metin) > 2200:   # Instagram sınırı: önce soru satırı düşer
        parcalar.pop(3)
        metin = "\n\n".join(parcalar)
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
    return metin
