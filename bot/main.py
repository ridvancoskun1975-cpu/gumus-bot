"""Gümüş fiyat botu.

Komutlar:
  python bot/main.py hazirla --tur reels|post|hafta|ay|yasal|bilgi|kisa|yorum --cikti site [--ornek] [--konu no]
  python bot/main.py yayinla --cikti site --url https://kullanici.github.io/repo/
  python bot/main.py token-yenile
  python bot/main.py gun-ici      (paylaşımsız gün içi fiyat kaydı; .github/workflows/kaydet.yml)

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


# MetalCharts kotası (ücretsiz plan: ayda 200 "weight"). Her yanıttaki X-RateLimit-* başlıkları günlüğe
# yazılır ve son okunan kalan hak gün içi kayıt dosyasında saklanır: gün içi kayıt (paylaşım yapmayan iş)
# kalan hak KOTA_YEDEK'in altına inince durur, paylaşımlara yetecek hak hep kalır (Rıdvan, 16 Ekim 2026).
SON_KOTA = {}
KOTA_YEDEK = 40


def _kota_oku(basliklar):
    """Yanıt başlıklarından X-RateLimit-* değerlerini SON_KOTA'ya alır ve günlüğe yazar (sayılar gizli değil)."""
    kota = {k.lower(): v for k, v in basliklar.items() if k.lower().startswith("x-ratelimit")}
    if not kota:
        print("MetalCharts kota başlığı yok (X-RateLimit-*).")
        return
    SON_KOTA.clear()
    SON_KOTA.update(kota)
    SON_KOTA["_zaman"] = datetime.now(TR_SAAT).isoformat(timespec="minutes")
    print("MetalCharts kota: " + ", ".join(f"{k}={v}" for k, v in sorted(kota.items())))


def kota_kalan(kota):
    """Kota sözlüğünden aylık kalan hakkı (sayı) çıkarır; bulunamazsa None.
    Dakikalık sınırın (10/dk) başlığı ayrıysa onu değil aylığı seçmeye çalışır."""
    def sayi(v):
        try:
            return int(float(str(v).split(",")[0].split(";")[0].strip()))
        except (TypeError, ValueError):
            return None

    adaylar = []
    for k, v in kota.items():
        if k.startswith("_") or "remaining" not in k or sayi(v) is None:
            continue
        sinir = sayi(kota.get(k.replace("remaining", "limit")))
        # Aylık hak: eşi olan "limit" başlığı aylık ölçekte (≥ 100; ücretsiz plan 200) ya da adında ay geçiyor.
        # Dakikalık sınır (10/dk) aylık sanılırsa gün içi kayıt hep durur; emin değilsek None.
        if (sinir is not None and sinir >= 100) or "month" in k:
            adaylar.append(sayi(v))
    return min(adaylar) if adaylar else None


def son_kayitli_fiyat():
    """Botun en son kaydettiği ons gümüş ve ons altın: günlük kayıtlar (gecmis.json) ile gün içi noktaların
    (gun_ici.json) en yenisi. Yoksa None. Deneme çalıştırmaları MetalCharts yerine bunu kullanır."""
    adaylar = []
    for gun, k in gecmis_oku().items():
        if isinstance(k, dict) and k.get("gumus") and k.get("altin"):
            adaylar.append((gun, k.get("saat", "00:00"), k))
    for gun, noktalar in gun_ici_oku().get("gunler", {}).items():
        for k in noktalar if isinstance(noktalar, list) else []:
            if isinstance(k, dict) and k.get("gumus") and k.get("altin"):
                adaylar.append((gun, k.get("saat", "00:00"), k))
    if not adaylar:
        return None
    gun, saat, k = max(adaylar, key=lambda a: (a[0], a[1]))
    return {"gumus": float(k["gumus"]), "altin": float(k["altin"]), "etiket": f"{gun} {saat}"}


