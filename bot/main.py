"""Gümüş fiyat botu.

Komutlar:
  python bot/main.py hazirla --tur reels|post|hafta --cikti site [--ornek]
  python bot/main.py yayinla --cikti site --url https://kullanici.github.io/repo/
  python bot/main.py token-yenile
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


def ffmpeg_yolu():
    """Sistemde ffmpeg varsa onu, yoksa pip paketiyle gelen hazır ffmpeg'i kullanır."""
    import shutil
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

KOK = Path(__file__).resolve().parent.parent
SABLONLAR = KOK / "templates"
ONS_GRAM = 31.1034768
TR_SAAT = ZoneInfo("Europe/Istanbul")
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

API_HOST = os.environ.get("IG_API_HOST", "https://graph.instagram.com").rstrip("/")
API_SURUM = os.environ.get("IG_API_VERSION", "v23.0")
API = f"{API_HOST}/{API_SURUM}"


# ---------------------------------------------------------------- fiyatlar

def _son_ve_onceki(sembol):
    """Bir sembolün son fiyatını ve önceki gün kapanışını döndürür."""
    import yfinance as yf

    son_hata = None
    for deneme in range(3):
        try:
            t = yf.Ticker(sembol)
            gunluk = t.history(period="10d", interval="1d")["Close"].dropna()
            gun_ici = t.history(period="2d", interval="15m")["Close"].dropna()
            son = float(gun_ici.iloc[-1]) if not gun_ici.empty else float(gunluk.iloc[-1])
            son_gun = (gun_ici.index[-1] if not gun_ici.empty else gunluk.index[-1]).date()
            # Önceki gün kapanışı: son işlem gününden önceki son günlük kapanış
            onceki_seri = gunluk[[d.date() < son_gun for d in gunluk.index]]
            onceki = float(onceki_seri.iloc[-1]) if not onceki_seri.empty else float(gunluk.iloc[-2])
            if not (son > 0 and onceki > 0 and math.isfinite(son) and math.isfinite(onceki)):
                raise ValueError(f"{sembol} için geçersiz fiyat: {son}, {onceki}")
            return son, onceki
        except Exception as e:  # ağ hatası, boş veri vb.
            son_hata = e
            time.sleep(5 * (deneme + 1))
    raise RuntimeError(f"{sembol} fiyatı alınamadı: {son_hata}")


def fiyatlari_al():
    gumus, gumus_once = _son_ve_onceki("SI=F")   # ons gümüş, USD
    altin, altin_once = _son_ve_onceki("GC=F")   # ons altın, USD
    dolar, dolar_once = _son_ve_onceki("TRY=X")  # USD/TRY
    return {
        "gram": gumus * dolar / ONS_GRAM,
        "gram_once": gumus_once * dolar_once / ONS_GRAM,
        "parite": altin / gumus,
        "parite_once": altin_once / gumus_once,
        "dolar": dolar,
        "dolar_once": dolar_once,
    }


def _gunluk_kapanislar(sembol):
    """Son ~1 ayın günlük kapanışlarını {tarih: fiyat} olarak döndürür."""
    import yfinance as yf

    son_hata = None
    for deneme in range(3):
        try:
            seri = yf.Ticker(sembol).history(period="1mo", interval="1d")["Close"].dropna()
            kapanis = {d.date(): float(v) for d, v in seri.items() if v > 0 and math.isfinite(v)}
            if len(kapanis) < 5:
                raise ValueError(f"{sembol} için yetersiz veri")
            return kapanis
        except Exception as e:
            son_hata = e
            time.sleep(5 * (deneme + 1))
    raise RuntimeError(f"{sembol} günlük verisi alınamadı: {son_hata}")


def _hafta_ayir(kapanis):
    """Son tamamlanan haftanın kapanışlarını ve ondan önceki haftanın son kapanışını ayırır.

    Hafta sonu çalışınca biten haftayı, hafta içi (elle) çalışınca yarım kalan bu
    haftayı değil bir önceki tam haftayı alır.
    """
    from datetime import timedelta
    bugun = datetime.now(TR_SAAT).date()
    if bugun.weekday() < 5:
        sinir = bugun - timedelta(days=bugun.weekday())   # bu haftanın pazartesi
    else:
        sinir = bugun + timedelta(days=7 - bugun.weekday())  # gelecek pazartesi
    tarihler = sorted(d for d in kapanis if d < sinir)
    son = tarihler[-1]
    pazartesi = son - timedelta(days=son.weekday())
    bu_hafta = [d for d in tarihler if d >= pazartesi]
    onceki = [d for d in tarihler if d < pazartesi]
    if not onceki:
        raise RuntimeError("Önceki haftanın kapanışı bulunamadı")
    return bu_hafta, onceki[-1]


