"""Gümüş fiyat botu.

Komutlar:
  python bot/main.py hazirla --tur reels|post|hafta|yasal|bilgi --cikti site [--ornek] [--konu 1-6]
  python bot/main.py yayinla --cikti site --url https://kullanici.github.io/repo/
  python bot/main.py token-yenile

Veri kaynakları (ikisi de kaynak gösterilerek herkese açık yayımlanmaya izin veriyor):
  - Ons gümüş ve ons altın (USD): MetalCharts API, ücretsiz plan.
    Şartlar: https://metalcharts.org/api-terms — ücretsiz planda veri herkese açık
    gösterildiğinde metalcharts.org kaynağı görünür olmalı.
  - Dolar/TL: Avrupa Merkez Bankası (ECB) euro referans kurları, Frankfurter API üzerinden
    (USD/TRY, EUR çaprazından hesaplanır). Şartlar: ECB verisi ücretsiz yeniden kullanılabilir,
    ticari kullanım dahil; ECB kaynak olarak gösterilmeli ve verinin değiştirildiği (çapraz
    hesaplandığı) belirtilmeli. https://www.ecb.europa.eu/services/disclaimer/html/index.en.html
    (TCMB kuru Ekim 2026'ya kadar kullanıldı; ticari kullanımı yazılı izne bağlı olduğu için bırakıldı.)

MetalCharts'ın ücretsiz planında geçmiş veri olmadığı için her hafta içi paylaşımda o
günün değerleri veri/gecmis.json dosyasına yazılır (iş akışı bu dosyayı GitHub önbelleğinde
saklar). "Önceki gün" karşılaştırması ve haftalık özet bu kayıtlardan hesaplanır.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
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
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

API_HOST = os.environ.get("IG_API_HOST", "https://graph.instagram.com").rstrip("/")
API_SURUM = os.environ.get("IG_API_VERSION", "v23.0")
API = f"{API_HOST}/{API_SURUM}"

METALCHARTS_URL = "https://api.metalcharts.org/v1/prices"
# ECB kurları her iş günü ~16:00 CET (≈17:00 TR) yayımlanır; günde bir değer.
KUR_URL = "https://api.frankfurter.dev/v2/providers/ecb/rates"
TARAYICI = "gumus-bot/1.0 (+https://github.com/ridvancoskun1975-cpu/gumus-bot)"
GECMIS_DOSYASI = KOK / "veri" / "gecmis.json"
MUZIK_KUNYE = KOK / "assets" / "muzik-kunye.txt"

# Görselde ve açıklamada görünen kaynak satırları (kaynak göstermek iki kaynağın da şartı)
KAYNAK_METAL = "MetalCharts · metalcharts.org"
KAYNAK_KUR = "ECB referans kuru"


class VeriYok(Exception):
    """Paylaşım için gereken veri (anahtar ya da kayıt) henüz yok; paylaşım atlanır."""


# ---------------------------------------------------------------- fiyatlar

def _bekle(deneme):
    time.sleep(5 * (deneme + 1))


def metal_fiyatlari():
    """MetalCharts'tan ons gümüş (XAG) ve ons altın (XAU) spot fiyatı, USD."""
    anahtar = os.environ.get("METALCHARTS_KEY", "").strip()
    if not anahtar:
        raise VeriYok("METALCHARTS_KEY tanımlı değil (GitHub → Settings → Secrets and variables → Actions).")

    son_hata = None
    for deneme in range(3):
        try:
            r = requests.get(METALCHARTS_URL, timeout=30, headers={
                "Authorization": f"Bearer {anahtar}", "Accept": "application/json", "User-Agent": TARAYICI})
        except requests.RequestException as e:
            son_hata = e
            _bekle(deneme)
            continue
        if r.status_code in (401, 403):
            raise RuntimeError(f"MetalCharts anahtarı geçersiz ya da yetkisiz (HTTP {r.status_code}).")
        if r.status_code == 429:
            bekleme = int(r.headers.get("Retry-After", "60") or 60)
            if bekleme > 120:
                raise RuntimeError("MetalCharts aylık kullanım hakkı dolmuş (HTTP 429); ayın 1'inde sıfırlanır.")
            son_hata = RuntimeError("HTTP 429")
            time.sleep(bekleme)
            continue
        if r.status_code >= 400:
            son_hata = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            _bekle(deneme)
            continue
        try:
            veri = r.json()["data"]
            sonuc = {}
            for sembol in ("XAG", "XAU"):
                q = veri[sembol]
                sonuc[sembol] = {
                    "fiyat": float(q["price"]),
                    "yuzde24": float(q.get("changePercent24h") or 0.0),   # yüzde cinsinden
                    "eski": bool(q.get("stale")),
                    "zaman": q.get("timestamp"),
                }
        except (ValueError, KeyError, TypeError) as e:
            son_hata = RuntimeError(f"Beklenmeyen yanıt: {e}")
            _bekle(deneme)
            continue
        gumus, altin = sonuc["XAG"]["fiyat"], sonuc["XAU"]["fiyat"]
        # Saçma bir değerle paylaşım yapılmasın diye kaba bir akıl sağlığı kontrolü
        if not (math.isfinite(gumus) and math.isfinite(altin) and 2 < gumus < 1000
                and 200 < altin < 50000 and 10 < altin / gumus < 300):
            raise RuntimeError(f"MetalCharts'tan geçersiz fiyat geldi: gümüş {gumus}, altın {altin}")
        for sembol, q in sonuc.items():
            if q["eski"]:
                print(f"Uyarı: {sembol} fiyatı güncel değil (piyasa kapalı olabilir), zaman: {q['zaman']}",
                      file=sys.stderr)
        return sonuc
    raise RuntimeError(f"Metal fiyatları alınamadı: {son_hata}")