def metal_fiyatlari():
    """MetalCharts'tan ons gümüş (XAG) ve ons altın (XAU) spot fiyatı, USD.

    Deneme çalıştırması (DENEME=true; paylas.yml'de elle "deneme" işaretli) MetalCharts'a istek atmaz, aylık
    hak harcamaz: fiyat botun son kaydından alınır (Rıdvan, 16 Ekim 2026: aylık hak yalnızca zamanlı işlere).
    Hiç kayıt yoksa (önbellek silinmişse) uyarıyla MetalCharts'a gidilir."""
    if _deneme_mi():
        kayit = son_kayitli_fiyat()
        if kayit:
            print(f"Deneme: MetalCharts'a istek atılmadı (hak harcanmadı); fiyat botun son kaydından: {kayit['etiket']}.")
            return {s: {"fiyat": kayit[a], "yuzde24": 0.0, "eski": False, "zaman": kayit["etiket"]}
                    for s, a in (("XAG", "gumus"), ("XAU", "altin"))}
        print("::warning::Deneme: kayıtlı fiyat yok; MetalCharts'tan alınıyor (1 hak harcanır).")
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
        _kota_oku(r.headers)
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
    (MetalCharts'a göre reddedilen istekler aylık hakka sayılmaz) ve None döndürülür.
    Denemede de istenir (17 Ekim 2026): pazar yorumu önizlemesi yarınki gerçek yorumla aynı veriyi göstersin. Starter
    planında ayda 10.000 hak var, iptalden sonra 403 hakka sayılmaz; geçmiş hiçbir yere yazılmaz."""
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
    # Pazar yorumu ve aylık/yıllık özetler için kayıtlar ~2 yıl tutulur (dosya yine de birkaç yüz KB'yi geçmez).
    sinir = (gun - timedelta(days=800)).isoformat()
    gecmis = {k: gecmis[k] for k in sorted(gecmis) if k >= sinir}
    GECMIS_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    GECMIS_DOSYASI.write_text(json.dumps(gecmis, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- gün içi kayıtlar
# Akşam özetinde "Gün içi: en düşük … · en yüksek …" satırı için hafta içi fiyat gün boyunca, paylaşım
# yapılmadan kaydedilir (Rıdvan, 16 Ekim 2026: sabah "şu an fiyat ne", akşam "bugün ne oldu").
# Noktalar: ~10:00 Reels, çarşamba/cuma ~12:00 kart, ~12:35 / 14:35 / 16:35 / 18:35 gün içi kayıt
# (.github/workflows/kaydet.yml) ve ~20:00 özet. Ayrı dosya ve ayrı önbellek: günlük kayıtlara
# (gecmis.json; önceki gün, haftalık, pazar yorumu) dokunmaz, pazar yorumuna da girmez.
GUN_ICI_DOSYASI = KOK / "veri" / "gun_ici.json"
GUN_ICI_DEGISTI = KOK / "veri" / "gun_ici_degisti.txt"   # iş akışı yalnızca bu varsa önbelleğe yazar
GUN_ICI_TUT = 10          # gün; dosyada en çok bu kadar günün noktaları durur
GUN_ICI_EN_AZ = 3         # akşam satırı için en az nokta (akşamki dahil)
GUN_ICI_YAKIN_DK = 60     # gün içi kayıt: son noktadan bu kadar dakika geçmediyse istek harcanmaz (kart günü)
GUN_ICI_PENCERE = ("11:00", "19:30")   # gün içi kayıt işi yalnızca bu saatler arasında çalışır (TR)


def gun_ici_oku():
    try:
        veri = json.loads(GUN_ICI_DOSYASI.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except FileNotFoundError:
        return {}
    except ValueError as e:
        print(f"Uyarı: gün içi kayıt dosyası okunamadı ({e}); boş başlanıyor", file=sys.stderr)
        return {}


def gun_ici_ekle(simdi, nokta):
    """Bugünün noktalarına bir nokta ekler; eski günleri atar; kota bilgisini saklar. Hata paylaşımı durdurmaz."""
    try:
        veri = gun_ici_oku()
        gunler = veri.get("gunler", {})
        bugun = simdi.date().isoformat()
        gunler.setdefault(bugun, []).append({"saat": simdi.strftime("%H:%M"), **nokta})
        sinir = (simdi.date() - timedelta(days=GUN_ICI_TUT)).isoformat()
        veri["gunler"] = {k: gunler[k] for k in sorted(gunler) if k >= sinir}
        if SON_KOTA:
            veri["kota"] = dict(SON_KOTA)
        GUN_ICI_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
        GUN_ICI_DOSYASI.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
        GUN_ICI_DEGISTI.write_text(simdi.isoformat(), encoding="utf-8")
    except Exception as e:
        print(f"::warning::Gün içi nokta yazılamadı: {type(e).__name__}: {e}")


def _deneme_mi():
    return os.environ.get("DENEME", "").strip().lower() == "true"


def gun_ici_noktalari(gun, gecmis_kaydi=None, simdiki=None):
    """O günün gün içi noktaları [(saat, gram)], saate göre sıralı. Sabahki kayıt (gecmis.json'daki günün
    kaydı) ve şimdiki değer de eklenir; aynı saat bir kez sayılır."""
    noktalar = {}
    for n in gun_ici_oku().get("gunler", {}).get(gun.isoformat(), []):
        if isinstance(n, dict) and n.get("saat") and isinstance(n.get("gram"), (int, float)):
            noktalar[n["saat"]] = float(n["gram"])
    if gecmis_kaydi and gecmis_kaydi.get("saat") and gecmis_kaydi.get("gram"):
        noktalar.setdefault(gecmis_kaydi["saat"], float(gecmis_kaydi["gram"]))
    if simdiki:
        noktalar[simdiki[0]] = float(simdiki[1])
    return sorted(noktalar.items())


def gun_ici_satiri(noktalar):
    """Akşam özeti açıklaması: 'Gün içi: en düşük 90,92 ₺ (12:35) · en yüksek 92,10 ₺ (16:35)'.
    Görselde yazan 2 ondalıklı değerlerle; en az GUN_ICI_EN_AZ nokta yoksa None."""
    if len(noktalar) < GUN_ICI_EN_AZ:
        return None
    yuvarli = [(s, round(g, 2)) for s, g in noktalar]
    en_az = min(yuvarli, key=lambda x: (x[1], x[0]))
    en_cok = max(yuvarli, key=lambda x: (x[1], [-int(p) for p in x[0].split(":")]))   # eşitse ilk saat
    if en_az[1] == en_cok[1]:
        return f"Gün içi: {tr_sayi(en_az[1], 2)} ₺, gün boyunca değişmedi"
    return (f"Gün içi: en düşük {tr_sayi(en_az[1], 2)} ₺ ({en_az[0]}) · "
            f"en yüksek {tr_sayi(en_cok[1], 2)} ₺ ({en_cok[0]})")


def gun_ici_kaydet(simdi=None):
    """Paylaşım yapmayan gün içi kayıt (kaydet.yml): fiyatı alır, gun_ici.json'a ekler.
    Atlar: hafta sonu, saat penceresi dışı, son nokta çok yakınsa, MetalCharts kalan hakkı azsa.
    Döner: "kaydedildi" ya da atlama nedeni (sınamalar için)."""
    simdi = simdi or datetime.now(TR_SAAT)
    saat = simdi.strftime("%H:%M")
    if simdi.weekday() >= 5:
        print("Hafta sonu: gün içi kayıt yok.")
        return "hafta-sonu"
    if not (GUN_ICI_PENCERE[0] <= saat <= GUN_ICI_PENCERE[1]):
        # GitHub zamanlı işi çok gecikirse akşam özetiyle çakışmasın (önbellek sırası); kayıt atlanır.
        print(f"::warning::Gün içi kayıt atlandı: saat {saat}, pencere {GUN_ICI_PENCERE[0]}–{GUN_ICI_PENCERE[1]}.")
        return "pencere-disi"
    veri = gun_ici_oku()
    bugunku = veri.get("gunler", {}).get(simdi.date().isoformat(), [])
    if bugunku:
        son = datetime.combine(simdi.date(), datetime.strptime(bugunku[-1]["saat"], "%H:%M").time(), TR_SAAT)
        if (simdi - son) < timedelta(minutes=GUN_ICI_YAKIN_DK):
            print(f"Son nokta {bugunku[-1]['saat']}: {GUN_ICI_YAKIN_DK} dk geçmedi, istek harcanmadı.")
            return "yakin"
    kota = veri.get("kota") or {}
    kalan = kota_kalan(kota)
    if kalan is not None and kota.get("_zaman", "")[:7] == simdi.isoformat()[:7] and kalan < KOTA_YEDEK:
        print(f"::warning::Gün içi kayıt durduruldu: MetalCharts'ta bu ay kalan hak {kalan} "
              f"(< {KOTA_YEDEK}); kalan hak paylaşımlara ayrıldı.")
        return "kota"
    metal = metal_fiyatlari()
    (kur_tarihi, dolar), _ = kurlar()
    gumus, altin = metal["XAG"]["fiyat"], metal["XAU"]["fiyat"]
    gram = gumus * dolar / ONS_GRAM
    gun_ici_ekle(simdi, {"gumus": gumus, "altin": altin, "dolar": dolar,
                         "kur_tarihi": kur_tarihi.isoformat(), "gram": gram, "kaynak": "kayit"})
    print(f"Gün içi nokta kaydedildi: {saat} · gram {tr_sayi(gram, 2)} ₺ "
          f"({len(bugunku) + 1}. nokta; kayıt işinde)")
    return "kaydedildi"


def fiyatlari_al(kaydet=True, kaynak=None):
    metal = metal_fiyatlari()
    (kur_tarihi, dolar), (_, dolar_once) = kurlar()
    gumus, altin = metal["XAG"]["fiyat"], metal["XAU"]["fiyat"]
    gram = gumus * dolar / ONS_GRAM

    simdi = datetime.now(TR_SAAT)
    bugun = simdi.date()
    gecmis = gecmis_oku()
    bugun_kaydi = gecmis.get(bugun.isoformat())       # sabahki Reels'in kaydı (akşam gün içi aralığı için)
    # Gün içi nokta: yalnızca gerçek (deneme olmayan) hafta içi fiyat paylaşımlarında
    if kaynak and bugun.weekday() < 5 and not _deneme_mi():
        gun_ici_ekle(simdi, {"gumus": gumus, "altin": altin, "dolar": dolar,
                             "kur_tarihi": kur_tarihi.isoformat(), "gram": gram, "kaynak": kaynak})
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

    # Deneme günlük kaydı yazmaz: fiyatı zaten kayıttan geliyor ve günün gerçek kaydını bozmasın
    # (eskiden 20:00'den sonra main'de deneme yapmak ertesi günün "önceki gün" değerini değiştiriyordu).
    if kaydet and bugun.weekday() < 5 and not _deneme_mi():
        gecmis_yaz(gecmis, bugun, {"saat": simdi.strftime("%H:%M"), "gumus": gumus, "altin": altin,
                                    "dolar": dolar, "kur_tarihi": kur_tarihi.isoformat(), "gram": gram})
    return {
        "gram": gram, "gram_once": gram_once,
        "parite": altin / gumus, "parite_once": parite_once,
        "dolar": dolar, "dolar_once": dolar_once,
        "kur_tarihi": kur_tarihi.isoformat(),
        # Günlük başlık ve özel gün kuralları (bot/baslik.py) için önceki günlerin gram değerleri
        "gecmis_gram": {k: v["gram"] for k, v in gecmis.items() if k < bugun.isoformat()},
        # Altın–gümüş kartı (bot/kart.py) için önceki günlerin paritesi
        "gecmis_parite": {k: v["altin"] / v["gumus"] for k, v in gecmis.items()
                          if k < bugun.isoformat() and v.get("gumus")},
        # Akşam özetinin gün içi aralığı: [(saat, gram)]
        "gun_ici": gun_ici_noktalari(bugun, bugun_kaydi, (simdi.strftime("%H:%M"), gram)),
    }


def _yuvarla_degisim(simdi, once, basamak=1):
    """degisim() gibi, ama iki değer önce görselde yazan 2 ondalığa yuvarlanır; metin 1 ondalık."""
    d = degisim(round(simdi, 2), round(once, 2))
    yuzde = round(d["yuzde"], basamak)
    if yuzde == 0:
        return {"isaret": "▬", "metin": "%" + tr_sayi(0, basamak)}
    return {"isaret": "▼" if yuzde < 0 else "▲", "metin": "%" + tr_sayi(abs(yuzde), basamak)}


def _ay_once(gun):
    """Bir ay önceki aynı gün (ay sonuna kısaltılır: 31 Mart → 28/29 Şubat)."""
    import calendar
    yil, ay = (gun.year, gun.month - 1) if gun.month > 1 else (gun.year - 1, 12)
    return date(yil, ay, min(gun.day, calendar.monthrange(yil, ay)[1]))


# "Son 1 hafta / Son 1 ay" satırları (akşam özeti; Rıdvan, 16 Ekim 2026): karşılaştırma günü bir hafta / bir ay
# önceki gün ya da (o gün kayıt yoksa: tatil, hata) ondan önceki en yakın kayıt; en çok bu kadar gün geriye.
DONEM_TOLERANS = {"hafta": 3, "ay": 4}


def donem_satirlari(gecmis_gram, gun, gram):
    """['Son 1 hafta: ▼ %2,2 (13 Ekim: 93,88 ₺)', 'Son 1 ay: …'] — kaydı olanlar; kayıt yoksa satır yok."""
    satirlar = []
    seri = {date.fromisoformat(k): v for k, v in gecmis_gram.items()}
    for ad, hedef in (("Son 1 hafta", gun - timedelta(days=7)), ("Son 1 ay", _ay_once(gun))):
        tolerans = DONEM_TOLERANS["hafta" if ad.endswith("hafta") else "ay"]
        adaylar = [d for d in seri if hedef - timedelta(days=tolerans) <= d <= hedef]
        if not adaylar:
            continue
        baz = max(adaylar)
        d = _yuvarla_degisim(gram, seri[baz])
        satirlar.append(f"{ad}: {d['isaret']} {d['metin']} ({baz.day} {AYLAR[baz.month - 1]}: "
                        f"{tr_sayi(seri[baz], 2)} ₺)")
    return satirlar


def kaynak_satiri(f, donem):
    """Haftalık/aylık özet: 'Haftanın kaynağı: ons gümüş ▼ %2,3 · dolar/TL ▲ %0,1' (gram = ons × kur;
    iki parçanın değişimi). Ons verisi yoksa None (Rıdvan, 16 Ekim 2026: yeri günlük değil haftalık/aylık)."""
    if not (f.get("ons") and f.get("ons_once") and f.get("dolar") and f.get("dolar_once")):
        return None
    o = degisim(f["ons"], f["ons_once"])
    k = degisim(f["dolar"], f["dolar_once"])

    def yaz(d):
        y = round(d["yuzde"], 1)
        return "▬ %0,0" if y == 0 else f"{'▼' if y < 0 else '▲'} %{tr_sayi(abs(y), 1)}"
    return f"{donem} kaynağı: ons gümüş {yaz(o)} · dolar/TL {yaz(k)}"


def _hafta_ayir(tarihler, bugun=None):
    """Son tamamlanan haftanın kayıtlı iş günlerini ve karşılaştırma gününü döndürür: (günler, önceki_gün).

    Hafta sonu çalışınca biten haftayı, hafta içi (elle) çalışınca yarım kalan bu
    haftayı değil bir önceki tam haftayı alır.
    Önceki haftaya ait kayıt yoksa (kayıtlar bu hafta başladı, 13 Ekim 2026) özet atlanmaz: önceki_gün None
    döner ve değişim haftanın ilk kaydına göre hesaplanır (kısmi hafta; aylık özetteki kuralın aynısı).
    Rıdvan, 14 Ekim 2026: ilk haftadan eksik olamaz; ücretsiz ve zahmetsiz olsun (dış geçmiş verisi yok).
    """
    bugun = bugun or datetime.now(TR_SAAT).date()
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
        if any(d < pazartesi for d in tarihler):
            raise VeriYok("Önceki haftaya ait kayıt yok; haftalık değişim hesaplanamıyor.")
        print(f"Kayıtlar {bu_hafta[0]:%d.%m.%Y}'de başladı: haftalık değişim haftanın ilk kaydına göre (kısmi hafta).")
        return bu_hafta, None
    return bu_hafta, onceki[-1]


def haftalik_fiyatlari_al():
    gecmis = {date.fromisoformat(k): v for k, v in gecmis_oku().items()}
    gunler, onceki_gun = _hafta_ayir(gecmis)
    kismi = onceki_gun is None
    baz_gun = gunler[0] if kismi else onceki_gun
    son, once = gecmis[gunler[-1]], gecmis[baz_gun]
    return {
        "gram": son["gram"], "gram_once": once["gram"],
        "parite": son["altin"] / son["gumus"], "parite_once": once["altin"] / once["gumus"],
        "dolar": son["dolar"], "dolar_once": once["dolar"],
        "ons": son.get("gumus"), "ons_once": once.get("gumus"),    # "Haftanın kaynağı" satırı
        "kur_tarihi": son["kur_tarihi"],
        "son_saat": son["saat"],
        "kismi": kismi, "baz_tarih": baz_gun.isoformat(),
        "gunluk": [{"tarih": g.isoformat(), "gram": gecmis[g]["gram"]} for g in gunler],
        "donem_kayit": _donem_kayit(gecmis, gunler[-1]),
    }


def _donem_kayit(gecmis, son_gun):
    """Dönem özetinin goril kutlaması için (bot/baslik.py → donem_ozel) dönem sonuna kadarki bütün kayıtlar.
    Anahtar bilerek "gecmis_gram" değil: o, günlük başlık ve özel gün görselini (gun_durumu) açar."""
    return {g.isoformat(): v["gram"] for g, v in gecmis.items() if g <= son_gun}


def donem_ozel_al(f, gunler):
    """Haftalık/aylık özette gorilin kutlaması; kayıt yoksa ya da hata olursa None (paylaşım etkilenmez)."""
    if not f.get("donem_kayit"):
        return None
    try:
        import baslik
        seri = {date.fromisoformat(k): v for k, v in f["donem_kayit"].items()}
        return baslik.donem_ozel(seri, gunler)
    except Exception as e:
        print(f"::warning::Dönem özel günü hesaplanamadı, kutlamasız devam ediliyor: {type(e).__name__}: {e}")
        return None


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
        "ons": son.get("gumus"), "ons_once": once.get("gumus"),    # "Ayın kaynağı" satırı
        "kur_tarihi": son["kur_tarihi"],
        "son_saat": son["saat"],
        "ay": ay_bas.isoformat(), "kismi": kismi, "baz_tarih": baz_gun.isoformat(),
        "gunluk": [{"tarih": g.isoformat(), "gram": gecmis[g]["gram"]} for g in gunler],
        "donem_kayit": _donem_kayit(gecmis, gunler[-1]),
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
    # Örnek kayıtlar: ay içinde 100 ₺ ilk kez aşılır → goril kutlar (bot/baslik.py → donem_ozel)
    f["donem_kayit"] = {**({} if kismi else {"2026-09-30": 97.62}), **{g["tarih"]: g["gram"] for g in gunluk}}
    f.update({"son_saat": "20:00", "ay": "2026-10-01", "kismi": kismi,
              "baz_tarih": gunluk[0]["tarih"] if kismi else "2026-09-30", "gunluk": gunluk})
    return f


# Haftalık özet örnekleri (ORNEK_HAFTA=<ad>, goril önizlemeleri için): (günlük değerler, önceki haftanın son değeri)
ORNEK_HAFTALAR = {
    "sevinen": ([100.62, 101.94, 101.18, 102.49, 103.79], 98.0),        # +%5,91
    "uzulen": ([103.1, 101.9, 100.4, 99.2, 97.6], 104.0),               # −%6,15
    "istif": ([100.2, 100.9, 100.4, 100.7, 100.6], 100.1),              # +%0,50
}


def ornek_haftalik(kismi=False):
    f = ornek_fiyatlar()
    f["son_saat"] = "20:00"
    degerler, once = ORNEK_HAFTALAR.get(os.environ.get("ORNEK_HAFTA", "").strip(),
                                        ([100.62, 101.94, 101.18, 102.49, 103.79], 99.85))
    f["gunluk"] = [{"tarih": t, "gram": v} for t, v in
                   zip(["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"], degerler)]
    f["gram"] = degerler[-1]
    if kismi:                                   # kayıtlar hafta ortasında başlamış: salı–cuma, baz salı
        f["gunluk"] = f["gunluk"][1:]
    f["gram_once"] = f["gunluk"][0]["gram"] if kismi else once
    f.update({"kismi": kismi, "baz_tarih": f["gunluk"][0]["tarih"] if kismi else "2026-10-02"})
    return f


def ornek_fiyatlar():
    f = {"gram": 103.79, "gram_once": 102.49, "parite": 66.2, "parite_once": 66.77,
         "dolar": 49.25, "dolar_once": 49.21, "kur_tarihi": "2026-10-12"}
    # Altın–gümüş kartı örneği: önceki 5 haftanın cuma kapanışı (örnek değerler)
    bugun = datetime.now(TR_SAAT).date()
    cuma = bugun - timedelta(days=bugun.weekday() + 3)
    f["gecmis_parite"] = {(cuma - timedelta(weeks=i)).isoformat(): v
                          for i, v in enumerate([66.77, 67.31, 65.62, 64.95, 65.88])}
    senaryo = os.environ.get("ORNEK_SENARYO", "").strip()
    if senaryo:
        f.update(ornek_senaryo(senaryo))
    return f


# Yerel deneme için günlük başlık ve özel gün örnekleri:
#   ORNEK_SENARYO=seri python bot/main.py hazirla --tur reels --cikti <klasör> --ornek
# Değerler eskiden yeniye önceki iş günlerinin kayıtlarıdır; sonuncusu bugünkü değerdir.
_DUZ = [95.0, 95.4, 95.1, 95.3, 95.2]
ORNEK_SENARYOLAR = {
    "seri": [97.6, 97.2, 95.1, 95.6, 96.0, 96.42],                       # Üst üste 3. gün yükseliş
    "donus": [97.0, 94.2, 94.7, 95.3, 95.9, 95.48],                      # 3 günlük yükseliş sona erdi
    "yuksek": [99.0] + _DUZ * 3 + [96.04],                               # Son 3 haftanın en yükseği
    "dusuk": [90.0, 95.0, 95.4, 95.1, 95.3, 95.6, 94.71],                # Son 1 haftanın en düşüğü
    "esik-alti": [101.0, 100.6, 100.9, 100.2, 100.3, 99.58],             # 100 liranın altına indi
    "esik": [96.1, 96.9, 97.4, 96.8, 97.9, 98.6, 98.2, 99.12, 100.42],   # özel: 100 lirayı aştı
    "zirve": [99.0] + [round(v + 0.9 * math.sin(i / 2.1), 2) for i, v in enumerate(_DUZ * 5)] + [96.84],   # özel: son 1 ayın en yükseği
    # Goril önizlemeleri (GORIL_ZORLA ile): hâle uyan değişim, özel gün çıkmasın diye yakın geçmişte daha yüksek değer
    "goril-sevinen": _DUZ * 3 + [101.0, 95.2, 98.44],                    # +%3,40
    "goril-uzulen": _DUZ * 3 + [95.3, 92.35],                            # −%3,10
    "goril-gezinen": _DUZ * 3 + [97.0, 95.3, 94.54],                     # −%0,80
    "goril-istif": _DUZ * 3 + [97.0, 95.3, 95.49],                       # +%0,20
    "goril-buyuk": [x * 13 for x in _DUZ * 3 + [101.0, 95.2, 98.44]],    # +%3,40, 1.279,72 ₺: goril sığmaz, gorilsiz
}


def ornek_senaryo(ad):
    import baslik
    if ad not in ORNEK_SENARYOLAR:
        raise RuntimeError(f"ORNEK_SENARYO şunlardan biri olmalı: {', '.join(ORNEK_SENARYOLAR)}")
    *onceki, bugunku = ORNEK_SENARYOLAR[ad]
    seri, gun = {}, datetime.now(TR_SAAT).date()
    for v in reversed(onceki):
        gun = baslik.onceki_is_gunu(gun)
        seri[gun.isoformat()] = v
    return {"gram": bugunku, "gram_once": onceki[-1], "gecmis_gram": seri}


# ---------------------------------------------------------------- biçimlendirme

def tr_sayi(x, basamak=2):
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


# Büyük hareket manşeti: değişim bu eşiği (yüzde, mutlak) aşınca görselde "GRAM GÜMÜŞ" başlığının
# yerine ve açıklamanın ilk satırında "Gümüş bugün %3,1 yükseldi" gibi manşet çıkar.
BUYUK_HAREKET_GUNLUK = 2.0   # günlük paylaşımlar: önceki iş gününe göre
# 4:5 videoların (akşam, haftalık, aylık özet) içerik genişliği: 1080 − sol 88 − sağ 180. Sağdaki 180 px ve alttaki
# 140 px telefonda Reels ekranının beğeni/yorum düğmelerine ve hesap adı satırına bırakılır (Rıdvan'ın 17 Ekim 2026
# ekran görüntüleriyle ölçüldü; Rıdvan onayladı: "A için önerilen çizimler uygun. uygula.").
GEN_45 = 1080 - 88 - 180
BUYUK_HAREKET_HAFTALIK = 5.0  # haftalık özet: önceki haftanın son değerine göre


def buyuk_hareket(d, zaman, esik):
    """d = degisim() sonucu. Eşik aşılmadıysa None.
    Görseldeki gibi 2 ondalığa yuvarlanmış değere bakar: görselde %2,00 yazıyorsa manşet de çıkar (Rıdvan,
    16 Ekim 2026; rakam, manşet ve goril hep uyumlu)."""
    if round(abs(d["yuzde"]), 2) < esik:
        return None
    fiil = "yükseldi" if d["yon"] == "artis" else "düştü"
    # zaman boşsa (sabah Reels'i) "Gümüş %3,4 yükseldi": hareket gece olmuştur, görselde altında "önceki güne göre"
    return {"yon": d["yon"], "metin": " ".join(p for p in ("Gümüş", zaman, f"%{tr_sayi(abs(d['yuzde']), 1)}", fiil) if p)}


# Parite satırı (Rıdvan, 16 Ekim 2026): görselde paritenin altında, ne anlama geldiğini söyleyen tek cümle; rakam
# zaten satırda. Gümüş yatırımcısının gözünden ama "altına karşı" (rehber #4: parite düşerse gümüş altına göre
# pahalanmış demektir). Gümüşün TL fiyatı düştüğü günde de doğru: kıyas altınla. Okun rengi bilerek standart kalır
# (düşüş kırmızı, yükseliş yeşil; Rıdvan: "herkesin gördüğü alıştığı standart bu"), cümle anlamı söyler.
def parite_cumlesi(d, zaman):
    """d = degisim() sonucu; zaman "bugün" / "bu hafta" / "bu ay". Görseldeki gibi 2 ondalığa yuvarlanır."""
    y = round(d["yuzde"], 2)
    if y == 0:
        return f"Gümüşün altına karşı değeri {zaman} değişmedi"
    return f"Gümüş {zaman} altına karşı değer {'kazandı' if y < 0 else 'kaybetti'}"


def gorsel_parite_cumlesi(veri, tur):
    """Parite cümlesi yalnız akşam özeti, haftalık ve aylık özette (Rıdvan, 16 Ekim 2026: "bugün" bütün günü kapsar,
    sabah erken). Sabah Reels'i önceki akşamın kaydıyla kıyaslar, gün henüz bitmedi; orada eski tanım satırı
    ("1 ons altın kaç ons gümüş eder") kalır. Reels takip etmeyenlere de ulaştığı için tanım yeni gelene yarar.
    Aynı kural sabah özel gün görseline de uyar."""
    return None if tur == "reels" else veri.get("parite_cumle")


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


def veri_hazirla(f, hesap, tur=None):
    """tur "reels" (sabah): gün daha bitmedi, manşette "bugün" yok ve bugünü tamamlanmış gün sayan başlıklar çıkmaz
    (Rıdvan, 16 Ekim 2026 23:00). Sabahki değişim önceki iş gününün akşam kaydına göredir (gece boyunca)."""
    sabah = tur == "reels"
    simdi = datetime.now(TR_SAAT)
    kur_gunu = date.fromisoformat(f["kur_tarihi"])
    return {
        "tarih": f"{simdi.day:02d} {AYLAR[simdi.month - 1]} {simdi.year}",
        "saat": simdi.strftime("%H:%M"),
        "gram": tr_sayi(f["gram"], 2),
        "gram_sayi": round(f["gram"], 2),            # hareketli videoda sayım için (dünden bugüne)
        "gram_once_sayi": round(f["gram_once"], 2),
        "gram_deg": degisim(f["gram"], f["gram_once"]),
        "buyuk_hareket": buyuk_hareket(degisim(f["gram"], f["gram_once"]), "" if sabah else "bugün",
                                       BUYUK_HAREKET_GUNLUK),
        "parite": tr_sayi(f["parite"], 1),
        "parite_deg": degisim(f["parite"], f["parite_once"]),
        "parite_cumle": parite_cumlesi(degisim(f["parite"], f["parite_once"]), "bugün"),
        "dolar": tr_sayi(f["dolar"], 2),
        "dolar_deg": degisim(f["dolar"], f["dolar_once"]),
        "kur_tarihi": f"{kur_gunu.day} {AYLAR[kur_gunu.month - 1]}",
        "kur_tarihi_tam": f"{kur_gunu:%d.%m.%Y}",
        "kaynak_metal": KAYNAK_METAL,
        "kaynak_kur": KAYNAK_KUR,
        "hesap": hesap,
        **gun_durumu(f, simdi.date(), sabah),
        **ozet_ek_satirlari(f, simdi.date()),
    }


def ozet_ek_satirlari(f, gun):
    """Akşam özeti açıklamasına (yalnız post) gün içi aralık ve son 1 hafta / 1 ay satırları.
    Veri yoksa satır yok; bir hata paylaşımı durdurmaz."""
    try:
        gun_ici = gun_ici_satiri(f["gun_ici"]) if f.get("gun_ici") else None
        donem = donem_satirlari(f["gecmis_gram"], gun, f["gram"]) if "gecmis_gram" in f else []
        return {"gun_ici_satiri": gun_ici, "donem_satirlari": donem}
    except Exception as e:
        print(f"::warning::Gün içi / dönem satırları hesaplanamadı, satırsız devam ediliyor: {type(e).__name__}: {e}")
        return {"gun_ici_satiri": None, "donem_satirlari": []}


def gun_durumu(f, gun, sabah=False):
    """Günlük başlık ve özel gün (bot/baslik.py). Yalnızca hafta içi fiyat paylaşımlarında
    (f içinde önceki günlerin kayıtları varsa) hesaplanır; bir hata paylaşımı durdurmaz."""
    bos = {"ozel": None, "gun_baslik": None, "baslik_notu": None}
    if "gecmis_gram" not in f:
        return bos
    try:
        import baslik
        seri = {date.fromisoformat(k): v for k, v in f["gecmis_gram"].items()}
        d = baslik.degerlendir(seri, gun, f["gram"], sabah=sabah)
        ozel = d["ozel"]
        if ozel:
            ozel["grafik"] = ozel_grafik(ozel, min(seri))
        buyuk = buyuk_hareket(degisim(f["gram"], f["gram_once"]), "bugün", BUYUK_HAREKET_GUNLUK)
        # Öncelik: özel gün > büyük hareket manşeti > günlük başlık
        return {"ozel": ozel, "gun_baslik": None if (ozel or buyuk) else d["baslik"],
                "baslik_notu": d["not"] if (ozel or (d["baslik"] and not buyuk)) else None}
    except Exception as e:
        print(f"::warning::Günlük başlık hesaplanamadı, başlıksız devam ediliyor: {type(e).__name__}: {e}")
        return bos


def ozel_grafik(ozel, ilk_kayit):
    """Özel görseldeki grafik: son günlerin kayıtları, bugünün noktası ve kesikli karşılaştırma
    çizgisi (aşılan eşik ya da önceki en yüksek)."""
    veri = ozel["grafik"]                      # [(tarih, gram)], sonuncusu bugün
    gen, yuk, ust, alt, yan = 814, 300, 64, 52, 14
    degerler = [v for _, v in veri]
    alt_s, ust_s = min(degerler + [ozel["cizgi"]]), max(degerler + [ozel["cizgi"]])
    aralik = (ust_s - alt_s) or 1
    adim = (gen - 2 * yan) / max(len(veri) - 1, 1)

    def y(x):
        return round(ust + (ust_s - x) / aralik * (yuk - ust - alt), 1)

    noktalar = [(round(yan + i * adim, 1), y(v)) for i, v in enumerate(degerler)]
    ilk_gun = veri[0][0]
    return {"gen": gen, "yuk": yuk,
            "cizgi": " ".join(f"{x},{yy}" for x, yy in noktalar),
            "alan": f"{noktalar[0][0]},{yuk - alt} " + " ".join(f"{x},{yy}" for x, yy in noktalar)
                    + f" {noktalar[-1][0]},{yuk - alt}",
            "taban": yuk - alt,
            "ref_y": y(ozel["cizgi"]), "ref_etiket": ozel["cizgi_etiket"],
            "son": {"x": noktalar[-1][0], "y": noktalar[-1][1], "deger": tr_sayi(degerler[-1], 2)},
            "ilk_gun": f"{ilk_gun.day} {AYLAR[ilk_gun.month - 1]}",
            "kayit_notu": ("Günlük kayıtlar: iş günlerinin son paylaşımı (~20:00) · başlangıç "
                           f"{ilk_kayit.day} {AYLAR[ilk_kayit.month - 1]} {ilk_kayit.year}")}


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
    v["kismi"] = bool(f.get("kismi"))
    baz = date.fromisoformat(f["baz_tarih"]) if f.get("baz_tarih") else None
    # Kısmi haftada (kayıtlar bu hafta başladı) karşılaştırma haftanın ilk kaydına göre; görselde ve açıklamada yazılır
    v["baz_metin"] = (f"{GUNLER[baz.weekday()]} {baz.day} {AY_DEN[baz.month - 1]} bu yana" if v["kismi"]
                      else "önceki haftanın son değerine göre")
    v["baz_gorsel"] = v["baz_metin"] if v["kismi"] else "Önceki haftanın son değerine göre"
    v["buyuk_hareket"] = buyuk_hareket(v["gram_deg"], "bu hafta", BUYUK_HAREKET_HAFTALIK)
    v["donem_ozel"] = donem_ozel_al(f, gunler)     # goril kutlaması (bot/goril.py)
    v["en_yuksek"] = tr_sayi(max(degerler), 2)
    v["en_dusuk"] = tr_sayi(min(degerler), 2)
    v["kaynak_satiri"] = kaynak_satiri(f, "Haftanın")
    v["parite_cumle"] = parite_cumlesi(v["parite_deg"], "bu hafta")

    # Grafik: gram gümüşün günlük değerleri, önceki haftanın son değeri kesikli çizgi (kısmi haftada çizgi yok)
    gen, yuk, kenar, yan = GEN_45, 150, 30, 64   # yükseklik 230 → 150: büyüyen yazılara yer (16 Ekim 2026)
    tum = degerler + ([] if v["kismi"] else [f["gram_once"]])
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
                   "onceki_y": None if v["kismi"] else y(f["gram_once"]), "yon": v["gram_deg"]["yon"]}
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
    v["ay_de"] = AY_DE[ay.month - 1]                # goril kutlama satırı: "ekimde"
    v["kismi"] = f["kismi"]
    v["aralik"] = (f"{gunler[0].day}–{gunler[-1].day} {AYLAR[ay.month - 1]}" if f["kismi"] else "")
    v["baz_metin"] = (f"{baz.day} {AY_DEN[baz.month - 1]} bu yana" if f["kismi"]
                      else "önceki ayın son değerine göre")
    zaman = f"{baz.day} {AY_DEN[baz.month - 1]} bu yana" if f["kismi"] else AY_DE[ay.month - 1]
    v["buyuk_hareket"] = buyuk_hareket(v["gram_deg"], zaman, BUYUK_HAREKET_AYLIK)
    v["donem_ozel"] = donem_ozel_al(f, gunler)     # goril kutlaması (bot/goril.py)
    i_cok, i_az = degerler.index(max(degerler)), degerler.index(min(degerler))
    v["en_yuksek"] = tr_sayi(degerler[i_cok], 2)
    v["en_yuksek_gun"] = f"{gunler[i_cok].day} {AYLAR[gunler[i_cok].month - 1]}"
    v["en_dusuk"] = tr_sayi(degerler[i_az], 2)
    v["en_dusuk_gun"] = f"{gunler[i_az].day} {AYLAR[gunler[i_az].month - 1]}"
    v["gun_sayisi"] = len(gunler)
    v["kaynak_satiri"] = kaynak_satiri(f, "Ayın")
    v["parite_cumle"] = parite_cumlesi(v["parite_deg"], "bu ay")

    # Grafik: ayın her iş günü; önceki ayın son değeri kesikli çizgi (kısmi ayda yok)
    gen, yuk, ust, alt, yan = GEN_45, 320, 56, 76, 14   # altta en düşük etiketine ve tarihlere yer
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
# Haftalık özet iki set arasında hafta hafta döner (ISO hafta numarası çiftse 1., tekse 2. set;
# ilk haftalık özet 17 Ekim 2026 = 42. hafta, yatırım ağırlıklı 1. setle başlar — Rıdvan 14 Ekim 2026).
HASHTAG_HAFTA = (
    "#gümüş #gramgümüş #gümüşyatırımı #gümüşfiyatları #değerlimetaller",
    "#gümüş #gramgümüş #külçegümüş #gumus #silver",
)


HASHTAG_AY = "#gümüş #gramgümüş #gümüşfiyatları #gümüşyatırımı #değerlimetaller"


def hashtag_sec(tur, tarih=None):
    if tur == "hafta":
        hafta_no = (tarih or datetime.now(TR_SAAT).date()).isocalendar()[1]
        return HASHTAG_HAFTA[hafta_no % 2]
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
# Rıdvan 19 Ekim 2026: soru (günlük, haftalık ve hikâye anketi) iptal, açılmaz; açmak için yeni karar
# gerekir. PAYLASIM_GUNLERI de kapalı. Büyük hareket günlerinde paylaşım satırı
# her zaman çıkar: o paylaşımlar takip etmeyenlere de gösterilir.
SORU_ACIK = False
PAYLASIM_GUNLERI = set()


def _cagri_satirlari(v, tur, gun=None):
    """Açıklamaya eklenecek soru ve paylaşım satırları (boş olabilir)."""
    gun = gun or datetime.now(TR_SAAT).date()
    satirlar = []
    if tur == "post" and SORU_ACIK:
        satirlar.append(f"{SORULAR_OZET[gun.toordinal() % len(SORULAR_OZET)]} Yorumlara yazın 👇")
    if v.get("buyuk_hareket") or v.get("ozel") or (tur == "post" and gun.weekday() in PAYLASIM_GUNLERI):
        satirlar.append(PAYLASIM_SATIRI)
    return ("\n" + "".join(s + "\n" for s in satirlar) + "\n") if satirlar else ""


def _ilk_satir(v, zaman):
    g = v["gram_deg"]
    if v.get("ozel"):
        return f"{v['ozel']['manset']}: {v['gram']} ₺ ({g['isaret']} {g['metin']})"
    if v.get("buyuk_hareket"):
        return f"{v['buyuk_hareket']['metin']}: gram gümüş fiyatı {v['gram']} ₺"
    if v.get("gun_baslik"):
        return f"{v['gun_baslik']['metin']}: gram gümüş fiyatı {zaman} {v['gram']} ₺ ({g['isaret']} {g['metin']})"
    return f"Gram gümüş fiyatı {zaman}: {v['gram']} ₺ ({g['isaret']} {g['metin']})"


def _ozel_satiri(v):
    """Özel günde açıklamaya eklenen ayrıntı satırı (boş olabilir)."""
    o = v.get("ozel")
    if not o:
        return ""
    parcalar = [f"Önceki iş günü: {tr_sayi(v['gram_once_sayi'], 2)} ₺"] + ([o["alt"]] if o.get("alt") else [])
    return " · ".join(parcalar) + "\n\n"


GUN_ICI_NOTU = "Gün içi aralık, gün boyunca yaklaşık 2 saatte bir alınan fiyatlara göredir."


def _ozet_ek(v):
    """Akşam özeti: başlık satırının altına gün içi aralık ve son 1 hafta / 1 ay (veri varsa)."""
    satirlar = ([v["gun_ici_satiri"]] if v.get("gun_ici_satiri") else []) + list(v.get("donem_satirlari") or [])
    return "".join(s + "\n" for s in satirlar)


def site_satiri():
    """Haftalık ve aylık özetin açıklamasındaki site satırı (Rıdvan, 19 Ekim 2026: web sayfası tanıtımı, 1. madde;
    günlük fiyat paylaşımlarına ve pazar analizine eklenmez)."""
    import bilgi
    return f"Son 30 günün grafiği ve hesap makinesi: {bilgi.SITE} (bağlantı biyografide)"


def aciklama_yaz(v, tur):
    # İlk satır aranan kelimeyle ("gram gümüş fiyatı") ve rakamla başlar: Instagram araması ve
    # Google ilk satıra en çok ağırlığı verir, akışta da "devamı"ndan önce yalnızca o görünür.
    if tur == "hafta":
        g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
        return (
            f"{_ilk_satir(v, 'bu hafta')}\n"
            f"{v.get('goril_satiri', '')}"
            f"Haftalık gümüş özeti · {v['aralik']}\n"
            f"{v['kaynak_satiri'] + chr(10) if v.get('kaynak_satiri') else ''}\n"
            f"Haftanın en yükseği: {v['en_yuksek']} ₺ · en düşüğü: {v['en_dusuk']} ₺\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            "Günlük değerler iş günlerinin son paylaşımına (yaklaşık 20:00) aittir; "
            + (f"değişimler {v['baz_metin']}dır (günlük kayıtlar o gün başladı; önceki haftaya ait kayıt yok).\n"
               if v["kismi"] else "değişimler önceki haftanın son değerine göredir.\n")
            # Haftalık soru kalktı (Rıdvan, 19 Ekim 2026: 'evet zaten anket iptal ettik').
            + (f"{v['pazar_hatirlatma']['kalin']} · {v['pazar_hatirlatma']['metin']}\n" if v.get("pazar_hatirlatma") else "")
            + f"{PAYLASIM_SATIRI + chr(10) if v.get('buyuk_hareket') else ''}\n"
            + f"{site_satiri()}\n\n"
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
            f"{v.get('goril_satiri', '')}"
            f"Aylık gümüş özeti · {v['ay_adi']}{' (' + v['aralik'] + ')' if v['kismi'] else ''}\n"
            f"{v['kaynak_satiri'] + chr(10) if v.get('kaynak_satiri') else ''}\n"
            f"Ayın en yükseği: {v['en_yuksek']} ₺ ({v['en_yuksek_gun']}) · en düşüğü: {v['en_dusuk']} ₺ ({v['en_dusuk_gun']})\n"
            f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
            f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
            f"{not_}\n"
            f"{PAYLASIM_SATIRI + chr(10) if v.get('buyuk_hareket') else ''}\n"
            f"{site_satiri()}\n\n"
            "Bilgi amaçlıdır, yatırım tavsiyesi değildir.\n\n"
            f"{_kaynak_satirlari(v)}\n\n"
            f"{HASHTAG_AY}"
        )
    baslik = "Günün gümüş özeti" if tur == "post" else "Güncel gümüş fiyatları"
    g, p, d = v["gram_deg"], v["parite_deg"], v["dolar_deg"]
    return (
        f"{_ilk_satir(v, 'bugün')}\n"
        f"{v.get('goril_satiri', '') if tur in ('post', 'reels') else ''}"
        f"{baslik} · {v['tarih']} · {v['saat']}\n"
        f"{_ozet_ek(v) if tur == 'post' else ''}\n"
        f"Altın/Gümüş paritesi: {v['parite']} ({p['isaret']} {p['metin']})\n"
        f"Dolar/TL: {v['dolar']} ₺ ({d['isaret']} {d['metin']})\n\n"
        f"{_ozel_satiri(v)}"
        f"Değişimler önceki iş gününe göredir."
        f"{' ' + GUN_ICI_NOTU if tur == 'post' and v.get('gun_ici_satiri') else ''}"
        f"{' ' + v['baslik_notu'] if v.get('baslik_notu') else ''}\n"
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
             "bilgi": (1080, 1350), "yorum": (1080, 1350), "ay": (1080, 1350), "kisa": (1080, 1920), "ozel": (1080, 1920),
             "kart-gram": (1080, 1920), "kart-parite": (1080, 1920), "sayfa-og": (1200, 630),
             "yorum-reels": (1080, 1920), "site-reels": (1080, 1920)}[tur]
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


KAPAK_ETIKET = {"reels": "GÜNCEL FİYAT", "post": "GÜNÜN ÖZETİ", "hafta": "HAFTALIK ÖZET", "ay": "AYLIK ÖZET"}   # kart: bot/kart.py


def kapak_verisi(tur, veri):
    """Reels kapağının (templates/kapak.html) büyük satırları: tür, gün, alt satır."""
    simdi = datetime.now(TR_SAAT)
    if tur == "ay":
        gun, yil = veri["ay_adi"].split()
        alt = f"{yil} · {veri['baz_metin'] if veri['kismi'] else 'önceki aya göre'}"
    elif tur == "hafta":
        gun = veri["aralik"].rsplit(" ", 1)[0]          # "05–09 Ekim" (yıl alt satırda)
        alt = f"{veri['aralik'].rsplit(' ', 1)[1]} · " + (veri["baz_metin"] if veri["kismi"] else "önceki haftaya göre")
    else:
        gun = f"{simdi.day} {AYLAR[simdi.month - 1]}"
        alt = f"{GUNLER[simdi.weekday()]} · {veri['saat']}"
    if veri.get("kart"):
        import kart
        return {"kapak_etiket": veri["kart_etiket"], "kapak_gun": gun, "kapak_alt": alt,
                "gun_baslik": None, **kart.kapak_verisi(veri)}
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

# Fiyat videolarının süresi (sn): sabah Reels'i 7, akşam özeti ve özel gün görseli 10, haftalık ve aylık özet 13
# (Rıdvan, 18 Ekim 2026: "Haftalık ve aylık özet ekranda 3 saniye daha uzun kalmalı"; önce 10). Hareketler ilk
# ~2,5 sn'de biter (templates/hareket.js), goril hareketleri de durağan bir sona oturur: ek süre son hâlin ekranda
# kalmasıdır. Haftalık/aylık özet özel gün görseline dönse de 13 sn kalır.
VIDEO_SURESI = {"reels": 7, "post": 10, "ozel": 10, "hafta": 13, "ay": 13}


def video_suresi(tur, sablon=None):
    if tur in ("hafta", "ay"):
        return VIDEO_SURESI[tur]
    return VIDEO_SURESI["ozel"] if sablon == "ozel" else VIDEO_SURESI.get(tur, 10)


def _ses_girdisi(sure):
    muzik = KOK / "assets" / "muzik.mp3"
    if muzik.exists():
        return (["-stream_loop", "-1", "-i", str(muzik)],
                ["-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={sure - 1.5}:d=1.5,aresample=44100"])
    print("Uyarı: assets/muzik.mp3 yok, video müziksiz üretiliyor", file=sys.stderr)
    return ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"], []


def _ses_kazanci(wav):
    """Seslendirme izinin -16 LUFS'a çıkması için gereken kazanç (dB); ölçülemezse 0."""
    import re
    try:
        r = subprocess.run([ffmpeg_yolu(), "-hide_banner", "-nostats", "-i", str(wav), "-af",
                            "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=120)
        olcum = json.loads(re.findall(r"\{[^{}]*\}", r.stderr)[-1])
        return max(-12.0, min(18.0, -16.0 - float(olcum["input_i"])))
    except Exception as e:
        print(f"Uyarı: seslendirme yüksekliği ölçülemedi ({type(e).__name__}); kazanç 0 dB", file=sys.stderr)
        return 0.0


def _seslendirme_girdisi(sure, wav):
    """Seslendirmeli video için ses girdileri ve filter_complex parçası ([a] çıkışı).

    Ses -16 LUFS'a getirilir; müzik (varsa) altında kısık çalar ve konuşma sırasında ayrıca kısılır
    (sidechain), konuşma araları müzikle dolar. Video girdisi 0. sıradadır."""
    kazanc = _ses_kazanci(wav)
    ses_zinciri = f"aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={kazanc:.2f}dB"
    muzik = KOK / "assets" / "muzik.mp3"
    son = f"alimiter=limit=0.89,afade=t=out:st={sure - 1.5}:d=1.5[a]"
    if not muzik.exists():
        print("Uyarı: assets/muzik.mp3 yok, video yalnızca seslendirmeyle üretiliyor", file=sys.stderr)
        return ["-i", str(wav)], f"[1:a]{ses_zinciri},apad,{son}"
    girdi = ["-stream_loop", "-1", "-i", str(muzik), "-i", str(wav)]
    filtre = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
              f"volume={SESLI_MUZIK_SEVIYE},afade=t=in:d=0.5[m];"
              f"[2:a]{ses_zinciri},apad,asplit=2[v1][vs];"
              "[m][vs]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=450[md];"
              f"[md][v1]amix=inputs=2:duration=first:normalize=0,{son}")
    return girdi, filtre


SESLI_MUZIK_SEVIYE = 0.45   # seslendirmede müziğin payı (1 = sessiz Reels'teki yükseklik; ~-7 dB)


def hareketli_video_uret(tur, veri, mp4_yolu, sure=7, seslendirme=None):
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
    goruntu = (f"scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color={ZEMIN_RENGI},format=yuv420p")
    if seslendirme:
        ses, ses_filtre = _seslendirme_girdisi(sure, seslendirme)
        akis = ["-filter_complex", f"[0:v]{goruntu}[v];{ses_filtre}", "-map", "[v]", "-map", "[a]"]
    else:
        ses, ses_filtre = _ses_girdisi(sure)
        akis = ["-vf", goruntu, *ses_filtre]
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error",
             "-f", "image2pipe", "-framerate", str(VIDEO_FPS), "-c:v", "mjpeg", "-i", "-", *ses,
             "-t", str(sure), *akis,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(VIDEO_FPS),
             "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(mp4_yolu)]
    boyut = {"reels": (1080, 1920), "kisa": (1080, 1920), "ozel": (1080, 1920),
             "kart-gram": (1080, 1920), "kart-parite": (1080, 1920), "yorum-reels": (1080, 1920),
             "site-reels": (1080, 1920)}.get(tur, (1080, 1350))
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


# ---------------------------------------------------------------- goril maskotu (kurallar: bot/goril.py)

GORIL_YOK = {"goril": None, "maskot": None, "maskot_js": None, "goril_satiri": ""}
# Gorilin üstüne binmemesi gereken öğeler. Metin öğelerinde kutunun değil yazının kendisi ölçülür.
GORIL_KORUNAN_METIN = ["#fiyat", ".kahraman-birim", ".kahraman-baslik", ".kahraman > .soluk", ".alt", ".etiket",
                       ".tarih", ".ozel-manset", "h1", ".satir"]
GORIL_KORUNAN_KUTU = ["#fiyat-deg", "#manset", "#gun-baslik", ".ag", ".grafik-deger"]
GORIL_DENETIM_ANLARI = tuple(i / 10 for i in range(131))   # en uzun videonun (13 sn) her 0,1 sn'si
GORIL_OGE_ADI = {"#fiyat": "fiyat", ".kahraman-birim": "₺ işareti", ".kahraman-baslik": "GRAM GÜMÜŞ başlığı",
                 ".kahraman > .soluk": "fiyatın altındaki satır", ".alt": "en alttaki satır", ".etiket": "üst etiket",
                 ".tarih": "tarih", ".ozel-manset": "özel gün manşeti", "h1": "Gümüş başlığı",
                 ".satir": "parite / dolar satırı", "#fiyat-deg": "yüzde rozeti", "#manset": "manşet",
                 "#gun-baslik": "günün başlığı", ".ag": "Ag rozeti", ".grafik-deger": "grafik değeri"}


def goril_alanlari(veri, tur, ornek=False):
    """Şablon alanları. Goril modülünde ya da kuralda herhangi bir hata "goril yok" sayılır: diğer paylaşımlar ve
    gorilsiz fiyat paylaşımı hiç etkilenmez."""
    try:
        import goril
        return goril.sablon_verisi(veri, tur, datetime.now(TR_SAAT).date(), ornek)
    except Exception as e:
        print(f"::warning::Goril hâli belirlenemedi, gorilsiz devam ediliyor: {type(e).__name__}: {e}")
        return dict(GORIL_YOK)


def goril_yerlesimi_denetle(sablon, veri, sure=None):
    """Gorilin bedeni (class="goril-beden") durağan pozda ve videonun her 0,1 sn'sinde fiyat, ₺, rozet, manşet, alt
    satırlar, Ag rozeti, uyarı satırı gibi öğelerle kesişiyor mu bakar. Kesişme varsa okunur bir özet döndürür
    ("fiyat, ₺ işareti (durağan pozda; 2,3–4,1 sn)"), yoksa None. Kesişme paylaşımı durdurmaz: goril kalır, uyarı
    çıkar ve Rıdvan'a bildirilir (Rıdvan, 16 Ekim 2026 22:43: "durmasına gerek yok ... sadece bunu bildirmen
    yeterli"). Goril hiç ölçülemezse ya da fiyat görünmüyorsa (çizim bozuk) RuntimeError verir; o zaman paylaşım
    gorilsiz üretilir. Saydam (giriş öncesi) parçalar sayılmaz."""
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    html = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True).get_template(f"{sablon}.html").render(**veri)
    gecici = SABLONLAR / f"_goril_denetim_{sablon}.html"
    gecici.write_text(html, encoding="utf-8")
    olc = """([metinler, kutular]) => {
      const kes = (a, b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
      const korunan = [];
      metinler.forEach(s => document.querySelectorAll(s).forEach(e => {
        if (e.closest('.maskot')) return;
        const r = document.createRange(); r.selectNodeContents(e); const b = r.getBoundingClientRect();
        if (b.width > 0 && b.height > 0) korunan.push([s, b]); }));
      kutular.forEach(s => document.querySelectorAll(s).forEach(e => {
        if (e.closest('.maskot')) return;
        const b = e.getBoundingClientRect(); if (b.width > 0 && b.height > 0) korunan.push([s, b]); }));
      const fiyat = document.getElementById('fiyat');
      if (!fiyat || fiyat.getBoundingClientRect().width === 0) return {hata: 'fiyat görünmüyor'};
      const sv = document.querySelector('.maskot svg');
      if (!sv) return {hata: 'maskot yok'};
      const kb = sv.getBoundingClientRect(), vb = sv.viewBox.baseVal;
      const olcek = Math.min(kb.width / vb.width, kb.height / vb.height);
      let g = null;
      sv.querySelectorAll('.goril-beden').forEach(grup => grup.querySelectorAll('path,ellipse,circle,rect,use,polygon').forEach(e => {
        const b = e.getBoundingClientRect(); if (b.width === 0 && b.height === 0) return;
        const cs = getComputedStyle(e);
        if (cs.visibility === 'hidden' || cs.display === 'none') return;
        let o = 1;                                  // görünmeyen (saydam) parça sayılmaz
        for (let a = e; a && a !== sv.parentNode; a = a.parentNode) o *= parseFloat(getComputedStyle(a).opacity);
        if (o < 0.05) return;
        const p = (cs.stroke && cs.stroke !== 'none') ? (parseFloat(cs.strokeWidth) || 0) / 2 * olcek : 0;
        const r = {left: b.left - p, top: b.top - p, right: b.right + p, bottom: b.bottom + p};
        g = g ? {left: Math.min(g.left, r.left), top: Math.min(g.top, r.top), right: Math.max(g.right, r.right),
                 bottom: Math.max(g.bottom, r.bottom)} : r; }));
      if (!g) return {carpan: [], goril: null};   // bu anda görünmüyor (giriş öncesi)
      const carpan = korunan.filter(([s, b]) => kes(g, b)).map(([s]) => s);
      return {carpan, goril: [Math.round(g.left), Math.round(g.top), Math.round(g.right), Math.round(g.bottom)]};
    }"""
    try:
        with sync_playwright() as p:
            kwargs = {"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}
            tarayici = p.chromium.launch(**kwargs)
            boyut = (1080, 1920) if sablon in ("ozel", "reels") else (1080, 1350)
            sayfa = tarayici.new_page(viewport={"width": boyut[0], "height": boyut[1]})
            sayfa.goto(gecici.as_uri())
            sayfa.evaluate("document.fonts.ready")
            sayfa.wait_for_timeout(200)
            hareket = sayfa.evaluate("typeof window.kare === 'function'")
            goruldu = False
            ogeler, durgun, anlar = set(), False, []
            # önce durağan poz (görsel ve durağan video), sonra hareketin anları
            anlar_ = tuple(t for t in GORIL_DENETIM_ANLARI if sure is None or t <= sure)   # videonun süresi kadar
            for t in ((None,) + anlar_ if hareket else (None,)):
                if t is not None:
                    sayfa.evaluate(f"window.kare({t})")
                s = sayfa.evaluate(olc, [GORIL_KORUNAN_METIN, GORIL_KORUNAN_KUTU])
                if s.get("hata"):
                    raise RuntimeError(f"goril denetimi: {s['hata']}")
                if s["carpan"]:
                    ogeler.update(s["carpan"])
                    if t is None:
                        durgun = True
                    else:
                        anlar.append(t)
                goruldu = goruldu or bool(s["goril"])
            tarayici.close()
            if not goruldu:
                raise RuntimeError("goril denetimi: goril bedeni hiçbir anda ölçülemedi")
    finally:
        gecici.unlink(missing_ok=True)
    if not ogeler:
        return None
    ne = ", ".join(sorted({GORIL_OGE_ADI.get(o, o) for o in ogeler}))
    ne_zaman = (["durağan pozda"] if durgun else []) + (
        [f"{tr_sayi(min(anlar), 1)}–{tr_sayi(max(anlar), 1)} sn" if len(anlar) > 1 else f"{tr_sayi(anlar[0], 1)} sn"]
        if anlar else [])
    return f"{ne} ({'; '.join(ne_zaman)})"


def goril_ciz(girdi, sonuc):
    """Ayrı süreçte çalışır (goril_ile_uret çağırır): denetim, gorilli görsel ve video."""
    import pickle
    d = pickle.loads(Path(girdi).read_bytes())
    png, mp4 = Path(d["png"]), Path(d["mp4"])
    cakisma = goril_yerlesimi_denetle(d["sablon"], d["veri"], d["sure"])
    gorsel_uret(d["sablon"], d["veri"], png)
    hareketli = hareketli_video_uret(d["sablon"], d["veri"], mp4, sure=d["sure"])
    if not hareketli:
        video_uret(png, mp4, sure=d["sure"])
    Path(sonuc).write_text(json.dumps({"hareketli": bool(hareketli), "cakisma": cakisma}, ensure_ascii=False),
                           encoding="utf-8")


def goril_ile_uret(sablon, veri, png, mp4, sure):
    """Gorilli görsel ve videoyu ayrı süreçte, süre sınırıyla üretir. Başarılıysa True. Hata, takılma ya da süre
    aşımında False döner ve yarım dosyaları siler; o zaman hazirla() bugünkü gibi gorilsiz üretir. Goril bir yazıyla
    üst üste binerse yine True döner (goril kalır), uyarı yazar ve veri["goril_cakisma"]'ya özeti koyar.
    Goril hiçbir zaman fiyat paylaşımını durdurmaz (taahhüt: hafta içi her gün 2 kez gram fiyatı)."""
    import pickle
    import signal
    try:
        import goril
        sinir = goril.SURE_SINIRI
    except Exception:
        sinir = 120
    girdi, sonuc = png.with_suffix(".goril.pkl"), png.with_suffix(".goril.json")
    kod = None
    try:
        girdi.write_bytes(pickle.dumps({"sablon": sablon, "veri": veri, "png": str(png), "mp4": str(mp4), "sure": sure}))
        p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "goril-ciz",
                              "--girdi", str(girdi), "--sonuc", str(sonuc)], start_new_session=True)
        try:
            kod = p.wait(timeout=sinir)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            print(f"::warning::Goril {sinir} sn içinde çizilemedi; paylaşım gorilsiz üretiliyor.")
        else:
            if kod != 0:
                print("::warning::Goril çizilemedi (yukarıdaki hata); paylaşım gorilsiz üretiliyor.")
    except Exception as e:
        print(f"::warning::Goril süreci başlatılamadı ({type(e).__name__}: {e}); paylaşım gorilsiz üretiliyor.")
    finally:
        girdi.unlink(missing_ok=True)
    tamam = kod == 0 and sonuc.exists() and png.exists() and mp4.exists()
    if tamam:
        try:
            cakisma = json.loads(sonuc.read_text(encoding="utf-8")).get("cakisma")
        except Exception:
            cakisma = None
        if cakisma:
            # Paylaşım gorilli gider; gece kontrolü bu satırı günlükten okuyup Rıdvan'a bildirir.
            print(f"::warning::Goril üst üste biniyor: {cakisma}. Paylaşım gorilli gidiyor (Rıdvan'a bildirilecek).")
            veri["goril_cakisma"] = cakisma
    sonuc.unlink(missing_ok=True)
    if not tamam:
        for f in (png, mp4):
            f.unlink(missing_ok=True)
        for kalip in ("_cikti_*.html", "_hareket_*.html", "_goril_denetim_*.html"):   # öldürülen süreçten kalanlar
            for f in SABLONLAR.glob(kalip):
                f.unlink(missing_ok=True)
    return tamam

