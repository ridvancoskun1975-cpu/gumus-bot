"""Gümüş fiyat botu.

Komutlar:
  python bot/main.py hazirla --tur reels|post --cikti site [--ornek]
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


def aciklama_yaz(v, tur):
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
    boyut = {"reels": (1080, 1920), "post": (1080, 1350)}[tur]
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


def video_uret(png_yolu, mp4_yolu, sure=7):
    muzik = KOK / "assets" / "muzik.mp3"
    if muzik.exists():
        ses = ["-stream_loop", "-1", "-i", str(muzik)]
        ses_filtre = ["-af", f"afade=t=in:d=0.5,afade=t=out:st={sure - 1}:d=1"]
    else:
        ses = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        ses_filtre = []
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png_yolu), *ses,
             "-t", str(sure), "-vf", "fade=t=in:st=0:d=0.6,format=yuv420p", *ses_filtre,
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
    if meta["tur"] == "reels":
        k = _istek("POST", f"{kullanici_id}/media", media_type="REELS", video_url=medya_url,
                   caption=meta["aciklama"], share_to_feed="true")
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
    fiyat = ornek_fiyatlar() if ornek else fiyatlari_al()
    hesap = os.environ.get("HESAP_ADI", "").strip()
    if not hesap and os.environ.get("IG_TOKEN"):
        try:
            hesap = hesap_bilgisi().get("username", "")
        except Exception as e:
            print(f"Uyarı: kullanıcı adı alınamadı ({e})", file=sys.stderr)
    hesap = ("@" + hesap.lstrip("@")) if hesap else ""
    veri = veri_hazirla(fiyat, hesap)

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    png = cikti / f"{tur}-{damga}.png"
    gorsel_uret(tur, veri, png)
    dosya = png.name
    if tur == "reels":
        mp4 = cikti / f"reels-{damga}.mp4"
        video_uret(png, mp4)
        dosya = mp4.name
    if tur == "post":
        # Instagram feed görsellerinde JPEG istiyor
        jpg = cikti / f"post-{damga}.jpg"
        subprocess.run([ffmpeg_yolu(), "-y", "-loglevel", "error", "-i", str(png), "-q:v", "2", str(jpg)], check=True)
        dosya = jpg.name

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
    h.add_argument("--tur", choices=["reels", "post"], required=True)
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
