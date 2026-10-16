"""Gün içi kayıt, akşam özeti ek satırları ve haftalık/aylık "kaynağı" satırı sınamaları (ağ yok).
Çalıştır: python bot/test_gun_ici.py

Rıdvan, 16 Ekim 2026: akşam özeti "bugün ne oldu" (gün içi aralık, son 1 hafta / 1 ay); ons/kur ayrımının
yeri günlük değil cumartesi ve aylık özet; gün içi kayıt paylaşım yapmaz, MetalCharts hakkı paylaşımlara kalır.
"""
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


TR = main.TR_SAAT
gecici = Path(tempfile.mkdtemp())
main.GUN_ICI_DOSYASI = gecici / "gun_ici.json"
main.GUN_ICI_DEGISTI = gecici / "gun_ici_degisti.txt"

# --- 1) Gün içi satırı -------------------------------------------------------------------------------
kontrol(main.gun_ici_satiri([("10:22", 91.8), ("20:04", 92.0)]) is None, "2 noktayla satır yok")
s = main.gun_ici_satiri([("10:22", 91.80), ("12:35", 90.921), ("16:35", 92.104), ("20:04", 91.5)])
kontrol(s == "Gün içi: en düşük 90,92 ₺ (12:35) · en yüksek 92,10 ₺ (16:35)", f"biçim: {s}")
s = main.gun_ici_satiri([("10:22", 91.801), ("12:35", 91.799), ("20:04", 91.80)])
kontrol(s == "Gün içi: 91,80 ₺, gün boyunca değişmedi", f"görselde aynı değer: {s}")
s = main.gun_ici_satiri([("10:22", 92.0), ("12:35", 91.0), ("14:35", 92.0), ("20:04", 91.0)])
kontrol(s == "Gün içi: en düşük 91,00 ₺ (12:35) · en yüksek 92,00 ₺ (10:22)", f"eşitlikte ilk saat: {s}")

# --- 2) Noktaların birleşmesi: dosya + sabahki kayıt + şimdiki, aynı saat bir kez ------------------
gun = date(2026, 10, 19)
main.GUN_ICI_DOSYASI.write_text('{"gunler": {"2026-10-19": [{"saat": "10:22", "gram": 91.0}, '
                                '{"saat": "12:35", "gram": 90.5}], "2026-10-16": [{"saat": "12:35", "gram": 1}]}}',
                                encoding="utf-8")
n = main.gun_ici_noktalari(gun, {"saat": "10:22", "gram": 91.0}, ("20:04", 92.0))
kontrol(n == [("10:22", 91.0), ("12:35", 90.5), ("20:04", 92.0)], f"birleşme: {n}")
n = main.gun_ici_noktalari(date(2026, 10, 20), {"saat": "10:15", "gram": 93.0}, ("20:01", 94.0))
kontrol(n == [("10:15", 93.0), ("20:01", 94.0)], "başka günün noktaları karışmaz")
main.GUN_ICI_DOSYASI.write_text("bozuk{", encoding="utf-8")
kontrol(main.gun_ici_noktalari(gun, None, ("20:04", 92.0)) == [("20:04", 92.0)], "bozuk dosya: patlamaz")

# --- 3) Son 1 hafta / 1 ay ----------------------------------------------------------------------------
kayitlar = {"2026-10-13": 93.88, "2026-10-14": 88.18, "2026-10-15": 90.46, "2026-10-16": 91.80}
kontrol(main.donem_satirlari(kayitlar, date(2026, 10, 19), 92.0) == [], "19 Ekim: bir hafta öncesi kayıt yok")
s = main.donem_satirlari(kayitlar, date(2026, 10, 20), 91.80)
kontrol(s == ["Son 1 hafta: ▼ %2,2 (13 Ekim: 93,88 ₺)"], f"20 Ekim örneği (Rıdvan'ın onayladığı biçim): {s}")
s = main.donem_satirlari({"2026-10-16": 91.80}, date(2026, 10, 26), 91.80)
kontrol(s == ["Son 1 hafta: ▬ %0,0 (16 Ekim: 91,80 ₺)"], f"pazartesi: bir hafta önce pazar, cuma kaydı alınır: {s}")
kontrol(main.donem_satirlari({"2026-10-12": 90.0}, date(2026, 10, 23), 91.0) == [],
        "en çok 3 gün geriye: 16 Ekim'den eskisi alınmaz")
