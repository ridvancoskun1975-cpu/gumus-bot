"""Haftalık kartlar: hafta içi ~10:00 Reels'inin yerine haftada bir gün giden iki kart (büyüme planı, Faz 2).

- Çarşamba ~10:00: "Kaç gram eder?" — 1.000 / 5.000 / 10.000 ₺ kaç gram gümüş; 100 gram ve 1 kilogram kaç ₺.
- Cuma ~10:00: "Altın–gümüş" — 1 gram altın kaç gram gümüş eder (altın/gümüş paritesi), gram altın ve gram
  gümüş TL değeri, önceki haftaların kapanış paritesiyle.

Paylaşım sayısı artmaz: kart o günün ~10:00 Reels'inin yerine gider (aynı çalıştırma, aynı tür "reels", aynı
günlük fiyat kaydı). Kartta da o anki gram fiyatı ve değişimi yazar. Özel gün (eşik / en yüksek) ya da büyük
hareket günü (%2) olağan Reels gider; kart o hafta atlanır, böyle günlerde fiyatın kendisi haberdir.

Gösterilen her sayı o anki fiyattan ve botun günlük kayıtlarından hesaplanır; tahmin yok.
Önizleme ve elle deneme: KART=gram|parite|yok ortam değişkeni günü ezer (iş akışında Run workflow → tür: reels,
konu: gram ya da parite).
"""
import os
from datetime import date, timedelta

# Python hafta günü (pazartesi 0) → kart
KART_GUNLERI = {2: "gram", 4: "parite"}
KART_ADI = {"gram": "Kaç gram eder?", "parite": "Altın–gümüş"}
KART_ETIKET = {"gram": "KAÇ GRAM EDER?", "parite": "ALTIN – GÜMÜŞ"}   # görselin ve kapağın üst etiketi
TL_MIKTARLAR = [1000, 5000, 10000]
GRAM_MIKTARLAR = [(100, "100 gram"), (1000, "1 kilogram")]
HAFTA_SAYISI = 6          # altın–gümüş kartında gösterilecek en çok önceki hafta
HASHTAG = {
    "gram": "#gümüş #gramgümüş #külçegümüş #gümüşyatırımı #gümüşfiyatları",
    "parite": "#gümüş #gramgümüş #değerlimetaller #gümüşyatırımı #emtia",
}
AYLAR_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def kart_turu(gun, veri):
    """Bugün kart gidecek mi: "gram", "parite" ya da None. KART ortam değişkeni günü ezer."""
    zorla = os.environ.get("KART", "").strip().lower()
    if zorla in ("yok", "hayir", "0"):
        return None
    kart = zorla if zorla in KART_ADI else KART_GUNLERI.get(gun.weekday())
    if not kart:
        return None
    if veri.get("ozel") or veri.get("buyuk_hareket"):
        print(f"Kart atlandı ({KART_ADI[kart]}): bugün özel gün ya da büyük hareket var, olağan Reels gidiyor.")
        return None
    return kart


def haftalik_pariteler(gecmis_parite, bugun, en_cok=HAFTA_SAYISI):
    """Önceki haftaların son kaydındaki parite (normalde cuma ~20:00), eskiden yeniye: [(gün, parite)].
    Bu haftanın kayıtları alınmaz (karşılaştırma bugünkü değerle yapılır)."""
    bu_pazartesi = bugun - timedelta(days=bugun.weekday())
    son = {}
    for k, v in gecmis_parite.items():
        g = date.fromisoformat(k)
        if g >= bu_pazartesi:
            continue
        hafta = g - timedelta(days=g.weekday())
        if hafta not in son or g > son[hafta][0]:
            son[hafta] = (g, v)
    return [son[h] for h in sorted(son)][-en_cok:]


def _gun_kisa(g):
    return f"{g.day} {AYLAR_KISA[g.month - 1]}"


def gram_karti(f, tr_sayi):
    gram = f["gram"]
    return {
        "kart": "gram",
        "kart_etiket": KART_ETIKET["gram"],
        "tl_tablo": [{"tl": tr_sayi(t, 0), "gram": tr_sayi(t / gram, 2)} for t in TL_MIKTARLAR],
        "gram_tablo": [{"ad": ad, "tl": tr_sayi(g * gram, 0)} for g, ad in GRAM_MIKTARLAR],
    }