# ---------------------------------------------------------------- instagram

class ErisimEngeli(RuntimeError):
    """Instagram'ın geçici olarak reddettiği istek: hesap/uygulama engeli ("API access blocked"), istek sınırı
    ya da Meta tarafında geçici arıza. Paylaşım (media_publish) henüz yapılmadıysa bir süre sonra yeniden
    denemek güvenlidir; yayinla() bunu yapar."""


# Meta'nın geçici hata kodları: 1 bilinmeyen hata, 2 hizmet geçici olarak kullanılamıyor,
# 4 / 17 / 32 / 613 istek sınırı (uygulama, kullanıcı, sayfa, saatlik). Kalıcı hatalar (geçersiz anahtar 190,
# izin 10, bozuk medya 36xx) bu listede değil; onlar beklemekle geçmez.
GECICI_HATA_KODLARI = {1, 2, 4, 17, 32, 613}


def _gecici_mi(durum, hata):
    if durum >= 500:
        return True
    if isinstance(hata, dict):
        if "API access blocked" in str(hata.get("message", "")):
            return True
        if hata.get("code") in GECICI_HATA_KODLARI:
            return True
    return False


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
        ileti = f"Instagram API hatası ({r.status_code}): {hata}"
        if _gecici_mi(r.status_code, hata):
            raise ErisimEngeli(ileti)
        raise RuntimeError(ileti)
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
        except ErisimEngeli:
            raise   # geçici engel: kapaksız denemek işe yaramaz, yayinla() bir süre sonra baştan dener
        except RuntimeError as e:
            print(f"::warning::Kapakla paylaşılamadı, son kareyle yeniden deneniyor: {e}")
    k = _istek("POST", f"{kullanici_id}/media", thumb_offset=str(meta.get("kapak_ms", 0)), **ortak)
    _hazir_olmasini_bekle(k["id"])
    return k


