"""Bilgi sayfası: Instagram biyografisindeki bağlantının açtığı tek sayfalık site.

Kullanım (iş akışı her paylaşımda çağırır, hazirla'dan sonra):
  python bot/sayfa.py --cikti site [--ornek]

site/index.html'i son fiyatlar, gram ↔ TL hesap makinesi, son günlerin tablosu ve grafiği, hesaplama
yöntemi, paylaşım takvimi ve kaynaklarla yeniden yazar. Gümüş rehberi ayrı sayfadadır (site/rehber/):
yalnızca başlıklar görünür, başlığa dokununca açılır; Instagram'da yayımlanmış bölümler ve ayrıntılı
bilgi (bot/ayrintili.py). Ana sayfa şişmesin diye rehberden orada yalnızca bir bağlantı kartı var
(Rıdvan, 14 Ekim 2026). Ayrıca WhatsApp/Instagram bağlantı önizlemesi için og.png (1200×630),
fontlar, sitemap.xml, robots.txt ve Google Search Console doğrulama dosyasını üretir. GitHub Pages her yayında siteyi baştan kurduğu için sayfa her
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
import ayrintili  # noqa: E402
import program as prg  # noqa: E402
import dar_sayfalar  # noqa: E402

GRAFIK_GUN = 30        # grafikteki en fazla iş günü
TABLO_GUN = 10         # tablodaki en fazla iş günü
REHBER_SAATI = (13, 45)  # rehber bölümü o gün bu saatten sonra sayfaya girer (~14:00 paylaşımı)
# Google Search Console sahiplik doğrulaması (URL ön eki mülkü, HTML dosyası yöntemi; 15 Ekim 2026).
# Site her yayında baştan kurulduğu için dosya her çalıştırmada yazılır; kaldırılırsa doğrulama düşer.
GOOGLE_DOGRULAMA = "googleade97aa5989bb9eb.html"
# Sitede istifçi goril: tanıtım kartında ve 404 sayfasında, fiyattan bağımsız tek hâl
# (Rıdvan, 19 Ekim 2026 "2 ama istifçi goril"). False yapılırsa site eskisi gibi gorilsiz üretilir.
SITE_GORIL = True
# Son pazar analizi düğmesi (Rıdvan, 18 Ekim 2026 "2 uygun"): pazar yorumunun açıklaması bununla başlar
# (bot/yorum.py → aciklama()); Instagram'daki son kaydırmalı yorum bu başlıkla bulunur.
PAZAR_BASLIK = "Haftalık gümüş görünümü | Üst düzey yapay zekâ yorumu"
# 19 Ekim 2026 (Rıdvan: "ikisini de değiştir") öncesi yorumların başlığı; düğme eski yorumu da bulsun.
ESKI_PAZAR_BASLIK = "Haftalık gümüş görünümü | Yapay zekâ yorumu"


# Sitenin kendi alan adı (Rıdvan, 19 Ekim 2026: GoDaddy'den alındı, "tam bağlama başla"). GitHub Pages'te özel
# alan adı olarak tanımlı; eski <sahip>.github.io/<depo>/ adresi kendiliğinden buraya yönlenir. Kanonik adres,
# site haritası, paylaşım önizlemesi ve "WhatsApp'ta paylaş" metni bu adresi kullanır.
ALAN_ADI = "https://gunlukgumus.com/"


def site_adresi():
    """Sitenin adresi: SAYFA_URL (deneme için) ya da ALAN_ADI."""
    url = os.environ.get("SAYFA_URL", "").strip() or ALAN_ADI
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


def _program(simdi, kayit_gunleri):
    """Paylaşım takvimi ve saatler botun gerçek ayarlarından (bot/program.py). Okunamazsa sayfa yine
    üretilir, saat ve takvim içeren yerler gizlenir (yanlış bilgi yazılmasın) ve uyarı çıkar."""
    try:
        return prg.program(simdi, kayit_gunleri, bot.HIKAYE_TURLERI, REHBER_SAATI,
                           getattr(bot, "REHBER_HIKAYE_OTOMATIK", True))
    except Exception as e:
        print(f"::warning::Bilgi sayfası: paylaşım takvimi üretilemedi, takvim gizlendi ({type(e).__name__}: {e})")
        return None


def son_pazar_analizi():
    """Instagram'daki son pazar yorumu: {"url", "tarih"} ya da None. Kaydırmalı gönderi tercih edilir (aynı
    açıklamayla giden Reels yalnız kaydırmalı bulunamazsa). Anahtar yoksa, istek başarısızsa ya da henüz yorum
    yoksa None: düğme çıkmaz, sayfa yine üretilir. Pazar paylaşımı bitince sayfa yeniden kurulur (paylas.yml →
    yayinla), böylece düğme aynı gün yeni yoruma gider."""
    if not os.environ.get("IG_TOKEN"):
        return None
    try:
        cevap = bot._istek("GET", "me/media", fields="caption,media_type,permalink,timestamp", limit=25)
        yorumlar = [m for m in cevap.get("data", []) if (m.get("caption") or "").startswith((PAZAR_BASLIK, ESKI_PAZAR_BASLIK))
                    and m.get("permalink")]
        if not yorumlar:
            return None
        en_yeni = max(m["timestamp"] for m in yorumlar)
        ayni_gun = [m for m in yorumlar if m["timestamp"][:10] == en_yeni[:10]]
        m = next((m for m in ayni_gun if m.get("media_type") == "CAROUSEL_ALBUM"),
                 max(ayni_gun, key=lambda m: m["timestamp"]))
        an = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(bot.TR_SAAT)
        return {"url": m["permalink"], "tarih": _kisa_tarih(an.date())}
    except Exception as e:   # sayfa bu yüzden hiçbir zaman üretilmeden kalmasın
        print(f"::warning::Bilgi sayfası: son pazar analizi bulunamadı, düğme gizlendi ({type(e).__name__}: {e})")
        return None


def _tanitim(program, pazar=None):
    """Google'dan gelen ziyaretçiye ilk temasta hesabın kısa tanıtımı (Rıdvan, 15 Ekim 2026: "benzersiz
    hizmetlerimiz ilk temasta kısaca tanıtılmalı; Instagram hesabını takip etmeye teşvik edici olmalı").
    Saat ve günler elle yazılmaz, botun takviminden (bot/program.py) alınır; takvimde olmayan hizmet
    kartta görünmez. Takvim okunamazsa kart da çıkmaz."""
    if not program:
        return None

    def bul(anahtar):
        return next((s for s in program["satirlar"] if anahtar in s["ne"]), None)

    def gun(s):
        return s["zaman"].split(" ~")[0]

    # Az ve öz (Rıdvan, 15 Ekim 08:46): tek satır. Pazar yapay zekâ yorumu adıyla yer alır (15 Ekim 08:17:
    # "tanıtım kartında şimdi yer almalı"); yorum kapalıysa satırda görünmez.
    satir = [f"{program['guncelleme']} fiyat"]
    haftalik = bul("Haftalık özet")
    if haftalik:
        satir.append(f"{gun(haftalik)} haftalık özet")
    # 15 Ekim 20:18 (Rıdvan, 2. seçenek): "Her gün fiyat, her pazar derin yorum" · "Pazar üst düzey yapay
    # zekâ analizi". "En gelişmiş" ya da "uzman" denmez (doğrulanamaz / yasal metinle çelişir); model adı
    # sitede yazılmaz (Rıdvan 20:27: "riske girmeyelim"). Yorum takvimde yoksa başlık eski hâline döner.
    yorum = bul("yapay zekâ yorumu") if program.get("yorum") else None
    if yorum:
        satir.append(f"{gun(yorum)} üst düzey yapay zekâ analizi")
    baslik = "Her gün fiyat, her pazar derin yorum" if yorum else "Gümüşü her gün saatinde takip edin"
    return {"baslik": baslik, "satir": satir, "pazar": pazar if yorum else None}


def _ayrintili(simdi):
    """Ayrıntılı rehber (bot/ayrintili.py). Gözden geçirme tarihi geçtiyse uyarı verir ve sayfada not gösterir."""
    eski = simdi.date() > ayrintili.SONRAKI_GOZDEN_GECIRME
    if eski:
        print(f"::warning::Bilgi sayfası: ayrıntılı rehberin rakamları {ayrintili.SONRAKI_GOZDEN_GECIRME} itibarıyla "
              "gözden geçirilmeli (yeni World Silver Survey / USGS raporları); bot/ayrintili.py")
    g = ayrintili.GOZDEN_GECIRME
    return {"bolumler": ayrintili.BOLUMLER, "eski": eski, "kaynak_donemi": ayrintili.KAYNAK_DONEMI,
            "gozden_gecirme": f"{g.day} {bot.AYLAR[g.month - 1]} {g.year}"}


def _kaynaklar():
    """Kaynak satırları botun kullandığı adreslerden (kaynak değişirse sayfa da değişsin)."""
    from urllib.parse import urlparse
    metal = urlparse(bot.METALCHARTS_URL).hostname or ""
    metal_site = metal[4:] if metal.startswith("api.") else metal
    kur = urlparse(bot.KUR_URL)
    kur_site = (kur.hostname or "")
    kur_site = kur_site[4:] if kur_site.startswith("api.") else kur_site
    ecb = "/providers/ecb/" in kur.path
    if "metalcharts" not in metal_site or not ecb:
        print("::warning::Bilgi sayfası: kaynak adresleri beklenenden farklı; kaynaklar bölümünü gözden geçir "
              f"(metal: {metal_site}, kur: {bot.KUR_URL})")
    return {"metal_ad": bot.KAYNAK_METAL, "metal_url": f"https://{metal_site}", "kur_ecb": ecb,
            "kur_ad": kur_site.split(".")[0].capitalize(), "kur_url": f"https://{kur_site}"}


def _rehber(simdi):
    """Instagram'da yayımlanmış rehber bölümleri (#1'den başlayarak). Henüz paylaşılmamış bölümler
    sayfada görünmez; paylaşıldığı gün (REHBER_SAATI'nden sonra) eklenir."""
    yayimlanan = []
    bugun = simdi.date()
    saat_gecti = (simdi.hour, simdi.minute) >= REHBER_SAATI
    for gun, no in bilgi.yayim_listesi():
        if gun < bugun or (gun == bugun and saat_gecti):
            b = bilgi.BOLUMLER[no - 1]
            yayimlanan.append({"no": no, "tarih": _kisa_tarih(gun), "baslik": b["baslik"], "alt": b["alt"],
                               "sayfalar": b["sayfalar"],
                               # bölümün kendi sayfası, rehber/ altında (bot/dar_sayfalar.py)
                               "adres": f"{no}-{dar_sayfalar.adres_parcasi(b['baslik'])}/"})
    return sorted(yayimlanan, key=lambda b: b["no"])


def veri_hazirla(gecmis, simdi=None, pazar=None):
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

    program = _program(simdi, [g for g, _ in kayitlar])
    rehber = _rehber(simdi)
    hesap = bot.hesap_adi()
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
        "tablo": tablo,
        "grafik": _grafik(kayitlar),
        "ilk_kayit": _tarih(kayitlar[0][0]),
        "rehber": rehber,
        "ayrintili": _ayrintili(simdi),
        "program": program,
        "tanitim": _tanitim(program, pazar),
        "site_goril": SITE_GORIL,
        "kaynak": _kaynaklar(),
        "yil": simdi.year,
    }


