"""Bilgi sayfası: Instagram biyografisindeki bağlantının açtığı tek sayfalık site.

Kullanım (iş akışı her paylaşımda çağırır, hazirla'dan sonra):
  python bot/sayfa.py --cikti site [--ornek]

site/index.html'i (önceki sade dosya listesinin yerine) son fiyatlar, gram ↔ TL hesap makinesi,
son günlerin tablosu ve grafiği, hesaplama yöntemi, yayımlanmış Gümüş rehberi bölümleri ve
kaynaklarla yeniden yazar. Ayrıca WhatsApp/Instagram bağlantı önizlemesi için og.png (1200×630),
fontlar ve sitemap.xml üretir. GitHub Pages her yayında siteyi baştan kurduğu için sayfa her
çalıştırmada yeniden üretilir.

Fiyatlar veri/gecmis.json kayıtlarından gelir (hafta içi her paylaşımın değeri); MetalCharts
isteği harcanmaz. Sayfa çerez ve dış istek kullanmaz (yazı tipleri de sitenin içinde).
Başarısız olursa yalnızca uyarı verir; paylaşım etkilenmez.
"""
import argparse
import os
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi  # noqa: E402
import main as bot  # noqa: E402

GRAFIK_GUN = 30        # grafikteki en fazla iş günü
TABLO_GUN = 10         # tablodaki en fazla iş günü
REHBER_SAATI = (13, 45)  # rehber bölümü o gün bu saatten sonra sayfaya girer (~14:00 paylaşımı)
TL_MIKTARLAR = [1000, 5000, 10000, 50000]
GRAM_MIKTARLAR = [(1, "1 gram"), (10, "10 gram"), (100, "100 gram"), (1000, "1 kilogram")]


def site_adresi():
    """GitHub Pages adresi: SAYFA_URL ya da <sahip>.github.io/<depo>/."""
    url = os.environ.get("SAYFA_URL", "").strip()
    if not url:
        depo = os.environ.get("GITHUB_REPOSITORY", "ridvancoskun1975-cpu/gumus-bot")
        sahip, ad = depo.split("/", 1)
        url = f"https://{sahip.lower()}.github.io/{ad}/"
    return url.rstrip("/") + "/"


def _tarih(gun, saat=None):
    metin = f"{gun.day} {bot.AYLAR[gun.month - 1]} {gun.year} {bot.GUNLER[gun.weekday()]}"
    return f"{metin} {saat}" if saat else metin


def _kisa_tarih(gun):
    return f"{gun.day} {bot.AYLAR[gun.month - 1]}"


def ornek_gecmis():
    """Yerel deneme için 22 iş günlük örnek kayıt."""
    import math
    kayit, gun, i = {}, date(2026, 9, 14), 0
    while len(kayit) < 22:
        if gun.weekday() < 5:
            gumus = 64.2 + 1.6 * math.sin(i / 3.1) + 0.09 * i
            altin = gumus * (66.6 - 0.04 * i)
            dolar = 48.95 + 0.017 * i
            kayit[gun.isoformat()] = {"saat": "20:00", "gumus": gumus, "altin": altin, "dolar": dolar,
                                      "kur_tarihi": gun.isoformat(), "gram": gumus * dolar / bot.ONS_GRAM}
            i += 1
        gun += timedelta(days=1)
    return kayit