def kurlar():
    """ECB'nin son yayımlanan iki USD/TRY referans kuru: ((tarih, kur), (önceki tarih, kur)).

    ECB her iş günü ~17:00 (TR) yayımlar; o saatten önce son kur bir önceki iş gününündür.
    """
    baslangic = (datetime.now(TR_SAAT).date() - timedelta(days=14)).isoformat()
    son_hata = None
    for deneme in range(3):
        try:
            r = requests.get(KUR_URL, timeout=30, headers={"User-Agent": TARAYICI, "Accept": "application/json"},
                             params={"base": "USD", "quotes": "TRY", "from": baslangic})
            r.raise_for_status()
            satirlar = sorted((date.fromisoformat(x["date"]), float(x["rate"]))
                              for x in r.json() if x.get("quote") == "TRY")
            if len(satirlar) < 2:
                raise ValueError(f"yeterli kur yok ({len(satirlar)})")
            for _, kur in satirlar[-2:]:
                if not (math.isfinite(kur) and 1 < kur < 1000):
                    raise ValueError(f"geçersiz kur {kur}")
            return satirlar[-1], satirlar[-2]
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            son_hata = e
            _bekle(deneme)
    raise RuntimeError(f"Dolar/TL kuru alınamadı (ECB / Frankfurter): {son_hata}")