def uret(cikti, gecmis, simdi=None, euro=None, pazar=None, kati=False):
    """kati=True (iş akışı): dar arama sayfaları da hatasız üretilmeli, yoksa hata verir; iş akışı yeniden dener,
    olmazsa sitenin önceki hâlini yayınlar (Rıdvan, 18 Ekim 2026: "2 kere belirli aralıklarda tekrar denesin.
    başarısız olursa önceki hali kalsın bana haber gelsin")."""
    from jinja2 import Environment, FileSystemLoader

    v = veri_hazirla(gecmis, simdi, pazar)
    env = Environment(loader=FileSystemLoader(str(bot.SABLONLAR)), autoescape=True)
    (cikti / "index.html").write_text(env.get_template("sayfa.html").render(**v, kok=""), encoding="utf-8")
    (cikti / "rehber").mkdir(exist_ok=True)
    (cikti / "rehber" / "index.html").write_text(env.get_template("rehber.html").render(**v, kok="../"),
                                                 encoding="utf-8")

    fontlar = cikti / "fonts"
    fontlar.mkdir(exist_ok=True)
    for f in (bot.KOK / "assets" / "fonts").iterdir():
        if f.suffix in (".woff2", ".txt"):
            shutil.copy2(f, fontlar / f.name)

    # Dar aramalar için sayfalar (hesap/, gecmis/, rehber bölümleri; bot/dar_sayfalar.py). Hata verirse
    # ana sayfa ve rehber yine yayınlanır, yalnızca uyarı çıkar.
    harita = []
    try:
        harita, dar = dar_sayfalar.uret(cikti, env, v, gecmis, euro)
        v["dar_sayi"] = len(dar)
    except Exception as e:
        if kati:
            raise
        print(f"::warning::Dar arama sayfaları üretilemedi: {type(e).__name__}: {e}")

    gun = (simdi or datetime.now(bot.TR_SAAT)).date().isoformat()
    satirlar = [(v["url"], gun, "daily"), (v["url"] + "rehber/", gun, "weekly")]
    satirlar += [(adres, son, "daily" if "/hesap/" in adres or adres.endswith("/gecmis/") else "weekly")
                 for adres, son in harita]
    (cikti / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{a}</loc><lastmod>{s}</lastmod><changefreq>{c}</changefreq></url>" for a, s, c in satirlar)
        + '</urlset>\n', encoding="utf-8")
    # Site 19 Ekim 2026'dan beri alan adının kökünde (gunlukgumus.com): arama motorları site haritasını robots.txt'ten de bulur.
    (cikti / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {v['url']}sitemap.xml\n", encoding="utf-8")
    (cikti / GOOGLE_DOGRULAMA).write_text(f"google-site-verification: {GOOGLE_DOGRULAMA}", encoding="utf-8")
    # Olmayan adreste Türkçe sayfa (Rıdvan, 18 Ekim 2026 "4 uygun"); her derinlikte açıldığı için kok tam adres
    (cikti / "404.html").write_text(env.get_template("bulunamadi.html").render(**v, kok=v["url"]), encoding="utf-8")

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
    ap.add_argument("--kati", action="store_true",
                    help="Hata olursa çıkış kodu 1 (iş akışı yeniden dener, olmazsa önceki siteyi yayınlar)")
    a = ap.parse_args()
    cikti = Path(a.cikti) if os.path.isabs(a.cikti) else bot.KOK / a.cikti
    cikti.mkdir(parents=True, exist_ok=True)
    try:
        if a.ornek:   # örnek kayıtlar; euro kuru örnek (EUR/USD ≈ 1,16), ağa çıkılmaz
            gecmis = ornek_gecmis()
            pazar = {"url": "https://www.instagram.com/gunlukgumus/", "tarih": "18 Ekim"}   # örnek düğme
            v = uret(cikti, gecmis, euro={k["kur_tarihi"]: k["dolar"] * 1.16 for k in gecmis.values()},
                     pazar=pazar, kati=a.kati)
        else:
            v = uret(cikti, bot.gecmis_oku(), pazar=son_pazar_analizi(), kati=a.kati)
    except bot.VeriYok as e:
        print(f"::warning::{e}")
        if a.kati:
            sys.exit(1)
        return
    except Exception as e:   # sayfa paylaşımı hiçbir zaman durdurmasın
        print(f"::warning::Bilgi sayfası üretilemedi: {type(e).__name__}: {e}")
        if a.kati:
            sys.exit(1)
        return
    print(f"Bilgi sayfası üretildi: {v['url']} (gram {v['gram']} ₺, {v['guncelleme']}; "
          f"rehber {len(v['rehber'])} bölüm)")


if __name__ == "__main__":
    main()
