"""Gümüş fiyat botu.

Komutlar:
  python bot/main.py hazirla --tur reels|post|hafta|ay|yasal|bilgi|yorum --cikti site [--ornek] [--konu 1-6]
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


def ecb_gecmisi(gun_sayisi=400):
    """Son ~13 ayın ECB USD/TRY referans kurları: {tarih: kur}. Tek istek, anahtarsız."""
    baslangic = (datetime.now(TR_SAAT).date() - timedelta(days=gun_sayisi)).isoformat()
    son_hata = None
    for deneme in range(3):
        try:
            r = requests.get(KUR_URL, timeout=60, headers={"User-Agent": TARAYICI, "Accept": "application/json"},
                             params={"base": "USD", "quotes": "TRY", "from": baslangic})
            r.raise_for_status()
            kurlar_ = {date.fromisoformat(x["date"]): float(x["rate"]) for x in r.json() if x.get("quote") == "TRY"}
            if len(kurlar_) < 100 or not all(1 < k < 1000 for k in kurlar_.values()):
                raise ValueError(f"beklenmeyen kur serisi ({len(kurlar_)} gün)")
            return kurlar_
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            son_hata = e
            _bekle(deneme)
    raise RuntimeError(f"Dolar/TL kur geçmişi alınamadı (ECB / Frankfurter): {son_hata}")


def metal_gecmisi():
    """MetalCharts günlük geçmişi (1 yıl). Yalnızca ücretli planlarda var; ücretsiz planda 403 döner
    (MetalCharts'a göre reddedilen istekler aylık hakka sayılmaz) ve None döndürülür."""
    anahtar = os.environ.get("METALCHARTS_KEY", "").strip()
    if not anahtar:
        return None
    sonuc = {}
    for sembol in ("XAG", "XAU"):
        try:
            r = requests.get(f"https://api.metalcharts.org/v1/history/{sembol}", timeout=60,
                             params={"range": "1Y", "interval": "1d"},
                             headers={"Authorization": f"Bearer {anahtar}", "Accept": "application/json",
                                      "User-Agent": TARAYICI})
        except requests.RequestException as e:
            print(f"Uyarı: MetalCharts geçmişi alınamadı ({e}); botun kendi kayıtları kullanılacak", file=sys.stderr)
            return None
        if r.status_code == 403:
            print("Bilgi: MetalCharts planında geçmiş veri yok; botun kendi günlük kayıtları kullanılacak.")
            return None
        if r.status_code >= 400:
            print(f"Uyarı: MetalCharts geçmişi alınamadı (HTTP {r.status_code}); kendi kayıtlar kullanılacak",
                  file=sys.stderr)
            return None
        try:
            sonuc[sembol] = {date.fromisoformat(x["timestamp"][:10]): float(x["close"]) for x in r.json()["data"]}
        except (ValueError, KeyError, TypeError) as e:
            print(f"Uyarı: MetalCharts geçmişi okunamadı ({e}); kendi kayıtlar kullanılacak", file=sys.stderr)
            return None
    return sonuc


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
    # Pazar yorumunun orta/uzun vadesi için kayıtlar ~2 yıl tutulur (dosya yine de birkaç yüz KB'yi geçmez).
    sinir = (gun - timedelta(days=800)).isoformat()
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


def _ay_ayir(tarihler, bugun=None):
    """Önceki takvim ayının kayıtlı iş günleri ve karşılaştırma günü.

    Karşılaştırma, önceki ayın son kaydıdır; o ay hiç kayıt yoksa (ör. kayıtların başladığı
    Ekim 2026) ayın ilk kaydına göre hesaplanır ve özet "kısmi" işaretlenir.
    """
    bugun = bugun or datetime.now(TR_SAAT).date()
    ay_son = bugun.replace(day=1) - timedelta(days=1)
    ay_bas = ay_son.replace(day=1)
    bu_ay = sorted(d for d in tarihler if ay_bas <= d <= ay_son and d.weekday() < 5)
    if len(bu_ay) < 5:
        raise VeriYok(f"{AYLAR[ay_bas.month - 1]} {ay_bas.year} için yeterli günlük kayıt yok ({len(bu_ay)} gün).")
    onceki = sorted(d for d in tarihler if d < ay_bas)
    return bu_ay, (onceki[-1] if onceki else None), ay_bas


def aylik_fiyatlari_al(bugun=None):
    gecmis = {date.fromisoformat(k): v for k, v in gecmis_oku().items()}
    gunler, onceki_gun, ay_bas = _ay_ayir(gecmis, bugun)
    kismi = onceki_gun is None
    baz_gun = gunler[0] if kismi else onceki_gun
    son, once = gecmis[gunler[-1]], gecmis[baz_gun]
    return {
        "gram": son["gram"], "gram_once": once["gram"],
        "parite": son["altin"] / son["gumus"], "parite_once": once["altin"] / once["gumus"],
        "dolar": son["dolar"], "dolar_once": once["dolar"],
        "kur_tarihi": son["kur_tarihi"],
        "son_saat": son["saat"],
        "ay": ay_bas.isoformat(), "kismi": kismi, "baz_tarih": baz_gun.isoformat(),
        "gunluk": [{"tarih": g.isoformat(), "gram": gecmis[g]["gram"]} for g in gunler],
    }


def ornek_aylik(kismi=False):
    import math
    f = ornek_fiyatlar()
    gunluk, gun, i = [], date(2026, 10, 1), 0
    while gun.month == 10:
        if gun.weekday() < 5 and (not kismi or gun.day >= 13):
            gunluk.append({"tarih": gun.isoformat(), "gram": round(98.4 + 0.22 * i + 1.7 * math.sin(i / 2.6), 2)})
            i += 1
        gun += timedelta(days=1)
    f["gram"] = gunluk[-1]["gram"]
    f["gram_once"] = gunluk[0]["gram"] if kismi else 97.62
    f.update({"son_saat": "20:00", "ay": "2026-10-01", "kismi": kismi,
              "baz_tarih": gunluk[0]["tarih"] if kismi else "2026-09-30", "gunluk": gunluk})
    return f


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


# Büyük hareket manşeti: değişim bu eşiği (yüzde, mutlak) aşınca görselde "GRAM GÜMÜŞ" başlığının
# yerine ve açıklamanın ilk satırında "Gümüş bugün %3,1 yükseldi" gibi manşet çıkar.
BUYUK_HAREKET_GUNLUK = 2.0   # günlük paylaşımlar: önceki iş gününe göre
BUYUK_HAREKET_HAFTALIK = 5.0  # haftalık özet: önceki haftanın son değerine göre


def buyuk_hareket(d, zaman, esik):
    """d = degisim() sonucu. Eşik aşılmadıysa None."""
    if abs(d["yuzde"]) < esik:
        return None
    fiil = "yükseldi" if d["yon"] == "artis" else "düştü"
    return {"yon": d["yon"], "metin": f"Gümüş {zaman} %{tr_sayi(abs(d['yuzde']), 1)} {fiil}"}


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
        "gram_sayi": round(f["gram"], 2),            # hareketli videoda sayım için (dünden bugüne)
        "gram_once_sayi": round(f["gram_once"], 2),
        "gram_deg": degisim(f["gram"], f["gram_once"]),
        "buyuk_hareket": buyuk_hareket(degisim(f["gram"], f["gram_once"]), "bugün", BUYUK_HAREKET_GUNLUK),
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
    v["buyuk_hareket"] = buyuk_hareket(v["gram_deg"], "bu hafta", BUYUK_HAREKET_HAFTALIK)
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
                 "deger": tr_sayi(d, 2),
                 "oran": round((i * adim) / max(gen - 2 * yan, 1), 3)}   # hareketli videoda belirme sırası
                for i, (g, d) in enumerate(zip(gunler, degerler))]
    v["grafik"] = {"gen": gen, "yuk": yuk, "noktalar": noktalar,
                   "cizgi": " ".join(f"{n['x']},{n['y']}" for n in noktalar),
                   "onceki_y": y(f["gram_once"]), "yon": v["gram_deg"]["yon"]}
    return v


