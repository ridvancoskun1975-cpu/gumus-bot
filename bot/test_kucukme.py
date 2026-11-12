# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Küçülme sınaması (Rıdvan, 12 Kasım 2026 21:51: "birşeyi kaldırma veya silme. şablonu düzelt."; 21:53: "tüm paylaşımları
kontrol et. eğer küçülme varsa bildir. düzelt."). O akşam neden kartlı akşam özeti sığmadığı için bütünüyle ~%11 küçük
çıkmıştı (salı hesap kartıyla ~%7, perşembe geçmiş kartıyla ~%10). Önizlemeler gün içi satırı olmayan örnek veriyle
yapıldığı için fark edilmemişti; bu sınama gerçek akşamdaki gibi gün içi satırıyla dener.

Denetlenen: akşam özeti (her kart × gün içi var/yok × fiyat 84 / 104 / 150 ₺ × yükseliş/düşüş/sakin, en uzun neden
cümlesiyle) çerçeve ölçeği 1,03'te kalmalı ve alt satır y 1628'i geçmemeli; sabah Reels'i, özel gün, haftalık ve aylık
özette çerçeve taşmamalı; haftalık özetteki pazar hatırlatması 27 px'te kalmalı.
Pazar yorumu (12 Kasım 2026, Rıdvan 22:58 "şimdi bakalım"): yayımlanmış 8 ve 9 Kasım yorumlarının metinleriyle kaydırmalı
gönderi ve Reels'te yazı en az şu boyda kalmalı: olağan hafta kaydırmalıda 42 px (tam boy), Reels'te 46 px; "Yön değişti"
notlu uzun hafta kaydırmalı kısa vadede 36, Reels kısa vadede 38 px (öncesi 30 / 34). Hiçbir sayfa taşmamalı; Reels'te
sahne başlığı üst şeride (hesap satırı, Ag rozeti) binmemeli.
Çalıştırma: python bot/test_kucukme.py (Chromium; CHROME_YOLU varsa o kullanılır)."""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402
import insan  # noqa: E402
import yorum  # noqa: E402
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


# Yayımlanmış iki pazar yorumu (8 Kasım: olağan; 9 Kasım: kısa vadede "Yön değişti" notlu, en uzun metinli hafta)
PAZAR_8KAS = {
    "kisa": {"yon": "düşüş", "guc": "zayıf", "ozet": "Toparlanmaya rağmen baskı sürüyor",
             "durum": "Gram, onstaki toparlanmayla haftayı yükselişle kapattı; ancak güçlü istihdam verisi sonrası dolar ve "
                      "faizler yükseldi.",
             "seyir": "Fed'in faiz artırma olasılığı yüksek kalır ve dolar güçlenirse gram gümüşte geri çekilme baskısı "
                      "sürebilir; ABD enflasyonu ılımlı gelirse toparlanma uzayabilir.",
             "izlenecek": "ABD enflasyon verisi, Fed beklentileri, TCMB raporu", "degisim": ""},
    "orta": {"yon": "düşüş", "guc": "orta", "ozet": "Aşağı yönlü eğilim sürüyor",
             "durum": "Ons son aylarda belirgin geriledi; kurdaki yükseliş gramdaki kaybı kısmen sınırladı, gümüş altından "
                      "zayıf kaldı.",
             "seyir": "Fed'in faiz artırımı beklentisi ve güçlü dolar sürerse düşüş eğilimi devam edebilir; arz açığı "
                      "beklentisi ve kurdaki artış gram fiyatı destekleyebilir.",
             "izlenecek": "Fed faiz beklentileri, dolar/TL, arz-talep dengesi", "degisim": ""},
    "haberler": [
        ("Gümüş", "Ons gümüş hafta ortasında düşen enerji fiyatları ve gerileyen tahvil faizleri ortamında yükseldi.",
         "tradingeconomics.com"),
        ("Dolar ve faiz", "Güçlü ABD istihdam verisi sonrası dolar, tahvil faizleri ve Fed'in faiz artırma olasılığı "
                          "yükseldi.", "cnbc.com"),
        ("Türkiye", "Dolar/TL hafta sonunda son bir yılın zirvesini gördü.", "tr.investing.com"),
        ("Önümüzdeki hafta", "Önümüzdeki hafta ABD enflasyon verisi ve TCMB Enflasyon Raporu açıklanacak.", "bloomberg.com")],
    "yuzde": {"kisa": (-12.69, -14.40, 1.99), "orta": (-14.11, -18.30, 5.13)}, "onceki": None,
}
PAZAR_9KAS = {
    "kisa": {"yon": "yükseliş", "guc": "zayıf", "ozet": "Dipten temkinli toparlanma",
             "durum": "Ons yılın en düşüğünden toparlandı; zayıf dolar, gerileyen faizler ve petrol etkili olmuş olabilir, "
                      "kur etkisi sınırlı.",
             "seyir": "Dolar ve faizlerdeki gerileme ile ABD yönetiminin İran'la diplomasi mesajları etkisini korursa "
                      "toparlanma sürebilir; yüksek enflasyon verisi Fed'in faiz artırma beklentisini güçlendirirse baskı "
                      "dönebilir.",
             "izlenecek": "ABD enflasyon verisi, Fed konuşmaları, dolar endeksi",
             "degisim": "Toparlanma yeni haftada da sürdü; zayıflayan dolar ve diplomasi umutları öne çıktı."},
    "orta": {"yon": "düşüş", "guc": "orta", "ozet": "Ana eğilim hâlâ aşağı",
             "durum": "Son aylarda ons belirgin geriledi, gümüş altından zayıf kaldı; kurdaki artış gram düşüşünü kısmen "
                      "sınırladı.",
             "seyir": "Fed'in faiz artırma beklentisi güçlü kalırsa düşüş eğilimi sürebilir; dolar zayıflığı kalıcılaşır, "
                      "arz açığı ve Hindistan talebi öne çıkarsa toparlanma güçlenebilir.",
             "izlenecek": "Fed faiz beklentileri, dolar/TL, arz açığı", "degisim": ""},
    "haberler": [
        ("Gümüş", "Ons gümüş yılın en düşüğünü gördükten sonra hafta içinde toparlandı.", "kitco.com"),
        ("Dolar ve faiz", "ABD'de tarım dışı istihdam beklentinin üzerinde arttı, Fed faiz artışı beklentisi güçlendi.",
         "ca.investing.com"),
        ("Siyaset", "ABD ara seçimlerinde muhalefet Kongre'de çoğunluğu aldı; ardından dolar ve tahvil faizleri geriledi.",
         "fxstreet.com"),
        ("Önümüzdeki hafta", "ABD enflasyon verisi açıklanacak, aynı gün bir Fed üyesi konuşacak.", "kitco.com")],
    "yuzde": {"kisa": (-11.14, -12.56, 1.62), "orta": (-15.80, -19.90, 5.12)},
    "onceki": {"tarih": "8 Kasım", "kisa": ("düşüş", "zayıf")},
}
PAZAR_KAY_OLC = """() => { const g = document.getElementById('govde');
  return {px: parseFloat(getComputedStyle(document.documentElement).getPropertyValue(g.dataset.degisken)),
          sh: g.scrollHeight, ch: g.clientHeight}; }"""
PAZAR_REELS_OLC = """() => {
  const s = [...document.querySelectorAll('.sahne-k')].find(e => !e.classList.contains('gizli'));
  const o = s.querySelector('[data-sigdir]'); const b = s.querySelector('.baslik-satir') || s.querySelector('h2');
  const r = b.getBoundingClientRect(); const ust = document.querySelectorAll('.kenar .kunye, .kenar .ag, .kenar .ses-rozet');
  const kes = (a, c) => a.left < c.right && c.left < a.right && a.top < c.bottom && c.top < a.bottom;
  const metin = [...b.children].map(e => e.getBoundingClientRect());
  return {px: parseFloat(o.style.getPropertyValue('--metin')), sh: o.scrollHeight, ch: o.clientHeight,
          carpisma: [...ust].some(u => metin.some(m => kes(m, u.getBoundingClientRect())))}; }"""


def pazar_verisi(ornek):
    """yorum.html ve yorum-reels.html için veri (bot/main.py → yorum_hazirla ile aynı alanlar, yapay zekâ çağrılmaz)."""
    vadeler = []
    for v in yorum.VADELER:
        k = v["anahtar"]
        g, o_, d = ornek["yuzde"][k]
        onceki = ornek["onceki"]
        vadeler.append({**v, "etiket": "Son 4 hafta" if k == "kisa" else "Son 3 ay", "not": "", "yorum": ornek[k],
                        "onceki": ({"yon": onceki[k][0], "guc": onceki[k][1], "tarih_metni": onceki["tarih"]}
                                   if onceki and k in onceki else None),
                        "hucreler": [{"ad": ad, "deg": main.degisim(1 + y / 100, 1)}
                                     for ad, y in (("Gram gümüş", g), ("Ons gümüş", o_), ("Dolar/TL", d))]})
    haberler = [{"konu": k, "baslik": yorum.HABER_KONU_BASLIK.get(k, k.upper()), "metin": m, "kaynak": kay}
                for k, m, kay in ornek["haberler"]]
    v = {"tarih": "9 Kasım 2026", "gun": "Pazar", "gram": "84,88", "gram_deg": main.degisim(1.0365, 1),
         "veri_ani": "9 Kasım Pazartesi 19:55", "veri_tarihi": "09.11.2026", "kur_tarihi_tam": "09.11.2026",
         "vadeler": vadeler, "hesap": "@gunlukgumus", "dayanak": "Fiyat ve kur verileri + haftanın haberleri",
         "kaynak_metal": main.KAYNAK_METAL, "baslik": yorum.vade_basligi(yorum.VADELER), "haberler": haberler,
         "hafta_araligi": "9–13 Kasım"}
    v["sayfa_sayisi"] = len(vadeler) + 2
    return v


def olc_html(sayfa, html, betik, once=None):
    gecici = main.SABLONLAR / "_kucukme_pazar.html"
    gecici.write_text(html, encoding="utf-8")
    try:
        sayfa.goto(gecici.as_uri())
        sayfa.evaluate("document.fonts.ready")
        sayfa.wait_for_timeout(300)
        if once:
            sayfa.evaluate(once)
            sayfa.wait_for_timeout(150)
        return sayfa.evaluate(betik)
    finally:
        gecici.unlink(missing_ok=True)


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

    # 4) Pazar yorumu: yayımlanmış iki yorumun metinleriyle yazı boyu ve taşma
    for ad, ornek, kay_alt, reels_alt in (("8 Kas", PAZAR_8KAS, (42, 42, 42), (46, 46, 46)),
                                         ("9 Kas", PAZAR_9KAS, (36, 42, 42), (38, 46, 46))):
        v = pazar_verisi(ornek)
        for s_ in range(1, v["sayfa_sayisi"]):
            sayfa.set_viewport_size({"width": 1080, "height": 1350})
            html = ENV.get_template("yorum.html").render(**{**v, "sayfa": s_, "toplam": v["sayfa_sayisi"]})
            o = olc_html(sayfa, html, PAZAR_KAY_OLC)
            esit(f"pazar {ad} kaydırmalı {s_ + 1}: en az {kay_alt[s_ - 1]} px", o["px"] >= kay_alt[s_ - 1], str(o))
            esit(f"pazar {ad} kaydırmalı {s_ + 1}: taşma yok", o["sh"] <= o["ch"] + 1, str(o))
        sayfa.set_viewport_size({"width": 1080, "height": 1920})
        for sesli in (False, True):
            sureler = [main.YORUM_REELS_SAHNELER[0]] * 3 + [main.YORUM_REELS_HABER_SN] + ([4] if sesli else [])
            html = ENV.get_template("yorum-reels.html").render(**{**v, "sahne_sureleri": sureler, "sesli": sesli})
            bas = 0
            for i, sn in enumerate(sureler[:4]):
                if i:
                    o = olc_html(sayfa, html, PAZAR_REELS_OLC, f"window.kare({bas + sn - 0.5})")
                    ek = f"pazar {ad} Reels{' sesli' if sesli else ''} sahne {i + 1}:"
                    esit(f"{ek} en az {reels_alt[i - 1]} px", o["px"] >= reels_alt[i - 1], str(o))
                    esit(f"{ek} taşma yok", o["sh"] <= o["ch"] + 1, str(o))
                    esit(f"{ek} üst şeride binmiyor", not o["carpisma"], str(o))
                bas += sn
        sayfa.set_viewport_size({"width": 1080, "height": 1920})
    tarayici.close()

if hatalar:
    print("\n".join(hatalar[:40]))
    print(f"test_kucukme: {len(hatalar)} / {sayac} sınama BAŞARISIZ")
    sys.exit(1)
print(f"test_kucukme: {sayac} sınama geçti")