def _grafik(kayitlar):
    """Son günlerin gram fiyatı: SVG çizgisi için noktalar (en az 3 gün)."""
    secilen = kayitlar[-GRAFIK_GUN:]
    if len(secilen) < 3:
        return None
    gen, yuk, ust, alt, yan = 400, 170, 24, 30, 6   # telefonda ~1:1 ölçekte görünür
    degerler = [k["gram"] for _, k in secilen]
    en_az, en_cok = min(degerler), max(degerler)
    aralik = (en_cok - en_az) or 1
    adim = (gen - 2 * yan) / (len(secilen) - 1)

    def y(d):
        return round(ust + (en_cok - d) / aralik * (yuk - ust - alt), 1)

    noktalar = [(round(yan + i * adim, 1), y(k["gram"])) for i, (_, k) in enumerate(secilen)]
    cizgi = " ".join(f"{x},{yy}" for x, yy in noktalar)
    alan = f"{noktalar[0][0]},{yuk - alt} {cizgi} {noktalar[-1][0]},{yuk - alt}"
    i_cok, i_az = degerler.index(en_cok), degerler.index(en_az)
    return {
        "gen": gen, "yuk": yuk, "cizgi": cizgi, "alan": alan, "taban": yuk - alt,
        "son": noktalar[-1],
        "en_cok": {"x": noktalar[i_cok][0], "y": noktalar[i_cok][1], "deger": bot.tr_sayi(en_cok)},
        "en_az": {"x": noktalar[i_az][0], "y": noktalar[i_az][1], "deger": bot.tr_sayi(en_az)},
        "ilk_gun": _kisa_tarih(secilen[0][0]), "son_gun": _kisa_tarih(secilen[-1][0]),
        "gun_sayisi": len(secilen),
        "yon": "artis" if degerler[-1] >= degerler[0] else "dusus",
        "aciklama": (f"Son {len(secilen)} iş gününde gram gümüş: en yüksek {bot.tr_sayi(en_cok)} ₺, "
                     f"en düşük {bot.tr_sayi(en_az)} ₺, son {bot.tr_sayi(degerler[-1])} ₺"),
    }


def _rehber(simdi):
    """Instagram'da yayımlanmış rehber bölümleri (yeniden eskiye) ve sıradaki bölüm."""
    yayimlanan, siradaki = [], None
    bugun = simdi.date()
    saat_gecti = (simdi.hour, simdi.minute) >= REHBER_SAATI
    for gun_metni, no in sorted(bilgi.takvim().items()):
        gun = date.fromisoformat(gun_metni)
        if gun < bugun or (gun == bugun and saat_gecti):
            b = bilgi.BOLUMLER[no - 1]
            yayimlanan.append({"no": no, "tarih": _kisa_tarih(gun), "baslik": b["baslik"], "alt": b["alt"],
                               "sayfalar": b["sayfalar"]})
        elif siradaki is None:
            siradaki = {"no": no, "baslik": bilgi.BOLUMLER[no - 1]["baslik"], "tarih": _tarih(gun)}
    return list(reversed(yayimlanan)), siradaki