# Ay adlarının bulunma hâli ("ekimde"); ay adı belirli bir tarih bildirmeyince küçük harfle yazılır.
AY_DE = ["ocakta", "şubatta", "martta", "nisanda", "mayısta", "haziranda", "temmuzda",
         "ağustosta", "eylülde", "ekimde", "kasımda", "aralıkta"]
BUYUK_HAREKET_AYLIK = 8.0     # aylık özet: önceki ayın son değerine göre
AY_DEN = ["Ocak'tan", "Şubat'tan", "Mart'tan", "Nisan'dan", "Mayıs'tan", "Haziran'dan", "Temmuz'dan",
          "Ağustos'tan", "Eylül'den", "Ekim'den", "Kasım'dan", "Aralık'tan"]


def aylik_veri_hazirla(f, hesap):
    v = veri_hazirla(f, hesap)
    ay = date.fromisoformat(f["ay"])
    gunler = [date.fromisoformat(g["tarih"]) for g in f["gunluk"]]
    degerler = [g["gram"] for g in f["gunluk"]]
    baz = date.fromisoformat(f["baz_tarih"])
    v["ay_adi"] = f"{AYLAR[ay.month - 1]} {ay.year}"
    v["kismi"] = f["kismi"]
    v["aralik"] = (f"{gunler[0].day}–{gunler[-1].day} {AYLAR[ay.month - 1]}" if f["kismi"] else "")
    v["baz_metin"] = (f"{baz.day} {AY_DEN[baz.month - 1]} bu yana" if f["kismi"]
                      else "önceki ayın son değerine göre")
    zaman = f"{baz.day} {AY_DEN[baz.month - 1]} bu yana" if f["kismi"] else AY_DE[ay.month - 1]
    v["buyuk_hareket"] = buyuk_hareket(v["gram_deg"], zaman, BUYUK_HAREKET_AYLIK)
    i_cok, i_az = degerler.index(max(degerler)), degerler.index(min(degerler))
    v["en_yuksek"] = tr_sayi(degerler[i_cok], 2)
    v["en_yuksek_gun"] = f"{gunler[i_cok].day} {AYLAR[gunler[i_cok].month - 1]}"
    v["en_dusuk"] = tr_sayi(degerler[i_az], 2)
    v["en_dusuk_gun"] = f"{gunler[i_az].day} {AYLAR[gunler[i_az].month - 1]}"
    v["gun_sayisi"] = len(gunler)

    # Grafik: ayın her iş günü; önceki ayın son değeri kesikli çizgi (kısmi ayda yok)
    gen, yuk, ust, alt, yan = 904, 320, 56, 76, 14   # altta en düşük etiketine ve tarihlere yer
    tum = degerler + ([] if f["kismi"] else [f["gram_once"]])
    alt_s, ust_s = min(tum), max(tum)
    aralik = (ust_s - alt_s) or 1
    adim = (gen - 2 * yan) / max(len(degerler) - 1, 1)

    def y(x):
        return round(ust + (ust_s - x) / aralik * (yuk - ust - alt), 1)

    noktalar = [(round(yan + i * adim, 1), y(d)) for i, d in enumerate(degerler)]
    oran = lambda i: round((i * adim) / max(gen - 2 * yan, 1), 3)   # hareketli videoda belirme sırası
    isaretler = []
    for i, ad, deger in [(i_cok, "en yüksek", v["en_yuksek"]), (i_az, "en düşük", v["en_dusuk"]),
                         (len(degerler) - 1, "son", v["gram"])]:
        if any(m["i"] == i for m in isaretler):
            continue
        x, yy = noktalar[i]
        ustte = ad != "en düşük"
        isaretler.append({"i": i, "x": x, "y": yy, "deger": deger, "oran": oran(i),
                          "ty": yy - 22 if ustte else yy + 38,
                          "tx": min(max(x, 70), gen - 70)})
    etiketler = [{"x": noktalar[0][0], "metin": f"{gunler[0].day} {AYLAR[ay.month - 1]}", "yan": "start"},
                 {"x": noktalar[-1][0], "metin": f"{gunler[-1].day} {AYLAR[ay.month - 1]}", "yan": "end"}]
    v["grafik"] = {"gen": gen, "yuk": yuk, "isaretler": isaretler, "etiketler": etiketler,
                   "cizgi": " ".join(f"{x},{yy}" for x, yy in noktalar),
                   "alan": f"{noktalar[0][0]},{yuk - alt} " + " ".join(f"{x},{yy}" for x, yy in noktalar)
                           + f" {noktalar[-1][0]},{yuk - alt}",
                   "taban": yuk - alt,
                   "onceki_y": None if f["kismi"] else y(f["gram_once"]), "yon": v["gram_deg"]["yon"]}
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


