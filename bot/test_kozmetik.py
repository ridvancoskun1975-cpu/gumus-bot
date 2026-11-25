# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Kozmetik dokunuşların sınaması (bot/kozmetik.py; Rıdvan, 25 Kasım 2026).

1) Ayarlar varsayılan kapalı; kapalıyken veriye hiçbir alan eklenmez (görsel bugünküyle aynı). KOZMETIK_ZORLA yalnız
   --ornek ile işler. 2) Tonlar bugünkü vurgudan koyu, zeminler bugünkü zeminden açık değil. 3) Her seçenek ve hepsi
   birlikte açıkken sabah Reels'i, akşam özeti (gün içi, kart, balon, manşet) ve kapakta: hiçbir yazı yer değiştirmez
   ya da küçülmez (her yazının kutusu kapalıdakiyle aynı), çerçeve taşmaz, her yazının zeminine karşı kontrastı
   kapalıdakinden düşük değil, mevsim işareti hiçbir yazıya, gorile ya da kutuya binmez (balonlu paylaşımda çıkmaz).
Çalıştırma: python bot/test_kozmetik.py (Chromium; CHROME_YOLU varsa o kullanılır)."""
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402
import insan  # noqa: E402
import baslik  # noqa: E402
import kozmetik  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

hatalar, sayac = [], 0


def bak(kosul, ad):
    global sayac
    sayac += 1
    if not kosul:
        hatalar.append(ad)


# 1) Varsayılan kapalı, kapalıyken alan yok
bak(not (kozmetik.HAFTA_TONU or kozmetik.MEVSIM_AYRACI or kozmetik.YON_ZEMINI), "ayarlar varsayılan kapalı olmalı")
ORNEK_DEG = {"gram_deg": main.degisim(1.03, 1)}
os.environ.pop("KOZMETIK_ZORLA", None)
for tur in ("reels", "post", "hafta", "ay"):
    bak(kozmetik.sablon_verisi(ORNEK_DEG, tur, date(2026, 12, 1), True) == {}, f"{tur}: kapalıyken alan eklendi")
os.environ["KOZMETIK_ZORLA"] = "ton,mevsim,zemin"
bak(kozmetik.sablon_verisi(ORNEK_DEG, "post", date(2026, 12, 1), False) == {}, "KOZMETIK_ZORLA --ornek olmadan işledi")
bak(kozmetik.sablon_verisi(ORNEK_DEG, "hafta", date(2026, 12, 1), True) == {}, "haftalık özete kozmetik geldi")
bak(kozmetik.sablon_verisi(ORNEK_DEG, "post", date(2026, 12, 1), True)["kozmetik"]["motif"] == "kis", "aralık = kış")
sakin = kozmetik.sablon_verisi({"gram_deg": main.degisim(1.003, 1)}, "post", date(2026, 12, 1), True)["kozmetik"]
bak("zemin" not in sakin["css"], "sakin günde zemin bugünkü gibi kalmalı")
os.environ.pop("KOZMETIK_ZORLA")
bak(sorted(set(kozmetik.MEVSIMLER)) == list(range(1, 13)), "12 ayın mevsimi")

# 2) Renkler: kontrast bugünkünden düşmez
for ad, renk in kozmetik.TONLAR:
    bak(kozmetik.kontrast(renk, kozmetik.ZEMIN) >= kozmetik.kontrast(kozmetik.VURGU, kozmetik.ZEMIN), f"ton {ad} koyu")
for yon, (zemin, _) in kozmetik.ZEMINLER.items():
    bak(all(int(zemin[i:i + 2], 16) <= int(kozmetik.ZEMIN[i:i + 2], 16) for i in (1, 3, 5)), f"zemin {yon} kanalları")
    for yazi in ("#EDEFF2", "#9AA3AE", kozmetik.VURGU, "#5BC98C", "#F07A6A"):
        bak(kozmetik.kontrast(yazi, zemin) >= kozmetik.kontrast(yazi, kozmetik.ZEMIN), f"zemin {yon} / {yazi}")

# 3) Görsel: yerleşim aynı, kontrast düşmez, işaret binmez
ENV = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True)
GUN = datetime.now(main.TR_SAAT).date()
OLC = """() => {
  const sayi = s => (s.match(/[\\d.]+/g) || []).map(Number);
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = c => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const zemin = el => {            // atalardaki arka plan renkleri üst üste (yarı saydamlar dahil)
    const kat = [];
    for (let e = el; e; e = e.parentElement) {
      const c = sayi(getComputedStyle(e).backgroundColor), a = c.length > 3 ? c[3] : 1;
      if (a > 0) { kat.push([c[0], c[1], c[2], a]); if (a >= 1) break; }
    }
    let r = [0, 0, 0];
    for (let i = kat.length - 1; i >= 0; i--) { const k = kat[i]; r = r.map((v, j) => k[j] * k[3] + v * (1 - k[3])); }
    return r;
  };
  const kutu = r => [r.left, r.top, r.width, r.height].map(v => Math.round(v * 2) / 2);
  const yazilar = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    const el = n.parentElement;
    if (!n.textContent.trim() || ['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const rg = document.createRange(); rg.selectNodeContents(n); const r = rg.getBoundingClientRect();
    if (!r.width) continue;
    const y = L(sayi(getComputedStyle(el).color)), z = L(zemin(el));
    yazilar.push({t: n.textContent.trim().slice(0, 30), r: kutu(r), k: (Math.max(y, z) + 0.05) / (Math.min(y, z) + 0.05)});
  }
  const c = document.querySelector('.cerceve'), m = document.querySelector('.mevsim');
  const kutular = ['.maskot', '#goril-balon', '.ag', '#manset', '#gun-baslik', '#not-karti']
    .flatMap(s => [...document.querySelectorAll(s)]).map(e => kutu(e.getBoundingClientRect()));
  return {yazilar, kutular, mevsim: m ? kutu(m.querySelector('svg').getBoundingClientRect()) : null,
          tasma: c ? c.scrollHeight > c.clientHeight + 1 : false, cerceve: c ? kutu(c.getBoundingClientRect()) : null};
}"""


def kesisir(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def olc(sayfa, sablon, veri):
    gecici = main.SABLONLAR / f"_kozmetik_{sablon}.html"
    gecici.write_text(ENV.get_template(f"{sablon}.html").render(**veri), encoding="utf-8")
    try:
        sayfa.goto(gecici.as_uri())
        sayfa.evaluate("document.fonts.ready")
        sayfa.wait_for_timeout(120)
        return sayfa.evaluate(OLC)
    finally:
        gecici.unlink(missing_ok=True)


def veriler():
    """(ad, şablon, veri): sabah Reels'i ve akşam özeti örnekleri (manşet, başlık, gün içi, kartlar, balon)."""
    for senaryo in ("", "goril-uzulen", "goril-sevinen", "goril-istif", "seri", "dusuk"):
        os.environ["ORNEK_SENARYO"] = senaryo
        for tur in ("reels", "post"):
            f = main.ornek_fiyatlar()
            if tur == "post" and senaryo in ("", "goril-istif"):
                f["gun_ici"] = [("10:00", f["gram"] * 1.012), ("13:55", f["gram"] * 0.99), ("19:55", f["gram"])]
            v = main.veri_hazirla(f, "@gunlukgumus", tur)
            v["parite_cumle"] = main.gorsel_parite_cumlesi(v, tur)
            v.update(main.goril_alanlari(v, tur, True))
            v.update({"gunun_notu": None, "goril_balon": None})
            if v.get("ozel"):
                continue
            yield f"{tur} {senaryo or 'düz'}", tur, v
            if v.get("maskot") and v["gram_deg"]["yon"] == "artis":
                yield f"{tur} {senaryo or 'düz'} balon", tur, {**v, "goril_balon": max(
                    (c for cs in insan.BALON.values() for c in cs), key=len)}
    os.environ.pop("ORNEK_SENARYO", None)
    for kart in ("neden", "gecmis", "hesap"):
        f = {"gram": 84.4, "gram_once": 81.5, "parite": 77.4, "parite_once": 76.83, "dolar": 50.26, "dolar_once": 50.23,
             "kur_tarihi": GUN.isoformat(), "gun_ici": [("10:00", 85.1), ("12:35", 84.0), ("19:55", 84.4)]}
        seri, g = {}, GUN
        for x in (81.5, 80.7, 83.1, 79.9, 83.9, 79.1):
            g = baslik.onceki_is_gunu(g)
            seri[g.isoformat()] = x
        f["gecmis_gram"] = seri
        v = main.veri_hazirla(f, "@gunlukgumus", "post")
        v["parite_cumle"] = main.gorsel_parite_cumlesi(v, "post")
        v.update(main.goril_alanlari(v, "post", True))
        v["goril_balon"] = None
        v["gunun_notu"] = ({"tur": "neden", "etiket": "NEDEN YÜKSELDİ?", "metin": "ABD'de beklenenden zayıf istihdam "
                            "verisi faiz indirimi beklentisini güçlendirdi", "alt": insan.NEDEN_NOTU} if kart == "neden"
                           else insan.gecmis_karti(v, seri, "post", GUN, zorla="gecmis", ons=main.bugunku_ons(f))
                           if kart == "gecmis" else insan.hesap_karti(v, seri, "post", GUN, zorla="hesap"))
        yield f"post kart={kart}", "post", v


AYARLAR = {"A ton": "ton", "B mevsim": "mevsim", "C zemin": "zemin", "hepsi": "ton,mevsim,zemin"}
GUNLER = [date(2026, 11, 25), date(2026, 12, 2), date(2026, 12, 9), date(2026, 12, 16), date(2027, 4, 7), date(2027, 7, 7)]

with sync_playwright() as p:
    tarayici = p.chromium.launch(**({"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}))
    sayfa = tarayici.new_page(viewport={"width": 1080, "height": 1920})
    for ad, sablon, v in veriler():
        kapali = olc(sayfa, sablon, v)
        kapak_v = {**v, **main.kapak_verisi(sablon, v)}
        kapak_kapali = olc(sayfa, "kapak", kapak_v)
        for ayar_ad, ayar in AYARLAR.items():
            for gun in (GUNLER if ayar_ad == "hepsi" else GUNLER[:1]):
                os.environ["KOZMETIK_ZORLA"], os.environ["KOZMETIK_GUN"] = ayar, gun.isoformat()
                ek = main.kozmetik_alanlari(v, sablon, True)
                sakin_gun = ayar == "zemin" and abs(v["gram_deg"]["yuzde"]) < kozmetik.SAKIN_ESIK
                bak(bool(ek) != sakin_gun, f"{ad} {ayar_ad}: alan gelmedi / sakin günde geldi")
                for s, eski in ((sablon, kapali), ("kapak", kapak_kapali)):
                    yeni = olc(sayfa, s, {**(v if s == sablon else kapak_v), **ek})
                    yer = f"{ad} [{s}] {ayar_ad} {gun}"
                    bak([y["r"] for y in yeni["yazilar"]] == [y["r"] for y in eski["yazilar"]], f"{yer}: yazı yer değiştirdi")
                    bak(yeni["cerceve"] == eski["cerceve"] and not yeni["tasma"], f"{yer}: çerçeve değişti / taştı")
                    for a, b in zip(eski["yazilar"], yeni["yazilar"]):
                        bak(b["k"] >= a["k"] - 1e-6, f"{yer}: '{a['t']}' kontrast {a['k']:.2f} → {b['k']:.2f}")
                    if yeni["mevsim"]:
                        m = yeni["mevsim"]
                        binen = [y["t"] for y in yeni["yazilar"] if kesisir(m, y["r"])] + \
                                [str(k) for k in yeni["kutular"] if kesisir(m, k)]
                        bak(not binen, f"{yer}: mevsim işareti biniyor: {binen}")
                    bak(bool(yeni["mevsim"]) == (s != "kapak" and "mevsim" in ayar and not v.get("goril_balon")),
                        f"{yer}: mevsim işareti yeri")
    tarayici.close()
os.environ.pop("KOZMETIK_ZORLA", None)
os.environ.pop("KOZMETIK_GUN", None)

if hatalar:
    print("\n".join(hatalar[:40]))
    print(f"test_kozmetik: {len(hatalar)} / {sayac} sınama BAŞARISIZ")
    sys.exit(1)
print(f"test_kozmetik: {sayac} sınama geçti")
