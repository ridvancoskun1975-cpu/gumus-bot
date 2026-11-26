# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Kozmetik dokunuşların sınaması (bot/kozmetik.py; Rıdvan, 25–26 Kasım 2026).

1) Ayarlar varsayılan kapalı; kapalıyken veriye hiçbir alan eklenmez (görsel bugünküyle aynı). KOZMETIK_ZORLA yalnız
   --ornek ile işler. Ton haftaya göre 4 ton arasında döner. 2) Her seçenek ve birlikte açıkken sabah
   Reels'i, akşam özeti (gün içi, kart, balon, manşet) ve kapakta: hiçbir yazı yer değiştirmez ya da küçülmez, çerçeve
   taşmaz; her yazının kontrastı gerçek piksellerden (ışıma dahil, yazının kutusundaki en kötü zemin pikseline karşı)
   ölçülür: gövde yazısı en az 7:1, küçük (< 28 px), soluk ve renkli (artış / düşüş) yazı en az 4,5:1. Yalnız ton
   açıkken hiçbir yazının kontrastı bugünkünden düşmez.
Çalıştırma: python bot/test_kozmetik.py (Chromium; CHROME_YOLU varsa o kullanılır). `olc` ve `veriler` önizleme ve
kontrast raporunda da kullanılır."""
import base64
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

ENV = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True)
GUN = datetime.now(main.TR_SAAT).date()
GOVDE_SINIR, KUCUK_SINIR, KUCUK_PX = 7.0, 4.5, 28
YAZILAR = """() => {
  const kutu = r => [r.left, r.top, r.width, r.height].map(v => Math.round(v * 2) / 2);
  const sonuc = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    const el = n.parentElement;
    if (!n.textContent.trim() || ['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const rg = document.createRange(); rg.selectNodeContents(n); const r = rg.getBoundingClientRect();
    if (!r.width) continue;
    const s = getComputedStyle(el);
    sonuc.push({t: n.textContent.trim().slice(0, 34), r: kutu(r), renk: s.color, px: parseFloat(s.fontSize)});
  }
  const c = document.querySelector('.cerceve');
  return {yazilar: sonuc, tasma: c ? c.scrollHeight > c.clientHeight + 1 : false, cerceve: c ? kutu(c.getBoundingClientRect()) : null};
}"""
GIZLE = ("*{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}"
         "svg{visibility:hidden!important}")
PIKSEL = """async ([resim, yazilar]) => {
  const img = new Image(); img.src = 'data:image/png;base64,' + resim; await img.decode();
  const cv = document.createElement('canvas'); cv.width = img.width; cv.height = img.height;
  const g = cv.getContext('2d'); g.drawImage(img, 0, 0); const d = g.getImageData(0, 0, img.width, img.height).data;
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = (r, gg, b) => 0.2126 * lin(r) + 0.7152 * lin(gg) + 0.0722 * lin(b);
  return yazilar.map(y => {
    const c = (y.renk.match(/[\\d.]+/g) || []).map(Number), ly = L(c[0], c[1], c[2]);
    let en = 99;
    const [x0, y0, w, h] = y.r;
    for (let yy = Math.max(0, Math.floor(y0)); yy < Math.min(img.height, y0 + h); yy += 2)
      for (let xx = Math.max(0, Math.floor(x0)); xx < Math.min(img.width, x0 + w); xx += 2) {
        const i = (yy * img.width + xx) * 4, lz = L(d[i], d[i + 1], d[i + 2]);
        en = Math.min(en, (Math.max(ly, lz) + 0.05) / (Math.min(ly, lz) + 0.05));
      }
    return en;
  });
}"""


def olc(sayfa, sablon, veri):
    """Yazıların kutuları, renkleri ve gerçek piksel zeminine karşı en kötü kontrastı (k)."""
    gecici = main.SABLONLAR / f"_kozmetik_{sablon}.html"
    gecici.write_text(ENV.get_template(f"{sablon}.html").render(**veri), encoding="utf-8")
    try:
        sayfa.goto(gecici.as_uri())
        sayfa.evaluate("document.fonts.ready")
        sayfa.wait_for_timeout(120)
        o = sayfa.evaluate(YAZILAR)
        sayfa.add_style_tag(content=GIZLE)
        sayfa.wait_for_timeout(30)
        resim = base64.b64encode(sayfa.screenshot()).decode()
        for y, k in zip(o["yazilar"], sayfa.evaluate(PIKSEL, [resim, o["yazilar"]])):
            y["k"] = k
        return o
    finally:
        gecici.unlink(missing_ok=True)


def sinir(y):
    """Yazının kontrast alt sınırı: gövde 7, küçük / soluk / renkli 4,5."""
    soluk = y["renk"] in ("rgb(154, 163, 174)", "rgb(91, 201, 140)", "rgb(240, 122, 106)")
    return KUCUK_SINIR if (soluk or y["px"] < KUCUK_PX) else GOVDE_SINIR


def veriler():
    """(ad, şablon, veri): sabah Reels'i ve akşam özeti örnekleri (manşet, başlık, gün içi, kartlar, balon)."""
    for senaryo in ("", "goril-uzulen", "goril-sevinen", "goril-istif", "seri", "dusuk"):
        os.environ["ORNEK_SENARYO"] = senaryo
        for tur in ("reels", "post"):
            f = main.ornek_fiyatlar()
            if tur == "post" and senaryo in ("", "goril-istif", "goril-uzulen"):
                f["gun_ici"] = [("10:00", f["gram"] * 1.012), ("13:55", f["gram"] * 0.99), ("19:55", f["gram"])]
            v = main.veri_hazirla(f, "@gunlukgumus", tur)
            v["parite_cumle"] = main.gorsel_parite_cumlesi(v, tur)
            v.update(main.goril_alanlari(v, tur, True))
            v.update({"gunun_notu": None, "goril_balon": None})
            if v.get("ozel"):
                continue
            yield f"{tur} {senaryo or 'düz'}", tur, v
            if v.get("maskot") and v["gram_deg"]["yon"] == "artis" and not v.get("buyuk_hareket"):   # manşette balon yok
                yield f"{tur} {senaryo or 'düz'} balon", tur, {**v, "goril_balon": max(
                    (c for cs in insan.BALON.values() for c in cs), key=len)}
    os.environ.pop("ORNEK_SENARYO", None)
    for kart, (gram, once) in (("neden", (84.4, 81.5)), ("gecmis", (79.2, 81.5)), ("hesap", (84.4, 81.5))):
        f = {"gram": gram, "gram_once": once, "parite": 77.4, "parite_once": 76.83, "dolar": 50.26, "dolar_once": 50.23,
             "kur_tarihi": GUN.isoformat(), "gun_ici": [("10:00", gram * 1.01), ("12:35", gram * 0.99), ("19:55", gram)]}
        seri, g = {}, GUN
        for x in (once, 80.7, 83.1, 79.9, 83.9, 79.1):
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


AYARLAR = {"A ton": "ton", "C2": "zemin2", "C3": "zemin3", "A+C2": "ton,zemin2", "A+C3": "ton,zemin3"}

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    hatalar, sayac = [], 0

    def bak(kosul, ad):
        global sayac
        sayac += 1
        if not kosul:
            hatalar.append(ad)

    # 1) Varsayılan kapalı, kapalıyken alan yok, ton seçimi
    bak(not (kozmetik.HAFTA_TONU or kozmetik.YON_ZEMINI), "ayarlar varsayılan kapalı olmalı")
    bak(not hasattr(kozmetik, "MEVSIM_AYRACI"), "mevsim ayracı kaldırıldı (Rıdvan, 26 Kasım 2026)")
    D = {"gram_deg": main.degisim(1.03, 1)}
    os.environ.pop("KOZMETIK_ZORLA", None)
    for tur in ("reels", "post", "hafta", "ay"):
        bak(kozmetik.sablon_verisi(D, tur, date(2026, 12, 1), True) == {}, f"{tur}: kapalıyken alan eklendi")
    os.environ["KOZMETIK_ZORLA"] = "ton,zemin3"
    bak(kozmetik.sablon_verisi(D, "post", date(2026, 12, 1), False) == {}, "KOZMETIK_ZORLA --ornek olmadan işledi")
    bak(kozmetik.sablon_verisi(D, "hafta", date(2026, 12, 1), True) == {}, "haftalık özete kozmetik geldi")
    sakin = kozmetik.sablon_verisi({"gram_deg": main.degisim(1.003, 1)}, "post", date(2026, 12, 1), True)["kozmetik"]
    bak("zemin" not in sakin["css"] and "vurgu" in sakin["css"], "sakin günde zemin bugünkü gibi")
    os.environ["KOZMETIK_ZORLA"] = "ton"
    donen = [kozmetik.sablon_verisi(D, "post", date(2026, 11, 2 + 7 * i), True)["kozmetik"]["css"]["vurgu"]
             for i in range(4)]
    bak(sorted(donen) == sorted(r for _, r in kozmetik.TONLAR), "art arda 4 hafta 4 farklı ton")
    os.environ.pop("KOZMETIK_ZORLA")
    for ad, renk in kozmetik.TONLAR:
        bak(kozmetik.kontrast(renk, kozmetik.ZEMIN) >= kozmetik.kontrast(kozmetik.VURGU, kozmetik.ZEMIN), f"ton {ad}")
    for duzey, yonler in kozmetik.ZEMINLER.items():
        bak(set(yonler) == {"artis", "dusus"}, f"C{duzey}: yalnız artış / düşüş (kırmızı zemin yok)")

    # 2) Görsel
    with sync_playwright() as p:
        tarayici = p.chromium.launch(**({"executable_path": os.environ["CHROME_YOLU"]}
                                        if os.environ.get("CHROME_YOLU") else {}))
        sayfa = tarayici.new_page(viewport={"width": 1080, "height": 1920})
        for ad, sablon, v in veriler():
            kapak_v = {**v, **main.kapak_verisi(sablon, v)}
            kapali = {s: olc(sayfa, s, x) for s, x in ((sablon, v), ("kapak", kapak_v))}
            for ayar_ad, ayar in AYARLAR.items():
                os.environ["KOZMETIK_ZORLA"] = ayar
                ek = main.kozmetik_alanlari(v, sablon, True)
                sakin_gun = abs(v["gram_deg"]["yuzde"]) < kozmetik.SAKIN_ESIK
                bak(bool(ek) != (sakin_gun and "ton" not in ayar), f"{ad} {ayar_ad}: alan")
                for s, x in ((sablon, v), ("kapak", kapak_v)):
                    eski_o, yeni = kapali[s], olc(sayfa, s, {**x, **ek})
                    yer = f"{ad} [{s}] {ayar_ad}"
                    bak([y["r"] for y in yeni["yazilar"]] == [y["r"] for y in eski_o["yazilar"]], f"{yer}: yazı yer değiştirdi")
                    bak(yeni["cerceve"] == eski_o["cerceve"] and not yeni["tasma"], f"{yer}: çerçeve değişti / taştı")
                    for a, b in zip(eski_o["yazilar"], yeni["yazilar"]):
                        bak(b["k"] >= min(sinir(b), a["k"]) - 0.01, f"{yer}: '{b['t']}' {a['k']:.2f} → {b['k']:.2f} < {sinir(b)}")
                        if ayar == "ton":
                            bak(b["k"] >= a["k"] - 0.01, f"{yer}: '{b['t']}' kontrast düştü {a['k']:.2f} → {b['k']:.2f}")
        tarayici.close()
    os.environ.pop("KOZMETIK_ZORLA", None)

    if hatalar:
        print("\n".join(hatalar[:40]))
        print(f"test_kozmetik: {len(hatalar)} / {sayac} sınama BAŞARISIZ")
        sys.exit(1)
    print(f"test_kozmetik: {sayac} sınama geçti")
