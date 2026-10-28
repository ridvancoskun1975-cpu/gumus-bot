"""Haftalık kartlar (büyüme planı, Faz 2): hafta içi iki gün ~12:00'de AYRI bir Reels.

19 Ekim 2026'DA TAKVİMDEN KALDIRILDI (Rıdvan: takipçiyi bıktırmamak için paylaşım sayısı azaltıldı; kartlar o gün
sabah ve akşam verilen fiyatın tekrarıydı; hiç yayımlanmadı). paylas.yml'de cron yok; yalnızca elle
(Run workflow → tür: kart). Geri açmak için cron '50 8 * * 3,5' ve "Türü belirle" eşlemesi yeter.

- Çarşamba ~12:00: "Kaç gram eder?" — 1.000 / 5.000 / 10.000 ₺ kaç gram gümüş; 100 gram ve 1 kilogram kaç ₺.
- Cuma ~12:00: "Altın–gümüş" — 1 gram altın kaç gram gümüş eder (altın/gümüş paritesi), gram altın ve gram
  gümüş TL değeri, önceki haftaların kapanış paritesiyle.

TAAHHÜT (Rıdvan, 15 Ekim 2026): "Hafta içi her gün 2 kere gümüş gram fiyatı verilecek." ~10:00 Reels ve ~20:00
özet her iş günü olduğu gibi gider; kartlar onların yerine geçmez, onlara eklenir (o gün 3 paylaşım, rehber ya
da aylık özete denk gelirse 4; günlük sınır 4). Kart günlük fiyat kaydı yazmaz.

Gösterilen her sayı o anki fiyattan ve botun günlük kayıtlarından hesaplanır; tahmin yok.
Elle ya da önizleme: Run workflow → tür: kart, konu: gram / parite (boşsa günün kartı).
Kontrol işi için: python3 bot/kart.py bugun → "gram", "parite" ya da boş.
"""
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import bilgi

# Python hafta günü (pazartesi 0) → kart
KART_GUNLERI = {2: "gram", 4: "parite"}
KART_BASLANGIC = date(2026, 10, 21)   # ilk kart (çarşamba); ilk hafta (13–16 Ekim) zaten kalabalık
KART_ADI = {"gram": "Kaç gram eder?", "parite": "Altın–gümüş"}
KART_ETIKET = {"gram": "KAÇ GRAM EDER?", "parite": "ALTIN – GÜMÜŞ"}   # görselin ve kapağın üst etiketi
TL_MIKTARLAR = [1000, 5000, 10000]
GRAM_MIKTARLAR = [(100, "100 gram"), (1000, "1 kilogram")]
HAFTA_SAYISI = 6          # altın–gümüş kartında gösterilecek en çok önceki hafta
HASHTAG = {
    "gram": "#gümüş #gramgümüş #külçegümüş #gümüşrehberi #gümüşfiyatları",
    "parite": "#gümüş #gramgümüş #değerlimetaller #gümüşrehberi #emtia",
}
AYLAR_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def bugunun_karti(gun):
    """Bugün hangi kart gidecek: "gram", "parite" ya da None."""
    if gun < KART_BASLANGIC:
        return None
    return KART_GUNLERI.get(gun.weekday())


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
    # Görselde yazan (2 ondalığa yuvarlanmış) gram fiyatıyla hesaplanır ki tablo kendi içinde tutarlı olsun:
    # 89,00 ₺ yazıyorsa 1 kilogram 89.000 ₺ (88.999 değil).
    gram = round(f["gram"], 2)
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


def aciklama(v, kaynaklar):
    """Kartın Instagram açıklaması. İlk satır aranan soruyla ve rakamla başlar (Instagram araması ilk satıra bakar)."""
    if v["kart"] == "gram":
        ilk_satir = (f"1.000 ₺ kaç gram gümüş eder? Bugün {v['tl_tablo'][0]['gram']} gram "
                     f"(gram gümüş {v['gram']} ₺, {v['gram_deg']['isaret']} {v['gram_deg']['metin']})")
        govde = (
            "".join(f"{s['tl']} ₺ ≈ {s['gram']} gram gümüş\n" for s in v["tl_tablo"])
            + "".join(f"{s['ad']} ≈ {s['tl']} ₺\n" for s in v["gram_tablo"])
            + "\nGram fiyatı ons gümüş ve dolar/TL'den hesaplanır; kuyumcu ve bankalarda işçilik, vergi ve "
            f"alış-satış farkı yüzünden fiyat farklıdır. Başka tutarlar için hesap makinesi: {bilgi.SITE} ({bilgi.LINK_BIO}).\n"
            "Gram gümüşteki değişim önceki iş gününe göredir.\n"
        )
    else:
        ilk_satir = (f"1 gram altın kaç gram gümüş eder? Bugün {tr_sayi_bir(v['parite_sayi'])} gram "
                     f"(gram altın {v['gram_altin']} ₺, gram gümüş {v['gram']} ₺)")
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
        "Kaydedin, lazım olunca bakarsınız.\n\n"
        "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
        f"{kaynaklar}\n\n"
        f"{HASHTAG[v['kart']]}"
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["bugun"]:
        print(bugunun_karti(datetime.now(ZoneInfo("Europe/Istanbul")).date()) or "")
    else:
        print("Kullanım: python3 bot/kart.py bugun", file=sys.stderr)
        sys.exit(2)