YENIDEN_DENEME_SN = int(os.environ.get("YENIDEN_DENEME_SN", "600"))   # geçici engelde iki deneme arası

# Günlük sınır (bot/sinir.py; Rıdvan, 19 Ekim 2026): takipçinin bizden gördüğü her şey sayılır — akış gönderisi,
# Reels, hikâye. yayinla bu çalıştırmada paylaşılan her şeyi sayar; iş akışı sayıyı "gorunen-…" eseri olarak saklar.
_GORUNEN = [0]


def _hikaye_izinli(ne):
    """kontrol işi günü 4'ün üstüne çıkmasın diye hikâye kopyasını düşürdüyse (HIKAYE=yok) False."""
    if os.environ.get("HIKAYE", "").strip().lower() == "yok":
        print(f"Hikâye BİLEREK paylaşılmadı ({ne}): günlük sınır — takipçinin gördüğü içerik bugün 4'ü "
              "aşacaktı, önce hikâye kopyası düşer (bot/sinir.py; Rıdvan, 19 Ekim 2026). Bu bir hata değil.")
        return False
    return True


def yayinla(cikti, taban_url, bekle_dk=0):
    """Paylaşır. Instagram geçici olarak reddederse (ErisimEngeli: "API access blocked", istek sınırı,
    sunucu hatası) bekle_dk dakika boyunca her YENIDEN_DENEME_SN saniyede bir baştan dener; süre bitince
    hata verir. Yalnızca paylaşım (media_publish) başarılı olmadan önceki hatalar yeniden denenir; sonrası
    (hikâye, bağlantı) zaten uyarıyla geçer, böylece aynı şey iki kez paylaşılmaz. 13 Ekim 2026'da
    Instagram ~1,5 saat boyunca her isteği "API access blocked" ile reddetmiş, 20:00 özeti elle yeniden
    çalıştırılmıştı; bu bekleme onun için."""
    bitis = time.time() + bekle_dk * 60
    deneme = 0
    while True:
        deneme += 1
        try:
            return _yayinla(cikti, taban_url)
        except ErisimEngeli as e:
            kalan = bitis - time.time()
            if kalan <= 0:
                if bekle_dk:
                    print(f"::error::Instagram {bekle_dk} dakikadır geçici engel veriyor, vazgeçildi "
                          f"({deneme} deneme). Engel kalkınca bu çalıştırmada \"Re-run failed jobs\" yeterli.")
                raise
            ara = min(YENIDEN_DENEME_SN, kalan)
            print(f"::warning::Instagram geçici olarak reddetti; {ara / 60:.0f} dk sonra yeniden denenecek "
                  f"(deneme {deneme}, en çok {kalan / 60:.0f} dk daha). Hata: {e}")
            sys.stdout.flush()
            time.sleep(ara)