def veri_hazirla(gecmis, simdi=None):
    simdi = simdi or datetime.now(bot.TR_SAAT)
    kayitlar = sorted((date.fromisoformat(g), k) for g, k in gecmis.items())
    if not kayitlar:
        raise bot.VeriYok("Henüz fiyat kaydı yok; bilgi sayfası üretilmedi.")
    gun, son = kayitlar[-1]
    once = kayitlar[-2][1] if len(kayitlar) > 1 else None
    gram, dolar, parite = son["gram"], son["dolar"], son["altin"] / son["gumus"]
    kur_gunu = date.fromisoformat(son["kur_tarihi"])

    tablo = []
    for i in range(len(kayitlar) - 1, max(len(kayitlar) - 1 - TABLO_GUN, -1), -1):
        g, k = kayitlar[i]
        d = bot.degisim(k["gram"], kayitlar[i - 1][1]["gram"]) if i > 0 else None
        tablo.append({"tarih": f"{g.day:02d}.{g.month:02d}", "gun": bot.GUN_KISA[g.weekday()],
                      "saat": k.get("saat", ""), "gram": bot.tr_sayi(k["gram"]), "deg": d})

    rehber, siradaki = _rehber(simdi)
    hesap = bot.hesap_adi() or "@gumusagtr"
    url = site_adresi()
    guncelleme = _tarih(gun, son.get("saat"))
    gram_deg = bot.degisim(gram, once["gram"]) if once else None
    paylasim_metni = f"Gram gümüş fiyatı, hesap makinesi ve son günler: {url}"
    return {
        "url": url,
        "surum": simdi.strftime("%Y%m%d%H%M"),
        "hesap": hesap,
        "instagram": f"https://www.instagram.com/{hesap.lstrip('@')}/",
        "whatsapp": "https://wa.me/?text=" + quote(paylasim_metni),
        "guncelleme": guncelleme,
        "guncelleme_kisa": f"{_kisa_tarih(gun)} {son.get('saat', '')}".strip(),
        "gram": bot.tr_sayi(gram),
        "gram_sayi": round(gram, 6),
        "gram_deg": gram_deg,
        "once_gram": bot.tr_sayi(once["gram"]) if once else None,
        "ons": bot.tr_sayi(son["gumus"]),
        "dolar": bot.tr_sayi(dolar),
        "dolar_deg": bot.degisim(dolar, once["dolar"]) if once else None,
        "kur_tarihi": _kisa_tarih(kur_gunu),
        "parite": bot.tr_sayi(parite, 1),
        "parite_deg": bot.degisim(parite, once["altin"] / once["gumus"]) if once else None,
        "tl_tablo": [{"tl": bot.tr_sayi(t, 0), "gram": bot.tr_sayi(t / gram)} for t in TL_MIKTARLAR],
        "gram_tablo": [{"ad": ad, "tl": bot.tr_sayi(g * gram)} for g, ad in GRAM_MIKTARLAR],
        "tablo": tablo,
        "grafik": _grafik(kayitlar),
        "ilk_kayit": _tarih(kayitlar[0][0]),
        "rehber": rehber,
        "siradaki": siradaki,
        "yil": simdi.year,
    }


def uret(cikti, gecmis, simdi=None):
    from jinja2 import Environment, FileSystemLoader

    v = veri_hazirla(gecmis, simdi)
    env = Environment(loader=FileSystemLoader(str(bot.SABLONLAR)), autoescape=True)
    (cikti / "index.html").write_text(env.get_template("sayfa.html").render(**v), encoding="utf-8")

    fontlar = cikti / "fonts"
    fontlar.mkdir(exist_ok=True)
    for f in (bot.KOK / "assets" / "fonts").iterdir():
        if f.suffix in (".woff2", ".txt"):
            shutil.copy2(f, fontlar / f.name)

    (cikti / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{v["url"]}</loc><lastmod>{(simdi or datetime.now(bot.TR_SAAT)).date().isoformat()}</lastmod>'
        '<changefreq>daily</changefreq></url></urlset>\n', encoding="utf-8")

    # Bağlantı önizlemesi (WhatsApp, Instagram DM): güncel fiyatlı görsel
    try:
        bot.gorsel_uret("sayfa-og", v, cikti / "og.png")
    except Exception as e:
        print(f"::warning::Bağlantı önizleme görseli üretilemedi: {e}")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", default="site")
    ap.add_argument("--ornek", action="store_true", help="Örnek kayıtlarla üret (yerel deneme)")
    a = ap.parse_args()
    cikti = Path(a.cikti) if os.path.isabs(a.cikti) else bot.KOK / a.cikti
    cikti.mkdir(parents=True, exist_ok=True)
    try:
        v = uret(cikti, ornek_gecmis() if a.ornek else bot.gecmis_oku())
    except bot.VeriYok as e:
        print(f"::warning::{e}")
        return
    except Exception as e:   # sayfa paylaşımı hiçbir zaman durdurmasın
        print(f"::warning::Bilgi sayfası üretilemedi: {type(e).__name__}: {e}")
        return
    print(f"Bilgi sayfası üretildi: {v['url']} (gram {v['gram']} ₺, {v['guncelleme']}; "
          f"rehber {len(v['rehber'])} bölüm)")


if __name__ == "__main__":
    main()