def gecmis_oku():
    try:
        return json.loads(GECMIS_DOSYASI.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except ValueError as e:
        print(f"Uyarı: günlük kayıt dosyası okunamadı ({e}); boş başlanıyor", file=sys.stderr)
        return {}


def gecmis_yaz(gecmis, gun, kayit):
    gecmis = dict(gecmis)
    gecmis[gun.isoformat()] = kayit
    sinir = (gun - timedelta(days=60)).isoformat()
    gecmis = {k: gecmis[k] for k in sorted(gecmis) if k >= sinir}
    GECMIS_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    GECMIS_DOSYASI.write_text(json.dumps(gecmis, ensure_ascii=False, indent=1), encoding="utf-8")


def fiyatlari_al(kaydet=True):
    metal = metal_fiyatlari()
    (kur_tarihi, dolar), (_, dolar_once) = kurlar()
    gumus, altin = metal["XAG"]["fiyat"], metal["XAU"]["fiyat"]
    gram = gumus * dolar / ONS_GRAM

    simdi = datetime.now(TR_SAAT)
    bugun = simdi.date()
    gecmis = gecmis_oku()
    alt_sinir = (bugun - timedelta(days=6)).isoformat()
    onceki_gunler = [k for k in gecmis if alt_sinir <= k < bugun.isoformat()]
    if onceki_gunler:
        # Önceki iş gününün son kaydı (normalde 20:00 paylaşımı)
        o = gecmis[max(onceki_gunler)]
        gram_once, parite_once = o["gram"], o["altin"] / o["gumus"]
    else:
        # İlk günlerde kayıt yok: MetalCharts'ın 24 saatlik değişiminden geri hesapla
        gumus_once = gumus / (1 + metal["XAG"]["yuzde24"] / 100)
        altin_once = altin / (1 + metal["XAU"]["yuzde24"] / 100)
        gram_once = gumus_once * dolar_once / ONS_GRAM
        parite_once = altin_once / gumus_once

    if kaydet and bugun.weekday() < 5:
        gecmis_yaz(gecmis, bugun, {"saat": simdi.strftime("%H:%M"), "gumus": gumus, "altin": altin,
                                    "dolar": dolar, "kur_tarihi": kur_tarihi.isoformat(), "gram": gram})
    return {
        "gram": gram, "gram_once": gram_once,
        "parite": altin / gumus, "parite_once": parite_once,
        "dolar": dolar, "dolar_once": dolar_once,
        "kur_tarihi": kur_tarihi.isoformat(),
    }


def _hafta_ayir(tarihler):
    """Son tamamlanan haftanın kayıtlı iş günlerini ve önceki haftanın son kayıtlı gününü döndürür.

    Hafta sonu çalışınca biten haftayı, hafta içi (elle) çalışınca yarım kalan bu
    haftayı değil bir önceki tam haftayı alır.
    """
    bugun = datetime.now(TR_SAAT).date()
    if bugun.weekday() < 5:
        sinir = bugun - timedelta(days=bugun.weekday())       # bu haftanın pazartesi
    else:
        sinir = bugun + timedelta(days=7 - bugun.weekday())   # gelecek pazartesi
    pazartesi = sinir - timedelta(days=7)
    bu_hafta = sorted(d for d in tarihler if pazartesi <= d < sinir and d.weekday() < 5)
    onceki = sorted(d for d in tarihler if pazartesi - timedelta(days=7) <= d < pazartesi)
    if len(bu_hafta) < 2:
        raise VeriYok(f"{pazartesi:%d.%m.%Y} haftası için yeterli günlük kayıt yok ({len(bu_hafta)} gün).")
    if not onceki:
        raise VeriYok("Önceki haftaya ait kayıt yok; haftalık değişim hesaplanamıyor.")
    return bu_hafta, onceki[-1]


def haftalik_fiyatlari_al():
    gecmis = {date.fromisoformat(k): v for k, v in gecmis_oku().items()}
    gunler, onceki_gun = _hafta_ayir(gecmis)
    son, once = gecmis[gunler[-1]], gecmis[onceki_gun]
    return {
        "gram": son["gram"], "gram_once": once["gram"],
        "parite": son["altin"] / son["gumus"], "parite_once": once["altin"] / once["gumus"],
        "dolar": son["dolar"], "dolar_once": once["dolar"],
        "kur_tarihi": son["kur_tarihi"],
        "son_saat": son["saat"],
        "gunluk": [{"tarih": g.isoformat(), "gram": gecmis[g]["gram"]} for g in gunler],
    }


def ornek_haftalik():
    f = ornek_fiyatlar()
    f["gram_once"] = 99.85
    f["son_saat"] = "20:00"
    f["gunluk"] = [{"tarih": t, "gram": v} for t, v in
                   [("2026-10-05", 100.62), ("2026-10-06", 101.94), ("2026-10-07", 101.18),
                    ("2026-10-08", 102.49), ("2026-10-09", 103.79)]]
    return f


def ornek_fiyatlar():
    return {"gram": 103.79, "gram_once": 102.49, "parite": 66.2, "parite_once": 66.77,
            "dolar": 49.25, "dolar_once": 49.21, "kur_tarihi": "2026-10-12"}


# ---------------------------------------------------------------- biçimlendirme

def tr_sayi(x, basamak=2):
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def degisim(simdi, once):
    yuzde = (simdi / once - 1) * 100
    yon = "dusus" if yuzde < 0 else "artis"
    return {"yon": yon, "yuzde": yuzde, "metin": "%" + tr_sayi(abs(yuzde), 2),
            "isaret": "▼" if yon == "dusus" else "▲"}


def muzik_kunyesi():
    try:
        return MUZIK_KUNYE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def veri_hazirla(f, hesap):
    simdi = datetime.now(TR_SAAT)
    kur_gunu = date.fromisoformat(f["kur_tarihi"])
    return {
        "tarih": f"{simdi.day:02d} {AYLAR[simdi.month - 1]} {simdi.year}",
        "saat": simdi.strftime("%H:%M"),
        "gram": tr_sayi(f["gram"], 2),
        "gram_deg": degisim(f["gram"], f["gram_once"]),
        "parite": tr_sayi(f["parite"], 1),
        "parite_deg": degisim(f["parite"], f["parite_once"]),
        "dolar": tr_sayi(f["dolar"], 2),
        "dolar_deg": degisim(f["dolar"], f["dolar_once"]),
        "kur_tarihi": f"{kur_gunu.day} {AYLAR[kur_gunu.month - 1]}",
        "kur_tarihi_tam": f"{kur_gunu:%d.%m.%Y}",
        "kaynak_metal": KAYNAK_METAL,
        "kaynak_kur": KAYNAK_KUR,
        "hesap": hesap,
    }


GUN_KISA = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def haftalik_veri_hazirla(f, hesap):
    v = veri_hazirla(f, hesap)
    gunler = [date.fromisoformat(g["tarih"]) for g in f["gunluk"]]
    degerler = [g["gram"] for g in f["gunluk"]]
    ilk, son = gunler[0], gunler[-1]
    if ilk.month == son.month:
        v["aralik"] = f"{ilk.day:02d}–{son.day:02d} {AYLAR[son.month - 1]} {son.year}"
    else:
        v["aralik"] = f"{ilk.day:02d} {AYLAR[ilk.month - 1]} – {son.day:02d} {AYLAR[son.month - 1]} {son.year}"
    v["son_an"] = f"{GUNLER[son.weekday()]} {f.get('son_saat', '')}".strip()
    v["en_yuksek"] = tr_sayi(max(degerler), 2)
    v["en_dusuk"] = tr_sayi(min(degerler), 2)

    # Grafik: gram gümüşün günlük değerleri, önceki haftanın son değeri kesikli çizgi
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


def _kaynak_satirlari(v):
    satirlar = [
        "Gram fiyatı ons gümüş × dolar/TL ÷ 31,1035 ile hesaplanmıştır; kuyumcu ve banka fiyatlarından farklı olabilir.",
        "Metal fiyatları: MetalCharts (metalcharts.org)",
        f"Dolar/TL: Avrupa Merkez Bankası (ECB) referans kurlarından EUR çaprazıyla hesaplanmıştır, Frankfurter (frankfurter.dev) üzerinden ({v['kur_tarihi_tam']} kuru)",
    ]
    kunye = muzik_kunyesi()
    if kunye:
        satirlar.append(f"Müzik: {kunye}")
    return "\n".join(satirlar)


# Instagram Aralık 2025'ten beri gönderi başına en fazla 5 hashtag'e izin veriyor.
# Etiket havuzu paylaşımlara dağıtılır: her paylaşım 5 etiket alır, hepsi kullanılmış olur.
HASHTAG_REELS = "#gümüş #gramgümüş #gümüşfiyatları #külçegümüş #silver"        # hafta içi ~10:00
HASHTAG_POST = "#gümüş #gümüşyatırımı #değerlimetaller #emtia #gumus"           # hafta içi ~20:00 özet
# Haftalık özet iki set arasında hafta hafta döner (ISO hafta numarası tekse 1., çiftse 2. set;
# ilk gerçek haftalık özet 24 Ekim 2026 = 43. hafta, 1. setle başlar).
HASHTAG_HAFTA = (
    "#gümüş #gramgümüş #gümüşyatırımı #gümüşfiyatları #değerlimetaller",
    "#gümüş #gramgümüş #külçegümüş #gumus #silver",
)


def hashtag_sec(tur, tarih=None):
    if tur == "hafta":
        hafta_no = (tarih or datetime.now(TR_SAAT).date()).isocalendar()[1]
        return HASHTAG_HAFTA[(hafta_no + 1) % 2]
    return HASHTAG_POST if tur == "post" else HASHTAG_REELS

# Bu türler Reels'in yanında hikâyeye de paylaşılır (aynı video, 9:16).
HIKAYE_TURLERI = {"post", "hafta"}


def aciklama_yaz(v, tur):
    if tur == "hafta":
        g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
        return (
            f"Haftalık gümüş özeti | {v['aralik']}\n\n"
            f"Gram gümüş: {v['gram']} ₺ ({g['isaret']} {g['metin']})\n"
            f"Haftanın en yükseği: {v['en_yuksek']} ₺ · en düşüğü: {v['en_dusuk']} ₺\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            "Günlük değerler iş günlerinin son paylaşımına (yaklaşık 20:00) aittir; "
            "değişimler önceki haftanın son değerine göredir.\n"
            "Sizce gümüş gelecek hafta ne yöne gider? Yorumlara yazın 👇\n\n"
            "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
            f"{_kaynak_satirlari(v)}\n\n"
            f"{hashtag_sec(tur)}"
        )
    baslik = "Günün gümüş özeti" if tur == "post" else "Güncel gümüş fiyatları"
    g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
    return (
        f"{baslik} | {v['tarih']} · {v['saat']}\n\n"
        f"Gram gümüş: {v['gram']} ₺ ({g['isaret']} {g['metin']})\n"
        f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
        f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
        "Değişimler önceki iş gününe göredir.\n"
        "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
        f"{_kaynak_satirlari(v)}\n\n"
        f"{hashtag_sec(tur)}"
    )


# ---------------------------------------------------------------- görsel ve video

def gorsel_uret(tur, veri, png_yolu):
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
    html = env.get_template(f"{tur}.html").render(**veri)
    gecici = SABLONLAR / f"_cikti_{tur}.html"   # fontlar göreli yolla yüklensin diye burada
    gecici.write_text(html, encoding="utf-8")
    boyut = {"reels": (1080, 1920), "post": (1080, 1350), "hafta": (1080, 1350), "yasal": (1080, 1350),
             "bilgi": (1080, 1350)}[tur]
    # Instagram görsel gönderilerde yalnızca JPEG kabul ediyor; uzantı .jpg ise JPEG kaydedilir.
    jpeg = {"quality": 92} if Path(png_yolu).suffix.lower() in (".jpg", ".jpeg") else {}
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
            sayfa.screenshot(path=str(png_yolu), clip={"x": 0, "y": 0, "width": boyut[0], "height": boyut[1]}, **jpeg)
            tarayici.close()
    finally:
        gecici.unlink(missing_ok=True)


ZEMIN_RENGI = "0x121418"   # templates/ortak.css içindeki --zemin ile aynı


def video_uret(png_yolu, mp4_yolu, sure=7):
    """Görselden sesli dikey video üretir. 9:16 olmayan görseller zemin rengiyle 1080x1920'ye tamamlanır.

    Müzik dosyası depoda şifreli durur (assets/muzik.mp3.enc); iş akışı MUZIK_ANAHTAR ile
    assets/muzik.mp3 olarak açar. Dosya yoksa video sessiz üretilir.
    """
    muzik = KOK / "assets" / "muzik.mp3"
    if muzik.exists():
        ses = ["-stream_loop", "-1", "-i", str(muzik)]
        ses_filtre = ["-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={sure - 1.5}:d=1.5,aresample=44100"]
    else:
        print("Uyarı: assets/muzik.mp3 yok, video müziksiz üretiliyor", file=sys.stderr)
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


def _kaydirmali_konteyner(kullanici_id, urller, aciklama):
    """Kaydırmalı (carousel) gönderi: her görsel için bir alt konteyner, sonra bunları toplayan ana konteyner."""
    cocuklar = []
    for url in urller:
        c = _istek("POST", f"{kullanici_id}/media", image_url=url, is_carousel_item="true")
        _hazir_olmasini_bekle(c["id"])
        cocuklar.append(c["id"])
    return _istek("POST", f"{kullanici_id}/media", media_type="CAROUSEL",
                  children=",".join(cocuklar), caption=aciklama)


def yayinla(cikti, taban_url):
    meta = json.loads((cikti / "meta.json").read_text(encoding="utf-8"))
    if "dosyalar" in meta:
        urller = [taban_url.rstrip("/") + "/" + d for d in meta["dosyalar"]]
        for url in urller:
            _url_hazir_mi(url)
        kullanici_id = hesap_bilgisi()["user_id"]
        k = _kaydirmali_konteyner(kullanici_id, urller, meta["aciklama"])
        _hazir_olmasini_bekle(k["id"])
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        print(f"Paylaşıldı: {meta['tur']} (medya id {sonuc.get('id')})")
        try:
            print("Bağlantı:", _istek("GET", sonuc["id"], fields="permalink").get("permalink"))
        except Exception as e:
            print(f"Uyarı: bağlantı alınamadı ({e})", file=sys.stderr)
        return
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
    if meta["tur"] in HIKAYE_TURLERI and meta["dosya"].endswith(".mp4"):
        hikaye_paylas(kullanici_id, medya_url)


def hikaye_paylas(kullanici_id, video_url):
    """Aynı videoyu hikâyeye de koyar. Hikâye başarısız olursa asıl paylaşım etkilenmez, yalnızca uyarı verilir."""
    try:
        k = _istek("POST", f"{kullanici_id}/media", media_type="STORIES", video_url=video_url)
        _hazir_olmasini_bekle(k["id"])
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        print(f"Hikâyeye de paylaşıldı (medya id {sonuc.get('id')})")
    except Exception as e:
        print(f"::warning::Hikâye paylaşılamadı: {e}")


def token_yenile():
    r = requests.get(f"{API_HOST}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"]},
                     timeout=60)
    cevap = r.json()
    if "access_token" not in cevap:
        raise RuntimeError(f"Token yenilenemedi: {cevap.get('error', cevap)}")
    print(cevap["access_token"])


