"""Deneme çalıştırmaları MetalCharts hakkı harcamaz (Rıdvan, 16 Ekim 2026). Ağ yok.
Çalıştır: python bot/test_deneme.py

- DENEME=true: /v1/prices ve /v1/history'ye istek atılmaz; fiyat botun son kaydından (günlük kayıt ya da gün içi
  noktanın en yenisi) gelir. Günlük kayıt yazılmaz. Hiç kayıt yoksa uyarıyla MetalCharts'a gidilir.
- DENEME yok/false: eskisi gibi MetalCharts'a gidilir.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


gecici = Path(tempfile.mkdtemp())
main.GECMIS_DOSYASI = gecici / "gecmis.json"
main.GUN_ICI_DOSYASI = gecici / "gun_ici.json"
main.GUN_ICI_DEGISTI = gecici / "gun_ici_degisti.txt"
os.environ["METALCHARTS_KEY"] = "mc_live_sahte"

istekler = []


class Yanit:
    status_code = 200
    headers = {"x-ratelimit-month-limit": "200", "x-ratelimit-month-remaining": "150"}

    def json(self):
        return {"data": {"XAG": {"price": 60.0, "changePercent24h": 1.0}, "XAU": {"price": 4400.0}}}


def sahte_get(url, **k):
    istekler.append(url)
    if "metalcharts" in url:
        return Yanit()
    raise AssertionError(f"beklenmeyen istek: {url}")


main.requests.get = sahte_get
main.kurlar = lambda: ((main.date(2026, 10, 16), 49.418), (main.date(2026, 10, 15), 49.39))

main.GECMIS_DOSYASI.write_text(json.dumps({
    "2026-10-15": {"saat": "20:18", "gumus": 56.94, "altin": 4250.0, "dolar": 49.418, "kur_tarihi": "2026-10-15", "gram": 90.46},
    "2026-10-16": {"saat": "10:22", "gumus": 57.78, "altin": 4290.0, "dolar": 49.418, "kur_tarihi": "2026-10-15", "gram": 91.80},
}), encoding="utf-8")

# 1) Deneme: istek yok, en yeni kayıt (günlük kayıt 10:22)
os.environ["DENEME"] = "true"
m = main.metal_fiyatlari()
kontrol(istekler == [] and m["XAG"]["fiyat"] == 57.78 and m["XAU"]["fiyat"] == 4290.0, f"deneme günlük kayıttan: {m}")

# 2) Gün içi nokta daha yeniyse o kullanılır
main.GUN_ICI_DOSYASI.write_text(json.dumps({"gunler": {"2026-10-16": [
    {"saat": "13:26", "gumus": 57.70, "altin": 4285.0, "gram": 91.79}]}}), encoding="utf-8")
m = main.metal_fiyatlari()
kontrol(istekler == [] and m["XAG"]["fiyat"] == 57.70, "deneme en yeni gün içi noktadan")

# 3) Geçmiş ve kapanış istekleri de denemede yok
kontrol(main.metal_gecmisi() is None and istekler == [], "denemede /v1/history isteği yok")
kontrol(main.kapanis_fiyati({}) is None and istekler == [], "denemede kapanış fiyatı isteği yok")

# 4) Denemede fiyatlari_al günlük kayıt yazmaz, gün içi nokta da yazmaz
once = main.GECMIS_DOSYASI.read_text(encoding="utf-8")
gun_ici_once = main.GUN_ICI_DOSYASI.read_text(encoding="utf-8")
f = main.fiyatlari_al(kaydet=True, kaynak="post")
kontrol(istekler == [] and main.GECMIS_DOSYASI.read_text(encoding="utf-8") == once, "denemede günlük kayıt yazılmaz")
kontrol(main.GUN_ICI_DOSYASI.read_text(encoding="utf-8") == gun_ici_once, "denemede gün içi nokta yazılmaz")
kontrol(abs(f["gram"] - 57.70 * 49.418 / main.ONS_GRAM) < 1e-9, "deneme gramı kayıtlı onsla hesaplanır")

# 5) Hiç kayıt yoksa uyarıyla MetalCharts'a gider (önbellek silinmişse deneme yine çalışsın)
main.GECMIS_DOSYASI.unlink()
main.GUN_ICI_DOSYASI.unlink()
m = main.metal_fiyatlari()
kontrol(len(istekler) == 1 and m["XAG"]["fiyat"] == 60.0, "kayıt yoksa MetalCharts'a 1 istek")

# 6) Gerçek çalıştırma: eskisi gibi MetalCharts
istekler.clear()
for deger in ("false", ""):
    os.environ["DENEME"] = deger
    m = main.metal_fiyatlari()
kontrol(len(istekler) == 2 and m["XAG"]["fiyat"] == 60.0, "gerçek çalıştırmada her seferinde MetalCharts")
kontrol(main.SON_KOTA.get("x-ratelimit-month-remaining") == "150", "gerçek çalıştırmada kota okunur")

print(f"test_deneme: {gecen} sınama geçti")