s = main.donem_satirlari(dict(kayitlar, **{"2026-11-06": 95.0}), date(2026, 11, 13), 100.0)
kontrol(s == ["Son 1 hafta: ▲ %5,3 (6 Kasım: 95,00 ₺)", "Son 1 ay: ▲ %6,5 (13 Ekim: 93,88 ₺)"], f"13 Kasım: {s}")
s = main.donem_satirlari(kayitlar, date(2026, 11, 16), 91.80)
kontrol(s == ["Son 1 ay: ▬ %0,0 (16 Ekim: 91,80 ₺)"], f"16 Kasım: {s}")
kontrol(main._ay_once(date(2027, 3, 31)) == date(2027, 2, 28), "31 Mart → 28 Şubat")
kontrol(main._ay_once(date(2028, 3, 31)) == date(2028, 2, 29), "artık yıl")
kontrol(main._ay_once(date(2027, 1, 15)) == date(2026, 12, 15), "ocak → geçen yılın aralığı")

# --- 4) Haftanın / ayın kaynağı -------------------------------------------------------------------------
f = {"ons": 57.78, "ons_once": 59.15, "dolar": 49.418, "dolar_once": 49.368}
kontrol(main.kaynak_satiri(f, "Haftanın") == "Haftanın kaynağı: ons gümüş ▼ %2,3 · dolar/TL ▲ %0,1",
        main.kaynak_satiri(f, "Haftanın"))
kontrol(main.kaynak_satiri({"dolar": 1, "dolar_once": 1}, "Ayın") is None, "ons yoksa satır yok")
kontrol(main.kaynak_satiri({"ons": 50, "ons_once": 50.01, "dolar": 49.4, "dolar_once": 49.4}, "Ayın")
        == "Ayın kaynağı: ons gümüş ▬ %0,0 · dolar/TL ▬ %0,0", "sıfır değişim")

# --- 5) Açıklamalar ----------------------------------------------------------------------------------------
temel = main.ornek_fiyatlar()
temel["gecmis_gram"] = kayitlar
v = main.veri_hazirla(dict(temel), "gunlukgumus")
eski_reels = main.aciklama_yaz(dict(v, gun_ici_satiri=None, donem_satirlari=[]), "reels")
kontrol(main.aciklama_yaz(dict(v, gun_ici_satiri="Gün içi: X", donem_satirlari=["Son 1 hafta: Y"]), "reels")
        == eski_reels, "sabah Reels'inin açıklaması değişmez")
post = main.aciklama_yaz(dict(v, gun_ici_satiri="Gün içi: en düşük 1 ₺ (12:35) · en yüksek 2 ₺ (16:35)",
                              donem_satirlari=["Son 1 hafta: ▼ %2,2 (13 Ekim: 93,88 ₺)"]), "post")
satirlar = post.split("\n")
i = next(k for k, s in enumerate(satirlar) if s.startswith("Günün gümüş özeti"))
kontrol(satirlar[i + 1].startswith("Gün içi:") and satirlar[i + 2].startswith("Son 1 hafta:") and satirlar[i + 3] == "",
        "akşam: başlığın altında gün içi, sonra son 1 hafta, sonra boş satır")
kontrol(main.GUN_ICI_NOTU in post, "gün içi notu (2 saatte bir) yazıyor")
sade = main.aciklama_yaz(dict(v, gun_ici_satiri=None, donem_satirlari=[]), "post")
kontrol(main.GUN_ICI_NOTU not in sade and "Gün içi" not in sade, "veri yokken akşam açıklaması eskisi gibi")
kontrol("\n\nAltın/Gümüş paritesi" in sade and "özeti · " in sade.split("\n\n")[0], "veri yokken boşluklar eskisi gibi")
uzun = main.aciklama_yaz(dict(v, goril_satiri="🦍 Goril bugün sevinçli\n",
                              gun_ici_satiri="Gün içi: en düşük 100,00 ₺ (12:35) · en yüksek 110,00 ₺ (16:35)",
                              donem_satirlari=["Son 1 hafta: ▲ %10,0 (13 Ekim: 93,88 ₺)",
                                               "Son 1 ay: ▲ %10,0 (13 Eylül: 93,88 ₺)"]), "post")
kontrol(len(uzun) <= 2200, f"en uzun akşam açıklaması {len(uzun)} ≤ 2200")