def _o_gundeki(kapanis, gun):
    """Verilen gündeki ya da ondan önceki en yakın kapanış (tatil farklarına karşı)."""
    uygun = [d for d in kapanis if d <= gun]
    return kapanis[max(uygun)] if uygun else kapanis[min(kapanis)]


def haftalik_fiyatlari_al():
    gumus = _gunluk_kapanislar("SI=F")
    altin = _gunluk_kapanislar("GC=F")
    dolar = _gunluk_kapanislar("TRY=X")
    gunler, onceki_gun = _hafta_ayir(gumus)

    def gram(g):
        return _o_gundeki(gumus, g) * _o_gundeki(dolar, g) / ONS_GRAM

    son = gunler[-1]
    return {
        "gram": gram(son), "gram_once": gram(onceki_gun),
        "parite": _o_gundeki(altin, son) / gumus[son],
        "parite_once": _o_gundeki(altin, onceki_gun) / gumus[onceki_gun],
        "dolar": _o_gundeki(dolar, son), "dolar_once": _o_gundeki(dolar, onceki_gun),
        "gunluk": [{"tarih": g.isoformat(), "gram": gram(g)} for g in gunler],
    }


def ornek_haftalik():
    f = ornek_fiyatlar()
    f["gram_once"] = 99.85
    f["gunluk"] = [{"tarih": t, "gram": v} for t, v in
                   [("2026-10-05", 100.62), ("2026-10-06", 101.94), ("2026-10-07", 101.18),
                    ("2026-10-08", 102.49), ("2026-10-09", 103.79)]]
    return f


def ornek_fiyatlar():
    return {"gram": 103.79, "gram_once": 102.49, "parite": 66.2, "parite_once": 66.77,
            "dolar": 48.48, "dolar_once": 48.46}


# ---------------------------------------------------------------- biçimlendirme

def tr_sayi(x, basamak=2):
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def degisim(simdi, once):
    yuzde = (simdi / once - 1) * 100
    yon = "dusus" if yuzde < 0 else "artis"
    return {"yon": yon, "yuzde": yuzde, "metin": "%" + tr_sayi(abs(yuzde), 2),
            "isaret": "▼" if yon == "dusus" else "▲"}


def veri_hazirla(f, hesap):
    simdi = datetime.now(TR_SAAT)
    return {
        "tarih": f"{simdi.day:02d} {AYLAR[simdi.month - 1]} {simdi.year}",
        "saat": simdi.strftime("%H:%M"),
        "gram": tr_sayi(f["gram"], 2),
        "gram_deg": degisim(f["gram"], f["gram_once"]),
        "parite": tr_sayi(f["parite"], 1),
        "parite_deg": degisim(f["parite"], f["parite_once"]),
        "dolar": tr_sayi(f["dolar"], 2),
        "dolar_deg": degisim(f["dolar"], f["dolar_once"]),
        "hesap": hesap,
    }


GUN_KISA = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def haftalik_veri_hazirla(f, hesap):
    from datetime import date
    v = veri_hazirla(f, hesap)
    gunler = [date.fromisoformat(g["tarih"]) for g in f["gunluk"]]
    degerler = [g["gram"] for g in f["gunluk"]]
    ilk, son = gunler[0], gunler[-1]
    if ilk.month == son.month:
        v["aralik"] = f"{ilk.day:02d}–{son.day:02d} {AYLAR[son.month - 1]} {son.year}"
    else:
        v["aralik"] = f"{ilk.day:02d} {AYLAR[ilk.month - 1]} – {son.day:02d} {AYLAR[son.month - 1]} {son.year}"
    v["en_yuksek"] = tr_sayi(max(degerler), 2)
    v["en_dusuk"] = tr_sayi(min(degerler), 2)

    # Grafik: gram gümüşün günlük kapanışları, önceki hafta kapanışı kesikli çizgi
    gen, yuk, kenar, yan = 904, 230, 30, 64
    tum = degerler + [f["gram_once"]]
    alt_s, ust_s = min(tum), max(tum)
    aralik = (ust_s - alt_s) or 1
    adim = (gen - 2 * yan) / max(len(degerler) - 1, 1)

    def y(x):
        return round(kenar + (ust_s - x) / aralik * (yuk - 2 * kenar), 1)

    noktalar = [{"x": round(yan + i * adim, 1), "y": y(d), "gun": GUN_KISA[g.weekday()],
                 "deger": tr_sayi(d, 2)} for i, (g, d) in enumerate(zip(gunler, degerler))]
    v["grafik"] = {"gen": gen, "yuk": yuk, "noktalar": noktalar,
                   "cizgi": " ".join(f"{n['x']},{n['y']}" for n in noktalar),
                   "onceki_y": y(f["gram_once"]), "yon": v["gram_deg"]["yon"]}
    return v


