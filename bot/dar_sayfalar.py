"""Dar aramalar için sayfalar: "100 gram gümüş kaç TL", "1000 TL kaç gram gümüş", "925 ayar gümüş
gram fiyatı", "1 ons gümüş kaç TL", "altın gümüş oranı", "gümüş fiyatları geçmiş" gibi.

Rıdvan (15 Ekim 2026): "dar aramaların hiç birini kaçırmayalım. bu mantık ile gelen aramalar konusunu
ciddi ele al ve genişlet." Arama ailesi listesi Google otomatik tamamlamasından çıkarıldı (proje belgesi
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
AYAR_SAYFALAR = [925, 800]
KISA_AD = {999: "külçe", 958: "Britannia", 925: "takı", 800: "en düşük"}   # dar tablolarda kısa açıklama
AYAR_AGIRLIK = [1, 5, 10, 20, 50, 100, 250, 1000]
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


def _ortak_notlar(ek=None):
    n = list(ek or [])
    n.append("Değer, uluslararası ons fiyatı ve ECB dolar kuruyla hesaplanan ham gümüş değeridir. Kuyumcu, "
             "banka ve satıcı fiyatları işçilik, alış-satış farkı (makas) ve vergiler yüzünden farklıdır; "
             "satış fiyatı genelde daha yüksek, alış (bozdurma) fiyatı daha düşüktür.")
    n.append("Anlık (canlı) fiyat değildir; hafta içi günde iki kez, Instagram paylaşımlarıyla birlikte "
             "güncellenir.")
    return n


def sayfalar(v, gecmis):
    """Bütün dar arama sayfalarının verisi: [{yol, sablon, ...}]. v = sayfa.veri_hazirla() çıktısı."""
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
    ayar_yol = {a: f"hesap/{a}-ayar-gumus-gram-fiyati/" for a in AYAR_SAYFALAR}
    yollar = {
        "merkez": "hesap/", "milyem": "hesap/hurda-gumus-milyem-hesabi/", "ons": "hesap/1-ons-gumus-kac-tl/",
        "dolar": "hesap/gram-gumus-kac-dolar/", "parite": "hesap/altin-gumus-orani/", "gecmis": "gecmis/",
    }
    rehber_yol = {b["no"]: f"rehber/{b['no']}-{adres_parcasi(b['baslik'])}/" for b in v["rehber"]}

    def rehber_bag(no, metin):
        return [(metin, rehber_yol[no])] if no in rehber_yol else []

    # ---- Ağırlık → TL
    for g, ad, _ in AGIRLIKLAR:
        deger = g * gram
        ad_uzun = "1 kg (1 kilo)" if g == 1000 else ad
        komsu = [{"hucreler": [ad2, para(g2 * gram) + " ₺"], "bag": agirlik_yol[g2] if g2 != g else None,
                  "vurgu": g2 == g} for g2, ad2, _ in AGIRLIKLAR]
        ayar_satir = [{"hucreler": [f"{a} ayar" + (f" ({KISA_AD[a]})" if a in KISA_AD else ""),
                                    gram_yaz(g * a / 1000), para(deger * a / 1000) + " ₺"],
                       "bag": ayar_yol.get(a)} for a, _, ack in AYARLAR]
        ilgili = [(f"{ad2} gümüş kaç TL", agirlik_yol[g2]) for g2, ad2, _ in AGIRLIKLAR if g2 != g][:4]
        ilgili += [("1.000 TL kaç gram gümüş", tl_yol[1000]), ("925 ayar gram fiyatı", ayar_yol[925]),
                   ("Gümüş hesap makinesi", yollar["merkez"])]
        ilgili += rehber_bag(6, "Kuyumcudaki fiyat neden farklı?")
        ekle(
            yol=agirlik_yol[g], kisa=f"{ad} gümüş kaç TL", grup="Ağırlık → TL",
            title=f"{ad_uzun.replace('kilo', 'Kilo').title() if g == 1000 else ad.title()} Gümüş Kaç TL? "
                  f"{para(deger)} ₺ · {tarih_kisa}",
            desc=f"{ad_uzun} gümüş {para(deger)} ₺ ({tarih}). {ad} saf gümüşün değeri, 925 ve 800 ayarda "
                 f"içindeki gümüş, dolar karşılığı ve son günler. Bilgi amaçlıdır, yatırım tavsiyesi değildir.",
            h1=f"{ad_uzun} gümüş kaç TL?",
            cevap=para(deger), birim="₺",
            deg=bot.degisim(deger, g * once["gram"]) if once else None,
            ozet=f"{ad_uzun} saf gümüşün değeri {tarih} itibarıyla {para(deger)} ₺ "
                 f"(yaklaşık {para(g * gram_usd)} $). Hesap: {bot.tr_sayi(g, 0)} g × {bot.tr_sayi(gram)} ₺.",
            formul=f"{bot.tr_sayi(g, 0)} g × {bot.tr_sayi(gram)} ₺ (1 gram) = {para(deger)} ₺",
            tablolar=[
                {"baslik": "Başka ağırlıklar", "sutunlar": ["Gümüş", "Değer"], "satirlar": komsu, "sayisal": [1]},
                {"baslik": f"{ad} eşyada içindeki gümüş (ayara göre)", "sutunlar": ["Ayar", "Saf gümüş", "Değer"],
                 "satirlar": ayar_satir, "sayisal": [1, 2],
                 "not": "999 külçede gümüşün binde 999'u saftır; tabloda bu küçük fark da hesaba katıldı."},
            ],
            seyir=_seyir(kayitlar, lambda k, g=g: g * k["gram"], lambda x: para(x) + " ₺"),
            seyir_baslik=f"Son günlerde {ad} gümüş (₺)",
            notlar=_ortak_notlar(["Külçe gümüş teslimi KDV'den istisnadır; takı ve eşyada KDV, içindeki gümüş "
                                  "bedeli düşüldükten sonra kalan tutar üzerinden hesaplanır (ayrıntı rehberde)."]),
            ilgili=ilgili,
        )

    # ---- TL → gram
    for t in TL_SAYFALAR:
        g = t / gram
        tablo = [{"hucreler": [tl_yaz(t2), gram_kisa(t2 / gram), gram_kisa(t2 / (gram * 0.925))],
                  "bag": tl_yol.get(t2) if t2 != t else None, "vurgu": t2 == t} for t2 in TL_TABLO]
        ad = f"{bot.tr_sayi(t, 0)} TL"
        ilgili = [(f"{bot.tr_sayi(t2, 0)} TL kaç gram gümüş", tl_yol[t2]) for t2 in TL_SAYFALAR if t2 != t]
        ilgili += [("100 gram gümüş kaç TL", agirlik_yol[100]), ("1 kg gümüş kaç TL", agirlik_yol[1000]),
                   ("Gümüş hesap makinesi", yollar["merkez"])]
        ilgili += rehber_bag(6, "Kuyumcudaki fiyat neden farklı?")
        ekle(
            yol=tl_yol[t], kisa=f"{ad} kaç gram gümüş", grup="TL → gram",
            title=f"{ad} Kaç Gram Gümüş Eder? {gram_yaz(g)} · {tarih_kisa}",
            desc=f"{ad} ile {gram_yaz(g)} saf gümüş alınır ({tarih}, gram {bot.tr_sayi(gram)} ₺). 500 TL'den "
                 f"1 milyon TL'ye tablo, 925 ayar karşılığı ve son günler. Bilgi amaçlıdır.",
            h1=f"{ad} kaç gram gümüş eder?",
            cevap=bot.tr_sayi(g, 1 if g >= 100 else 2), birim="g",
            alt=f"yaklaşık {bot.tr_sayi(g / 1000, 2)} kg" if g >= 1000 else None,
            ozet=f"{tarih} itibarıyla {ad} ile ham fiyattan {gram_yaz(g)} saf gümüş alınır "
                 f"(1 gram {bot.tr_sayi(gram)} ₺). Kuyumcu ve bankada satış fiyatı daha yüksek olduğu için "
                 f"alınan miktar bundan az olur.",
            formul=f"{bot.tr_sayi(t, 0)} ₺ ÷ {bot.tr_sayi(gram)} ₺ (1 gram) = {gram_yaz(g)}",
            tablolar=[{"baslik": "Tutara göre gümüş", "sutunlar": ["Tutar", "Saf gümüş", "925 ayar"],
                       "satirlar": tablo, "sayisal": [1, 2],
                       "not": "925 ayar sütunu: aynı tutarla kaç gram 925 ayar eşyanın içindeki gümüşe denk gelir "
                              "(işçilik hariç)."}],
            seyir=_seyir(kayitlar, lambda k, t=t: t / k["gram"], gram_yaz),
            seyir_baslik=f"Son günlerde {ad} ile alınan gümüş",
            seyir_ters=True,
            notlar=_ortak_notlar(),
            ilgili=ilgili,
        )

    # ---- Ayar → gram fiyatı
    for a in AYAR_SAYFALAR:
        f = gram * a / 1000
        tablo = [{"hucreler": [f"{bot.tr_sayi(g2, 0)} g", gram_yaz(g2 * a / 1000), para(g2 * f) + " ₺"]}
                 for g2 in AYAR_AGIRLIK]
        ayarlar = [{"hucreler": [f"{a2} ayar", f"%{bot.tr_sayi(a2 / 10, 1)}", bot.tr_sayi(gram * a2 / 1000) + " ₺"],
                    "bag": ayar_yol.get(a2) if a2 != a else None, "vurgu": a2 == a} for a2, _, _ in AYARLAR]
        ack = dict((x, c) for x, _, c in AYARLAR)[a]
        ilgili = [(f"{a2} ayar gümüş gram fiyatı", ayar_yol[a2]) for a2 in AYAR_SAYFALAR if a2 != a]
        ilgili += [("Hurda gümüş ve milyem hesabı", yollar["milyem"]), ("10 gram gümüş kaç TL", agirlik_yol[10]),
                   ("Gümüş hesap makinesi", yollar["merkez"])]
        ilgili += rehber_bag(3, "Külçede 999 ne demek? (ayar ve damga)")
        ekle(
            yol=ayar_yol[a], kisa=f"{a} ayar gümüş gram fiyatı", grup="Ayar",
            title=f"{a} Ayar Gümüş Gram Fiyatı: {bot.tr_sayi(f)} ₺ · {tarih_kisa}",
            desc=f"{a} ayar gümüşün 1 gramındaki saf gümüşün değeri {bot.tr_sayi(f)} ₺ ({tarih}). 1 gramdan "
                 f"1 kilograma tablo, ayar karşılaştırması. Takı ve hurda fiyatı farkı açıklamalı.",
            h1=f"{a} ayar gümüş gram fiyatı",
            cevap=bot.tr_sayi(f), birim="₺",
            alt=f"1 gram {a} ayarın içindeki {bot.tr_sayi(a / 1000, 3)} g saf gümüşün değeri",
            ozet=f"{a} ayar{f' ({ack})' if ack else ''} gümüşün binde {a}'i saf gümüştür. {tarih} itibarıyla 1 gram {a} ayar "
                 f"gümüşün içindeki gümüşün değeri {bot.tr_sayi(f)} ₺. Takı fiyatına işçilik ve KDV eklenir; "
                 f"hurda alış fiyatı ise genelde bunun altındadır.",
            formul=f"{bot.tr_sayi(gram)} ₺ × {a} ÷ 1000 = {bot.tr_sayi(f)} ₺ (1 gram {a} ayar)",
            tablolar=[
                {"baslik": f"{a} ayar: ağırlığa göre", "sutunlar": ["Ağırlık", "İçindeki gümüş", "Değer"],
                 "satirlar": tablo, "sayisal": [1, 2]},
                {"baslik": "Ayarlara göre 1 gram", "sutunlar": ["Ayar", "Saflık", "1 gram"],
                 "satirlar": ayarlar, "sayisal": [1, 2]},
            ],
            seyir=_seyir(kayitlar, lambda k, a=a: k["gram"] * a / 1000, lambda x: bot.tr_sayi(x) + " ₺"),
            seyir_baslik=f"Son günlerde 1 gram {a} ayar (₺)",
            notlar=_ortak_notlar(["Ayar, alaşımın binde kaçının saf gümüş olduğunu gösterir (milyem). Uluslararası "
                                  "damga sözleşmesinin tanıdığı en düşük gümüş ayarı 800'dür."]),
            ilgili=ilgili,
        )

    # ---- Hurda / milyem hesabı (hesap makinesiyle)
    ekle(
        yol=yollar["milyem"], kisa="Hurda gümüş ve milyem hesabı", grup="Ayar", hesap_turu="milyem",
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
                                 "bag": ayar_yol.get(a)} for a, _, c in AYARLAR], "sayisal": [1, 2]}],
        notlar=_ortak_notlar(["Ürünün üzerindeki damga (ör. 925, 800) ayarı gösterir; damgasız eşyanın ayarı "
                              "ancak ölçümle anlaşılır."]),
        ilgili=[("925 ayar gümüş gram fiyatı", ayar_yol[925]), ("800 ayar gümüş gram fiyatı", ayar_yol[800]),
                ("Gümüş hesap makinesi", yollar["merkez"])] + rehber_bag(3, "Külçede 999 ne demek?"),
    )

    # ---- Ons
    ons_tl = ons * dolar
    ekle(
        yol=yollar["ons"], kisa="1 ons gümüş kaç TL, kaç gram", grup="Ons ve dolar",
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
        yol=yollar["dolar"], kisa="Gram gümüş kaç dolar", grup="Ons ve dolar",
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
                "Anlık (canlı) değer değildir; hafta içi günde iki kez güncellenir."],
        ilgili=[("Gram gümüş kaç dolar", yollar["dolar"]), ("Gümüş fiyatları geçmiş", yollar["gecmis"])]
               + rehber_bag(4, "Altın/gümüş paritesi ne anlatır?"),
    )

    # ---- Geçmiş fiyatlar
    aylar = {}
    for g, k in kayitlar:
        aylar.setdefault((g.year, g.month), []).append((g, k))
    ay_ozet = []
    onceki_son = None
    for (y, m), kk in aylar.items():
        degerler = [k["gram"] for _, k in kk]
        bas = onceki_son if onceki_son is not None else degerler[0]
        ay_ozet.append({"ad": f"{bot.AYLAR[m - 1]} {y}", "yol": f"gecmis/{y}-{m:02d}/",
                        "acilis": bot.tr_sayi(degerler[0]), "kapanis": bot.tr_sayi(degerler[-1]),
                        "yuksek": bot.tr_sayi(max(degerler)), "dusuk": bot.tr_sayi(min(degerler)),
                        "deg": bot.degisim(degerler[-1], bas), "gun": len(kk), "kismi": onceki_son is None,
                        "kayitlar": kk, "y": y, "m": m, "son": kk[-1][0]})
        onceki_son = degerler[-1]
    dun = kayitlar[-2] if len(kayitlar) > 1 else None
    ekle(
        sablon="gecmis.html", yol=yollar["gecmis"], kisa="Gümüş fiyatları geçmiş", grup="Geçmiş",
        title=f"Gram Gümüş Geçmiş Fiyatları: Dün, Haftalık, Aylık · {tarih_kisa}",
        desc=f"Gram gümüşün geçmiş fiyatları: dün {bot.tr_sayi(dun[1]['gram']) + ' ₺' if dun else '—'}, son "
             f"{tarih} {bot.tr_sayi(gram)} ₺. Gün gün tablo ve aylık özet (açılış, kapanış, en yüksek, en düşük).",
        h1="Gram gümüş geçmiş fiyatları",
        dun=({"tarih": _tarih(dun[0]), "gram": bot.tr_sayi(dun[1]["gram"])} if dun else None),
        aylar=list(reversed(ay_ozet)),
        satirlar=[
            {"tarih": f"{g.day:02d}.{g.month:02d}.{g.year}", "gun": bot.GUN_KISA[g.weekday()], "saat": k.get("saat", ""),
             "gram": bot.tr_sayi(k["gram"]), "ons": bot.tr_sayi(k["gumus"]), "dolar": bot.tr_sayi(k["dolar"]),
             "deg": bot.degisim(k["gram"], kayitlar[i - 1][1]["gram"]) if i > 0 else None}
            for i, (g, k) in reversed(list(enumerate(kayitlar)))][:GECMIS_SATIR],
        ilk=_tarih(kayitlar[0][0]),
    )
    for a in ay_ozet:
        ekle(
            sablon="gecmis.html", yol=a["yol"], kisa=f"{a['ad']} gümüş fiyatları", grup="Geçmiş", ay=a,
            title=f"{a['ad']} Gram Gümüş Fiyatları: Gün Gün Tablo",
            desc=f"{a['ad']} gram gümüş fiyatları: açılış {a['acilis']} ₺, kapanış {a['kapanis']} ₺, en yüksek "
                 f"{a['yuksek']} ₺, en düşük {a['dusuk']} ₺. Gün gün tablo.",
            h1=f"{a['ad']} gram gümüş fiyatları",
            lastmod=a["son"],
            satirlar=[{"tarih": f"{g.day:02d}.{g.month:02d}.{g.year}", "gun": bot.GUN_KISA[g.weekday()],
                       "saat": k.get("saat", ""), "gram": bot.tr_sayi(k["gram"]), "ons": bot.tr_sayi(k["gumus"]),
                       "dolar": bot.tr_sayi(k["dolar"]),
                       "deg": bot.degisim(k["gram"], a["kayitlar"][i - 1][1]["gram"]) if i > 0 else None}
                      for i, (g, k) in reversed(list(enumerate(a["kayitlar"])))],
            ilk=_tarih(kayitlar[0][0]),
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
        desc=f"Gümüş hesaplama: gram, kilogram ya da ons; 999, 925, 800 ayar; TL ve dolar karşılığı. Gram gümüş "
             f"{bot.tr_sayi(gram)} ₺ ({tarih}). Kaç gram eder, kaç TL eder sayfaları.",
        h1="Gümüş hesap makinesi",
        gram_sayi=round(gram, 6), usd_sayi=round(gram_usd, 8),
        ayarlar=[(a, f"{a}" + (f" ({KISA_AD[a]})" if a in KISA_AD else "")) for a, _, c in AYARLAR],
        gruplar=list(gruplar.items()),
    )
    return liste


def uret(cikti, env, v, gecmis):
    """Sayfaları yazar; site haritası için [(adres, son değişiklik)] döndürür."""
    liste = sayfalar(v, gecmis)
    son = max(date.fromisoformat(g) for g in gecmis)
    harita = []
    for s in liste:
        kok = "../" * s["yol"].count("/")
        hedef = cikti / s["yol"]
        hedef.mkdir(parents=True, exist_ok=True)
        (hedef / "index.html").write_text(env.get_template(s["sablon"]).render(**v, s=s, kok=kok), encoding="utf-8")
        harita.append((v["url"] + s["yol"], (s.get("lastmod") or son).isoformat()))
    return harita, liste
