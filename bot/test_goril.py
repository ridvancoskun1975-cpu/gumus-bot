"""Goril maskotu sınamaları: python bot/test_goril.py   (yalnız kurallar: python bot/test_goril.py --hizli)

Kurallar (bot/goril.py) paket gerektirmez. Şablon, yerleşim denetimi ve gorilsiz yedek yol için jinja2, Playwright
ve ffmpeg gerekir; bunlar --hizli ile atlanır. Yavaş bölüm ~2 dakika sürer.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

BOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOT))
for _d in ("GORIL_ZORLA", "GORIL_DENEME", "ORNEK_SENARYO", "ORNEK_HAFTA"):
    os.environ.pop(_d, None)
import goril  # noqa: E402

sayac = 0


def esit(ad, gercek, beklenen):
    global sayac
    sayac += 1
    if gercek != beklenen:
        raise AssertionError(f"{ad}: beklenen {beklenen!r}, gelen {gercek!r}")


ILK, SAL = date(2026, 10, 16), date(2026, 11, 3)
CMT, PAZAR = date(2026, 11, 7), date(2026, 11, 8)
ONCE = date(2026, 10, 15)                 # başlangıçtan önceki gün (gorilsiz kıyas: 13–15 Ekim)


# ---------------------------------------------------------------- kurallar (paketsiz)

def v_kur(yuzde, esik, ozel=None):
    """main.degisim / buyuk_hareket ile aynı karar: görseldeki 2 ondalık değer."""
    yon = "dusus" if yuzde < 0 else "artis"
    b = {"yon": yon} if round(abs(yuzde), 2) >= esik else None
    return {"ozel": ozel, "gram_deg": {"yuzde": yuzde, "yon": yon}, "buyuk_hareket": b}


aksam = [(3.40, "sevinen"), (2.00, "sevinen"), (1.9951, "sevinen"), (1.9949, "gezinen"), (1.99, "gezinen"),
         (0.50, "gezinen"), (-0.50, "gezinen"), (0.497, "gezinen"), (0.494, "istif"), (0.0, "istif"),
         (-0.30, "istif"), (-1.99, "gezinen"), (-1.996, "uzulen"), (-2.00, "uzulen"), (-3.10, "uzulen")]
for y, beklenen in aksam:
    esit(f"akşam {y:+}", goril.durum(v_kur(y, 2.0), "post", SAL), beklenen)
esit("özel gün önce gelir", goril.durum(v_kur(4.0, 2.0, ozel={"tur": "esik"}), "post", SAL), "ozel")
esit("özel gün sakin günde de", goril.durum(v_kur(0.1, 2.0, ozel={"tur": "zirve"}), "post", SAL), "ozel")

hafta = [(5.00, "sevinen"), (6.2, "sevinen"), (4.99, "gezinen"), (1.25, "gezinen"), (1.24, "istif"), (0.0, "istif"),
         (-1.24, "istif"), (-1.25, "gezinen"), (-4.99, "gezinen"), (-5.00, "uzulen")]
for y, beklenen in hafta:
    esit(f"hafta {y:+}", goril.durum(v_kur(y, 5.0), "hafta", CMT), beklenen)
esit("haftalıkta özel gün hâli yok", goril.durum(v_kur(1.0, 5.0, ozel={"tur": "esik"}), "hafta", CMT), "istif")

# tarih ve tür
v = v_kur(3.0, 2.0)
esit("başlangıçtan önce yok", goril.durum(v, "post", ONCE), None)
esit("ilk gün var", goril.durum(v, "post", ILK), "sevinen")
esit("cumartesi akşam özeti yok", goril.durum(v, "post", CMT), None)
esit("pazar akşam özeti yok", goril.durum(v, "post", PAZAR), None)
esit("ilk cumartesi var", goril.durum(v_kur(6.0, 5.0), "hafta", date(2026, 10, 17)), "sevinen")
for tur in ("ay", "bilgi", "kisa", "yorum", "hikaye", "kart", "yasal"):
    esit(f"{tur} türünde goril yok", goril.durum(v, tur, SAL), None)
# sabah Reels'i (Rıdvan, 16 Ekim 2026 22:25): akşamla aynı kural, hafta sonu yok, özel gün var
for y, beklenen in aksam:
    esit(f"sabah {y:+}", goril.durum(v_kur(y, 2.0), "reels", SAL), beklenen)
esit("sabah özel gün", goril.durum(v_kur(0.2, 2.0, ozel={"tur": "esik"}), "reels", SAL), "ozel")
esit("cumartesi sabah Reels'i yok", goril.durum(v, "reels", CMT), None)
esit("sabah başlangıçtan önce yok", goril.durum(v, "reels", ONCE), None)
eski = goril.GORIL_ACIK
goril.GORIL_ACIK = False
esit("kapatma anahtarı", goril.durum(v, "post", SAL), None)
goril.GORIL_ACIK = eski

# şablon alanları ve açıklama satırı
s = goril.sablon_verisi(v_kur(3.0, 2.0), "post", SAL)
esit("sevinen alanları", (s["goril"], s["maskot"], s["maskot_js"]), ("sevinen", "goril/sevinen.svg", "goril/sevinen.js"))
esit("akşam sevinen satırı", s["goril_satiri"], "🦍 Goril bugün sevinçli\n")
esit("haftalık sevinen satırı", goril.sablon_verisi(v_kur(6.0, 5.0), "hafta", CMT)["goril_satiri"],
     "🦍 Goril bu hafta sevinçli\n")
for y, d in ((-3.0, "uzulen"), (1.0, "gezinen"), (0.1, "istif")):
    s = goril.sablon_verisi(v_kur(y, 2.0), "post", SAL)
    esit(f"{d} satırsız", (s["goril"], s["goril_satiri"]), (d, ""))
esit("özel gün satırsız", goril.sablon_verisi(v_kur(4.0, 2.0, ozel={"tur": "esik"}), "post", SAL)["goril_satiri"], "")
esit("goril yoksa boş alanlar", goril.sablon_verisi(v, "post", ONCE), goril.YOK)
for d in goril.DURUMLAR:
    for uzanti in ("svg", "js"):
        esit(f"{d}.{uzanti} var", (BOT.parent / "templates" / "goril" / f"{d}.{uzanti}").exists(), True)

# önizleme zorlaması
os.environ["GORIL_ZORLA"] = "uzulen"
esit("GORIL_ZORLA yalnız örnekle", goril.sablon_verisi(v, "post", ONCE)["goril"], None)
esit("GORIL_ZORLA örnekle, tarih öncesi de", goril.sablon_verisi(v, "post", ONCE, ornek=True)["goril"], "uzulen")
esit("GORIL_ZORLA sabah Reels'inde de", goril.sablon_verisi(v, "reels", SAL, ornek=True)["goril"], "uzulen")
esit("sabah sevinen satırı", goril.sablon_verisi(v_kur(3.0, 2.0), "reels", SAL)["goril_satiri"],
     "🦍 Goril bu sabah sevinçli\n")
esit("sabah satırında 'bugün' yok", "bugün" in goril.SATIR["reels"], False)
os.environ["GORIL_ZORLA"] = "ozel"
esit("özel gün zorlaması özel veri ister", goril.sablon_verisi(v, "post", SAL, ornek=True)["goril"], "sevinen")
esit("özel gün zorlaması haftalıkta yok", goril.sablon_verisi(v_kur(1.0, 5.0, ozel={"tur": "esik"}), "hafta", CMT,
                                                              ornek=True)["goril"], "istif")
os.environ["GORIL_ZORLA"] = "kral"
esit("bilinmeyen hâl yok sayılır", goril.sablon_verisi(v, "post", ONCE, ornek=True)["goril"], None)
del os.environ["GORIL_ZORLA"]
os.environ["GORIL_DENEME"] = "istif"
esit("GORIL_DENEME (iş akışı denemesi) gerçek veriyle", goril.sablon_verisi(v, "post", ONCE)["goril"], "istif")
del os.environ["GORIL_DENEME"]

# takipci.md etiketi
esit("etiket", goril.etiket_ekle("Günlük özet", "istif"), "Günlük özet · goril: istif")
esit("etiket hâlsiz", goril.etiket_ekle("Günlük özet", None), "Günlük özet")
esit("etiket ayır", goril.etiket_ayir("Günlük özet · goril: istif"), ("Günlük özet", "istif"))
esit("etiket ayır, deneme", goril.etiket_ayir("Haftalık özet · goril: sevinen (deneme)"), ("Haftalık özet (deneme)", "sevinen"))
esit("etiket ayır, eski satır", goril.etiket_ayir("Günlük özet"), ("Günlük özet", None))
esit("etiket ayır, bozuk hâl", goril.etiket_ayir("Günlük özet · goril: ?"), ("Günlük özet", None))

print(f"Kurallar: {sayac} sınama geçti.")
if "--hizli" in sys.argv:
    sys.exit(0)


# ---------------------------------------------------------------- bot ile (jinja2, Playwright, ffmpeg)

import main  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

# manşet kararı görseldeki yazıyla aynı (yuvarlama): her değer için rozet %2,00 ise manşet var
for i in range(0, 30001, 7):
    y = i / 10000
    d = main.degisim(100 * (1 + y / 100), 100)
    yazili = float(main.tr_sayi(abs(d["yuzde"]), 2).replace(".", "").replace(",", "."))
    esit(f"manşet yuvarlaması {y}", main.buyuk_hareket(d, "bugün", 2.0) is not None, yazili >= 2.0)
    esit(f"istif sınırı {y}", goril.durum({"ozel": None, "gram_deg": d,
                                           "buyuk_hareket": main.buyuk_hareket(d, "bugün", 2.0)}, "post", SAL)
         in ("istif",), yazili < 0.5)

# goril modülü bozuksa diğer her şey sürer
gercek_modul = sys.modules.pop("goril")
sys.modules["goril"] = None                       # import goril → ImportError
esit("goril modülü yoksa alanlar boş", main.goril_alanlari({"gram_deg": {"yuzde": 3}}, "post"), main.GORIL_YOK)
sys.modules["goril"] = gercek_modul


def ornek_veri(tur, senaryo=None, hafta=None, zorla=None):
    for k, deger in (("ORNEK_SENARYO", senaryo), ("ORNEK_HAFTA", hafta), ("GORIL_ZORLA", zorla)):
        if deger is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = deger
    if tur == "hafta":
        v = main.haftalik_veri_hazirla(main.ornek_haftalik(), "@gunlukgumus")
    else:
        v = main.veri_hazirla(main.ornek_fiyatlar(), "@gunlukgumus")
    v["pazar_hatirlatma"] = main.PAZAR_HATIRLATMA if tur == "hafta" else None
    v.update(main.goril_alanlari(v, tur, ornek=True))
    return v


# açıklama: 1. satır değişmez, 2. satır yalnız sevinen
for tur, senaryo, hafta_, d in (("reels", "goril-sevinen", None, "sevinen"), ("reels", "goril-istif", None, "istif"),
                                ("post", "goril-sevinen", None, "sevinen"), ("post", "goril-uzulen", None, "uzulen"),
                                ("post", "goril-istif", None, "istif"), ("hafta", None, "sevinen", "sevinen"),
                                ("hafta", None, "istif", "istif")):
    v = ornek_veri(tur, senaryo, hafta_, d)
    esit(f"{tur}/{d} hâli", v["goril"], d)
    a = main.aciklama_yaz(v, tur).split("\n")
    yok = dict(v, **main.GORIL_YOK)
    b = main.aciklama_yaz(yok, tur).split("\n")
    esit(f"{tur}/{d} 1. satır aynı", a[0], b[0])
    if d == "sevinen":
        esit(f"{tur}/{d} 2. satır", a[1], goril.SATIR[tur])
        esit(f"{tur}/{d} gerisi aynı", a[:1] + a[2:], b)
    else:
        esit(f"{tur}/{d} açıklama aynı", a, b)

# şablonlar: her hâl hatasız; goril yokken çıktı gorilsiz alanlarla aynı
env = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True)
ornekler = [("post", "post", "goril-" + d, None, d) for d in ("sevinen", "uzulen", "gezinen", "istif")]
ornekler += [("post", "ozel", "esik", None, "ozel")]
ornekler += [("reels", "reels", "goril-" + d, None, d) for d in ("sevinen", "uzulen", "gezinen", "istif")]
ornekler += [("reels", "reels", None, None, d) for d in ("sevinen", "gezinen")]   # 3 haneli fiyat (100 ₺ üstü)
ornekler += [("reels", "ozel", "esik", None, "ozel")]
ornekler += [("hafta", "hafta", None, h, d) for h, d in (("sevinen", "sevinen"), ("uzulen", "uzulen"),
                                                         ("istif", "istif"), (None, "gezinen"))]
for tur, sablon, senaryo, hafta_, d in ornekler:
    v = ornek_veri(tur, senaryo, hafta_, d)
    esit(f"{sablon}/{d} şablon", "ozel" if v.get("ozel") else tur, sablon)
    html = env.get_template(f"{sablon}.html").render(**v)
    esit(f"{sablon}/{d} maskot içeride", 'id="goril-' in html and 'class="maskot"' in html, True)
    yok = dict(v, **main.GORIL_YOK)
    ham = {k: deger for k, deger in v.items() if k not in main.GORIL_YOK}
    esit(f"{sablon} gorilsiz çıktı", env.get_template(f"{sablon}.html").render(**yok),
         env.get_template(f"{sablon}.html").render(**ham))
    esit(f"{sablon} gorilsizde maskot yok", 'class="maskot"' in env.get_template(f"{sablon}.html").render(**yok), False)
    # yerleşim: bütün hâller kendi kutusunda fiyat ve yazılarla çakışmaz
    esit(f"{sablon}/{d} yerleşim temiz", main.goril_yerlesimi_denetle(sablon, v), None)
# kapak (profil ızgarası; Rıdvan 16 Ekim 2026): gorilli günde videodaki hâl kapakta da, gorilsizde kapak aynı
from playwright.sync_api import sync_playwright  # noqa: E402


def kapak_olc(v, tur, gun=None):
    k = main.kapak_verisi(tur, v)
    if gun:
        k["kapak_gun"] = gun
    html = env.get_template("kapak.html").render(**{**v, **k})
    gecici = main.SABLONLAR / "_kapak_sinama.html"
    gecici.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            t = p.chromium.launch()
            sf = t.new_page(viewport={"width": 1080, "height": 1920})
            sf.goto(gecici.as_uri())
            sf.evaluate("document.fonts.ready")
            sf.wait_for_timeout(300)
            r = sf.evaluate("""() => { const m = document.querySelector('.kapak-goril svg'); if (!m) return null;
                const b = m.getBoundingClientRect(), f = document.querySelector('.fiyat-satir').getBoundingClientRect();
                const y = s => { const r = document.createRange(); r.selectNodeContents(document.querySelector(s)); return r.getBoundingClientRect(); };
                const kes = (a, c) => a.left < c.right && a.right > c.left && a.top < c.bottom && a.bottom > c.top;
                return {h: b.height, ust: b.top, alt: b.bottom, sag: b.right, fiyat_ust: f.top,
                        carpar: ['.tur', '.gun', '.gun-alt'].some(s => kes(b, y('.kapak ' + s)))}; }""")
            t.close()
            return r
    finally:
        gecici.unlink(missing_ok=True)


for tur, senaryo, hafta_, d, gun, en_az in (("post", "goril-istif", None, "istif", None, 280),
                                            ("reels", "goril-sevinen", None, "sevinen", None, 280),
                                            ("hafta", None, None, "gezinen", None, 150),
                                            ("post", "goril-istif", None, "istif", "29 Temmuz", 150),
                                            ("post", "esik", None, "ozel", None, 150)):
    v = ornek_veri(tur, senaryo, hafta_, d)
    r = kapak_olc(v, tur, gun)
    esit(f"kapak/{tur}/{d}/{gun}: goril var", r is not None, True)
    esit(f"kapak/{tur}/{d}/{gun}: yeterince büyük ({r['h']:.0f} px)", r["h"] >= en_az, True)
    esit(f"kapak/{tur}/{d}/{gun}: fiyatın üstünde", r["alt"] <= r["fiyat_ust"] + 1, True)
    esit(f"kapak/{tur}/{d}/{gun}: ızgara kırpımında (y 240–1680)", r["ust"] >= 240 and r["alt"] <= 1680, True)
    esit(f"kapak/{tur}/{d}/{gun}: tarih yazılarına binmez", r["carpar"], False)
    yok = dict(v, **main.GORIL_YOK)
    ham = {k: deger for k, deger in v.items() if k not in main.GORIL_YOK}
    esit(f"kapak/{tur} gorilsiz çıktı aynı", env.get_template("kapak.html").render(**{**yok, **main.kapak_verisi(tur, yok)}),
         env.get_template("kapak.html").render(**{**ham, **main.kapak_verisi(tur, ham)}))
print(f"Şablon ve yerleşim: {sayac} sınama geçti.")

# büyük fiyat: goril rakama biner → denetim yakalar ve okunur özet verir (paylaşımı durdurmaz; Rıdvan, 16 Ekim 22:43)
v = ornek_veri("post", "goril-buyuk", None, "sevinen")
ozet_ = main.goril_yerlesimi_denetle("post", v)
esit("büyük fiyat çakışması yakalanır", bool(ozet_) and "fiyat" in ozet_, True)
esit("çakışma özeti okunur (seçici adı yok)", "#" in ozet_ or "." in ozet_.split("(")[0], False)


def yedek_dene(ad, v, beklenen_sure):
    with tempfile.TemporaryDirectory() as d:
        png, mp4 = Path(d) / "post-x.png", Path(d) / "post-x.mp4"
        t = time.time()
        sonuc = main.goril_ile_uret("post", v, png, mp4, 10)
        gecen = time.time() - t
        esit(f"{ad}: gorilsize düşer", sonuc, False)
        esit(f"{ad}: yarım dosya kalmaz", sorted(p.name for p in Path(d).iterdir()), [])
        esit(f"{ad}: süre sınırı içinde ({gecen:.0f} sn)", gecen < beklenen_sure, True)
    esit(f"{ad}: geçici şablon kalmaz", [p.name for p in main.SABLONLAR.glob("_*.html")], [])


# bozuk dosya: şablon bulunamaz
v = ornek_veri("post", "goril-sevinen", None, "sevinen")
yedek_dene("eksik maskot dosyası", dict(v, maskot="goril/_olmayan.svg"), 60)

# takılma: hareket sonsuz döngüye girer → süre sınırında süreç öldürülür
dongu = main.SABLONLAR / "goril" / "_sinama_dongu.js"
eski_sinir = goril.SURE_SINIRI
try:
    dongu.write_text("window.kare = function (t) { while (true) {} };\n", encoding="utf-8")
    goril.SURE_SINIRI = 25
    yedek_dene("takılan hareket", dict(v, maskot_js="goril/_sinama_dongu.js"), 40)
finally:
    goril.SURE_SINIRI = eski_sinir
    dongu.unlink(missing_ok=True)
print(f"Yedek yol: {sayac} sınama geçti.")


# uçtan uca (botun kendi yolu, ayrı süreç): gorilli ve gorilsize düşen akşam özeti
def hazirla(senaryo, zorla):
    with tempfile.TemporaryDirectory() as d:
        ortam = {k: deger for k, deger in os.environ.items() if k not in ("ORNEK_HAFTA", "GORIL_DENEME")}
        ortam.update(ORNEK_SENARYO=senaryo, GORIL_ZORLA=zorla)
        r = subprocess.run([sys.executable, str(BOT / "main.py"), "hazirla", "--tur", "post", "--cikti", d, "--ornek"],
                           env=ortam, capture_output=True, text=True, timeout=400)
        if r.returncode != 0:
            raise AssertionError(f"hazirla hata verdi:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
        meta = json.loads((Path(d) / "meta.json").read_text(encoding="utf-8"))
        esit(f"{senaryo}: video var", (Path(d) / meta["dosya"]).exists(), True)
        return meta, r.stdout + r.stderr


meta, cikti = hazirla("goril-sevinen", "sevinen")
esit("uçtan uca gorilli: meta", meta["goril"], "sevinen")
esit("uçtan uca gorilli: 2. satır", meta["aciklama"].split("\n")[1], goril.SATIR["post"])
esit("uçtan uca gorilli: uyarı yok", "Goril" in cikti and "gorilsiz" in cikti, False)
esit("uçtan uca gorilli: çakışma yok", meta.get("goril_cakisma"), None)
meta, cikti = hazirla("goril-buyuk", "sevinen")
esit("uçtan uca büyük fiyat: goril kalır", meta["goril"], "sevinen")
esit("uçtan uca büyük fiyat: satır var", meta["aciklama"].split("\n")[1], goril.SATIR["post"])
esit("uçtan uca büyük fiyat: çakışma metada", "fiyat" in (meta.get("goril_cakisma") or ""), True)
esit("uçtan uca büyük fiyat: bildirim satırı", "::warning::Goril üst üste biniyor" in cikti, True)
esit("uçtan uca büyük fiyat: gorilsize düşmez", "gorilsiz" in cikti, False)

print(f"Tamam: {sayac} sınama geçti.")