def aciklama_yaz(v, tur):
    if tur == "hafta":
        g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
        return (
            f"Haftalık gümüş özeti | {v['aralik']}\n\n"
            f"Gram gümüş: {v['gram']} ₺ ({g['isaret']} {g['metin']})\n"
            f"Haftanın en yükseği: {v['en_yuksek']} ₺ · en düşüğü: {v['en_dusuk']} ₺\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            "Değişimler önceki haftanın kapanışına, en yüksek/en düşük günlük kapanışlara göredir.\n"
            "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
            "#gümüş #gramgümüş #gümüşfiyatları #haftalıközet #altın #dolar #piyasa #yatırım"
        )
    baslik = "Günün gümüş özeti" if tur == "post" else "Güncel gümüş fiyatları"
    g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
    return (
        f"{baslik} | {v['tarih']} · {v['saat']}\n\n"
        f"Gram gümüş: {v['gram']} ₺ ({g['isaret']} {g['metin']})\n"
        f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
        f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
        "Değişimler önceki günün kapanışına göredir.\n"
        "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
        "#gümüş #gramgümüş #gümüşfiyatları #altın #dolar #piyasa #yatırım"
    )


# ---------------------------------------------------------------- görsel ve video

def gorsel_uret(tur, veri, png_yolu):
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
    html = env.get_template(f"{tur}.html").render(**veri)
    gecici = SABLONLAR / f"_cikti_{tur}.html"   # fontlar göreli yolla yüklensin diye burada
    gecici.write_text(html, encoding="utf-8")
    boyut = {"reels": (1080, 1920), "post": (1080, 1350), "hafta": (1080, 1350)}[tur]
    try:
        with sync_playwright() as p:
            kwargs = {}
            if os.environ.get("CHROME_YOLU"):
                kwargs["executable_path"] = os.environ["CHROME_YOLU"]
            tarayici = p.chromium.launch(**kwargs)
            sayfa = tarayici.new_page(viewport={"width": boyut[0], "height": boyut[1]})
            sayfa.goto(gecici.as_uri())
            sayfa.evaluate("document.fonts.ready")
            sayfa.wait_for_timeout(300)
            sayfa.screenshot(path=str(png_yolu), clip={"x": 0, "y": 0, "width": boyut[0], "height": boyut[1]})
            tarayici.close()
    finally:
        gecici.unlink(missing_ok=True)


ZEMIN_RENGI = "0x121418"   # templates/ortak.css içindeki --zemin ile aynı


def video_uret(png_yolu, mp4_yolu, sure=7):
    """Görselden sesli dikey video üretir. 9:16 olmayan görseller zemin rengiyle 1080x1920'ye tamamlanır."""
    muzik = KOK / "assets" / "muzik.mp3"
    if muzik.exists():
        ses = ["-stream_loop", "-1", "-i", str(muzik)]
        ses_filtre = ["-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={sure - 1.5}:d=1.5,aresample=44100"]
    else:
        ses = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        ses_filtre = []
    goruntu = (f"scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color={ZEMIN_RENGI},"
               "fade=t=in:st=0:d=0.6,format=yuv420p")
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png_yolu), *ses,
             "-t", str(sure), "-vf", goruntu, *ses_filtre,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(mp4_yolu)]
    subprocess.run(komut, check=True)


# ---------------------------------------------------------------- instagram