HASHTAG_AY = "#gümüş #gramgümüş #gümüşfiyatları #gümüşyatırımı #değerlimetaller"


def hashtag_sec(tur, tarih=None):
    if tur == "hafta":
        hafta_no = (tarih or datetime.now(TR_SAAT).date()).isocalendar()[1]
        return HASHTAG_HAFTA[(hafta_no + 1) % 2]
    return HASHTAG_POST if tur == "post" else HASHTAG_REELS

# Bu türler Reels'in yanında hikâyeye de paylaşılır (aynı video, 9:16).
HIKAYE_TURLERI = {"post", "hafta", "ay"}


# 20:00 özetinin açıklamasında güne göre dönen soru (yorum almak için). Yön tahmini, al/sat
# ya da kişisel finans sorusu yok; takipçinin deneyimini ve ne görmek istediğini sorar.
SORULAR_OZET = [
    "Gram gümüşü en çok nereden takip ediyorsunuz: kuyumcu, banka, uygulama?",
    "Rehberde hangi konuyu görmek istersiniz?",
    "Kuyumcudaki fiyatla buradaki fiyat arasındaki farkı fark ettiniz mi?",
    "Gümüşü en çok hangi birimle düşünüyorsunuz: gram, ons, kilogram?",
    "Altın/gümüş paritesini bu sayfadan önce duymuş muydunuz?",
    "Fiyatları hangi saatte görmek size daha uygun: sabah mı, akşam mı?",
    "Sizin şehrinizde gümüş en çok ne için alınır?",
    "Gümüşle ilk tanışmanız nasıl oldu: hediye, takı, merak?",
    "Bu sayfada başka hangi bilgiyi görmek istersiniz?",
    "Gümüş külçeyi hiç elinize alıp gördünüz mü?",
]
PAYLASIM_SATIRI = "Gümüşü takip eden bir tanıdığınıza gönderebilirsiniz."
# Rıdvan (13 Ekim 2026): takipçi yokken sorular erken. Takipçi artınca SORU_ACIK = True ve
# PAYLASIM_GUNLERI = {1, 3} (salı, perşembe) yapılır. Büyük hareket günlerinde paylaşım satırı
# her zaman çıkar: o paylaşımlar takip etmeyenlere de gösterilir.
SORU_ACIK = False
PAYLASIM_GUNLERI = set()