def _yayinla(cikti, taban_url):
    meta = json.loads((cikti / "meta.json").read_text(encoding="utf-8"))
    if meta["tur"] == "hikaye":
        videolar = meta.get("hikaye_videolari") or []
        if not videolar:
            # Kareler tek tek paylaşılmaz (hikâye kalabalık olmasın); video yoksa hiçbir şey gitmez.
            raise RuntimeError(f"Rehber #{meta['konu']} hikâye videosu üretilmemiş; hikâye paylaşılmadı")
        urller = [taban_url.rstrip("/") + "/" + v for v in videolar]
        kullanici_id = hesap_bilgisi()["user_id"]
        gorsel_hikayeler(kullanici_id, urller, _PAYLASILAN_HIKAYELER)
        print(f"Rehber #{meta['konu']} hikâyesi paylaşıldı ({len(urller)} video). "
              "Profilde Öne çıkanlar › Rehber'e eklemeyi unutma.")
        return
    if "dosyalar" in meta:
        urller = [taban_url.rstrip("/") + "/" + d for d in meta["dosyalar"]]
        for url in urller:
            _url_hazir_mi(url)
        kullanici_id = hesap_bilgisi()["user_id"]
        k = _kaydirmali_konteyner(kullanici_id, urller, meta["aciklama"])
        _hazir_olmasini_bekle(k["id"])
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        _GORUNEN[0] += 1   # günlük sınır: takipçinin gördüğü her şey sayılır (bot/sinir.py)
        print(f"Paylaşıldı: {meta['tur']} (medya id {sonuc.get('id')})")
        try:
            print("Bağlantı:", _istek("GET", sonuc["id"], fields="permalink").get("permalink"))
        except Exception as e:
            print(f"Uyarı: bağlantı alınamadı ({e})", file=sys.stderr)
        if meta.get("reels"):
            yorum_reelsi(kullanici_id, meta["reels"], taban_url)
        _rehber_hikayesi_sonra(kullanici_id, meta, taban_url)
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
    _GORUNEN[0] += 1   # günlük sınır: takipçinin gördüğü her şey sayılır (bot/sinir.py)
    print(f"Paylaşıldı: {meta['tur']} (medya id {sonuc.get('id')})")
    if meta["tur"] in HIKAYE_TURLERI and meta["dosya"].endswith(".mp4") and _hikaye_izinli(meta["tur"]):
        hikaye_paylas(kullanici_id, medya_url)
    _rehber_hikayesi_sonra(kullanici_id, meta, taban_url)   # rehber Reels'inden sonra müzikli rehber hikâyesi


def _rehber_hikayesi_sonra(kullanici_id, meta, taban_url):
    if not meta.get("hikayeler"):
        return
    if not _hikaye_izinli(f"rehber #{meta['konu']}"):
        print(f"Rehber #{meta['konu']} hikâye videosu sonradan gönderilebilir (öne çıkan için): Run workflow → "
              f"tür: hikaye, konu: {meta['konu']}, deneme kapalı.")
        return
    if REHBER_HIKAYE_OTOMATIK:
        rehber_hikayeleri(kullanici_id, meta, taban_url)
    else:
        print(f"Rehber #{meta['konu']} hikâye videosu otomatik paylaşılmadı (REHBER_HIKAYE_OTOMATIK "
              f"kapalı). İstersen: Run workflow → tür: hikaye, konu: {meta['konu']}, deneme kapalı.")


# Rehber gönderisinden sonra aynı bölüm hikâyeye tek müzikli video olarak gider (14 Ekim 2026 21:23, Rıdvan:
# kapak 3 sn, her kare 6 sn; kareler tek tek gitmez, hikâye kalabalık olmasın — 05:35'teki karar). Video
# gönderiyle aynı çalıştırmada gittiği için günlük sınırda ayrıca sayılmaz. Rıdvan videoyu "Rehber" öne
# çıkanına ekler. Kapatmak için False; o zaman elle: Run workflow → tür: hikaye, konu: <no>, deneme kapalı.
REHBER_HIKAYE_OTOMATIK = True
HIKAYE_ARA_SN = int(os.environ.get("HIKAYE_ARA_SN", "20"))   # iki hikâye karesi arası (art arda istek yağmasın)
_PAYLASILAN_HIKAYELER = set()   # yeniden denemede (geçici engel) aynı kare iki kez gitmesin


def gorsel_hikayeler(kullanici_id, urller, paylasilan):
    """Görselleri ya da videoları (.mp4) sırayla hikâyeye koyar. paylasilan kümesindeki adresler atlanır,
    paylaşılan eklenir."""
    for i, url in enumerate(urller, 1):
        if url in paylasilan:
            continue
        if paylasilan:
            time.sleep(HIKAYE_ARA_SN)
        _url_hazir_mi(url)
        medya = {"video_url": url} if url.endswith(".mp4") else {"image_url": url}
        k = _istek("POST", f"{kullanici_id}/media", media_type="STORIES", **medya)
        _hazir_olmasini_bekle(k["id"])
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        _GORUNEN[0] += 1   # günlük sınır: takipçinin gördüğü her şey sayılır (bot/sinir.py)
        paylasilan.add(url)
        print(f"Hikâye {i}/{len(urller)} paylaşıldı (medya id {sonuc.get('id')})")


def rehber_hikayeleri(kullanici_id, meta, taban_url):
    """Rehber gönderisinden sonra aynı bölüm hikâyeye, tek müzikli video olarak (uzun bölümde birkaç video).
    Gönderi zaten paylaşıldığı için hata yalnızca uyarı verir (yeniden deneme gönderiyi ikinci kez
    paylaşmasın). Video üretilemediyse kareler tek tek paylaşılmaz (hikâye kalabalık olmasın)."""
    videolar = meta.get("hikaye_videolari") or []
    if not videolar:
        print(f"::warning::Rehber #{meta['konu']} hikâye videosu yok; hikâye paylaşılmadı. "
              f"Sonradan: Run workflow → tür: hikaye, konu: {meta['konu']}, deneme kapalı.")
        return
    urller = [taban_url.rstrip("/") + "/" + v for v in videolar]
    paylasilan = set()
    try:
        gorsel_hikayeler(kullanici_id, urller, paylasilan)
        print(f"Rehber #{meta['konu']} hikâyeye de paylaşıldı ({len(urller)} video). "
              "Profilde Öne çıkanlar › Rehber'e eklemeyi unutma.")
    except Exception as e:
        print(f"::warning::Rehber hikâyesi yarıda kaldı: {len(paylasilan)}/{len(urller)} video paylaşıldı ({e}). "
              f"Tamamlamak için paylaşılan videoları hikâyeden silip Run workflow → tür: hikaye, "
              f"konu: {meta['konu']}, deneme kapalı.")


def yorum_reelsi(kullanici_id, reels, taban_url):
    """Pazar yorumunun Reels'i ve aynı videonun hikâyesi. Kaydırmalı gönderi zaten paylaşıldığı için HER hata
    (geçici engel dahil) yalnızca uyarı verir: yayinla() baştan denerse kaydırmalı ikinci kez gitmesin."""
    try:
        video_url = taban_url.rstrip("/") + "/" + reels["dosya"]
        _url_hazir_mi(video_url)
        k = _reels_konteyneri(kullanici_id, video_url, reels, taban_url)
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        _GORUNEN[0] += 1   # günlük sınır: takipçinin gördüğü her şey sayılır (bot/sinir.py)
        print(f"Pazar Reels'i paylaşıldı (medya id {sonuc.get('id')})")
    except Exception as e:
        print(f"::warning::Pazar Reels'i paylaşılamadı ({type(e).__name__}: {e}); kaydırmalı gönderi paylaşıldı. "
              "Reels'i sonradan göndermek için Claude'a yaz.")
        return
    # Sesli Reels ~1,5 dk: hikâyeye 24 sn'lik müzikli sürüm gider (hikâye en çok 60 sn)
    if not _hikaye_izinli("pazar yorumu"):
        return
    hikaye = reels.get("hikaye_dosya")
    hikaye_paylas(kullanici_id, taban_url.rstrip("/") + "/" + hikaye if hikaye else video_url)


def hikaye_paylas(kullanici_id, video_url):
    """Aynı videoyu hikâyeye de koyar. Hikâye başarısız olursa asıl paylaşım etkilenmez, yalnızca uyarı verilir."""
    try:
        k = _istek("POST", f"{kullanici_id}/media", media_type="STORIES", video_url=video_url)
        _hazir_olmasini_bekle(k["id"])
        sonuc = _istek("POST", f"{kullanici_id}/media_publish", creation_id=k["id"])
        _GORUNEN[0] += 1   # günlük sınır: takipçinin gördüğü her şey sayılır (bot/sinir.py)
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

# Instagram kullanıcı adı: görsellerde, kapaklarda ve bilgi sayfasında (takip düğmesi) bu yazar.
# Tek kaynak burası; ad değişirse yalnızca bu satır değişir (15 Ekim 2026: gumusagtr → gunlukgumus).
# Instagram'a kullanıcı adı sorulmaz (13 Ekim engelinden beri gereksiz istek yapılmıyor); GitHub'daki
# HESAP_ADI değişkeni artık okunmaz. HESAP_ADI ortam değişkeni yalnızca yerel denemeler içindir.
HESAP_VARSAYILAN = "gunlukgumus"


def hesap_adi():
    hesap = os.environ.get("HESAP_ADI", "").strip() or HESAP_VARSAYILAN
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


# Rehber günü akışa giden: sesli Reels (Rıdvan, 16 Ekim 2026 23:4x: "Yerine geçsin" — salı/perşembe kaydırmalı
# gönderinin yerine kadın sesiyle seslendirilmiş Reels; hikâyeye giden rehber videosu müzikli kalır; cumartesi
# kısa Reels'i kaldırıldı). Reels üretilemezse aynı gün eski kaydırmalı gönderi gider. False: hep kaydırmalı.
REHBER_REELS = True


