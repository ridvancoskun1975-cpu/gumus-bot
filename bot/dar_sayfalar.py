"""Dar aramalar için sayfalar: "100 gram gümüş kaç TL", "1000 TL kaç gram gümüş", "1 ons gümüş kaç TL",
"gram gümüş kaç euro", "altın gümüş oranı", "gümüş fiyatları geçmiş" gibi.

Rıdvan (15 Ekim 2026): "dar aramaların hiç birini kaçırmayalım. bu mantık ile gelen aramalar konusunu
ciddi ele al ve genişlet." 925/800 ayar sayfaları Rıdvan'ın isteğiyle yok (15 Ekim 07:25: takı
aramalarına yönelmesin; hurda/milyem hesabı kaldı). Arama ailesi listesi Google otomatik tamamlamasından çıkarıldı (proje belgesi
arastirma/dar-aramalar-15-ekim.md). Her aile için tek ve dolu bir sayfa yapılır (çok sayıda ince sayfa
değil: Google aynı kalıpta toplu üretilmiş zayıf sayfaları cezalandırıyor). Her sayfa:
  - sorunun cevabını ilk satırda, rakamla verir (görselde ve açıklamada kullanılan aynı kayıttan),
  - komşu miktarlar, ayar, dolar ve son günlerin tablosuyla kendi verisini taşır,
  - kuyumcu/banka farkını ve "anlık değildir" notunu açıkça yazar,
  - birbirine, hesap makinesine ve rehbere bağlanır.

Sayfalar bot/sayfa.py → uret() içinden her paylaşımda yeniden üretilir; rakam ve tarihler kendiliğinden
güncellenir. Yeni bir miktar ya da sayfa eklemek için aşağıdaki listelere satır eklemek yeter; site
haritası (sitemap.xml) ve "Hesaplar" sayfası listeyi kendiliğinden alır.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as bot  # noqa: E402
import bilgi  # noqa: E402
import arsiv as arsiv_mod  # noqa: E402

SON_GUN = 10          # sayfalardaki "son günler" tablosu
PARITE_HAFTA = 8      # altın–gümüş oranı sayfasındaki haftalık kapanışlar
GECMIS_SATIR = 60     # geçmiş sayfasındaki gün sayısı (daha eskisi aylık sayfalarda)

# Ağırlık → TL ("100 gram gümüş kaç TL"). (gram, görünen ad, adres parçası)
AGIRLIKLAR = [
    (1, "1 gram", "1-gram"),
    (10, "10 gram", "10-gram"),
    (50, "50 gram", "50-gram"),
    (100, "100 gram", "100-gram"),
    (250, "250 gram", "250-gram"),
    (500, "500 gram", "500-gram"),
    (1000, "1 kg", "1-kg"),
]
# TL → gram ("1000 TL kaç gram gümüş"): kendi sayfası olan tutarlar ve her sayfadaki tablo
TL_SAYFALAR = [1000, 10000, 100000]
TL_TABLO = [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
# Ayarlar (milyem). Yalnızca kaynaklı olanlar: 999, 958, 925, 830, 800 (Uluslararası damga sözleşmesi;
# bot/bilgi.py #3 ve bot/ayrintili.py). 800 sözleşmenin tanıdığı en düşük ayar.
AYARLAR = [
    (999, "999", "külçe"),
    (958, "958", "Britannia"),
    (925, "925", "sterling, takının yaygın ayarı"),
    (830, "830", ""),
    (800, "800", "damga sözleşmesindeki en düşük ayar"),
]
KISA_AD = {999: "külçe", 958: "Britannia", 925: "sterling", 800: "en düşük"}   # dar tablolarda kısa açıklama
ONS_MIKTARLAR = [1, 5, 10, 32.1507, 100]   # 32,15 ons = 1 kg

HARFLER = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def adres_parcasi(metin):
    """Türkçe başlıktan adres parçası: "Altın/gümüş paritesi ne anlatır?" → "altin-gumus-paritesi-ne-anlatir"."""
    s = metin.translate(HARFLER).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def para(x):
    """TL ya da $ tutarı: 1.000 ve üstünde kuruşsuz, altında 2 ondalık."""
    return bot.tr_sayi(x, 0) if abs(x) >= 1000 else bot.tr_sayi(x, 2)


def gram_yaz(g):
    """Gram miktarı: 1.000 g ve üstünde kilogram da yazılır."""
    if g >= 1000:
        return f"{bot.tr_sayi(g, 0)} g ({bot.tr_sayi(g / 1000, 2)} kg)"
    return f"{bot.tr_sayi(g, 1 if g >= 100 else 2)} g"


def gram_kisa(g):
    """Tablolarda kısa yazım: 1.000 g ve üstü kilogramla."""
    return f"{bot.tr_sayi(g / 1000, 2)} kg" if g >= 1000 else f"{bot.tr_sayi(g, 1 if g >= 100 else 2)} g"


def tl_yaz(tl):
    return f"{bot.tr_sayi(tl, 0)} ₺"


def _kisa(gun):
    return f"{gun.day} {bot.AYLAR[gun.month - 1]}"


def _tarih(gun):
    return f"{gun.day} {bot.AYLAR[gun.month - 1]} {gun.year}"


def _seyir(kayitlar, deger, bicim):
    """Son günler: [(gün, değer metni, değişim)] — en yeni üstte."""
    satirlar = []
    secilen = kayitlar[-(SON_GUN + 1):]
    for i in range(len(secilen) - 1, 0 if len(secilen) > 1 else -1, -1):
        g, k = secilen[i]
        d = bot.degisim(deger(k), deger(secilen[i - 1][1])) if i > 0 else None
        satirlar.append({"tarih": f"{g.day:02d}.{g.month:02d}", "gun": bot.GUN_KISA[g.weekday()],
                         "deger": bicim(deger(k)), "deg": d})
    if len(secilen) == 1:
        g, k = secilen[0]
        satirlar = [{"tarih": f"{g.day:02d}.{g.month:02d}", "gun": bot.GUN_KISA[g.weekday()],
                     "deger": bicim(deger(k)), "deg": None}]
    return satirlar


def _cizgi(noktalar, gen=400, yuk=170):
    """[(gün, gram)] → çizgi grafiği verisi (bot/sayfa.py → _grafik ile aynı alanlar; şablon makrosu cizgi_grafik).
    En az 3 nokta; yoksa None."""
    if len(noktalar) < 3:
        return None
    ust, alt, yan = 24, 30, 6
    degerler = [d for _, d in noktalar]
    en_az, en_cok = min(degerler), max(degerler)
    aralik = (en_cok - en_az) or 1
    adim = (gen - 2 * yan) / (len(noktalar) - 1)

    def y(d):
        return round(ust + (en_cok - d) / aralik * (yuk - ust - alt), 1)

    xy = [(round(yan + i * adim, 1), y(d)) for i, (_, d) in enumerate(noktalar)]
    cizgi = " ".join(f"{a},{b}" for a, b in xy)
    i_cok, i_az = degerler.index(en_cok), degerler.index(en_az)
    return {
        "gen": gen, "yuk": yuk, "cizgi": cizgi, "alan": f"{xy[0][0]},{yuk - alt} {cizgi} {xy[-1][0]},{yuk - alt}",
        "taban": yuk - alt, "son": xy[-1],
        "en_cok": {"x": xy[i_cok][0], "y": xy[i_cok][1], "deger": bot.tr_sayi(en_cok)},
        "en_az": {"x": xy[i_az][0], "y": xy[i_az][1], "deger": bot.tr_sayi(en_az)},
        "ilk_gun": _kisa(noktalar[0][0]), "son_gun": _kisa(noktalar[-1][0]), "gun_sayisi": len(noktalar),
        "yon": "artis" if degerler[-1] >= degerler[0] else "dusus",
        "aciklama": (f"{_kisa(noktalar[0][0])} – {_kisa(noktalar[-1][0])} gram gümüş: en yüksek {bot.tr_sayi(en_cok)} ₺, "
                     f"en düşük {bot.tr_sayi(en_az)} ₺, son {bot.tr_sayi(degerler[-1])} ₺"),
    }


def _cubuk(degerler, bicim, gen=400, yuk=170):
    """[(yıl, değer)] → çubuk grafiği: her yıl bir çubuk, ilk/son ve en yüksek çubuğun değeri yazılır."""
    if len(degerler) < 2:
        return None
    ust, alt, yan = 22, 26, 2
    en_cok = max(d for _, d in degerler) or 1
    adim = (gen - 2 * yan) / len(degerler)
    gen_c = max(adim * 0.68, 2)
    cubuklar = []
    i_cok = max(range(len(degerler)), key=lambda i: degerler[i][1])
    son_i = len(degerler) - 1
    yillar = [y for y, _ in degerler]
    for i, (yil, d) in enumerate(degerler):
        h = max((d / en_cok) * (yuk - ust - alt), 1.5)
        x = yan + i * adim + (adim - gen_c) / 2
        # Eksende ilk ve son yıl, arada 5'in katları; ilk/son yıla 2 yıldan yakın olan katlar yazılmaz (üst üste binmesin)
        etiket = i in (0, son_i) or (yil % 5 == 0 and yil - yillar[0] > 2 and yillar[-1] - yil > 2)
        cubuklar.append({"x": round(x, 1), "y": round(yuk - alt - h, 1), "g": round(gen_c, 1), "h": round(h, 1),
                         "orta": round(x + gen_c / 2, 1), "yil": yil, "etiket": etiket, "deger": None})
    # Değer yazıları: ilk, en yüksek ve son çubuk; yazı komşu çubukların da üstünde durur
    for i in sorted({0, i_cok, son_i}):
        komsu = [cubuklar[j]["y"] for j in range(max(0, i - 2), min(son_i, i + 2) + 1)]
        cubuklar[i]["deger"] = bicim(degerler[i][1])
        cubuklar[i]["yazi_y"] = round(max(min(komsu) - 6, 14), 1)
    return {"gen": gen, "yuk": yuk, "taban": yuk - alt, "cubuklar": cubuklar,
            "aciklama": "; ".join(f"{c['yil']}: {bicim(d)}" for c, (_, d) in zip(cubuklar, degerler))}


# Sitenin güncelleme saatleri (sayfa.veri_hazirla → site_guncelleme; ör. "Hafta içi ~10:00, ~12:35, ~16:35 ve
# ~20:00"). sayfalar() her üretimde doldurur; saatler elle yazılmaz (Rıdvan, 14 Ekim 2026). Yasal inceleme 17
# (25 Ekim 2026): eski "günde iki kez" metni site 20 Ekim'den beri günde 4 kez güncellendiği için yanlıştı.
_SITE_SAATLERI = [None]


def _guncelleme_notu(ne="fiyat"):
    s = _SITE_SAATLERI[0]
    if s:
        return f"Anlık (canlı) {ne} değildir; güncelleme saatleri: {s[0].lower() + s[1:]} (Türkiye saati)."
    return f"Anlık (canlı) {ne} değildir; hafta içi günde birkaç kez güncellenir."


def _ortak_notlar(ek=None):
    n = list(ek or [])
    n.append("Değer, uluslararası ons fiyatı ve ECB dolar kuruyla hesaplanan ham gümüş değeridir. Kuyumcu, "
             "banka ve satıcı fiyatları işçilik, alış-satış farkı (makas) ve vergiler yüzünden farklıdır; "
             "satış fiyatı genelde daha yüksek, alış (bozdurma) fiyatı daha düşüktür.")
    n.append(_guncelleme_notu())
    return n


def sayfalar(v, gecmis, euro=None, arsiv=None):
    """Bütün dar arama sayfalarının verisi: [{yol, sablon, ...}]. v = sayfa.veri_hazirla() çıktısı;
    euro = {ECB tarihi: EUR/TRY} (euro_kurlari(); yoksa euro sayfası üretilmez); arsiv = bot/arsiv.py → oku()
    (yalnız geçmiş sayfaları kullanır)."""
    _SITE_SAATLERI[0] = v.get("site_guncelleme")
    kayitlar = sorted((date.fromisoformat(g), k) for g, k in gecmis.items())
    gun, son = kayitlar[-1]
    gram, dolar, ons = son["gram"], son["dolar"], son["gumus"]
    gram_usd = ons / bot.ONS_GRAM
    parite = son["altin"] / son["gumus"]
    once = kayitlar[-2][1] if len(kayitlar) > 1 else None
    tarih_kisa, tarih = _kisa(gun), _tarih(gun)
    ortak = {"son_gun": tarih, "son_kisa": tarih_kisa, "gram_birim": bot.tr_sayi(gram)}
    liste = []

    def ekle(**s):
        s.setdefault("sablon", "hesap.html")
        liste.append({**ortak, **s})

    agirlik_yol = {g: f"hesap/{p}-gumus-kac-tl/" for g, _, p in AGIRLIKLAR}
    tl_yol = {t: f"hesap/{t}-tl-kac-gram-gumus/" for t in TL_SAYFALAR}
    yollar = {
        "merkez": "hesap/", "milyem": "hesap/hurda-gumus-milyem-hesabi/", "ons": "hesap/1-ons-gumus-kac-tl/",
        "dolar": "hesap/gram-gumus-kac-dolar/", "euro": "hesap/gram-gumus-kac-euro/",
        "parite": "hesap/altin-gumus-orani/", "gecmis": "gecmis/",
    }
    # Euro: ECB EUR/TRY, kaydın kendi ECB tarihindeki kur (dolar kuruyla aynı gün; tutarlı çapraz)
    euro = euro or {}

    def eur_kur(k):
        return euro.get(k.get("kur_tarihi"))

    eur_son = eur_kur(son)
    if euro and not eur_son:
        print(f"::warning::Euro sayfası: {son.get('kur_tarihi')} tarihli ECB EUR/TRY kuru yok; euro atlandı.")
    rehber_yol = {b["no"]: f"rehber/{b['no']}-{adres_parcasi(b['baslik'])}/" for b in v["rehber"]}

    def rehber_bag(no, metin):
        return [(metin, rehber_yol[no])] if no in rehber_yol else []

    # ---- Ağırlık → TL
    for g, ad, _ in AGIRLIKLAR:
        deger = g * gram
        ad_uzun = "1 kg (1 kilo)" if g == 1000 else ad
        komsu = [{"hucreler": [ad2, para(g2 * gram) + " ₺"], "bag": agirlik_yol[g2] if g2 != g else None,
                  "vurgu": g2 == g} for g2, ad2, _ in AGIRLIKLAR]
        ilgili = [(f"{ad2} gümüş kaç TL", agirlik_yol[g2]) for g2, ad2, _ in AGIRLIKLAR if g2 != g][:4]
        ilgili += [("1.000 TL kaç gram gümüş", tl_yol[1000])]
        ilgili += [("Gram gümüş kaç euro", yollar["euro"])] if eur_son else []
        ilgili += [("Gümüş hesap makinesi", yollar["merkez"])]
        ilgili += rehber_bag(6, "Kuyumcudaki fiyat neden farklı?")
        eur_metin = f" / {para(deger / eur_son)} €" if eur_son else ""
        ekle(
            yol=agirlik_yol[g], kisa=f"{ad} gümüş kaç TL", grup="Ağırlık → TL",
            title=f"{ad_uzun.replace('kilo', 'Kilo').title() if g == 1000 else ad.title()} Gümüş Kaç TL? "
                  f"{para(deger)} ₺ · {tarih_kisa}",
            desc=f"{ad_uzun} gümüş {para(deger)} ₺ ({tarih}). {ad} saf gümüşün TL, dolar"
                 f"{' ve euro' if eur_son else ''} karşılığı, başka ağırlıklar ve son günler. Bilgi amaçlıdır, "
                 f"yatırım tavsiyesi değildir.",
            h1=f"{ad_uzun} gümüş kaç TL?",
            cevap=para(deger), birim="₺",
            deg=bot.degisim(deger, g * once["gram"]) if once else None,
            ozet=f"{ad_uzun} saf gümüşün değeri {tarih} itibarıyla {para(deger)} ₺ "
                 f"(yaklaşık {para(g * gram_usd)} ${eur_metin}). Hesap: {bot.tr_sayi(g, 0)} g × {bot.tr_sayi(gram)} ₺. "
                 f"999 külçede gümüşün binde 999'u saftır; aradaki fark binde birdir.",
            formul=f"{bot.tr_sayi(g, 0)} g × {bot.tr_sayi(gram)} ₺ (1 gram) = {para(deger)} ₺",
            tablolar=[
                {"baslik": "Başka ağırlıklar", "sutunlar": ["Gümüş", "Değer"], "satirlar": komsu, "sayisal": [1]},
            ],
            seyir=_seyir(kayitlar, lambda k, g=g: g * k["gram"], lambda x: para(x) + " ₺"),
            seyir_baslik=f"Son günlerde {ad} gümüş (₺)",
            notlar=_ortak_notlar(["Külçe gümüş teslimi KDV'den istisnadır (KDV Kanunu md. 17/4-g; ayrıntı "
                                  "rehberde)."]),
            ilgili=ilgili,
        )

    # ---- TL → gram
    for t in TL_SAYFALAR:
        g = t / gram
        tablo = [{"hucreler": [tl_yaz(t2), gram_kisa(t2 / gram)],
                  "bag": tl_yol.get(t2) if t2 != t else None, "vurgu": t2 == t} for t2 in TL_TABLO]
        ad = f"{bot.tr_sayi(t, 0)} TL"
        ilgili = [(f"{bot.tr_sayi(t2, 0)} TL kaç gram gümüş", tl_yol[t2]) for t2 in TL_SAYFALAR if t2 != t]
        ilgili += [("100 gram gümüş kaç TL", agirlik_yol[100]), ("1 kg gümüş kaç TL", agirlik_yol[1000]),
                   ("Gümüş hesap makinesi", yollar["merkez"])]
        ilgili += rehber_bag(6, "Kuyumcudaki fiyat neden farklı?")
        ekle(
            yol=tl_yol[t], kisa=f"{ad} kaç gram gümüş", grup="TL → gram",
            title=f"{ad} Kaç Gram Gümüş Eder? {gram_yaz(g)} · {tarih_kisa}",
            desc=f"{ad}, {gram_yaz(g)} saf gümüşe denk gelir ({tarih}, gram {bot.tr_sayi(gram)} ₺). 500 TL'den "
                 f"1 milyon TL'ye tablo ve son günler. Bilgi amaçlıdır, yatırım tavsiyesi değildir.",
            h1=f"{ad} kaç gram gümüş eder?",
            cevap=bot.tr_sayi(g, 1 if g >= 100 else 2), birim="g",
            alt=f"yaklaşık {bot.tr_sayi(g / 1000, 2)} kg" if g >= 1000 else None,
            ozet=f"{tarih} itibarıyla {ad}, ham fiyatla {gram_yaz(g)} saf gümüşe denk gelir "
                 f"(1 gram {bot.tr_sayi(gram)} ₺). Kuyumcu ve bankada satış fiyatı daha yüksek olduğu için "
                 f"alınabilecek miktar bundan az olur.",
            formul=f"{bot.tr_sayi(t, 0)} ₺ ÷ {bot.tr_sayi(gram)} ₺ (1 gram) = {gram_yaz(g)}",
            tablolar=[{"baslik": "Tutara göre gümüş", "sutunlar": ["Tutar", "Saf gümüş"],
                       "satirlar": tablo, "sayisal": [1]}],
            seyir=_seyir(kayitlar, lambda k, t=t: t / k["gram"], gram_yaz),
            seyir_baslik=f"Son günlerde {ad} ile alınan gümüş",
            seyir_ters=True,
            notlar=_ortak_notlar(),
            ilgili=ilgili,
        )

    # ---- Hurda / milyem hesabı (hesap makinesiyle)
    ekle(
        yol=yollar["milyem"], kisa="Hurda gümüş ve milyem hesabı", grup="Hurda ve milyem", hesap_turu="milyem",
        title=f"Hurda Gümüş Hesaplama: Milyem Tablosu ve Gram Değeri · {tarih_kisa}",
        desc=f"Hurda ya da eski gümüşün içindeki saf gümüşü ve değerini hesaplayın: ağırlık × milyem. Güncel "
             f"gram gümüş {bot.tr_sayi(gram)} ₺ ({tarih}). 999, 958, 925, 830, 800 ayar tablosu.",
        h1="Hurda gümüş hesaplama (milyem)",
        cevap=bot.tr_sayi(gram), birim="₺", alt="1 gram saf gümüşün ham değeri",
        ozet="Hurda gümüşün değeri, içindeki saf gümüş miktarıyla bulunur: ağırlık × milyem ÷ 1000 × gram "
             "gümüş fiyatı. Aşağıdaki hesap makinesi bunu yapar. Hurdayı alan yer eritme, ayar tespiti ve "
             "kâr payı düştüğü için ödenen tutar genelde bu değerin altındadır.",
        formul=f"Değer = ağırlık (g) × milyem ÷ 1000 × {bot.tr_sayi(gram)} ₺",
        tablolar=[{"baslik": "Milyem tablosu (1 gram)", "sutunlar": ["Ayar / milyem", "Saflık", "1 gram"],
                   "satirlar": [{"hucreler": [f"{a}" + (f" ({KISA_AD[a]})" if a in KISA_AD else ""), f"%{bot.tr_sayi(a / 10, 1)}", bot.tr_sayi(gram * a / 1000) + " ₺"],
                                 } for a, _, c in AYARLAR], "sayisal": [1, 2]}],
        notlar=_ortak_notlar(["Ürünün üzerindeki damga (ör. 925, 800) ayarı gösterir; damgasız eşyanın ayarı "
                              "ancak ölçümle anlaşılır."]),
        ilgili=[("100 gram gümüş kaç TL", agirlik_yol[100]), ("Gümüş hesap makinesi", yollar["merkez"])]
               + rehber_bag(3, "Külçede 999 ne demek?"),
    )

    # ---- Ons
    ons_tl = ons * dolar
    ekle(
        yol=yollar["ons"], kisa="1 ons gümüş kaç TL, kaç gram", grup="Ons, dolar, euro",
        title=f"1 Ons Gümüş Kaç TL? {para(ons_tl)} ₺ · Ons Kaç Gram · {tarih_kisa}",
        desc=f"1 ons gümüş {bot.tr_sayi(ons)} $ = {para(ons_tl)} ₺ ({tarih}). 1 troy ons 31,1035 gramdır. "
             f"5, 10, 100 ons ve 1 kg'ın ons karşılığı.",
        h1="1 ons gümüş kaç TL? Ons kaç gram?",
        cevap=para(ons_tl), birim="₺", alt=f"1 ons = {bot.tr_sayi(ons)} $ · 1 troy ons = 31,1035 g",
        deg=bot.degisim(ons_tl, once["gumus"] * once["dolar"]) if once else None,
        ozet=f"Gümüş dünyada troy ons ile fiyatlanır: 1 troy ons 31,1035 gramdır. {tarih} itibarıyla 1 ons gümüş "
             f"{bot.tr_sayi(ons)} $, ECB kuruyla (1 $ = {bot.tr_sayi(dolar)} ₺) {para(ons_tl)} ₺ eder. Mutfakta "
             f"kullanılan ons (28,35 g) farklıdır.",
        formul=f"{bot.tr_sayi(ons)} $ × {bot.tr_sayi(dolar)} ₺ = {para(ons_tl)} ₺ (1 ons)",
        tablolar=[{"baslik": "Ons karşılıkları", "sutunlar": ["Ons", "Gram", "Dolar", "TL"],
                   "satirlar": [{"hucreler": ["32,15 ons (1 kg)" if abs(o - 32.1507) < 0.01 else f"{bot.tr_sayi(o, 0)} ons",
                                              gram_yaz(o * bot.ONS_GRAM), para(o * ons) + " $", para(o * ons_tl) + " ₺"]}
                                for o in ONS_MIKTARLAR], "sayisal": [1, 2, 3]}],
        seyir=_seyir(kayitlar, lambda k: k["gumus"] * k["dolar"], lambda x: para(x) + " ₺"),
        seyir_baslik="Son günlerde 1 ons gümüş (₺)",
        notlar=_ortak_notlar(),
        ilgili=[("Gram gümüş kaç dolar", yollar["dolar"]), ("1 kg gümüş kaç TL", agirlik_yol[1000]),
                ("Gümüş hesap makinesi", yollar["merkez"])] + rehber_bag(1, "Ons nedir?") + rehber_bag(2, "Gram gümüş nasıl hesaplanır?"),
    )

    # ---- Dolar
    ekle(
        yol=yollar["dolar"], kisa="Gram gümüş kaç dolar", grup="Ons, dolar, euro",
        title=f"Gram Gümüş Kaç Dolar? {bot.tr_sayi(gram_usd, 3)} $ · {tarih_kisa}",
        desc=f"1 gram gümüş {bot.tr_sayi(gram_usd, 3)} $ ({tarih}); 1 kg gümüş {para(1000 * gram_usd)} $. Ons "
             f"fiyatından gram dolar hesabı ve ağırlık tablosu.",
        h1="Gram gümüş kaç dolar?",
        cevap=bot.tr_sayi(gram_usd, 3), birim="$", alt=f"1 ons {bot.tr_sayi(ons)} $ ÷ 31,1035",
        deg=bot.degisim(ons, once["gumus"]) if once else None,
        ozet=f"{tarih} itibarıyla 1 gram saf gümüş {bot.tr_sayi(gram_usd, 3)} $, 1 kilogram {para(1000 * gram_usd)} $ "
             f"eder. Dolar fiyatı ons fiyatının 31,1035'e bölünmesiyle bulunur; TL karşılığı için dolar/TL ile "
             f"çarpılır (1 $ = {bot.tr_sayi(dolar)} ₺, ECB).",
        formul=f"{bot.tr_sayi(ons)} $ ÷ 31,1035 = {bot.tr_sayi(gram_usd, 3)} $ (1 gram)",
        tablolar=[{"baslik": "Ağırlığa göre dolar", "sutunlar": ["Gümüş", "Dolar", "TL"],
                   "satirlar": [{"hucreler": [ad, para(g * gram_usd) + " $", para(g * gram) + " ₺"],
                                 "bag": agirlik_yol[g]} for g, ad, _ in AGIRLIKLAR], "sayisal": [1, 2]}],
        seyir=_seyir(kayitlar, lambda k: k["gumus"] / bot.ONS_GRAM, lambda x: bot.tr_sayi(x, 3) + " $"),
        seyir_baslik="Son günlerde 1 gram gümüş ($)",
        notlar=_ortak_notlar(),
        ilgili=[("1 ons gümüş kaç TL", yollar["ons"]), ("1 kg gümüş kaç TL", agirlik_yol[1000]),
                ("Gümüş hesap makinesi", yollar["merkez"])],
    )

    # ---- Euro (ECB EUR/TRY; kur alınamazsa sayfa yok)
    if eur_son:
        gram_eur = gram / eur_son
        ekle(
            yol=yollar["euro"], kisa="Gram gümüş kaç euro", grup="Ons, dolar, euro",
            title=f"Gram Gümüş Kaç Euro? {bot.tr_sayi(gram_eur, 3)} € · {tarih_kisa}",
            desc=f"1 gram gümüş {bot.tr_sayi(gram_eur, 3)} € ({tarih}); 1 kg gümüş {para(1000 * gram_eur)} €. "
                 f"250 g, 500 g ve 1 ons gümüşün euro karşılığı, ECB euro kuruyla.",
            h1="Gram gümüş kaç euro?",
            cevap=bot.tr_sayi(gram_eur, 3), birim="€", alt=f"1 € = {bot.tr_sayi(eur_son)} ₺ (ECB, {_kisa(date.fromisoformat(son['kur_tarihi']))})",
            ozet=f"{tarih} itibarıyla 1 gram saf gümüş {bot.tr_sayi(gram_eur, 3)} €, 1 kilogram {para(1000 * gram_eur)} € "
                 f"eder. Euro karşılığı, TL fiyatın Avrupa Merkez Bankası'nın aynı günkü euro kuruna "
                 f"(1 € = {bot.tr_sayi(eur_son)} ₺) bölünmesiyle bulunur.",
            formul=f"{bot.tr_sayi(gram)} ₺ ÷ {bot.tr_sayi(eur_son)} ₺ = {bot.tr_sayi(gram_eur, 3)} € (1 gram)",
            tablolar=[{"baslik": "Ağırlığa göre euro", "sutunlar": ["Gümüş", "Euro", "TL"],
                       "satirlar": [{"hucreler": [ad, para(g * gram_eur) + " €", para(g * gram) + " ₺"],
                                     "bag": agirlik_yol[g]} for g, ad, _ in AGIRLIKLAR]
                                  + [{"hucreler": ["1 ons", para(bot.ONS_GRAM * gram_eur) + " €", para(ons * dolar) + " ₺"],
                                      "bag": yollar["ons"]}], "sayisal": [1, 2]}],
            seyir=[r for r in _seyir(kayitlar, lambda k: k["gram"] / eur_kur(k) if eur_kur(k) else float("nan"),
                                     lambda x: bot.tr_sayi(x, 3) + " €")
                   if "nan" not in r["deger"]],
            seyir_baslik="Son günlerde 1 gram gümüş (€)",
            notlar=_ortak_notlar(["Euro kuru, ECB'nin euro referans kurudur; dolar kuru da aynı kaynaktan ve aynı "
                                  "günden alındığı için euro ve dolar karşılıkları birbiriyle tutarlıdır."]),
            ilgili=[("Gram gümüş kaç dolar", yollar["dolar"]), ("1 ons gümüş kaç TL", yollar["ons"]),
                    ("1 kg gümüş kaç TL", agirlik_yol[1000]), ("Gümüş hesap makinesi", yollar["merkez"])],
        )

    # ---- Altın / gümüş oranı
    haftalar = {}
    for g, k in kayitlar:
        haftalar[g.isocalendar()[:2]] = (g, k)
    hafta_list = list(haftalar.values())[-PARITE_HAFTA:]
    ekle(
        yol=yollar["parite"], kisa="Altın gümüş oranı (1 gram altın kaç gram gümüş)", grup="Altın ve gümüş",
        title=f"Altın Gümüş Oranı: 1 Gram Altın = {bot.tr_sayi(parite, 1)} Gram Gümüş · {tarih_kisa}",
        desc=f"Altın/gümüş oranı (rasyo) {bot.tr_sayi(parite, 1)} ({tarih}): 1 gram altın {bot.tr_sayi(parite, 1)} "
             f"gram gümüş eder. Nasıl hesaplanır, haftalık kapanışlar ve geçmişte oran.",
        h1="Altın gümüş oranı: 1 gram altın kaç gram gümüş eder?",
        cevap=bot.tr_sayi(parite, 1), birim="g gümüş", alt="1 gram altın karşılığı (altın/gümüş oranı)",
        deg=bot.degisim(parite, once["altin"] / once["gumus"]) if once else None,
        ozet=f"Altın/gümüş oranı (rasyo, parite), bir ons altının kaç ons gümüş ettiğini gösterir; oran gramda da "
             f"aynıdır. {tarih} itibarıyla oran {bot.tr_sayi(parite, 1)}: 1 gram altın {bot.tr_sayi(parite, 1)} gram "
             f"gümüş eder. Oran yükselirse gümüş altına göre ucuzlamış, düşerse pahalanmış demektir.",
        formul=f"Oran = ons altın ÷ ons gümüş = {para(son['altin'])} $ ÷ {bot.tr_sayi(ons)} $ = {bot.tr_sayi(parite, 1)}",
        tablolar=[
            {"baslik": "Altının gümüş karşılığı", "sutunlar": ["Altın", "Gümüş", "TL"],
             "satirlar": [{"hucreler": ["1 gram altın", gram_yaz(parite), para(parite * gram) + " ₺"]},
                          {"hucreler": ["10 gram altın", gram_yaz(10 * parite), para(10 * parite * gram) + " ₺"]},
                          {"hucreler": ["1 ons altın", f"{bot.tr_sayi(parite, 1)} ons",
                                        para(son['altin'] * dolar) + " ₺"]}], "sayisal": [1, 2]},
            {"baslik": "Haftalık kapanışlar", "sutunlar": ["Hafta", "Oran"],
             "satirlar": [{"hucreler": [f"{_kisa(g)} ({bot.GUN_KISA[g.weekday()]})", bot.tr_sayi(k['altin'] / k['gumus'], 1)]}
                          for g, k in reversed(hafta_list)], "sayisal": [1],
             "not": "Her haftanın botta kayıtlı son değeri (genelde cuma akşamı)."},
        ],
        seyir=_seyir(kayitlar, lambda k: k["altin"] / k["gumus"], lambda x: bot.tr_sayi(x, 1)),
        seyir_baslik="Son günlerde altın/gümüş oranı",
        notlar=["Geçmişte oran 1980 başında 20'nin altına inmiş, Mart 2020'de 120'nin üstüne çıkmıştır "
                "(ayrıntı rehberde).",
                "Gram altın burada ons altın ve ECB dolar kurundan hesaplanan ham değerdir (24 ayar, işçiliksiz); "
                "piyasadaki gram altın fiyatından farklıdır.",
                _guncelleme_notu("değer")],
        ilgili=[("Gram gümüş kaç dolar", yollar["dolar"]), ("Gümüş fiyatları geçmiş", yollar["gecmis"])]
               + rehber_bag(4, "Altın/gümüş paritesi ne anlatır?"),
    )

    # ---- Geçmiş fiyatlar: yıl yıl, ay ay, gün gün (Rıdvan, 3 Kasım 2026: "Kullanıcılar geçmiş bilgilerle erişmek
    # istiyor. Ay ay yıl yil" → "1 ve 2"). Günler: botun kayıtları + ondan önceki ~12 ay MetalCharts günlük kapanışı
    # (bot/arsiv.py; yalnız bu bölümde kullanılır, öteki sayfalar ve paylaşımlar yalnız botun kayıtlarını okur).
    # Yıllar: USGS yıllık ortalama × ECB yıllık ortalama kur; içinde bulunulan yıl günlük verilerden.
    gunluk = arsiv_mod.birlesik(gecmis, arsiv or {})
    gk = [(date.fromisoformat(g), k) for g, k in gunluk.items()]
    kendi_ilk = kayitlar[0][0]
    arsivli = gk[0][0] < kendi_ilk

    def satir(i, g, k):
        return {"tarih": f"{g.day:02d}.{g.month:02d}.{g.year}", "gun": bot.GUN_KISA[g.weekday()],
                "saat": k.get("saat", ""), "gram": bot.tr_sayi(k["gram"]), "ons": bot.tr_sayi(k["gumus"]),
                "dolar": bot.tr_sayi(k["dolar"]), "arsiv": k.get("kaynak") == arsiv_mod.KAYNAK,
                "deg": bot.degisim(k["gram"], gk[i - 1][1]["gram"]) if i > 0 else None}

    aylar = {}
    for i, (g, k) in enumerate(gk):
        aylar.setdefault((g.year, g.month), []).append((i, g, k))
    ay_ozet = []
    onceki_son = None
    for (y, m), kk in aylar.items():
        degerler = [k["gram"] for _, _, k in kk]
        bas = onceki_son if onceki_son is not None else degerler[0]
        i_cok, i_az = degerler.index(max(degerler)), degerler.index(min(degerler))
        ay_ozet.append({"ad": f"{bot.AYLAR[m - 1]} {y}", "kisa_ad": bot.AYLAR[m - 1], "yol": f"gecmis/{y}-{m:02d}/",
                        "acilis": bot.tr_sayi(degerler[0]), "kapanis": bot.tr_sayi(degerler[-1]),
                        "yuksek": bot.tr_sayi(max(degerler)), "dusuk": bot.tr_sayi(min(degerler)),
                        "yuksek_gun": _kisa(kk[i_cok][1]), "dusuk_gun": _kisa(kk[i_az][1]),
                        "ortalama": bot.tr_sayi(sum(degerler) / len(degerler)),
                        "deg": bot.degisim(degerler[-1], bas), "gun": len(kk), "kismi": onceki_son is None,
                        "arsiv": sum(1 for _, _, k in kk if k.get("kaynak") == arsiv_mod.KAYNAK),
                        "satirlar": [satir(i, g, k) for i, g, k in reversed(kk)],
                        "y": y, "m": m, "son": kk[-1][1]})
        onceki_son = degerler[-1]

    # Yıl sayfaları: günlük verisi olan yıllar (ilk yıl kısmi olabilir)
    yil_ozet = []
    onceki_yil_son = None
    for y in sorted({g.year for g, _ in gk}):
        kk = [(i, g, k) for i, (g, k) in enumerate(gk) if g.year == y]
        degerler = [k["gram"] for _, _, k in kk]
        i_cok, i_az = degerler.index(max(degerler)), degerler.index(min(degerler))
        bas = onceki_yil_son if onceki_yil_son is not None else degerler[0]
        yil_ozet.append({
            "yil": y, "yol": f"gecmis/{y}/", "ilk": _tarih(kk[0][1]), "son_tarih": _tarih(kk[-1][1]),
            "aralik": f"{_kisa(kk[0][1])} – {_kisa(kk[-1][1])}",
            "kismi_bas": onceki_yil_son is None, "devam": y == gun.year,
            "acilis": bot.tr_sayi(degerler[0]), "kapanis": bot.tr_sayi(degerler[-1]),
            "ortalama": bot.tr_sayi(sum(degerler) / len(degerler)),
            "yuksek": bot.tr_sayi(max(degerler)), "yuksek_gun": _tarih(kk[i_cok][1]),
            "dusuk": bot.tr_sayi(min(degerler)), "dusuk_gun": _tarih(kk[i_az][1]),
            "deg": bot.degisim(degerler[-1], bas), "gun": len(kk),
            "aylar": [a for a in reversed(ay_ozet) if a["y"] == y],
            "grafik": _cizgi([(g, k["gram"]) for _, g, k in kk]), "son": kk[-1][1],
            "arsiv": sum(1 for _, _, k in kk if k.get("kaynak") == arsiv_mod.KAYNAK)})
        onceki_yil_son = degerler[-1]
    yil_yol = {a["yil"]: a["yol"] for a in yil_ozet}

    yillik = []
    for r in arsiv_mod.yillik_satirlar(gunluk, gun):
        yillik.append({**r, "gram_m": bot.tr_sayi(r["gram"]), "ons_m": bot.tr_sayi(r["ons"]),
                       "kur_m": bot.tr_sayi(r["kur"]), "yol": yil_yol.get(r["yil"]),
                       "deg": bot.degisim(r["gram"], r["deg_once"]) if r["deg_once"] else None,
                       "ons_deg": bot.degisim(r["ons"], r["ons_once"]) if r["ons_once"] else None})
    for a in yil_ozet:   # yıl sayfasında o yılın tablodaki ortalaması (kısmi yılda günlük ortalamayla karışmasın)
        a["yillik"] = next((r for r in yillik if r["yil"] == a["yil"]), None)
    yillik_ilk, yillik_son = (yillik[0]["yil"], yillik[-1]["yil"]) if yillik else (None, None)
    yillik_ozet = {"ilk": yillik_ilk, "son": yillik_son,
                   "grafik_tl": _cubuk([(r["yil"], r["gram"]) for r in yillik], bot.tr_sayi),
                   "grafik_usd": _cubuk([(r["yil"], r["ons"]) for r in yillik], bot.tr_sayi),
                   "satirlar": list(reversed(yillik)), "usgs_url": arsiv_mod.USGS_KAYNAK_URL}
    kaynak_notu = {"arsivli": arsivli, "kendi_ilk": _tarih(kendi_ilk), "arsiv_ilk": _tarih(gk[0][0]),
                   "arsiv_son": _tarih(gk[[g for g, _ in gk].index(kendi_ilk) - 1][0]) if arsivli else None}
    ortak_gecmis = {"yillar": yillik_ozet, "kaynak_notu": kaynak_notu, "ilk": _tarih(gk[0][0])}

    dun = kayitlar[-2] if len(kayitlar) > 1 else None
    ekle(
        sablon="gecmis.html", yol=yollar["gecmis"], kisa="Gümüş fiyatları geçmiş", grup="Geçmiş", tur="merkez",
        title=f"Gram Gümüş Geçmiş Fiyatları: Yıllık, Aylık, Günlük · {tarih_kisa}",
        desc=f"Gram gümüşün geçmiş fiyatları: {yillik_ilk}–{yillik_son} yıl yıl ortalama, ay ay açılış–kapanış ve "
             f"gün gün tablo. Dün {bot.tr_sayi(dun[1]['gram']) + ' ₺' if dun else '—'}, son {tarih} {bot.tr_sayi(gram)} ₺."
             if yillik else
             f"Gram gümüşün geçmiş fiyatları: dün {bot.tr_sayi(dun[1]['gram']) + ' ₺' if dun else '—'}, son "
             f"{tarih} {bot.tr_sayi(gram)} ₺. Gün gün tablo ve aylık özet (açılış, kapanış, en yüksek, en düşük).",
        h1="Gram gümüş geçmiş fiyatları",
        dun=({"tarih": _tarih(dun[0]), "gram": bot.tr_sayi(dun[1]["gram"])} if dun else None),
        aylar=list(reversed(ay_ozet)), yil_listesi=list(reversed(yil_ozet)),
        satirlar=[satir(i, g, k) for i, (g, k) in reversed(list(enumerate(gk)))][:GECMIS_SATIR],
        **ortak_gecmis,
    )
    if yillik:
        son_tam = next((r for r in reversed(yillik) if not r["kismi"]), yillik[-1])
        ekle(
            sablon="gecmis.html", yol="gecmis/yillik/", kisa="Yıllara göre gümüş fiyatı", grup="Geçmiş", tur="yillik",
            title=f"Yıllara Göre Gram Gümüş Fiyatı ({yillik_ilk}–{yillik_son}): Yıllık Ortalama",
            desc=f"Gram gümüşün yıllık ortalama fiyatı {yillik_ilk}–{yillik_son}: {son_tam['yil']} ortalaması yaklaşık "
                 f"{son_tam['gram_m']} ₺ (ons {son_tam['ons_m']} $, dolar/TL {son_tam['kur_m']}). Yıl yıl tablo ve grafik.",
            h1="Yıllara göre gram gümüş fiyatı", son_tam=son_tam, lastmod=gun,
            **ortak_gecmis,
        )
    for a in reversed(yil_ozet):
        ekle(
            sablon="gecmis.html", yol=a["yol"], kisa=f"{a['yil']} gümüş fiyatları", grup="Geçmiş", tur="yil", yil=a,
            title=f"{a['yil']} Gram Gümüş Fiyatları: Aylık Tablo ve Grafik",
            desc=f"{a['yil']} gram gümüş fiyatları: ortalama {a['ortalama']} ₺, en yüksek {a['yuksek']} ₺ "
                 f"({a['yuksek_gun']}), en düşük {a['dusuk']} ₺ ({a['dusuk_gun']}). Ay ay açılış, kapanış ve değişim.",
            h1=f"{a['yil']} gram gümüş fiyatları", lastmod=a["son"],
            **ortak_gecmis,
        )
    for a in ay_ozet:
        ekle(
            sablon="gecmis.html", yol=a["yol"], kisa=f"{a['ad']} gümüş fiyatları", grup="Geçmiş", tur="ay", ay=a,
            title=f"{a['ad']} Gram Gümüş Fiyatları: Gün Gün Tablo",
            desc=f"{a['ad']} gram gümüş fiyatları: açılış {a['acilis']} ₺, kapanış {a['kapanis']} ₺, en yüksek "
                 f"{a['yuksek']} ₺, en düşük {a['dusuk']} ₺. Gün gün tablo.",
            h1=f"{a['ad']} gram gümüş fiyatları",
            lastmod=a["son"], satirlar=a["satirlar"], yil_yol=yil_yol.get(a["y"]),
            **ortak_gecmis,
        )

    # ---- Rehber bölümleri: her biri kendi adresinde
    rehber = v["rehber"]
    for i, b in enumerate(rehber):
        ekle(
            sablon="rehber-bolum.html", yol=rehber_yol[b["no"]], kisa=b["baslik"], grup="Rehber", bolum=b,
            title=f"{b['baslik']} · Gümüş Rehberi #{b['no']}",
            desc=f"{b['alt']} Gümüş rehberi #{b['no']}: kaynaklı, kısa ve sade. Bilgi amaçlıdır.",
            h1=b["baslik"],
            onceki=(rehber[i - 1]["baslik"], rehber_yol[rehber[i - 1]["no"]]) if i > 0 else None,
            sonraki=(rehber[i + 1]["baslik"], rehber_yol[rehber[i + 1]["no"]]) if i + 1 < len(rehber) else None,
        )

    # ---- Hesaplar merkezi (hesap makinesi + bütün sayfalar)
    gruplar = {}
    for s in liste:
        if s["grup"] not in ("Rehber",):
            gruplar.setdefault(s["grup"], []).append((s["kisa"], s["yol"]))
    gruplar["Geçmiş"] = gruplar.get("Geçmiş", [])[:4]
    ekle(
        sablon="hesap-merkez.html", yol=yollar["merkez"], kisa="Gümüş hesap makinesi", grup="Merkez",
        title=f"Gümüş Hesap Makinesi: Gram, Kg, Ons, Ayar → TL ve Dolar · {tarih_kisa}",
        desc=f"Gümüş hesaplama: gram, kilogram ya da ons; ayara (milyem) göre; TL ve dolar karşılığı. Gram gümüş "
             f"{bot.tr_sayi(gram)} ₺ ({tarih}). Kaç gram eder, kaç TL eder sayfaları.",
        h1="Gümüş hesap makinesi",
        gram_sayi=round(gram, 6), usd_sayi=round(gram_usd, 8),
        ayarlar=[(a, f"{a}" + (f" ({KISA_AD[a]})" if a in KISA_AD else "")) for a, _, c in AYARLAR],
        gruplar=list(gruplar.items()),
    )
    return liste


def euro_kurlari(gecmis):
    """Kayıtların ECB tarihlerini kapsayan EUR/TRY referans kurları: {"YYYY-AA-GG": kur}. Tek istek
    (Frankfurter, yalnızca ECB sağlayıcısı; dolar kuruyla aynı kaynak). Alınamazsa boş sözlük (euro yok)."""
    import requests
    tarihler = sorted(k.get("kur_tarihi") for k in gecmis.values() if k.get("kur_tarihi"))
    if not tarihler:
        return {}
    try:
        r = requests.get(bot.KUR_URL, timeout=30, headers={"User-Agent": bot.TARAYICI, "Accept": "application/json"},
                         params={"base": "EUR", "quotes": "TRY", "from": tarihler[0]})
        r.raise_for_status()
        kur = {x["date"]: float(x["rate"]) for x in r.json() if x.get("quote") == "TRY"}
        if not kur or not all(1 < k < 1000 for k in kur.values()):
            raise ValueError(f"beklenmeyen kur ({len(kur)} gün)")
        return kur
    except Exception as e:
        print(f"::warning::Euro kuru alınamadı (ECB / Frankfurter), euro sayfası atlandı: {type(e).__name__}: {e}")
        return {}


def uret(cikti, env, v, gecmis, euro=None, arsiv=None):
    """Sayfaları yazar; site haritası için [(adres, son değişiklik)] döndürür. euro verilmezse ECB'den alınır."""
    liste = sayfalar(v, gecmis, euro_kurlari(gecmis) if euro is None else euro, arsiv)
    son = max(date.fromisoformat(g) for g in gecmis)
    harita = []
    for s in liste:
        kok = "../" * s["yol"].count("/")
        hedef = cikti / s["yol"]
        hedef.mkdir(parents=True, exist_ok=True)
        (hedef / "index.html").write_text(env.get_template(s["sablon"]).render(**v, s=s, kok=kok), encoding="utf-8")
        harita.append((v["url"] + s["yol"], (s.get("lastmod") or son).isoformat()))
    return harita, liste