def _cagri_satirlari(v, tur, gun=None):
    """Açıklamaya eklenecek soru ve paylaşım satırları (boş olabilir)."""
    gun = gun or datetime.now(TR_SAAT).date()
    satirlar = []
    if tur == "post" and SORU_ACIK:
        satirlar.append(f"{SORULAR_OZET[gun.toordinal() % len(SORULAR_OZET)]} Yorumlara yazın 👇")
    if v.get("buyuk_hareket") or (tur == "post" and gun.weekday() in PAYLASIM_GUNLERI):
        satirlar.append(PAYLASIM_SATIRI)
    return ("\n" + "".join(s + "\n" for s in satirlar) + "\n") if satirlar else ""


def _ilk_satir(v, zaman):
    g = v["gram_deg"]
    if v.get("buyuk_hareket"):
        return f"{v['buyuk_hareket']['metin']}: gram gümüş fiyatı {v['gram']} ₺"
    return f"Gram gümüş fiyatı {zaman}: {v['gram']} ₺ ({g['isaret']} {g['metin']})"


def aciklama_yaz(v, tur):
    # İlk satır aranan kelimeyle ("gram gümüş fiyatı") ve rakamla başlar: Instagram araması ve
    # Google ilk satıra en çok ağırlığı verir, akışta da "devamı"ndan önce yalnızca o görünür.
    if tur == "hafta":
        g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
        return (
            f"{_ilk_satir(v, 'bu hafta')}\n"
            f"Haftalık gümüş özeti · {v['aralik']}\n\n"
            f"Haftanın en yükseği: {v['en_yuksek']} ₺ · en düşüğü: {v['en_dusuk']} ₺\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            "Günlük değerler iş günlerinin son paylaşımına (yaklaşık 20:00) aittir; "
            "değişimler önceki haftanın son değerine göredir.\n"
            "Sizce gümüş gelecek hafta ne yöne gider? Yorumlara yazın 👇\n"
            f"{PAYLASIM_SATIRI + chr(10) if v.get('buyuk_hareket') else ''}\n"
            "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
            f"{_kaynak_satirlari(v)}\n\n"
            f"{hashtag_sec(tur)}"
        )
    if tur == "ay":
        g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
        ay = v["ay_adi"].split()[0]
        if v["buyuk_hareket"]:
            ilk = f"{v['buyuk_hareket']['metin']}: gram gümüş {ay.lower()} sonunda {v['gram']} ₺"
        else:
            ilk = f"Gram gümüş fiyatı {ay.lower()} sonunda: {v['gram']} ₺ ({g['isaret']} {g['metin']})"
        not_ = ("Günlük değerler iş günlerinin son paylaşımına (yaklaşık 20:00) aittir; "
                + (f"kayıtlar {v['aralik'].split('–')[0]} {ay} tarihinde başladığı için değişimler o güne göredir."
                   if v["kismi"] else "değişimler önceki ayın son değerine göredir."))
        return (
            f"{ilk}\n"
            f"Aylık gümüş özeti · {v['ay_adi']}{' (' + v['aralik'] + ')' if v['kismi'] else ''}\n\n"
            f"Ayın en yükseği: {v['en_yuksek']} ₺ ({v['en_yuksek_gun']}) · en düşüğü: {v['en_dusuk']} ₺ ({v['en_dusuk_gun']})\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            f"{not_}\n"
            f"{PAYLASIM_SATIRI + chr(10) if v.get('buyuk_hareket') else ''}\n"
            "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
            f"{_kaynak_satirlari(v)}\n\n"
            f"{HASHTAG_AY}"
        )
    baslik = "Günün gümüş özeti" if tur == "post" else "Güncel gümüş fiyatları"
    g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
    return (
        f"{_ilk_satir(v, 'bugün')}\n"
        f"{baslik} · {v['tarih']} · {v['saat']}\n\n"
        f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
        f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
        "Değişimler önceki iş gününe göredir.\n"
        f"{_cagri_satirlari(v, tur)}"
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
    boyut = {"reels": (1080, 1920), "kapak": (1080, 1920), "post": (1080, 1350), "hafta": (1080, 1350), "yasal": (1080, 1350),
             "bilgi": (1080, 1350), "yorum": (1080, 1350), "ay": (1080, 1350), "kisa": (1080, 1920), "sayfa-og": (1200, 630)}[tur]
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


KAPAK_ETIKET = {"reels": "GÜNCEL FİYAT", "post": "GÜNÜN ÖZETİ", "hafta": "HAFTALIK ÖZET", "ay": "AYLIK ÖZET"}


def kapak_verisi(tur, veri):
    """Reels kapağının (templates/kapak.html) büyük satırları: tür, gün, alt satır."""
    simdi = datetime.now(TR_SAAT)
    if tur == "ay":
        gun, yil = veri["ay_adi"].split()
        alt = f"{yil} · {veri['baz_metin'] if veri['kismi'] else 'önceki aya göre'}"
    elif tur == "hafta":
        gun = veri["aralik"].rsplit(" ", 1)[0]          # "05–09 Ekim" (yıl alt satırda)
        alt = f"{veri['aralik'].rsplit(' ', 1)[1]} · önceki haftaya göre"
    else:
        gun = f"{simdi.day} {AYLAR[simdi.month - 1]}"
        alt = f"{GUNLER[simdi.weekday()]} · {veri['saat']}"
    return {"kapak_etiket": KAPAK_ETIKET.get(tur, ""), "kapak_gun": gun, "kapak_alt": alt}


def kapak_uret(tur, veri, jpg_yolu):
    """Profil ızgarasında okunan Reels kapağı (JPEG). Başarısız olursa None; kapak son kareden alınır."""
    try:
        gorsel_uret("kapak", {**veri, **kapak_verisi(tur, veri)}, jpg_yolu)
        return jpg_yolu.name
    except Exception as e:
        print(f"::warning::Kapak üretilemedi, videonun son karesi kullanılacak: {e}")
        return None


ZEMIN_RENGI = "0x121418"   # templates/ortak.css içindeki --zemin ile aynı


VIDEO_FPS = 30


def _ses_girdisi(sure):
    muzik = KOK / "assets" / "muzik.mp3"
    if muzik.exists():
        return (["-stream_loop", "-1", "-i", str(muzik)],
                ["-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={sure - 1.5}:d=1.5,aresample=44100"])
    print("Uyarı: assets/muzik.mp3 yok, video müziksiz üretiliyor", file=sys.stderr)
    return ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"], []


def hareketli_video_uret(tur, veri, mp4_yolu, sure=7):
    """Şablonda window.kare(t) varsa her kareyi tarayıcıda çizip sesli video üretir.

    Şablon hareket tanımlamıyorsa False döner; o zaman durağan video_uret() kullanılır.
    Kareler JPEG olarak doğrudan ffmpeg'e akıtılır (diske yazılmaz).
    """
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
    html = env.get_template(f"{tur}.html").render(**veri)
    if "window.kare" not in html:
        return False
    gecici = SABLONLAR / f"_hareket_{tur}.html"
    gecici.write_text(html, encoding="utf-8")
    ses, ses_filtre = _ses_girdisi(sure)
    goruntu = (f"scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color={ZEMIN_RENGI},format=yuv420p")
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error",
             "-f", "image2pipe", "-framerate", str(VIDEO_FPS), "-c:v", "mjpeg", "-i", "-", *ses,
             "-t", str(sure), "-vf", goruntu, *ses_filtre,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(VIDEO_FPS),
             "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(mp4_yolu)]
    boyut = {"reels": (1080, 1920), "kisa": (1080, 1920)}.get(tur, (1080, 1350))
    try:
        with sync_playwright() as p:
            kwargs = {"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}
            tarayici = p.chromium.launch(**kwargs)
            sayfa = tarayici.new_page(viewport={"width": boyut[0], "height": boyut[1]})
            sayfa.goto(gecici.as_uri())
            sayfa.evaluate("document.fonts.ready")
            sayfa.wait_for_timeout(300)
            if not sayfa.evaluate("typeof window.kare === 'function'"):
                tarayici.close()
                return False   # betik veri eksikliği yüzünden hareketi kapattı
            ff = subprocess.Popen(komut, stdin=subprocess.PIPE)
            try:
                for i in range(int(sure * VIDEO_FPS)):
                    sayfa.evaluate(f"window.kare({i / VIDEO_FPS:.4f})")
                    ff.stdin.write(sayfa.screenshot(type="jpeg", quality=95,
                                                    clip={"x": 0, "y": 0, "width": boyut[0], "height": boyut[1]}))
            finally:
                ff.stdin.close()
                if ff.wait() != 0:
                    raise RuntimeError("ffmpeg hareketli videoyu üretemedi")
            tarayici.close()
    finally:
        gecici.unlink(missing_ok=True)
    return True


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
               "format=yuv420p")   # kararmadan açılış yok: fiyat ilk karede görünsün
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


def _reels_konteyneri(kullanici_id, medya_url, meta, taban_url):
    """Reels konteyneri. Önce tasarlanmış kapakla (cover_url) dener; kapak alınamazsa ya da
    Instagram işleyemezse kapaksız yeniden dener ve videonun son karelerinden birini kullanır
    (hareketli videoda ilk kare sayımın başı olduğu için)."""
    ortak = {"media_type": "REELS", "video_url": medya_url, "caption": meta["aciklama"], "share_to_feed": "true"}
    if meta.get("kapak"):
        kapak_url = taban_url.rstrip("/") + "/" + meta["kapak"]
        try:
            _url_hazir_mi(kapak_url, sure_sn=60)
            k = _istek("POST", f"{kullanici_id}/media", cover_url=kapak_url, **ortak)
            _hazir_olmasini_bekle(k["id"])
            return k
        except RuntimeError as e:
            print(f"::warning::Kapakla paylaşılamadı, son kareyle yeniden deneniyor: {e}")
    k = _istek("POST", f"{kullanici_id}/media", thumb_offset=str(meta.get("kapak_ms", 0)), **ortak)
    _hazir_olmasini_bekle(k["id"])
    return k


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
        k = _reels_konteyneri(kullanici_id, medya_url, meta, taban_url)
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

    konu verilmezse bugünün bölümü bilgi.takvim()'den seçilir; takvimde yoksa paylaşım atlanır.
    """
    import bilgi
    if not konu:
        bugun = datetime.now(TR_SAAT).date().isoformat()
        konu = bilgi.bugunun_bolumu()
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
        gorsel_uret("bilgi", {"b": b, "no": konu, "sayfa": sayfa,
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


def _sayilabilir(metin):
    """Kısa Reels'te sayarak gelecek büyük cevap: ("önek", "31,1035", " g") ya da None."""
    import re
    m = re.match(r"^([%~]?)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)([^\d/]*)$", metin.strip())
    return [m.group(1), m.group(2), m.group(3)] if m else None


def kisa_hazirla(cikti, konu):
    """Gümüş rehberi bölümünden kısa Reels (~12 sn): soru → büyük cevap → tek cümle → profile çağrı.

    Metin bölümün kendisinden gelir (başlık, alt başlık, büyük rakam, ilk sayfanın formülü ve ilk
    maddesi); ayrıca yazılmaz. Açıklama bölümün tam metnini taşır.
    """
    import bilgi
    if not 1 <= konu <= len(bilgi.BOLUMLER):
        raise RuntimeError(f"Konu 1-{len(bilgi.BOLUMLER)} arasında olmalı (verilen: {konu})")
    b = bilgi.BOLUMLER[konu - 1]
    ilk_sayfa = b["sayfalar"][0]
    sayi = _sayilabilir(b["buyuk"])
    veri = {"b": b, "no": konu, "seri": bilgi.SERI, "hesap": hesap_adi(),
            "sayi": json.dumps(sayi, ensure_ascii=False) if sayi else "",
            "formul": ilk_sayfa.get("formul"), "cumle": (ilk_sayfa.get("maddeler") or [b["alt"]])[0]}
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    mp4 = cikti / f"kisa{konu}-{damga}.mp4"
    sure = 12
    if not hareketli_video_uret("kisa", veri, mp4, sure=sure):
        raise RuntimeError("Kısa Reels üretilemedi (şablonda hareket yok)")
    kapak = cikti / f"kapak-kisa{konu}-{damga}.jpg"
    gorsel_uret("kisa", veri, kapak)

    parcalar = [f"{b['baslik']} Kısa cevap: {b['buyuk']}, {b['buyuk_alt']} | Gümüş rehberi #{konu}", b["alt"]]
    parcalar += [bilgi._sayfa_metni(s) for s in b["sayfalar"]]
    parcalar += ["Bölümün kaydırmalı hâli profilde; kaydedin, lazım olunca bakarsınız.",
                 "Bilgi amaçlıdır, yatırım tavsiyesi değildir."]
    kunye = muzik_kunyesi()
    if kunye:
        parcalar.append(f"Müzik: {kunye}")
    parcalar.append(b["hashtag"])
    metin = "\n\n".join(parcalar)
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
    (cikti / "meta.json").write_text(json.dumps({"tur": "kisa", "konu": konu, "dosya": mp4.name, "aciklama": metin,
                                                 "kapak_ms": int((sure - 0.5) * 1000), "kapak": kapak.name},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(metin)
    print(f"\nÜretilen dosya: {mp4}")


def _zaman_coz(zaman):
    """MetalCharts zaman damgası (ISO metin ya da epoch sn/ms) → UTC datetime; çözülemezse None."""
    from datetime import timezone
    try:
        if isinstance(zaman, (int, float)) or (isinstance(zaman, str) and zaman.strip().isdigit()):
            sayi = float(zaman)
            return datetime.fromtimestamp(sayi / 1000 if sayi > 1e11 else sayi, tz=timezone.utc)
        if isinstance(zaman, str) and zaman.strip():
            z = datetime.fromisoformat(zaman.strip().replace("Z", "+00:00"))
            return z if z.tzinfo else z.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def kapanis_fiyati(ecb):
    """Pazar yorumu için o anki son fiyat (1 MetalCharts isteği): (tarih, kayıt) ya da None.

    Hafta sonu piyasa kapalı olduğu için bu, haftanın kapanış fiyatıdır (cuma New York kapanışı ≈
    cumartesi 00:00 TR); cuma 20:00 kaydından sonraki saatleri de kapsar. Kayıt dosyasına yazılmaz,
    yalnızca yorumda kullanılır (günlük ve haftalık paylaşımlar 20:00 kayıtlarıyla tutarlı kalsın).
    """
    try:
        metal = metal_fiyatlari()
    except Exception as e:
        print(f"::warning::Kapanış fiyatı alınamadı ({e}); botun son kaydı kullanılacak")
        return None
    simdi = datetime.now(TR_SAAT)
    zaman = _zaman_coz(metal["XAG"].get("zaman"))
    gun = zaman.date() if zaman else simdi.date()        # UTC tarihi: cuma 21:00 UTC kapanışı cumaya düşer
    gun = min(gun, simdi.date())
    while gun.weekday() >= 5:
        gun -= timedelta(days=1)
    if (simdi.date() - gun).days > 4:
        print(f"::warning::MetalCharts fiyatı eski ({zaman}); botun son kaydı kullanılacak")
        return None
    kur_gunu = max(d for d in ecb if d <= gun)
    gumus, altin, dolar = metal["XAG"]["fiyat"], metal["XAU"]["fiyat"], ecb[kur_gunu]
    saat = "kapanış" if simdi.weekday() >= 5 else simdi.strftime("%H:%M")
    print(f"Son fiyat alındı ({gun:%d.%m.%Y} {saat}): ons gümüş {gumus} $, ons altın {altin} $")
    return gun, {"saat": saat, "gumus": gumus, "altin": altin, "dolar": dolar,
                 "kur_tarihi": kur_gunu.isoformat(), "gram": gumus * dolar / ONS_GRAM}


def yorum_hazirla(cikti, ornek):
    """Pazar yapay zekâ yorumu: kapak + kısa/orta/uzun vade, kaydırmalı 4 görsel. Ayrıntı: bot/yorum.py

    Pazar sabahı bütün verilerle şekillenir: botun günlük kayıtları, o anki (haftanın kapanış)
    fiyatı, 13 aylık dolar/TL, varsa MetalCharts geçmişi ve web aramasıyla derlenen haftanın haberleri.
    """
    import yorum
    bugun = datetime.now(TR_SAAT).date()
    kapanis = None
    if ornek:
        bugun += timedelta(days=(6 - bugun.weekday()) % 7)   # örnekte bu haftanın pazarı gibi
        kayitlar, ecb = yorum.ornek_veri(bugun)
        kayitlar[max(kayitlar)]["saat"] = "kapanış"
        kapanis = max(kayitlar)
        metal, kaynak_notu = None, "yalnızca botun kendi günlük kayıtları"
    else:
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            raise VeriYok("ANTHROPIC_API_KEY tanımlı değil (GitHub → Settings → Secrets and variables → Actions).")
        kayitlar = {date.fromisoformat(k): v for k, v in gecmis_oku().items()}
        son_hafta = [d for d in kayitlar if d >= bugun - timedelta(days=10)]
        if len(son_hafta) < 2:
            raise VeriYok(f"Son 10 günde yeterli günlük kayıt yok ({len(son_hafta)} gün); yorum yazılamaz.")
        ecb = ecb_gecmisi()
        son = kapanis_fiyati(ecb)
        if son:
            kapanis, kayitlar[son[0]] = son[0], son[1]
        metal = metal_gecmisi()
        kaynak_notu = ("MetalCharts 1 yıllık günlük geçmiş + botun günlük kayıtları" if metal
                       else "yalnızca botun kendi günlük kayıtları (geçmiş kısa olabilir)")
        if kapanis:
            kaynak_notu += "; son değer pazar günü alınan güncel fiyat"
    seri = yorum.seri_kur(kayitlar, ecb, metal)
    ist = yorum.vade_istatistikleri(seri, ecb)

    if ornek:
        gelismeler, yz = yorum.ORNEK_GELISMELER, yorum.ORNEK_YORUM
        hatalar = yorum.denetle(yz, gelismeler)
        if hatalar:
            raise RuntimeError(f"Örnek yorum denetimden geçmedi: {hatalar}")
    else:
        gelismeler = yorum.haftanin_gelismeleri(bugun)
        yz = yorum.yz_yorum(yorum.model_girdisi(seri, ecb, ist, bugun, kaynak_notu, gelismeler,
                                                kapanis=kapanis == max(seri)), gelismeler)
        if yz is None:
            raise VeriYok("ANTHROPIC_API_KEY tanımlı değil (GitHub → Settings → Secrets and variables → Actions).")

    son_gun = max(seri)
    son = seri[son_gun]
    _, hafta_once = yorum._deger_once(seri, son_gun - timedelta(days=7))
    if hafta_once is None:
        hafta_once = seri[min(seri)]
    ilk = min(seri)
    hesap = hesap_adi()
    saat = son.get("saat")
    veri_ani = f"{son_gun.day} {AYLAR[son_gun.month - 1]} {GUNLER[son_gun.weekday()]}"
    if saat == "kapanış":
        veri_ani += " kapanışı"
    elif saat:
        veri_ani += f" {saat}"

    def hucre(ad, yuzde):
        return {"ad": ad, "deg": None if yuzde is None else degisim(1 + yuzde / 100, 1)}

    vadeler = []
    for v in yorum.VADELER:
        x = ist[v["anahtar"]]
        not_ = ""
        if not x["veri_yeterli"]:
            not_ = (f"Gram ve ons için {v['etiket'].lower()} kayıt henüz yok · kayıtlar "
                    f"{ilk.day} {AYLAR[ilk.month - 1]} {ilk.year}'de başladı")
        elif x["kisa_kayit"]:
            not_ = f"Kayıtlar {ilk.day} {AYLAR[ilk.month - 1]}'de başladığı için {x['etiket'].lower()}"
        vadeler.append({**v, "etiket": x["etiket"], "not": not_, "yorum": yz[v["anahtar"]],
                        "hucreler": [hucre("Gram gümüş", x["gram"]), hucre("Ons gümüş", x["ons"]),
                                     hucre("Dolar/TL", x["dolar"])]})
    veri = {
        "tarih": f"{bugun.day} {AYLAR[bugun.month - 1]} {bugun.year}",
        "gun": GUNLER[bugun.weekday()],
        "gram": tr_sayi(son["gram"], 2),
        "gram_deg": degisim(son["gram"], hafta_once["gram"]),
        "veri_ani": veri_ani,
        "veri_tarihi": f"{son_gun:%d.%m.%Y}",
        "kur_tarihi_tam": f"{max(d for d in ecb if d <= son_gun):%d.%m.%Y}",
        "vadeler": vadeler,
        "hesap": hesap,
        "dayanak": "Fiyat ve kur verileri + haftanın haberleri" if gelismeler else "Fiyat ve kur verileri",
    }

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    dosyalar = []
    for sayfa in range(len(vadeler) + 1):
        jpg = cikti / f"yorum-{damga}-{sayfa + 1}.jpg"
        gorsel_uret("yorum", {**veri, "sayfa": sayfa, "toplam": len(vadeler) + 1}, jpg)
        dosyalar.append(jpg.name)
    kaynaklar = _kaynak_satirlari(veri).replace(f"\nMüzik: {muzik_kunyesi()}", "")
    metin = yorum.aciklama(veri, yz, kaynaklar, gelismeler)
    (cikti / "meta.json").write_text(json.dumps({"tur": "yorum", "dosyalar": dosyalar, "aciklama": metin,
                                                 "yorum": yz, "istatistik": ist, "gelismeler": gelismeler,
                                                 "son_veri": {"tarih": son_gun, **son}},
                                                ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if gelismeler:
        print("Haftanın gelişmeleri (yapay zekâ özeti, web araması):\n" + gelismeler["metin"] + "\n")
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
    if tur == "kisa":
        import bilgi
        konu = konu or bilgi.bugunun_kisa_bolumu()
        if not konu:
            print("::warning::Paylaşım atlandı: bugün kısa Reels takviminde bölüm yok")
            return
        kisa_hazirla(cikti, konu)
        return
    if tur == "yorum":
        try:
            yorum_hazirla(cikti, ornek)
        except VeriYok as e:
            print(f"::warning::Paylaşım atlandı: {e}")
        return
    try:
        if tur == "hafta":
            fiyat = ornek_haftalik() if ornek else haftalik_fiyatlari_al()
        elif tur == "ay":
            fiyat = ornek_aylik(kismi=os.environ.get("ORNEK_KISMI") == "1") if ornek else aylik_fiyatlari_al()
        else:
            fiyat = ornek_fiyatlar() if ornek else fiyatlari_al(kaydet=True)
    except VeriYok as e:
        # Hata değil: paylaşım bu sefer atlanır, iş akışı sonraki adımları çalıştırmaz.
        print(f"::warning::Paylaşım atlandı: {e}")
        return
    hesap = hesap_adi()
    hazirlayici = {"hafta": haftalik_veri_hazirla, "ay": aylik_veri_hazirla}.get(tur, veri_hazirla)
    veri = hazirlayici(fiyat, hesap)

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    png = cikti / f"{tur}-{damga}.png"
    gorsel_uret(tur, veri, png)
    # Her paylaşım sesli video (Reels) olarak gider; özetler okunabilsin diye biraz daha uzun.
    mp4 = cikti / f"{tur}-{damga}.mp4"
    sure = 7 if tur == "reels" else 10
    if not hareketli_video_uret(tur, veri, mp4, sure=sure):
        video_uret(png, mp4, sure=sure)
    dosya = mp4.name
    kapak = kapak_uret(tur, veri, cikti / f"kapak-{tur}-{damga}.jpg")

    aciklama = aciklama_yaz(veri, tur)
    (cikti / "meta.json").write_text(json.dumps({"tur": tur, "dosya": dosya, "aciklama": aciklama,
                                                 "kapak_ms": int((sure - 0.5) * 1000),
                                                 "kapak": kapak,
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
    h.add_argument("--tur", choices=["reels", "post", "hafta", "ay", "yasal", "bilgi", "kisa", "yorum"], required=True)
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