def bilgi_hazirla(cikti, konu=None):
    """Gümüş rehberi bölümü: sesli Reels (REHBER_REELS) ya da kapak + 3 sayfa kaydırmalı gönderi, ve aynı bölümün
    müzikli hikâye videosu. Fiyat verisi kullanmaz.

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
    # Aynı bölümün 9:16 hikâye kareleri: hem müzikli hikâye videosu (REHBER_HIKAYE_OTOMATIK; "Rehber" öne çıkanı)
    # hem rehber günü Reels'i (REHBER_REELS; kareler kadın sesiyle okunur) bunlardan yapılır.
    plan = []
    hikaye_videolari = []
    try:
        hikayeler = rehber_hikaye_uret(cikti, konu, hesap, damga, plan=plan, reels_kapak=REHBER_REELS)
    except Exception as e:
        print(f"::warning::Rehber hikâye kareleri üretilemedi ({e}); hikâye ve Reels yok, kaydırmalı gidiyor.")
        hikayeler = []
    if hikayeler:
        try:
            hikaye_videolari = rehber_hikaye_videosu_uret(cikti, hikayeler, konu, damga)
        except Exception as e:
            print(f"::warning::Rehber hikâye videosu üretilemedi, gönderi hikâyesiz gidecek: {e}")
    reels = None
    if REHBER_REELS and hikayeler:
        try:
            reels = rehber_reels_tam_uret(cikti, konu, damga, hikayeler, plan)
        except Exception as e:
            print(f"::warning::Rehber Reels'i üretilemedi ({type(e).__name__}: {str(e)[:200]}); "
                  "bugün kaydırmalı gönderi gidiyor.")
            (cikti / f"bilgi{konu}-{damga}.mp4").unlink(missing_ok=True)
    (cikti / f"bilgi{konu}-{damga}-reels-son.jpg").unlink(missing_ok=True)   # site kartı yalnızca Reels videosuna girer
    dosyalar = []
    if reels:
        metin = bilgi.aciklama(konu, reels=True, ek=_reels_ek_satirlari(reels["seslendirme"]),
                               muzik=muzik_kunyesi())
    else:
        toplam = len(b["sayfalar"]) + 1
        for sayfa in range(toplam):
            jpg = cikti / f"bilgi{konu}-{damga}-{sayfa + 1}.jpg"
            gorsel_uret("bilgi", {"b": b, "no": konu, "sayfa": sayfa,
                                  "toplam_sayfa": toplam, "sonraki": sonraki, "seri": bilgi.SERI,
                                  "hesap": hesap}, jpg)
            dosyalar.append(jpg.name)
        metin = bilgi.aciklama(konu)
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
    meta = {"tur": "bilgi", "konu": konu, "hikayeler": hikayeler, "hikaye_videolari": hikaye_videolari,
            "aciklama": metin}
    if reels:
        sl = reels["seslendirme"]
        meta.update({"dosya": reels["dosya"], "kapak": reels["kapak"], "kapak_ms": 1000,
                     "seslendirme": sl["ses"] if sl else None, "ses_metni": sl["metin"] if sl else None})
        dosyalar = [reels["dosya"], reels["kapak"]]
    else:
        meta["dosyalar"] = dosyalar
    (cikti / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in dosyalar), encoding="utf-8")
    print(metin)
    bicim = ("sesli Reels" if reels["seslendirme"] else "Reels, yalnızca müzik") if reels else "kaydırmalı"
    print(f"\nÜretilen dosyalar ({len(metin)} karakter açıklama; {bicim}):",
          *dosyalar, sep="\n")
    if hikayeler:
        print(f"Hikâye kareleri ({len(hikayeler)}):", *hikayeler, sep="\n")
    if hikaye_videolari:
        print(f"Hikâye videosu ({len(hikaye_videolari)}):", *hikaye_videolari, sep="\n")


def rehber_hikaye_uret(cikti, konu, hesap, damga, plan=None, reels_kapak=False):
    """Rehber bölümünün hikâye karelerini üretir (bot/rehber_hikaye.py); dosya adlarını döndürür."""
    import bilgi
    import rehber_hikaye
    b = bilgi.BOLUMLER[konu - 1]
    sonraki = bilgi.BOLUMLER[konu]["baslik"] if konu < len(bilgi.BOLUMLER) else None
    return rehber_hikaye.uret(b, konu, sonraki, bilgi.SERI, hesap, cikti, damga, plan=plan, reels_kapak=reels_kapak,
                              site=bilgi.SITE if reels_kapak else None)


def rehber_tam_seslendirmesi(konu, plan, cikti, site_karti=False):
    """Rehber günü Reels'i için bölümün tamamının kare kare seslendirmesi (bot/ses.py → rehber_seslendir). Kapalıysa
    ya da herhangi bir hata olursa None: Reels o gün yalnızca müzikle (hikâye videosu gibi) gider."""
    import bilgi
    import ses
    if not ses.SES_ACIK or os.environ.get("SES_KAPALI"):
        return None
    try:
        b = bilgi.BOLUMLER[konu - 1]
        sonraki = bilgi.BOLUMLER[konu]["baslik"] if konu < len(bilgi.BOLUMLER) else None
        metinler = ses.rehber_metinleri(konu, b, plan, sonraki, site_karti=site_karti)
        return ses.rehber_seslendir(metinler, cikti, f"rehber{konu}",
                                    ses=os.environ.get("SES_ADI", "").strip() or ses.SES, deneme=_deneme_mi())
    except Exception as e:
        print(f"::warning::Rehber seslendirmesi yapılamadı ({type(e).__name__}: {str(e)[:200]}); "
              "rehber Reels'i yalnızca müzikle gidiyor.")
        return None


def _rehber_reels_sesi(sure, wav):
    """Uzun rehber Reels'inin ses girdileri ve filtresi ([a]): müzik hikâye videosundaki gibi kendi üstüne bindirilerek
    uzatılır (döngü yerinde kesik duyulmasın), konuşmanın altında kısık çalar ve konuşurken ayrıca kısılır.
    Video girdisi 0. sırada."""
    kazanc = _ses_kazanci(wav)
    ses_zinciri = f"aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={kazanc:.2f}dB"
    son = f"alimiter=limit=0.89,afade=t=out:st={sure - 1.5}:d=1.5[a]"
    muzik = KOK / "assets" / "muzik.mp3"
    if not muzik.exists():
        print("Uyarı: assets/muzik.mp3 yok, rehber Reels'i yalnızca seslendirmeyle üretiliyor", file=sys.stderr)
        return ["-i", str(wav)], f"[1:a]{ses_zinciri},apad,{son}"
    girdi = ["-i", str(muzik), "-i", str(muzik), "-stream_loop", "-1", "-i", str(muzik), "-i", str(wav)]
    filtre = ("[1:a][2:a]acrossfade=d=2:c1=tri:c2=tri[m0];[m0][3:a]acrossfade=d=2:c1=tri:c2=tri,"
              "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
              f"volume={SESLI_MUZIK_SEVIYE},afade=t=in:d=0.5[m];"
              f"[4:a]{ses_zinciri},apad,asplit=2[v1][vs];"
              "[m][vs]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=450[md];"
              f"[md][v1]amix=inputs=2:duration=first:normalize=0,{son}")
    return girdi, filtre


# "Sesi açın" rozeti (Rıdvan, 17 Ekim 2026): sesli rehber Reels'inde videonun üst ortasında, kare içeriğinin üstündeki
# boşlukta (hikâye karelerinde üst 260 px yazısız) hareket eden hoparlör simgesi ve "Sesi açın". Yalnız sesliyse.
SES_ROZETI_Y = 140          # px, rozetin üst kenarı (1080×1920 karede)
SES_ROZETI_KARE = 36        # 1,2 sn'lik döngü, 30 fps
# Ortada büyük rozet (Rıdvan, 19 Ekim 2026 "onaylıyorum uygula"): üstteki rozet akışta görünmüyor (masaüstünde 4:5
# kırpmada kalıyor, telefon akışında "Orijinal ses" satırının altına biniyor). Videonun ilk saniyelerinde ekran
# kararır, rozet ortada büyük çıkar; sonra yalnız üstteki küçük rozet kalır. Video başa sarınca yine çıkar.
SES_ROZETI_ORTA_SN = 2.5    # sn, ortadaki büyük rozetin ekranda kaldığı süre
SES_ROZETI_ORTA_YAZI = 72   # px (üstteki 42)
SES_ROZETI_KARARTMA = 0.55  # ortadaki rozet varken zeminin kararması (0 = yok, 1 = siyah)


def _ses_rozeti_kareleri(klasor, yazi=42, opak=False):
    """Rozetin döngü karelerini saydam PNG olarak klasöre yazar; ffmpeg girdi deseni (rozet_%02d.png) döner.
    opak=True: rozetin zemini tam dolu (ortadaki büyük rozet; arkadaki yazı içinden görünmesin)."""
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright
    env = Environment(loader=FileSystemLoader(str(SABLONLAR)), autoescape=True)
    gecici = SABLONLAR / "_ses_rozet.html"
    gecici.write_text(env.get_template("ses-rozet.html").render(yazi=yazi, opak=opak), encoding="utf-8")
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            kwargs = {"executable_path": os.environ["CHROME_YOLU"]} if os.environ.get("CHROME_YOLU") else {}
            tarayici = p.chromium.launch(**kwargs)
            sayfa = tarayici.new_page(viewport={"width": 1080, "height": 300})
            sayfa.goto(gecici.as_uri())
            sayfa.evaluate("document.fonts.ready")
            sayfa.wait_for_timeout(200)
            kutu = sayfa.locator("#kutu").bounding_box()
            alan = {"x": kutu["x"], "y": kutu["y"], "width": math.ceil(kutu["width"] / 2) * 2,
                    "height": math.ceil(kutu["height"] / 2) * 2}
            for i in range(SES_ROZETI_KARE):
                sayfa.evaluate(f"window.kare({i / VIDEO_FPS:.4f})")
                sayfa.screenshot(path=str(klasor / f"rozet_{i:02d}.png"), clip=alan, omit_background=True)
            tarayici.close()
    finally:
        gecici.unlink(missing_ok=True)
    return str(klasor / "rozet_%02d.png")


def rehber_reels_tam_uret(cikti, konu, damga, hikayeler, plan):
    """Rehber Reels'i, rehber günü ve arşiv günü (Rıdvan, 17 Ekim 2026: "Tabii ki tamamının okunması gerekiyor"):
    ekranda hikâye videosunun büyük yazılı kareleri, kadın sesi her karenin yazısını okur, kare okuma bitince değişir; müzik altta kısık.
    Kapak, "Dokunun →" yazısı olmayan Reels kapağıdır. Ses alınamazsa kareler hikâye videosundaki sürelerle
    (kapak 3 sn, kare 6 sn) yalnızca müzikle döner. Dönüş: {"dosya", "kapak", "sure", "seslendirme"}."""
    import rehber_hikaye as rh
    cikti = Path(cikti)
    kareler = list(hikayeler)
    reels_kapak = f"bilgi{konu}-{damga}-reels-kapak.jpg"
    if (cikti / reels_kapak).exists():
        kareler[0] = reels_kapak
    # Son kare: site kartı (Rıdvan, 19 Ekim 2026: web sayfası tanıtımı). Çizilemediyse Reels onsuz gider.
    site_son = f"bilgi{konu}-{damga}-reels-son.jpg"
    site_karti = (cikti / site_son).exists()
    if site_karti:
        kareler.append(site_son)
    sl = rehber_tam_seslendirmesi(konu, plan, cikti, site_karti=site_karti)
    if sl and len(sl["kare_sn"]) != len(kareler):
        print(f"::warning::Rehber seslendirmesi kare sayısıyla uyuşmuyor ({len(sl['kare_sn'])} ≠ {len(kareler)}); "
              "rehber Reels'i yalnızca müzikle gidiyor.")
        sl = None
    mp4 = cikti / f"bilgi{konu}-{damga}.mp4"
    liste = cikti / f"_reels-{konu}-{damga}.txt"
    import tempfile
    rozet_klasoru = Path(tempfile.mkdtemp(prefix="ses-rozet-"))   # yayına çıkmasın diye çıktı klasörü dışında

    def yap(sl_):
        sureler = sl_["kare_sn"] if sl_ else [rh.kare_suresi(i) for i in range(len(kareler))]
        sure = round(sum(sureler), 2)
        satirlar = []
        for k, d in zip(kareler, sureler):
            satirlar += [f"file '{(cikti / k).resolve().as_posix()}'", f"duration {d}"]
        satirlar.append(f"file '{(cikti / kareler[-1]).resolve().as_posix()}'")   # concat: son kare yinelenir
        liste.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        ses_girdi, ses_filtre = _rehber_reels_sesi(sure, sl_["wav"]) if sl_ else _hikaye_sesi(sure)
        goruntu = f"[0:v]scale=1080:1920,fps={VIDEO_FPS},format=yuv420p[v]"
        rozet_girdi = []
        if sl_:   # sesliyse üst ortada "Sesi açın" rozeti (hareketli) + ilk saniyelerde ortada büyük rozet
            try:
                desen = _ses_rozeti_kareleri(rozet_klasoru / "ust")
                rozet_girdi = ["-stream_loop", "-1", "-framerate", str(VIDEO_FPS), "-i", desen]
                r = 1 + ses_girdi.count("-i")
                goruntu = (f"[0:v]scale=1080:1920,fps={VIDEO_FPS}[zemin];[{r}:v]format=rgba[rozet];"
                           f"[zemin][rozet]overlay=x=(W-w)/2:y={SES_ROZETI_Y}:shortest=1")
                try:
                    orta = _ses_rozeti_kareleri(rozet_klasoru / "orta", yazi=SES_ROZETI_ORTA_YAZI, opak=True)
                    rozet_girdi += ["-stream_loop", "-1", "-framerate", str(VIDEO_FPS), "-i", orta]
                    acik = f"enable='lt(t,{SES_ROZETI_ORTA_SN})'"
                    goruntu += (f"[ust];[ust]drawbox=x=0:y=0:w=iw:h=ih:color=black@{SES_ROZETI_KARARTMA}:t=fill:{acik}"
                                f"[kara];[{r + 1}:v]format=rgba[orta];"
                                f"[kara][orta]overlay=x=(W-w)/2:y=(H-h)/2-40:{acik}:shortest=1")
                except Exception as e:
                    print(f"::warning::Ortadaki ses rozeti çizilemedi ({type(e).__name__}: {str(e)[:120]}); "
                          "yalnız üstteki rozet.")
                goruntu += ",format=yuv420p[v]"
            except Exception as e:
                rozet_girdi = []
                goruntu = f"[0:v]scale=1080:1920,fps={VIDEO_FPS},format=yuv420p[v]"
                print(f"::warning::Ses rozeti çizilemedi ({type(e).__name__}: {str(e)[:120]}); rozetsiz.")
        komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste), *ses_girdi,
                 *rozet_girdi, "-filter_complex", f"{goruntu};{ses_filtre}",
                 "-map", "[v]", "-map", "[a]", "-t", str(sure),
                 "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(VIDEO_FPS),
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)]
        subprocess.run(komut, check=True)
        return sure

    try:
        try:
            sure = yap(sl)
        except Exception as e:
            if not sl:
                raise
            print(f"::warning::Seslendirmeli rehber Reels'i üretilemedi ({type(e).__name__}: {str(e)[:200]}); "
                  "yalnızca müzikle gidiyor.")
            sl = None
            sure = yap(None)
    finally:
        import shutil
        liste.unlink(missing_ok=True)
        (cikti / site_son).unlink(missing_ok=True)                    # yalnızca videoya girer
        (cikti / f"_ses-rehber{konu}.wav").unlink(missing_ok=True)   # ara dosya yayına çıkmasın
        shutil.rmtree(rozet_klasoru, ignore_errors=True)
    if sl:
        print(f"Seslendirme: {sl['ses']} ({sl['model']}), {sure} sn, kareler {sl['kare_sn']}")
    return {"dosya": mp4.name, "kapak": kareler[0], "sure": sure, "seslendirme": sl}


def _hikaye_sesi(sure):
    """Rehber hikâye videosunun ses girdileri ve filtresi ([a] çıkışı). Depodaki müzik parçanın ilk 30 sn'si;
    hikâye videosu daha uzun olabildiği için parça düz döngüyle değil, kendi üstüne 2 sn bindirilerek
    uzatılır (döngü yerinde kesik duyulmasın). Müzik yoksa sessiz."""
    muzik = KOK / "assets" / "muzik.mp3"
    if not muzik.exists():
        print("Uyarı: assets/muzik.mp3 yok, video müziksiz üretiliyor", file=sys.stderr)
        return ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"], "[1:a]aresample=44100[a]"
    girdi = ["-i", str(muzik), "-i", str(muzik), "-stream_loop", "-1", "-i", str(muzik)]
    filtre = ("[1:a][2:a]acrossfade=d=2:c1=tri:c2=tri[m];[m][3:a]acrossfade=d=2:c1=tri:c2=tri,"
              f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={sure - 1.5}:d=1.5,"
              "aresample=44100[a]")
    return girdi, filtre


def rehber_hikaye_videosu_uret(cikti, hikayeler, konu, damga):
    """Rehber hikâye karelerinden müzikli 9:16 hikâye videosu üretir; dosya adlarını sırayla döndürür.

    Kapak 3 sn, diğer kareler 6 sn ekranda kalır (rehber_hikaye.KAPAK_SN / KARE_SN). Video 60 sn'yi
    aşacaksa kareler arasından eşit parçalara bölünür (rehber_hikaye.video_parcalari); müzik her
    parçada baştan başlar. Müzik yoksa (MUZIK_ANAHTAR tanımlı değil) video sessiz üretilir."""
    import rehber_hikaye as rh
    cikti = Path(cikti)
    videolar = []
    for i, parca in enumerate(rh.video_parcalari(len(hikayeler)), 1):
        sureler = [rh.kare_suresi(j) for j in parca]
        sure = sum(sureler)
        liste = cikti / f"_hikaye-video-{konu}-{i}.txt"
        satirlar = []
        for j, s in zip(parca, sureler):
            satirlar += [f"file '{(cikti / hikayeler[j]).resolve().as_posix()}'", f"duration {s}"]
        satirlar.append(f"file '{(cikti / hikayeler[parca[-1]]).resolve().as_posix()}'")   # concat: son kare yinelenir
        liste.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        mp4 = cikti / f"bilgi{konu}-{damga}-hikaye-video-{i}.mp4"
        ses, filtre = _hikaye_sesi(sure)
        komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste), *ses,
                 "-filter_complex", f"[0:v]scale=1080:1920,fps={VIDEO_FPS},format=yuv420p[v];{filtre}",
                 "-map", "[v]", "-map", "[a]", "-t", str(sure),
                 "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(VIDEO_FPS),
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)]
        try:
            subprocess.run(komut, check=True)
        finally:
            liste.unlink(missing_ok=True)
        videolar.append(mp4.name)
    return videolar


def hikaye_hazirla(cikti, konu):
    """Yalnızca rehber bölümünün hikâye kareleri (gönderi yok). Gönderisi önceden paylaşılmış bölümler
    için (1-2. bölüm 13 Ekim'de) ya da gönderiden sonraki hikâye paylaşımı yarıda kaldıysa."""
    import bilgi
    if not konu or not 1 <= konu <= len(bilgi.BOLUMLER):
        raise RuntimeError(f"hikaye türünde konu (bölüm no 1-{len(bilgi.BOLUMLER)}) verilmeli (verilen: {konu})")
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    hikayeler = rehber_hikaye_uret(cikti, konu, hesap_adi(), damga)
    videolar = rehber_hikaye_videosu_uret(cikti, hikayeler, konu, damga)   # hikâyeye giden bunlar
    (cikti / "meta.json").write_text(json.dumps({"tur": "hikaye", "konu": konu, "hikayeler": hikayeler,
                                                 "hikaye_videolari": videolar},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in videolar + hikayeler),
                                      encoding="utf-8")
    print(f"Rehber #{konu} hikâye kareleri ({len(hikayeler)}):", *hikayeler, sep="\n")
    print(f"Hikâye videosu ({len(videolar)}):", *videolar, sep="\n")


def _reels_ek_satirlari(seslendirme):
    """Rehber Reels'i açıklamasının uyarı satırından önceki ekleri: seslendirme notu."""
    import ses
    return [ses.ACIKLAMA_SATIRI] if seslendirme else []


def kisa_hazirla(cikti, konu):
    """Yalnız Reels: rehber bölümünün tamamını kare kare okuyan sesli Reels'i, kaydırmalı gönderi ve hikâye olmadan.

    Zamanlı: rehber arşivi günleri (bilgi.arsiv_takvim(); Rıdvan 17 Ekim 2026: sesli rehber Reels'inden önce yayımlanan
    #3–#5 birer kez; 19 Ekim 2026'dan beri haftalık rehber sırasında, çarşamba). Elle: Run workflow → tür: kisa, konu: <no>. Reels rehber günündekiyle aynıdır
    (rehber_reels_tam_uret; okuma kısaltılmaz); ses alınamazsa yalnızca müzikle gider. Reels hiç üretilemezse paylaşım
    atlanır: bölümün kaydırmalısı ve hikâye videosu zaten paylaşıldığı için yedek gönderi yok. (16 Ekim'e kadarki
    ~15–20 sn'lik kısa Reels biçimi kaldırıldı: Rıdvan, 17 Ekim 2026 "Tabii ki tamamının okunması gerekiyor".)"""
    import bilgi
    if not 1 <= konu <= len(bilgi.BOLUMLER):
        raise RuntimeError(f"Konu 1-{len(bilgi.BOLUMLER)} arasında olmalı (verilen: {konu})")
    cikti = Path(cikti)
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    plan = []
    hikayeler = []
    try:
        hikayeler = rehber_hikaye_uret(cikti, konu, hesap_adi(), damga, plan=plan, reels_kapak=True)
        reels = rehber_reels_tam_uret(cikti, konu, damga, hikayeler, plan)
    except Exception as e:
        print(f"::warning::Paylaşım atlandı: rehber #{konu} Reels'i üretilemedi ({type(e).__name__}: {str(e)[:200]})")
        for f in hikayeler + [f"bilgi{konu}-{damga}-reels-kapak.jpg", f"bilgi{konu}-{damga}-reels-son.jpg",
                              f"bilgi{konu}-{damga}.mp4"]:
            (cikti / f).unlink(missing_ok=True)
        return
    for f in hikayeler:   # kareler yalnızca videoya girdi; hikâye bu türde paylaşılmaz
        if f != reels["kapak"]:
            (cikti / f).unlink(missing_ok=True)
    sl = reels["seslendirme"]
    metin = bilgi.aciklama(konu, reels=True, ek=_reels_ek_satirlari(sl), muzik=muzik_kunyesi())
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200 karakter)")
    meta = {"tur": "kisa", "konu": konu, "dosya": reels["dosya"], "kapak": reels["kapak"], "kapak_ms": 1000,
            "aciklama": metin, "seslendirme": sl["ses"] if sl else None, "ses_metni": sl["metin"] if sl else None}
    (cikti / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in (reels["dosya"], reels["kapak"])),
                                      encoding="utf-8")
    print(metin)
    print(f"\nÜretilen dosyalar ({len(metin)} karakter açıklama; "
          f"{'sesli Reels' if sl else 'Reels, yalnızca müzik'}, {reels['sure']} sn):", reels["dosya"], reels["kapak"],
          sep="\n")


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
    Deneme çalıştırmasında istek atılmaz: botun son kaydı kullanılır (yorum zaten o yola düşer).
    """
    if _deneme_mi():
        print("Deneme: kapanış fiyatı için MetalCharts'a istek atılmadı; botun son kaydı kullanılacak.")
        return None
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
    """Pazar yapay zekâ yorumu: kapak + kısa ve orta vade, kaydırmalı 3 görsel (Rıdvan, 17 Ekim 2026; uzun vade
    kalıcı olarak yok). Ayrıntı: bot/yorum.py

    Pazar sabahı bütün verilerle şekillenir: botun günlük kayıtları, o anki (haftanın kapanış)
    fiyatı, 13 aylık dolar/TL, varsa MetalCharts geçmişi ve web aramasıyla derlenen haftanın haberleri.
    """
    import yorum
    bugun = datetime.now(TR_SAAT).date()
    kapanis = None
    if ornek:
        bugun += timedelta(days=(6 - bugun.weekday()) % 7)   # örnekte bu haftanın pazarı gibi
        if os.environ.get("ORNEK_GUN", "").strip():          # örnek önizlemede başka bir pazar
            bugun = date.fromisoformat(os.environ["ORNEK_GUN"].strip())
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
    aktif = yorum.VADELER   # kısa ve orta vade (uzun vade 17 Ekim 2026'da kalıcı olarak kaldırıldı)
    ist = {v["anahtar"]: ist[v["anahtar"]] for v in aktif}

    if ornek:
        gelismeler, yz = yorum.ORNEK_GELISMELER, yorum.ORNEK_YORUM
        hatalar = yorum.denetle(yz, gelismeler, aktif)
        if hatalar:
            raise RuntimeError(f"Örnek yorum denetimden geçmedi: {hatalar}")
    else:
        gelismeler = yorum.haftanin_gelismeleri(bugun)
        if gelismeler is None and os.environ.get("ANTHROPIC_API_KEY", "").strip():
            # 14 Ekim 2026 denemesi: tarama bir kez kaynaksız döndü, hemen ardından düzgün çalıştı. Bir kez daha dene
            # (~6 sent); yine olmazsa yorum yalnızca fiyat ve kur verileriyle yazılır (açıklamada belirtilir).
            print("Haber taraması bir kez daha deneniyor.")
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
    for v in aktif:
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
        "baslik": yorum.vade_basligi(aktif),   # "Kısa ve orta vade"
    }

    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    dosyalar = []
    for sayfa in range(len(vadeler) + 1):
        jpg = cikti / f"yorum-{damga}-{sayfa + 1}.jpg"
        gorsel_uret("yorum", {**veri, "sayfa": sayfa, "toplam": len(vadeler) + 1}, jpg)
        dosyalar.append(jpg.name)
    kaynaklar = _kaynak_satirlari(veri).replace(f"\nMüzik: {muzik_kunyesi()}", "")
    metin = yorum.aciklama(veri, yz, kaynaklar, gelismeler)
    reels = yorum_reels_uret(cikti, veri, metin, damga) if YORUM_REELS else None
    (cikti / "meta.json").write_text(json.dumps({"tur": "yorum", "dosyalar": dosyalar, "aciklama": metin,
                                                 "reels": reels,
                                                 "yorum": yz, "istatistik": ist, "gelismeler": gelismeler,
                                                 "son_veri": {"tarih": son_gun, **son}},
                                                ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if gelismeler:
        print("Haftanın gelişmeleri (yapay zekâ özeti, web araması):\n" + gelismeler["metin"] + "\n")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      + "".join(f"<p><a href='{d}'>{d}</a></p>" for d in dosyalar), encoding="utf-8")
    print(metin)
    print(f"\nÜretilen dosyalar ({len(metin)} karakter açıklama):", *dosyalar,
          *([reels["dosya"], reels["kapak"]] + ([reels["hikaye_dosya"]] if reels.get("hikaye_dosya") else [])
            if reels else []), sep="\n")


# Pazar yorumunun Reels'i (Rıdvan, 15 Ekim 2026 21:25: "Reels bence şart"; 21:53: "Reels'te düzgün bir pazar
# analizi videosu olmalı. Zaten 4 sayfa. Süre biraz uzun olabilir"): kaydırmalı gönderinin sayfaları sırayla,
# 9:16 ekranı dolduran bir video (kapak → kısa → orta vade; uzun vade 17 Ekim 2026'da kaldırıldı). Kaydırmalıyla AYNI çalıştırmada,
# gönderiden hemen sonra paylaşılır ve aynı video hikâyeye de konur. Reels üretilemez ya da paylaşılamazsa
# kaydırmalı gönderi yine gider (yalnızca uyarı). Kapatmak için False.
YORUM_REELS = True
# Rıdvan 21:59: "3 sn giriş 6 sn sayfalar"; 22:05: "Giriş çok kısa oldu. Hepsi 8 saniye olsun".
# Müzikli sürümde sahne sayısı vadelere göre: kapak + vade başına YORUM_REELS_SAHNELER[0] sn (kısa ve orta vade: 24 sn).
YORUM_REELS_SAHNELER = (8, 8, 8)   # sn: kapak, kısa, orta vade (toplam 24 sn)


# Pazar Reels'i sesli (Rıdvan, 17 Ekim 2026: "Pazar günü analiz sesli olsun"; Gemini erkek sesi, analizin TAMAMI):
# analizi Claude yazar, ses ekrandaki metnin tamamını sahne sahne okur (bot/yorum.py → seslendirme_parcalari),
# her sahne sesi kadar sürer (1,5 kat hızla ~1,5 dk) ve sonda kapanış sahnesi gelir. Ses seçilmediyse (ses.YORUM_SES None),
# kapalıysa ya da herhangi bir hatada Reels 24 sn ve yalnızca müzikle gider. Hikâyeye her zaman 24 sn'lik
# müzikli video gider (hikâye en çok 60 sn; rehberdeki gibi). Kapatmak için False.
YORUM_SESLI = True


def _yorum_zamanlari(parcalar, sl, sureler):
    """Sahne öğelerinin belirme anı (sahne süresinin oranı): her öğe kendi cümlesi okunmaya başlarken belirir.
    Konuşma süresi sahnedeki harf sayısına göre paylaştırılır (tek okuma, parça parça süre yok)."""
    import ses
    zaman = []
    for sahne, konusma, d in zip(parcalar, sl["parca_sn"], sureler):
        toplam = sum(len(m) for _, m in sahne) or 1
        bas, g = 0, {}
        for ad, m in sahne:
            g[ad] = round(max(0.0, ses.KARE_ON + konusma * bas / toplam - 0.25) / d, 4)
            bas += len(m) + 1
        zaman.append(g)
    return zaman


def yorum_seslendirmesi(veri, cikti):
    """Pazar Reels'inin erkek sesi seslendirmesi: (parçalar, sonuç) ya da None (o hafta sessiz Reels)."""
    import ses
    import yorum
    # SES_ADI: yalnız paylaşmayan elle denemede (paylas.yml → ses girdisi); ses seçilmeden önizleme için de
    ad = os.environ.get("SES_ADI", "").strip() or ses.YORUM_SES
    if not YORUM_SESLI or not ses.SES_ACIK or not ad or os.environ.get("SES_KAPALI"):
        return None
    try:
        parcalar = yorum.seslendirme_parcalari(veri)
        metinler = [ses._cumle(ses.okunur(" ".join(m for _, m in sahne))) for sahne in parcalar]
        sl = ses.rehber_seslendir(metinler, cikti, "yorum", ses=ad,
                                  uslup=ses.USLUP_ERKEK, en_uzun=ses.YORUM_EN_UZUN,
                                  en_az=[ses.YORUM_EN_AZ[0]] + [ses.YORUM_EN_AZ[1]] * len(veri["vadeler"])
                                  + [ses.YORUM_EN_AZ[-1]],
                                  deneme=_deneme_mi())
        return parcalar, sl
    except Exception as e:
        print(f"::warning::Pazar seslendirmesi yapılamadı ({type(e).__name__}: {str(e)[:200]}); "
              "pazar Reels'i yalnızca müzikle gidiyor.")
        return None