def _istek(yontem, yol, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    r = requests.request(yontem, f"{API}/{yol}", data=params if yontem == "POST" else None,
                         params=params if yontem == "GET" else None, timeout=60)
    try:
        cevap = r.json()
    except ValueError:
        cevap = {"ham": r.text[:500]}
    if r.status_code >= 400 or "error" in cevap:
        hata = cevap.get("error", cevap)
        raise RuntimeError(f"Instagram API hatası ({r.status_code}): {hata}")
    return cevap


def hesap_bilgisi():
    return _istek("GET", "me", fields="user_id,username")


def _hazir_olmasini_bekle(konteyner_id, sure_sn=300):
    bitis = time.time() + sure_sn
    while time.time() < bitis:
        durum = _istek("GET", konteyner_id, fields="status_code,status").get("status_code")
        if durum == "FINISHED":
            return
        if durum in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram medyayı işleyemedi: {durum}")
        time.sleep(10)
    raise RuntimeError("Instagram medyayı zamanında işleyemedi")


def _url_hazir_mi(url, sure_sn=180):
    bitis = time.time() + sure_sn
    while time.time() < bitis:
        try:
            if requests.head(url, timeout=15, allow_redirects=True).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(10)
    raise RuntimeError(f"Dosya yayına çıkmadı: {url}")


def yayinla(cikti, taban_url):
    meta = json.loads((cikti / "meta.json").read_text(encoding="utf-8"))
    medya_url = taban_url.rstrip("/") + "/" + meta["dosya"]
    _url_hazir_mi(medya_url)
    kullanici_id = hesap_bilgisi()["user_id"]
    if meta["dosya"].endswith(".mp4"):
        # thumb_offset: kapak, kararmadan açılış bittikten sonraki kareden alınsın
        k = _istek("POST", f"{kullanici_id}/media", media_type="REELS", video_url=medya_url,
                   caption=meta["aciklama"], share_to_feed="true", thumb_offset="1500")
    else:
        k = _istek("POST", f"{kullanici_id}/media", image_url=medya_url, caption=meta["aciklama"])
    _hazir_olmasini_bekle(k["id"])
    sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
    print(f"Paylaşıldı: {meta['tur']} (medya id {sonuc.get('id')})")


def token_yenile():
    r = requests.get(f"{API_HOST}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"]},
                     timeout=60)
    cevap = r.json()
    if "access_token" not in cevap:
        raise RuntimeError(f"Token yenilenemedi: {cevap.get('error', cevap)}")
    print(cevap["access_token"])


# ---------------------------------------------------------------- giriş

def hazirla(tur, cikti, ornek):
    cikti.mkdir(parents=True, exist_ok=True)
    if tur == "hafta":
        fiyat = ornek_haftalik() if ornek else haftalik_fiyatlari_al()
    else:
        fiyat = ornek_fiyatlar() if ornek else fiyatlari_al()
    hesap = os.environ.get("HESAP_ADI", "").strip()
    if not hesap and os.environ.get("IG_TOKEN"):
        try:
            hesap = hesap_bilgisi().get("username", "")
        except Exception as e:
            print(f"Uyarı: kullanıcı adı alınamadı ({e})", file=sys.stderr)
    hesap = ("@" + hesap.lstrip("@")) if hesap else ""
    veri = haftalik_veri_hazirla(fiyat, hesap) if tur == "hafta" else veri_hazirla(fiyat, hesap)

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    png = cikti / f"{tur}-{damga}.png"
    gorsel_uret(tur, veri, png)
    dosya = png.name
    # Her paylaşım sesli video (Reels) olarak gider; özetler okunabilsin diye biraz daha uzun.
    mp4 = cikti / f"{tur}-{damga}.mp4"
    video_uret(png, mp4, sure=7 if tur == "reels" else 10)
    dosya = mp4.name

    aciklama = aciklama_yaz(veri, tur)
    (cikti / "meta.json").write_text(json.dumps({"tur": tur, "dosya": dosya, "aciklama": aciklama,
                                                 "fiyatlar": fiyat}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      f"<p>Son üretilen dosya: <a href='{dosya}'>{dosya}</a></p>", encoding="utf-8")
    print(aciklama)
    print(f"\nÜretilen dosya: {cikti / dosya}")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    h = alt.add_parser("hazirla")
    h.add_argument("--tur", choices=["reels", "post", "hafta"], required=True)
    h.add_argument("--cikti", default="site")
    h.add_argument("--ornek", action="store_true", help="Gerçek fiyat yerine örnek veri kullan")
    y = alt.add_parser("yayinla")
    y.add_argument("--cikti", default="site")
    y.add_argument("--url", required=True)
    alt.add_parser("token-yenile")
    a = ap.parse_args()

    if a.komut == "hazirla":
        hazirla(a.tur, KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.ornek)
    elif a.komut == "yayinla":
        yayinla(KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.url)
    else:
        token_yenile()


if __name__ == "__main__":
    main()