# ---------------------------------------------------------------- giriş

def hesap_adi():
    hesap = os.environ.get("HESAP_ADI", "").strip()
    if not hesap and os.environ.get("IG_TOKEN"):
        try:
            hesap = hesap_bilgisi().get("username", "")
        except Exception as e:
            print(f"Uyarı: kullanıcı adı alınamadı ({e})", file=sys.stderr)
    return ("@" + hesap.lstrip("@")) if hesap else ""


def yasal_hazirla(cikti):
    """Profilde sabitlenecek yasal bilgilendirme: kapak + 4 sayfa, kaydırmalı görsel gönderi."""
    import yasal
    hesap = hesap_adi()
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    toplam = len(yasal.SAYFALAR) + 1
    dosyalar = []
    for sayfa in range(toplam):
        jpg = cikti / f"yasal-{damga}-{sayfa + 1}.jpg"
        gorsel_uret("yasal", {"sayfa": sayfa, "toplam": toplam, "sayfalar": yasal.SAYFALAR,
                              "hesap": hesap, "guncelleme": yasal.GUNCELLEME}, jpg)
        dosyalar.append(jpg.name)
    if len(yasal.ACIKLAMA) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(yasal.ACIKLAMA)} > 2200 karakter)")
    (cikti / "meta.json").write_text(json.dumps({"tur": "yasal", "dosyalar": dosyalar, "aciklama": yasal.ACIKLAMA},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in dosyalar), encoding="utf-8")
    print(yasal.ACIKLAMA)
    print(f"\nÜretilen dosyalar ({len(yasal.ACIKLAMA)} karakter açıklama):", *dosyalar, sep="\n")