def _yorum_sesli_metin(metin):
    """Açıklamaya seslendirme notu (uyarıdan önce). Sınır aşılırsa önce soru satırı çıkar; yine aşarsa not eklenmez."""
    import ses
    ek = ses.ACIKLAMA_SATIRI + "\n\n"
    yeni = metin.replace("Uyarı: ", ek + "Uyarı: ", 1) if "Uyarı: " in metin else metin + "\n\n" + ses.ACIKLAMA_SATIRI
    if len(yeni) > 2200:
        yeni = yeni.replace("Sizce gümüş önümüzdeki haftalarda ne yöne gider? Yorumlara yazın 👇\n\n", "")
    return yeni if len(yeni) <= 2200 else metin


def yorum_reels_uret(cikti, veri, metin, damga):
    """Pazar Reels'inin videosu, kapağı ve açıklaması. Hata verirse None (kaydırmalı gönderi etkilenmez).
    Sesliyse Reels uzun sesli video, hikâye 24 sn'lik müzikli video ("hikaye_dosya")."""
    sahneler_ = [YORUM_REELS_SAHNELER[0]] * (len(veri["vadeler"]) + 1)   # kapak + vadeler, 8'er sn
    sure = sum(sahneler_)
    muzikli = {**veri, "sahne_sureleri": sahneler_}
    try:
        mp4 = cikti / f"yorum-reels-{damga}.mp4"
        if not hareketli_video_uret("yorum-reels", muzikli, mp4, sure=sure):
            raise RuntimeError("şablonda hareket yok")
        kapak = cikti / f"kapak-yorum-reels-{damga}.jpg"
        gorsel_uret("yorum-reels", muzikli, kapak)
    except Exception as e:
        print(f"::warning::Pazar Reels'i üretilemedi ({type(e).__name__}: {e}); yalnızca kaydırmalı gönderi gidecek.")
        return None
    # Açıklama kaydırmalıyla aynı (uyarılar, kaynaklar, etiketler); yalnızca "kaydırın" satırı profile yönlendirir.
    reels_metin = metin.replace("Ayrıntılar görsellerde, kaydırın →",
                                f"Yorumun {len(veri['vadeler']) + 1} sayfası profildeki kaydırmalı gönderide de var →")
    # Yedek kapak anı: kapak sahnesinin bütün öğeleri görünürken (kapak sahnesinin sonundan 1 sn önce)
    sonuc = {"dosya": mp4.name, "kapak": kapak.name, "kapak_ms": int((sahneler_[0] - 1) * 1000),
             "aciklama": reels_metin, "seslendirme": None}
    sesli = yorum_seslendirmesi(veri, cikti)
    if sesli:
        parcalar, sl = sesli
        sureler = sl["kare_sn"]
        zaman = _yorum_zamanlari(parcalar, sl, sureler)
        vadeler = [{**v, "g": z} for v, z in zip(veri["vadeler"], zaman[1:])]
        mp4s = cikti / f"yorum-reels-sesli-{damga}.mp4"
        try:
            if not hareketli_video_uret("yorum-reels", {**veri, "vadeler": vadeler, "kapak_g": zaman[0],
                                                        "sahne_sureleri": sureler, "sesli": True},
                                        mp4s, sure=sl["sure"], seslendirme=sl["wav"]):
                raise RuntimeError("şablonda hareket yok")
            sonuc.update({"dosya": mp4s.name, "hikaye_dosya": mp4.name, "aciklama": _yorum_sesli_metin(reels_metin),
                          "kapak_ms": int((sureler[0] - 0.5) * 1000), "seslendirme": sl["ses"],
                          "ses_metni": sl["metin"], "sure": sl["sure"]})
            print(f"Pazar seslendirmesi: {sl['ses']} ({sl['model']}), {sl['sure']} sn, sahneler {sureler}")
        except Exception as e:
            print(f"::warning::Sesli pazar Reels'i üretilemedi ({type(e).__name__}: {str(e)[:200]}); "
                  "24 sn'lik müzikli Reels gidiyor.")
            mp4s.unlink(missing_ok=True)
        finally:
            sl["wav"].unlink(missing_ok=True)   # ara dosya yayına çıkmasın
    return sonuc