h = main.ornek_haftalik(kismi=True)
vh = main.haftalik_veri_hazirla(h, "gunlukgumus")
kontrol(vh.get("kaynak_satiri") is None, "örnek haftada ons yok: satır yok (örnek çıktılar main ile aynı)")
hafta_eski = main.aciklama_yaz(vh, "hafta")
h.update({"ons": 57.78, "ons_once": 59.15})   # dolar örnekteki gibi: 49,25 / 49,21
vh2 = main.haftalik_veri_hazirla(h, "gunlukgumus")
hafta = main.aciklama_yaz(vh2, "hafta")
hs = hafta.split("\n")
j = next(k for k, s in enumerate(hs) if s.startswith("Haftalık gümüş özeti"))
kontrol(hs[j + 1] == "Haftanın kaynağı: ons gümüş ▼ %2,3 · dolar/TL ▲ %0,1" and hs[j + 2] == "",
        "haftalık: başlığın altında kaynak satırı")
kontrol(hafta.replace("Haftanın kaynağı: ons gümüş ▼ %2,3 · dolar/TL ▲ %0,1\n", "") == hafta_eski,
        "haftalıkta başka hiçbir şey değişmez")
kontrol(len(main.aciklama_yaz(dict(vh2, goril_satiri="🦍 Goril bu hafta sevinçli\n",
                                   pazar_hatirlatma=main.PAZAR_HATIRLATMA, buyuk_hareket={"metin": "x"}), "hafta"))
        <= 2200, "en uzun haftalık açıklama ≤ 2200")
a = main.ornek_aylik(kismi=False)
a.update({"ons": 60.0, "ons_once": 55.0, "dolar": 50.2, "dolar_once": 49.3})
ay = main.aciklama_yaz(main.aylik_veri_hazirla(a, "gunlukgumus"), "ay")
kontrol("\nAyın kaynağı: ons gümüş ▲ %9,1 · dolar/TL ▲ %1,8\n\n" in ay, "aylık: kaynak satırı")

# --- 5b) Parite cümlesi (Rıdvan, 16 Ekim 2026): görselde paritenin altında; ok renkleri standart kalır
pc = main.parite_cumlesi
kontrol(pc(main.degisim(72.41, 72.84), "bugün") == "Gümüş bugün altına karşı değer kazandı", "parite düştü")
kontrol(pc(main.degisim(73.10, 72.84), "bugün") == "Gümüş bugün altına karşı değer kaybetti", "parite yükseldi")
kontrol(pc(main.degisim(72.840001, 72.84), "bugün") == "Gümüşün altına karşı değeri bugün değişmedi", "%0,00")
kontrol(pc(main.degisim(70.0, 72.0), "bu hafta") == "Gümüş bu hafta altına karşı değer kazandı", "haftalık")
kontrol(pc(main.degisim(75.0, 72.0), "bu ay") == "Gümüş bu ay altına karşı değer kaybetti", "aylık")
kontrol(main.veri_hazirla(main.ornek_fiyatlar(), "x")["parite_cumle"].startswith("Gümüş bugün altına karşı"),
        "günlük veride cümle var")
kontrol(main.haftalik_veri_hazirla(main.ornek_haftalik(), "x")["parite_cumle"].startswith("Gümüş bu hafta"), "haftalık veri")
kontrol(main.aylik_veri_hazirla(main.ornek_aylik(), "x")["parite_cumle"].startswith("Gümüş bu ay"), "aylık veri")
kontrol("renk" not in main.veri_hazirla(main.ornek_fiyatlar(), "x")["parite_deg"], "ok rengi standart (ters çevrilmez)")
vg = main.veri_hazirla(main.ornek_fiyatlar(), "x")
kontrol(main.gorsel_parite_cumlesi(vg, "reels") is None, "sabah Reels'inde cümle yok (tanım satırı kalır)")
kontrol(main.gorsel_parite_cumlesi(vg, "post") == vg["parite_cumle"], "akşam özetinde cümle var")
kontrol(main.gorsel_parite_cumlesi(main.haftalik_veri_hazirla(main.ornek_haftalik(), "x"), "hafta").startswith("Gümüş bu hafta"),
        "haftalıkta cümle var")

# --- 6) Kota başlıkları -----------------------------------------------------------------------------------
kontrol(main.kota_kalan({"x-ratelimit-limit": "200", "x-ratelimit-remaining": "143"}) == 143, "aylık eş")
kontrol(main.kota_kalan({"x-ratelimit-limit": "10", "x-ratelimit-remaining": "9"}) is None,
        "yalnız dakikalık sınır: aylık sanılmaz")
kontrol(main.kota_kalan({"x-ratelimit-limit-minute": "10", "x-ratelimit-remaining-minute": "9",
                         "x-ratelimit-limit-month": "200", "x-ratelimit-remaining-month": "120"}) == 120, "ikisi birden")