def bilgi_hazirla(cikti, konu=None):
    """Gümüş rehberi bölümü: kapak + 3 sayfa, kaydırmalı görsel gönderi. Fiyat verisi kullanmaz.

    konu verilmezse bugünün bölümü bilgi.TAKVIM'den seçilir; takvimde yoksa paylaşım atlanır.
    """
    import bilgi
    if not konu:
        bugun = datetime.now(TR_SAAT).date().isoformat()
        konu = bilgi.TAKVIM.get(bugun)
        if not konu:
            print(f"::warning::Paylaşım atlandı: {bugun} için takvimde bilgi gönderisi yok")
            return
    if not 1 <= konu <= len(bilgi.BOLUMLER):
        raise RuntimeError(f"Konu 1-{len(bilgi.BOLUMLER)} arasında olmalı (verilen: {konu})")
    b = bilgi.BOLUMLER[konu - 1]
    sonraki = bilgi.BOLUMLER[konu]["baslik"] if konu < len(bilgi.BOLUMLER) else None
    hesap = hesap_adi()
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    toplam = len(b["sayfalar"]) + 1
    dosyalar = []
    for sayfa in range(toplam):
        jpg = cikti / f"bilgi{konu}-{damga}-{sayfa + 1}.jpg"
        gorsel_uret("bilgi", {"b": b, "no": konu, "toplam_bolum": len(bilgi.BOLUMLER), "sayfa": sayfa,
                              "toplam_sayfa": toplam, "sonraki": sonraki, "seri": bilgi.SERI,
                              "hesap": hesap}, jpg)
        dosyalar.append(jpg.name)
    metin = bilgi.aciklama(konu)
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
    (cikti / "meta.json").write_text(json.dumps({"tur": "bilgi", "konu": konu, "dosyalar": dosyalar,
                                                 "aciklama": metin}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in dosyalar), encoding="utf-8")
    print(metin)
    print(f"\nÜretilen dosyalar ({len(metin)} karakter açıklama):", *dosyalar, sep="\n")