def parite_karti(f, tr_sayi, degisim, bugun):
    parite = f["parite"]
    haftalar = haftalik_pariteler(f.get("gecmis_parite", {}), bugun)
    satirlar = [{"ad": _gun_kisa(g), "deger": v} for g, v in haftalar]
    satirlar.append({"ad": "Bugün", "deger": parite, "bugun": True})
    en_cok = max(s["deger"] for s in satirlar)
    en_az = min(s["deger"] for s in satirlar)
    # Çubuklar en küçük değerin biraz altından başlar ki farklar görünsün (eksen etiketi gerekmez,
    # her çubuğun değeri yanında yazar).
    taban = en_az - max((en_cok - en_az) * 0.6, en_cok * 0.02)
    for s in satirlar:
        s["oran"] = round((s["deger"] - taban) / (en_cok - taban) * 100, 1)
        s["metin"] = tr_sayi(s["deger"], 1)
    gecen = haftalar[-1] if haftalar else None
    return {
        "kart": "parite",
        "kart_etiket": KART_ETIKET["parite"],
        "parite_sayi": round(parite, 1),
        "parite_gecen_sayi": round(gecen[1], 1) if gecen else round(parite, 1),
        "parite_hafta_deg": degisim(parite, gecen[1]) if gecen else None,
        "gecen_hafta": _gun_kisa(gecen[0]) if gecen else None,
        "gram_altin": tr_sayi(f["gram"] * parite, 0),
        "haftalar": satirlar,
        "hafta_yok": not haftalar,
    }


def kapak_verisi(v):
    """Reels kapağındaki büyük satır kartın kendi sayısıdır (ızgarada kart tanınsın)."""
    if v["kart"] == "gram":
        ilk = v["tl_tablo"][0]
        return {"kapak_ust": f"{ilk['tl']} ₺ İLE", "kapak_sayi": ilk["gram"], "kapak_birim": "gram",
                "kapak_not": f"Gram gümüş {v['gram']} ₺"}
    return {"kapak_ust": "1 GRAM ALTIN ≈", "kapak_sayi": tr_sayi_bir(v["parite_sayi"]), "kapak_birim": "gram",
            "kapak_not": "gümüş eder"}


def tr_sayi_bir(x):
    return f"{x:,.1f}".replace(",", "§").replace(".", ",").replace("§", ".")


def aciklama(v, ilk_satir, kaynaklar):
    """Kartın Instagram açıklaması. İlk satır öteki fiyat paylaşımlarıyla aynı ("Gram gümüş fiyatı bugün: …")."""
    if v["kart"] == "gram":
        govde = (
            "".join(f"{s['tl']} ₺ ≈ {s['gram']} gram gümüş\n" for s in v["tl_tablo"])
            + "".join(f"{s['ad']} ≈ {s['tl']} ₺\n" for s in v["gram_tablo"])
            + "\nGram fiyatı ons gümüş ve dolar/TL'den hesaplanır; kuyumcu ve bankalarda işçilik, vergi ve "
            "alış-satış farkı yüzünden fiyat farklıdır. Başka tutarlar için hesap makinesi biyografideki bağlantıda.\n"
        )
    else:
        d = v["parite_hafta_deg"]
        haftalar = [s for s in v["haftalar"] if not s.get("bugun")]
        govde = (
            f"1 gram altın ≈ {tr_sayi_bir(v['parite_sayi'])} gram gümüş (altın/gümüş paritesi"
            + (f", {v['gecen_hafta']} kapanışına göre {d['isaret']} {d['metin']}" if d else "") + ")\n"
            f"Gram altın ≈ {v['gram_altin']} ₺ · gram gümüş {v['gram']} ₺\n"
            + ("Önceki haftaların kapanışı: " + " · ".join(f"{s['ad']} {s['metin']}" for s in haftalar) + "\n"
               if haftalar else "")
            + "\nParite yükseldikçe 1 gram altın daha çok gümüşe denk gelir, düştükçe daha aza. "
            "Gram altın ons altın ve dolar/TL'den hesaplanır (saf altın); kuyumcu fiyatlarından farklıdır. "
            "Haftanın kapanışı, o haftanın botta kayıtlı son değeridir (genelde cuma ~20:00).\n"
        )
    return (
        f"{ilk_satir}\n"
        f"{KART_ADI[v['kart']]} · {v['tarih']} · {v['saat']}\n\n"
        f"{govde}"
        f"Gram gümüşteki değişim önceki iş gününe göredir.{' ' + v['baslik_notu'] if v.get('baslik_notu') else ''}\n"
        "Kaydedin, lazım olunca bakarsınız.\n\n"
        "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
        f"{kaynaklar}\n\n"
        f"{HASHTAG[v['kart']]}"
    )