def kart_hazirla(cikti, konu, ornek):
    """Haftalık kart (bot/kart.py): çarşamba "Kaç gram eder?", cuma altın–gümüş. ~10:00 Reels ve ~20:00 özetten
    AYRI bir paylaşımdır; onlara dokunmaz. Günlük fiyat kaydı yazmaz (kayıt Reels ve özetin işi)."""
    import kart
    bugun = datetime.now(TR_SAAT).date()
    hangi = konu or kart.bugunun_karti(bugun)
    if hangi not in kart.KART_ADI:
        print(f"::warning::Paylaşım atlandı: bugün haftalık kart yok (konu: {konu or 'boş'})")
        return
    try:
        fiyat = ornek_fiyatlar() if ornek else fiyatlari_al(kaydet=False, kaynak="kart")
    except VeriYok as e:
        print(f"::warning::Paylaşım atlandı: {e}")
        return
    veri = veri_hazirla(fiyat, hesap_adi())
    # Kartta günlük başlık, manşet ve özel gün görseli yok (onlar Reels ve özette)
    veri.update({"ozel": None, "gun_baslik": None, "baslik_notu": None, "buyuk_hareket": None})
    if hangi == "gram":
        veri.update(kart.gram_karti(fiyat, tr_sayi))
    else:
        veri.update(kart.parite_karti(fiyat, tr_sayi, degisim, bugun))
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    sablon = f"kart-{hangi}"
    png = cikti / f"kart-{hangi}-{damga}.png"
    gorsel_uret(sablon, veri, png)
    mp4 = cikti / f"kart-{hangi}-{damga}.mp4"
    sure = 10
    if not hareketli_video_uret(sablon, veri, mp4, sure=sure):
        video_uret(png, mp4, sure=sure)
    kapak = kapak_uret("kart", veri, cikti / f"kapak-kart-{hangi}-{damga}.jpg")
    aciklama = kart.aciklama(veri, _kaynak_satirlari(veri))
    (cikti / "meta.json").write_text(json.dumps({"tur": "kart", "kart": hangi, "dosya": mp4.name, "aciklama": aciklama,
                                                 "kapak_ms": int((sure - 0.5) * 1000), "kapak": kapak,
                                                 "fiyatlar": {k: v for k, v in fiyat.items()
                                                              if k not in ("gecmis_gram", "gecmis_parite", "donem_kayit")}},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      f"<p>Son üretilen dosya: <a href='{mp4.name}'>{mp4.name}</a></p>", encoding="utf-8")
    print(aciklama)
    print(f"\nKart: {kart.KART_ADI[hangi]}")
    print(f"Üretilen dosya: {mp4}")


# Bilgi sayfasının bir kezlik tanıtım Reels'i (Rıdvan, 19 Ekim 2026: web sayfası tanıtımı, 2. madde "2 uygula").
# Fiyat yok: eskimez, Rıdvan profilde sabitler, ileride reklam olarak da kullanılabilir. Takvimde yok; yalnızca elle
# (Run workflow → tür: tanitim) ya da tek seferlik zamanlanmış görevle gider. Hikâyeye gitmez (sayımda 1).
# Özellikler sitenin gerçekten sunduklarıdır (ana sayfa, hesap/, gecmis/, rehber/); site değişirse burası da değişir.
TANITIM_SURE = 12
TANITIM_OZELLIKLER = [
    {"baslik": "Hesap makinesi", "alt": "gram ↔ TL",
     "simge": '<rect x="10" y="5" width="32" height="42" rx="5"/><path d="M17 15h18"/>'
              '<path d="M18 26h2M26 26h2M34 26h2M18 34h2M26 34h2M34 34h2M18 41h2M26 41h10"/>'},
    {"baslik": "Son 30 günün grafiği", "alt": None,
     "simge": '<path d="M6 44h40"/><path d="M8 36l10-11 8 6 9-13 9 7"/>'},
    {"baslik": "Kaç gram, kaç lira?", "alt": "1 g'dan 1 kg'a",
     "simge": '<path d="M26 8v34M15 44h22M9 15h34"/><path d="M9 15 3 29h12zM43 15l-6 14h12z"/>'},
    {"baslik": "Geçmiş fiyatlar", "alt": "ay ay",
     "simge": '<rect x="7" y="10" width="38" height="34" rx="5"/><path d="M7 21h38M17 5v9M35 5v9"/>'},
    {"baslik": "Gümüş rehberi", "alt": "bütün bölümler",
     "simge": '<path d="M26 14c-5-4-12-5-19-4v30c7-1 14 0 19 4 5-4 12-5 19-4V10c-7-1-14 0-19 4z"/><path d="M26 14v30"/>'},
]
HASHTAG_TANITIM = "#gümüş #gramgümüş #gümüşfiyatları #gümüşyatırımı #külçegümüş"


def tanitim_aciklamasi(muzik=None):
    """Tanıtım Reels'inin açıklaması (fiyatsız; model ya da şirket adı yok)."""
    import bilgi
    satirlar = [
        f"Gram gümüş için tek adres: {bilgi.SITE} (bağlantı biyografide)",
        "",
        "Sitemizde neler var?",
        "· Hesap makinesi: gram ↔ TL, Türkçe sayı yazımıyla (1.250,5)",
        "· Son 30 günün grafiği ve son günlerin fiyatları",
        "· Kaç gram eder, kaç lira eder? 1 gramdan 1 kilograma; hurda ve milyem hesabı",
        "· Ay ay geçmiş fiyatlar",
        "· Gümüş rehberinin bütün bölümleri",
        "",
        "Sayfa her paylaşımla kendiliğinden güncellenir; çerez kullanmaz.",
        "Hafta içi ~10:00 ve ~20:00 gram gümüş fiyatı, cumartesi haftalık özet, pazar üst düzey yapay zekâ analizi: "
        "hepsi burada, Instagram'da.",
        "",
        "Bilgi amaçlıdır, yatırım tavsiyesi değildir.",
    ]
    if muzik:
        satirlar += ["", f"Müzik: {muzik}"]
    satirlar += ["", HASHTAG_TANITIM]
    return "\n".join(satirlar)


def tanitim_hazirla(cikti):
    """Bilgi sayfasının tanıtım Reels'i: 12 sn müzikli hareketli video + kapak (videonun son hâli)."""
    import bilgi
    cikti = Path(cikti)
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    veri = {"site": bilgi.SITE, "hesap": hesap_adi(), "ozellikler": TANITIM_OZELLIKLER,
            "maskot": "goril/istif.svg", "maskot_js": "goril/istif.js"}
    kapak = cikti / f"tanitim-{damga}-kapak.jpg"
    gorsel_uret("site-reels", veri, kapak)                       # kare çağrılmadan: son hâl
    mp4 = cikti / f"tanitim-{damga}.mp4"
    if not hareketli_video_uret("site-reels", veri, mp4, sure=TANITIM_SURE):
        raise RuntimeError("tanıtım Reels'i hareketli üretilemedi")
    aciklama = tanitim_aciklamasi(muzik_kunyesi())
    if len(aciklama) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(aciklama)} > 2200 karakter)")
    (cikti / "meta.json").write_text(json.dumps({"tur": "tanitim", "dosya": mp4.name, "aciklama": aciklama,
                                                 "kapak": kapak.name, "kapak_ms": int((TANITIM_SURE - 0.5) * 1000)},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      f"<p><a href='{mp4.name}'>{mp4.name}</a></p><p><a href='{kapak.name}'>{kapak.name}</a></p>",
                                      encoding="utf-8")
    print(aciklama)
    print(f"\nÜretilen dosyalar ({len(aciklama)} karakter açıklama): {mp4.name}, {kapak.name}")


def _baslik_ozeti(veri):
    """meta.json ve iş akışı günlüğü için: o gün hangi başlık kuralı tuttu."""
    if veri.get("ozel"):
        return {"tur": "ozel-" + veri["ozel"]["tur"], "metin": veri["ozel"]["manset"]}
    if veri.get("buyuk_hareket"):
        return {"tur": "buyuk-hareket", "metin": veri["buyuk_hareket"]["metin"]}
    if veri.get("gun_baslik"):
        return {"tur": "gunluk-" + veri["gun_baslik"]["kural"], "metin": veri["gun_baslik"]["metin"]}
    return None


# Cumartesi haftalık özetinde ertesi günün pazar yorumu hatırlatması (Rıdvan, 15 Ekim 2026 21:28: "Cumartesi
# için pazar derin analizi kaçırmayın benzeri bir hatırlatma"). Görselde (Reels ve hikâyesi) ve açıklamada.
# KURAL (Rıdvan, 15 Ekim 2026 23:22: "bu kural olmalı. her cumartesi bu yazı çıkmalı."): her cumartesi çıkar;
# takvime ya da kayıtlara bakılmaz, hata yüzünden düşmez. Pazar yorumu her pazar zamanlı olduğu için söz boş
# kalmaz; bot/test_pazar.py ikisini birlikte denetler (pazar yorumu takvimden çıkarsa sınama kırılır).
PAZAR_HATIRLATMA = {"kalin": "Yarın ~11:00", "metin": "Pazar derin analizi: kısa ve orta vade. Kaçırmayın."}


def pazar_yorumu_yarin(bugun=None):
    """Haftalık özette pazar hatırlatması çıkacak mı: KURAL, her cumartesi evet (TR saatine göre).
    Başka gün elle çalıştırılan haftalık özette "Yarın ~11:00" yanlış olacağı için çıkmaz."""
    bugun = bugun or datetime.now(TR_SAAT).date()
    return bugun.weekday() == 5


def hazirla(tur, cikti, ornek, konu=None):
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "meta.json").unlink(missing_ok=True)   # eski bir paylaşım yanlışlıkla tekrar gitmesin
    if tur == "yasal":
        yasal_hazirla(cikti)
        return
    if tur == "bilgi":
        bilgi_hazirla(cikti, konu)
        return
    if tur == "hikaye":
        hikaye_hazirla(cikti, konu)
        return
    if tur == "kisa":
        import bilgi
        konu = konu or bilgi.bugunun_arsiv_bolumu()
        if not konu:
            print("::warning::Paylaşım atlandı: bugün rehber arşivi Reels'i günü değil")
            return
        kisa_hazirla(cikti, konu)
        return
    if tur == "kart":
        kart_hazirla(cikti, konu, ornek)
        return
    if tur == "tanitim":
        tanitim_hazirla(cikti)
        return
    if tur == "yorum":
        try:
            yorum_hazirla(cikti, ornek)
        except VeriYok as e:
            print(f"::warning::Paylaşım atlandı: {e}")
        return
    try:
        if tur == "hafta":
            fiyat = ornek_haftalik(kismi=os.environ.get("ORNEK_KISMI") == "1") if ornek else haftalik_fiyatlari_al()
        elif tur == "ay":
            fiyat = ornek_aylik(kismi=os.environ.get("ORNEK_KISMI") == "1") if ornek else aylik_fiyatlari_al()
        else:
            fiyat = ornek_fiyatlar() if ornek else fiyatlari_al(kaydet=True, kaynak=tur)
    except VeriYok as e:
        # Hata değil: paylaşım bu sefer atlanır, iş akışı sonraki adımları çalıştırmaz.
        print(f"::warning::Paylaşım atlandı: {e}")
        return
    hesap = hesap_adi()
    hazirlayici = {"hafta": haftalik_veri_hazirla, "ay": aylik_veri_hazirla}.get(tur)
    veri = hazirlayici(fiyat, hesap) if hazirlayici else veri_hazirla(fiyat, hesap, tur)
    if tur == "hafta":
        veri["pazar_hatirlatma"] = PAZAR_HATIRLATMA if (ornek or pazar_yorumu_yarin()) else None

    veri["parite_cumle"] = gorsel_parite_cumlesi(veri, tur)
    veri.update(goril_alanlari(veri, tur, ornek))
    damga = datetime.now(TR_SAAT).strftime("%Y%m%d-%H%M")
    # Özel günde (eşik aşıldı / en az bir aylık en yüksek) aynı paylaşım özel görselle gider.
    # Özel görsel üretilemezse paylaşım olağan görselle yapılır.
    sablon = "ozel" if veri.get("ozel") else tur
    png = cikti / f"{tur}-{damga}.png"
    # Her paylaşım sesli video (Reels) olarak gider; özetler okunabilsin diye biraz daha uzun.
    # Haftalık ve aylık özet 3 sn daha uzun ekranda kalır (Rıdvan, 18 Ekim 2026; özel gün görseline dönse de).
    mp4 = cikti / f"{tur}-{damga}.mp4"
    sure = video_suresi(tur, sablon)
    # Goril: ayrı süreçte, süre sınırı ve yerleşim denetimiyle. Olmazsa aşağıdaki bugünkü yol gorilsiz çalışır.
    gorilli = bool(veri.get("maskot")) and goril_ile_uret(sablon, veri, png, mp4, sure)
    if not gorilli:
        veri.update(GORIL_YOK)
        try:
            gorsel_uret(sablon, veri, png)
        except Exception as e:
            if sablon != "ozel":
                raise
            print(f"::warning::Özel gün görseli üretilemedi, olağan görselle devam ediliyor: {type(e).__name__}: {e}")
            veri["ozel"], veri["baslik_notu"], sablon = None, None, tur
            gorsel_uret(sablon, veri, png)
        sure = video_suresi(tur, sablon)
        try:
            hareketli = hareketli_video_uret(sablon, veri, mp4, sure=sure)
        except Exception as e:
            if sablon != "ozel":
                raise
            print(f"::warning::Özel gün videosu hareketli üretilemedi, durağan video kullanılıyor: {type(e).__name__}: {e}")
            hareketli = False
        if not hareketli:
            video_uret(png, mp4, sure=sure)
    dosya = mp4.name
    kapak = kapak_uret(tur, veri, cikti / f"kapak-{tur}-{damga}.jpg")

    aciklama = aciklama_yaz(veri, tur)
    (cikti / "meta.json").write_text(json.dumps({"tur": tur, "dosya": dosya, "aciklama": aciklama,
                                                 "kapak_ms": int((sure - 0.5) * 1000),
                                                 "kapak": kapak,
                                                 "baslik": _baslik_ozeti(veri),
                                                 "goril": veri.get("goril"),
                                                 "goril_cakisma": veri.get("goril_cakisma"),
                                                 "fiyatlar": {k: v for k, v in fiyat.items()
                                                              if k not in ("gecmis_gram", "gecmis_parite", "donem_kayit")}},
                                                ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (cikti / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Gümüş bot</title>"
                                      f"<p>Son üretilen dosya: <a href='{dosya}'>{dosya}</a></p>"
                                      "<p>Metal fiyatları: <a href='https://metalcharts.org'>MetalCharts</a>"
                                      " · Dolar/TL: ECB referans kurları (<a href='https://frankfurter.dev'>Frankfurter</a>)</p>", encoding="utf-8")
    print(aciklama)
    ozet = _baslik_ozeti(veri)
    print(f"\nBaşlık: {ozet['metin']} ({ozet['tur']})" if ozet else "\nBaşlık: yok (olağan gün)")
    print(f"Üretilen dosya: {cikti / dosya}")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    h = alt.add_parser("hazirla")
    h.add_argument("--tur", choices=["reels", "post", "hafta", "ay", "yasal", "bilgi", "kisa", "yorum", "hikaye", "kart",
                                     "tanitim"],
                   required=True)
    h.add_argument("--cikti", default="site")
    h.add_argument("--ornek", action="store_true", help="Gerçek fiyat yerine örnek veri kullan")
    h.add_argument("--konu", default=None,
                   help="bilgi/kisa/hikaye türünde bölüm numarası (boşsa bilgi için bugünün rehber, kisa için bugünün "
                        "arşiv Reels'i bölümü); "
                        "kart türünde gram ya da parite (boşsa günün kartı)")
    y = alt.add_parser("yayinla")
    y.add_argument("--cikti", default="site")
    y.add_argument("--url", required=True)
    y.add_argument("--bekle-dk", type=int, default=0,
                   help="Instagram geçici engel verirse en çok bu kadar dakika bekleyip yeniden dene (0: deneme)")
    alt.add_parser("token-yenile")
    alt.add_parser("gun-ici", help="paylaşımsız gün içi fiyat kaydı (kaydet.yml)")
    alt.add_parser("gecmis-kontrol", help="MetalCharts 1 yıllık geçmişi geliyor mu (gecmis-kontrol.yml; paylaşım yok)")
    gc = alt.add_parser("goril-ciz", help="iç kullanım: gorilli görseli ayrı süreçte üretir (goril_ile_uret)")
    gc.add_argument("--girdi", required=True)
    gc.add_argument("--sonuc", required=True)
    a = ap.parse_args()

    if a.komut == "hazirla":
        if a.konu is not None and a.tur != "kart":
            a.konu = int(a.konu)
        hazirla(a.tur, KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.ornek, a.konu)
    elif a.komut == "yayinla":
        try:
            yayinla(KOK / a.cikti if not os.path.isabs(a.cikti) else Path(a.cikti), a.url, a.bekle_dk)
        finally:
            # Günlük sınır için gerçek sayı (bot/sinir.py): iş akışı bunu "gorunen-…" eseri olarak saklar
            print(f"Bu çalıştırmada takipçiye gösterilen içerik (akış + Reels + hikâye): {_GORUNEN[0]}")
            if os.environ.get("GORUNEN_DOSYA"):
                Path(os.environ["GORUNEN_DOSYA"]).write_text(str(_GORUNEN[0]), encoding="utf-8")
    elif a.komut == "goril-ciz":
        goril_ciz(a.girdi, a.sonuc)
    elif a.komut == "gecmis-kontrol":
        # MetalCharts planında 1 yıllık geçmiş var mı (Starter, 17 Ekim 2026; Ocak 2027'de iptal edilince 403 beklenir)
        g = metal_gecmisi()
        if not g:
            print("::warning::MetalCharts geçmişi gelmedi (ücretsiz plan ya da hata); pazar yorumu kendi kayıtlarla yazılır.")
        for sembol, gunler in (g or {}).items():
            print(f"{sembol}: {len(gunler)} gün, {min(gunler)} – {max(gunler)}")
        if g:
            # Pazar yorumunun vadeleri bu geçmişle doluyor mu (yalnız MetalCharts + ECB; kendi kayıtlar katılmaz)
            import yorum
            ecb = ecb_gecmisi()
            ist = yorum.vade_istatistikleri(yorum.seri_kur({}, ecb, g), ecb)
            yz = lambda x: "—" if x is None else f"%{x:+.2f}"
            for v in yorum.VADELER:
                s = ist[v["anahtar"]]
                print(f"{v['anahtar']}: veri {'tam' if s['veri_yeterli'] and not s['kisa_kayit'] else 'EKSİK'}, "
                      f"başlangıç {s['baslangic']}, gram {yz(s['gram'])}, ons {yz(s['ons'])}, dolar/TL {yz(s['dolar'])}")
    elif a.komut == "gun-ici":
        try:
            gun_ici_kaydet()
        except Exception as e:          # paylaşım değil: iş kırmızı bitmesin, hata maili gelmesin
            print(f"::warning::Gün içi kayıt yapılamadı: {type(e).__name__}: {e}")
    else:
        token_yenile()


if __name__ == "__main__":
    main()
