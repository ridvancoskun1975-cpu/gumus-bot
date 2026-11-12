# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Küçülme sınaması (Rıdvan, 12 Kasım 2026 21:51: "birşeyi kaldırma veya silme. şablonu düzelt."; 21:53: "tüm paylaşımları
kontrol et. eğer küçülme varsa bildir. düzelt."). O akşam neden kartlı akşam özeti sığmadığı için bütünüyle ~%11 küçük
çıkmıştı (salı hesap kartıyla ~%7, perşembe geçmiş kartıyla ~%10). Önizlemeler gün içi satırı olmayan örnek veriyle
yapıldığı için fark edilmemişti; bu sınama gerçek akşamdaki gibi gün içi satırıyla dener.

Denetlenen: akşam özeti (her kart × gün içi var/yok × fiyat 84 / 104 / 150 ₺ × yükseliş/düşüş/sakin, en uzun neden
cümlesiyle) çerçeve ölçeği 1,03'te kalmalı ve alt satır y 1628'i geçmemeli; sabah Reels'i, özel gün, haftalık ve aylık
özette çerçeve taşmamalı; haftalık özetteki pazar hatırlatması 27 px'te kalmalı.
Çalıştırma: python bot/test_kucukme.py (Chromium; CHROME_YOLU varsa o kullanılır)."""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402
import insan  # noqa: E402
import baslik  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ENV = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True)
GUN = datetime.now(main.TR_SAAT).date()
EN_UZUN_NEDEN = ("ABD'de beklenenden güçlü istihdam verisi faiz indirimi beklentisini zayıflattı ve doları güçlendirdi"
                 )[:insan.NEDEN_EN_UZUN]
ALT_SINIR = 1628          # px: haftalık ve aylık özetin onaylı alt sınırı (README → Instagram arayüzü)
hatalar, sayac = [], 0

OLC = """() => {
  const c = document.querySelector('.cerceve'); const r = c.getBoundingClientRect();
  const h = document.getElementById('hatirlatma');
  return {olcek: c.dataset.olcek ? +c.dataset.olcek : null, transform: c.style.transform, sh: c.scrollHeight,
          ch: c.clientHeight, alt: Math.round(r.bottom), hatirlatma: h ? parseFloat(getComputedStyle(h).fontSize) : null};
}"""


def olc(sayfa, sablon, veri):
    html = ENV.get_template(f"{sablon}.html").render(**veri)
    gecici = main.SABLONLAR / f"_kucukme_{sablon}.html"
    gecici.write_text(html, encoding="utf-8")
    try:
        sayfa.goto(gecici.as_uri())
        sayfa.evaluate("document.fonts.ready")
        sayfa.wait_for_timeout(150)
        return sayfa.evaluate(OLC)
    finally:
        gecici.unlink(missing_ok=True)


def esit(ad, kosul, ayrinti=""):
    global sayac
    sayac += 1
    if not kosul:
        hatalar.append(f"{ad} {ayrinti}")


def aksam_verisi(gram, once, gun_ici, kart):
    f = {"gram": gram, "gram_once": once, "parite": 77.4, "parite_once": 76.83, "dolar": 50.26, "dolar_once": 50.23,
         "kur_tarihi": GUN.isoformat()}
    seri, g = {}, GUN
    for v in [once, once * 0.99, once * 1.02, once * 0.98, once * 1.03, once * 0.97]:
        g = baslik.onceki_is_gunu(g)
        seri[g.isoformat()] = round(v, 2)
    f["gecmis_gram"] = seri
    if gun_ici:
        f["gun_ici"] = [("10:00", gram * 1.012), ("12:35", gram * 0.995), ("16:35", gram * 0.988), ("19:55", gram)]
    v = main.veri_hazirla(f, "@gunlukgumus", "post")
    v["parite_cumle"] = main.gorsel_parite_cumlesi(v, "post")
    v.update(main.goril_alanlari(v, "post", True))
    v["gunun_notu"], v["goril_balon"] = None, None
    if kart == "neden":
        v["gunun_notu"] = {"tur": "neden", "etiket": insan.NEDEN_ETIKET[v["gram_deg"]["yon"] if v["gram_deg"]["yon"] in
                                                                       insan.NEDEN_ETIKET else "dusus"],
                           "metin": EN_UZUN_NEDEN, "alt": insan.NEDEN_NOTU}
    elif kart == "gecmis":
        v["gunun_notu"] = insan.gecmis_karti(v, seri, "post", GUN, zorla="gecmis", ons=main.bugunku_ons(f))
    elif kart == "hesap":
        v["gunun_notu"] = insan.hesap_karti(v, seri, "post", GUN, zorla="hesap")
    return v


with sync_playwright() as p:
    kw = {"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}
    tarayici = p.chromium.launch(**kw)
    sayfa = tarayici.new_page(viewport={"width": 1080, "height": 1920})

    # 1) Akşam özeti: kartlı günler küçülmez
    for kart in ("neden", "gecmis", "hesap", None):
        for gun_ici in (True, False):
            for taban in (84.05, 104.05, 150.05):
                for carpan in (0.962, 1.004, 1.031):          # düşüş (manşet), sakin, yükseliş (manşet)
                    gram = round(taban * carpan, 2)
                    for hal in ("sevinen", "uzulen", "istif", "gezinen"):
                        os.environ["GORIL_ZORLA"] = hal
                        v = aksam_verisi(gram, taban, gun_ici, kart)
                        o = olc(sayfa, "post", v)
                        ad = f"akşam kart={kart} gün_içi={gun_ici} {gram} ₺ goril={hal}:"
                        if kart:
                            esit(ad + " ölçek 1,03", o["olcek"] is not None and o["olcek"] >= 1.029, str(o))
                            esit(ad + " alt sınır", o["alt"] <= ALT_SINIR, str(o))
                        else:
                            esit(ad + " kartsız taşma yok", o["sh"] <= o["ch"] + 1 and o["transform"] == "scale(1.03)", str(o))
    os.environ.pop("GORIL_ZORLA", None)

    # 2) Sabah Reels'i ve özel gün: taşma yok
    for senaryo in ("", "goril-uzulen", "goril-sevinen", "seri", "esik-alti", "esik", "zirve"):
        os.environ["ORNEK_SENARYO"] = senaryo
        tur = "reels" if senaryo not in ("esik", "zirve") else "post"
        f = main.ornek_fiyatlar()
        v = main.veri_hazirla(f, "@gunlukgumus", tur)
        v["parite_cumle"] = main.gorsel_parite_cumlesi(v, tur)
        v.update(main.goril_alanlari(v, tur, True))
        v.update({"gunun_notu": None, "goril_balon": None})
        sablon = "ozel" if v.get("ozel") else tur
        o = olc(sayfa, sablon, v)
        esit(f"{sablon} {senaryo or 'düz'}: taşma yok", o["sh"] <= o["ch"] + 1, str(o))
    os.environ.pop("ORNEK_SENARYO", None)

    # 3) Haftalık ve aylık özet: taşma yok, pazar hatırlatması 27 px
    for tur, al, haz in (("hafta", main.ornek_haftalik, main.haftalik_veri_hazirla),
                         ("ay", main.ornek_aylik, main.aylik_veri_hazirla)):
        for kismi in (False, True):
            for carpan in (1.0, 1.12, 0.88):
                f = al(kismi=kismi)
                if carpan != 1.0:
                    f["gram"] = round(f["gram_once"] * carpan, 2)
                v = haz(f, "@gunlukgumus")
                v["parite_cumle"] = main.gorsel_parite_cumlesi(v, tur)
                if tur == "hafta":
                    v["pazar_hatirlatma"] = main.PAZAR_HATIRLATMA
                v.update(main.goril_alanlari(v, tur, True))
                o = olc(sayfa, tur, v)
                ad = f"{tur} kısmi={kismi} ×{carpan}:"
                esit(ad + " taşma yok", o["sh"] <= o["ch"] + 1, str(o))
                if tur == "hafta":
                    esit(ad + " hatırlatma 27 px", o["hatirlatma"] == 27, str(o))
    tarayici.close()

if hatalar:
    print("\n".join(hatalar[:40]))
    print(f"test_kucukme: {len(hatalar)} / {sayac} sınama BAŞARISIZ")
    sys.exit(1)
print(f"test_kucukme: {sayac} sınama geçti")