def hazirla(tur, cikti, ornek, konu=None):
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "meta.json").unlink(missing_ok=True)   # eski bir paylaşım yanlışlıkla tekrar gitmesin
    if tur == "yasal":
        yasal_hazirla(cikti)
        return
    if tur == "bilgi":
        bilgi_hazirla(cikti, konu)
        return
    try:
        if tur == "hafta":
            fiyat = ornek_haftalik() if ornek else haftalik_fiyatlari_al()
        else:
            fiyat = ornek_fiyatlar() if ornek else fiyatlari_al(kaydet=True)
    except VeriYok as e:
        # Hata değil: paylaşım bu sefer atlanır, iş akışı sonraki adımları çalıştırmaz.
        print(f"::warning::Paylaşım atlandı: {e}")
        return
    hesap = hesap_adi()
    veri = haftalik_veri_hazirla(fiyat, hesap) if tur == "hafta" else veri_hazirla(fiyat, hesap)

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    png = cikti / f"{tur}-{damga}.png"
    gorsel_uret(tur, veri, png)
    # Her paylaşım sesli video (Reels) olarak gider; özetler okunabilsin diye biraz daha uzun.
    mp4 = cikti / f"{tur}-{damga}.mp4"
    video_uret(png, mp4, sure=7 if tur == "reels" else 10)
    dosya = mp4.name

    aciklama = aciklama_yaz(veri, tur)
    (cikti / "meta.json").write_text(json.dumps({"tur": tur, "dosya": dosya, "aciklama": aciklama,
                                                 "fiyatlar": fiyat}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      f"<p>Son üretilen dosya: <a href='{dosya}'>{dosya}</a></p>"
                                      "<p>Metal fiyatları: <a href='https://metalcharts.org'>MetalCharts</a>"
                                      " · Dolar/TL: ECB referans kurları (<a href='https://frankfurter.dev'>Frankfurter</a>)</p>", encoding="utf-8")
    print(aciklama)
    print(f"\nÜretilen dosya: {cikti / dosya}")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    h = alt.add_parser("hazirla")
    h.add_argument("--tur", choices=["reels", "post", "hafta", "yasal", "bilgi"], required=True)
    h.add_argument("--cikti", default="site")
    h.add_argument("--ornek", action="store_true", help="Gerçek fiyat yerine örnek veri kullan")
    h.add_argument("--konu", type=int, default=None,
                   help="bilgi türünde bölüm numarası (boşsa bugünün takvim bölümü)")
    y = alt.add_parser("yayinla")
    y.add_argument("--cikti", default="site")
    y.add_argument("--url", required=True)
    alt.add_parser("token-yenile")
    a = ap.parse_args()

    if a.komut == "hazirla":
        hazirla(a.tur, KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.ornek, a.konu)
    elif a.komut == "yayinla":
        yayinla(KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.url)
    else:
        token_yenile()


if __name__ == "__main__":
    main()