kontrol(main.kota_kalan({}) is None, "başlık yok")
# MetalCharts'ın gerçek başlıkları (16 Ekim 2026 13:23 deneme çalıştırması #38886753911): /v1/prices 1 hak
gercek = {"x-ratelimit-limit": "10", "x-ratelimit-month-limit": "200", "x-ratelimit-month-remaining": "159",
          "x-ratelimit-month-reset": "1793491200", "x-ratelimit-month-used": "41", "x-ratelimit-remaining": "9",
          "x-ratelimit-reset": "1792146180", "x-ratelimit-used": "1"}
kontrol(main.kota_kalan(gercek) == 159, "gerçek başlıklar: aylık kalan 159, dakikalık 9 değil")

# --- 7) Gün içi kayıt işi: atlama kuralları ve yazım -------------------------------------------------
main.GUN_ICI_DOSYASI.unlink(missing_ok=True)
cagri = []
main.metal_fiyatlari = lambda: (cagri.append(1), {"XAG": {"fiyat": 57.78}, "XAU": {"fiyat": 4300.0}})[1]
main.kurlar = lambda: ((date(2026, 10, 16), 49.418), (date(2026, 10, 15), 49.39))
cuma = lambda s: datetime(2026, 10, 16, *map(int, s.split(":")), tzinfo=TR)   # noqa: E731
kontrol(main.gun_ici_kaydet(datetime(2026, 10, 17, 12, 35, tzinfo=TR)) == "hafta-sonu" and not cagri, "cumartesi")
kontrol(main.gun_ici_kaydet(cuma("19:55")) == "pencere-disi" and not cagri, "gecikip 19:30'u geçerse atlar")
kontrol(main.gun_ici_kaydet(cuma("10:40")) == "pencere-disi" and not cagri, "sabah Reels'iyle çakışmaz")
kontrol(main.gun_ici_kaydet(cuma("12:35")) == "kaydedildi" and len(cagri) == 1, "ilk kayıt")
kontrol(main.GUN_ICI_DEGISTI.exists(), "önbelleğe yazma işareti")
kontrol(main.gun_ici_kaydet(cuma("13:20")) == "yakin" and len(cagri) == 1, "60 dk içinde ikinci istek yok (kart günü)")
main.SON_KOTA.update({"x-ratelimit-limit": "200", "x-ratelimit-remaining": "35", "_zaman": "2026-10-16T14:35+03:00"})
kontrol(main.gun_ici_kaydet(cuma("14:35")) == "kaydedildi" and len(cagri) == 2, "kota bilgisi bu kayıtla dosyaya girer")
kontrol(main.gun_ici_kaydet(cuma("16:35")) == "kota" and len(cagri) == 2, "kalan hak < 40: istek harcanmaz")
main.SON_KOTA.clear()
d = main.gun_ici_oku()
kontrol([n["saat"] for n in d["gunler"]["2026-10-16"]] == ["12:35", "14:35"] and d["kota"]["x-ratelimit-remaining"] == "35",
        "dosya içeriği")
kontrol(main.gun_ici_kaydet(datetime(2026, 11, 2, 12, 35, tzinfo=TR)) == "kaydedildi", "yeni ayda kota engeli kalkar")

# Denemede ve hafta sonunda fiyat paylaşımı nokta yazmaz; gerçek paylaşımda yazar
main.GUN_ICI_DOSYASI.unlink(missing_ok=True)
main.GECMIS_DOSYASI = gecici / "gecmis.json"
main.metal_fiyatlari = lambda: {"XAG": {"fiyat": 57.78, "yuzde24": 0}, "XAU": {"fiyat": 4300.0, "yuzde24": 0}}
os.environ["DENEME"] = "true"
f = main.fiyatlari_al(kaydet=False, kaynak="post")
kontrol(not main.GUN_ICI_DOSYASI.exists() and f["gun_ici"][-1][1] > 0, "deneme: nokta yazılmaz ama şimdiki değer satırda")
os.environ["DENEME"] = "false"
main.fiyatlari_al(kaydet=False, kaynak="kart")
kontrol(main.GUN_ICI_DOSYASI.exists() == (datetime.now(TR).weekday() < 5), "kart: hafta içi nokta yazar")
main.GUN_ICI_DOSYASI.unlink(missing_ok=True)
main.fiyatlari_al(kaydet=False)
kontrol(not main.GUN_ICI_DOSYASI.exists(), "kaynaksız çağrı (pazar yorumu vb.) nokta yazmaz")

print(f"test_gun_ici: {gecen} sınama geçti")
