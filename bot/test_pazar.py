"""Pazar Reels'i ve cumartesi hatırlatması sınamaları (ağ yok). Çalıştır: python bot/test_pazar.py

- Pazar Reels'inin paylaşımı patlarsa (geçici engel dahil) hata dışarı sızmaz: yayinla() baştan denerse
  kaydırmalı gönderi ikinci kez gitmesin.
- Cumartesi hatırlatması KURAL: her cumartesi (ve yalnızca cumartesi) görselde ve açıklamada çıkar; kayıt okunamasa
  da düşmez; pazar yorumu ve haftalık özet takvimde durmalı.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


# 1) Reels paylaşımı hata verirse (engel, ağ, kapak) yorum_reelsi sessizce uyarır, hikâye denenmez
cagrilar = []
eski = (main._url_hazir_mi, main._istek, main.hikaye_paylas)
try:
    main._url_hazir_mi = lambda *a, **k: None
    for hata in (main.ErisimEngeli("API access blocked"), RuntimeError("konteyner işlenemedi")):
        def patla(*a, _h=hata, **k):
            raise _h
        main._istek = patla
        main.hikaye_paylas = lambda *a, **k: cagrilar.append("hikaye")
        main.yorum_reelsi("1", {"dosya": "r.mp4", "kapak": "k.jpg", "kapak_ms": 11500, "aciklama": "x"}, "https://ornek/")
    kontrol(cagrilar == [], "Reels gitmediyse hikâye de gitmez, hata sızmaz")

    # Başarılı akış: konteyner → publish → hikâye
    istekler = []
    def sahte(yontem, yol, **p):
        istekler.append((yontem, yol, p.get("media_type")))
        return {"id": "42", "status_code": "FINISHED"}
    main._istek = sahte
    main._hazir_olmasini_bekle = lambda *a, **k: None
    main.yorum_reelsi("1", {"dosya": "r.mp4", "kapak": "k.jpg", "kapak_ms": 11500, "aciklama": "x"}, "https://ornek/")
    kontrol(("POST", "1/media", "REELS") in istekler and ("POST", "1/media_publish", None) in istekler,
            "Reels konteyneri ve yayın")
    # Pazar hikâyesi 25 Ekim 2026'dan beri kapalı (main.PAZAR_HIKAYE): Reels gider, hikâye gitmez
    kontrol(cagrilar == ([] if not main.PAZAR_HIKAYE else ["hikaye"]), "pazar hikâyesi yalnız PAZAR_HIKAYE açıksa")
    kontrol(main.PAZAR_HIKAYE is False, "pazar hikâyesi kapalı (Rıdvan, 25 Ekim 2026)")
finally:
    main._url_hazir_mi, main._istek, main.hikaye_paylas = eski

# 2) Cumartesi hatırlatması — KURAL (Rıdvan, 15 Ekim 2026 23:22): "her cumartesi bu yazı çıkmalı"
gun = date(2026, 10, 17)
for i in range(2 * 366):                      # iki yıl boyunca her gün: cumartesi evet, diğer günler hayır
    g = gun + timedelta(days=i)
    kontrol(main.pazar_yorumu_yarin(g) is (g.weekday() == 5), f"{g}: hatırlatma yalnızca ve her cumartesi")

# Kayıt dosyası okunamasa da (ör. önbellek boş) cumartesi hatırlatması düşmez: takvime/kayda bakılmaz
eski_oku = main.gecmis_oku
try:
    def patla():
        raise RuntimeError("kayıt yok")
    main.gecmis_oku = patla
    kontrol(main.pazar_yorumu_yarin(date(2026, 10, 24)) is True, "kayıt okunamasa da cumartesi hatırlatma var")
finally:
    main.gecmis_oku = eski_oku

# Söz boş kalmasın: haftalık özet cumartesi, pazar yorumu pazar zamanlı (biri takvimden çıkarsa kural konuşulur)
akis = (Path(__file__).parent.parent / ".github" / "workflows" / "paylas.yml").read_text(encoding="utf-8")
kontrol("cron: '50 6 * * 6'" in akis, "haftalık özet her cumartesi zamanlı")
kontrol("cron: '50 7 * * 0'" in akis, "pazar yorumu her pazar zamanlı (hatırlatmanın sözü)")

# Haftalık özet her zaman hafta şablonuyla çizilir (özel gün şablonunda şerit yok): gerçek veride özel gün yok
f = main.ornek_haftalik()
f.pop("gecmis_gram", None)                    # haftalik_fiyatlari_al() bu anahtarı hiç vermez
v = main.haftalik_veri_hazirla(f, "@gunlukgumus")
kontrol(not v.get("ozel"), "haftalık özet özel gün şablonuna geçmez")

kontrol("Yarın ~11:00" not in main.aciklama_yaz(v, "hafta"), "hatırlatma yoksa açıklamada da yok")
v["pazar_hatirlatma"] = main.PAZAR_HATIRLATMA
metin = main.aciklama_yaz(v, "hafta")
kontrol("Yarın ~11:00 · Pazar derin analizi: kısa ve orta vade. Kaçırmayın." in metin, "açıklamada hatırlatma")
kontrol(len(metin) <= 2200, "açıklama 2200 sınırında")

# Görselde (Reels ve hikâyesi aynı şablondan) şerit
from jinja2 import Environment, FileSystemLoader  # noqa: E402
html = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True).get_template("hafta.html").render(**v)
kontrol('id="hatirlatma"' in html and "Pazar derin analizi" in html and "Yarın ~11:00" in html, "görselde hatırlatma")

# 3) Pazar yorumu yasal metinleri (25 Ekim 2026 yasal denetimi)
import copy  # noqa: E402
import yorum  # noqa: E402

# SPK III-37.1 EK/3 uyarı notu harfi harfine (RG 11.07.2013/28704); yapay zekâ cümlesi ayrı ve sonra gelir
EK3 = ("Burada yer alan yatırım bilgi, yorum ve tavsiyeleri yatırım danışmanlığı kapsamında değildir. Yatırım "
       "danışmanlığı hizmeti, yetkili kuruluşlar tarafından kişilerin risk ve getiri tercihleri dikkate alınarak "
       "kişiye özel sunulmaktadır. Burada yer alan yorum ve tavsiyeler ise genel niteliktedir. Bu tavsiyeler mali "
       "durumunuz ile risk ve getiri tercihlerinize uygun olmayabilir. Bu nedenle, sadece burada yer alan bilgilere "
       "dayanılarak yatırım kararı verilmesi beklentilerinize uygun sonuçlar doğurmayabilir.")
kontrol(yorum.UYARI_EK3 == EK3, "EK/3 uyarı notu harfi harfine")
kontrol(yorum.UYARI == EK3 and "yapay zekâ" in yorum.YZ_NOTU, "yapay zekâ cümlesi EK/3'ten ayrı")

# Yön değişikliği (md. 78/2-c): yön değiştiyse gerekçe zorunlu; değişmediyse gerekçe görünmez
onceki = {"tarih": date(2026, 10, 18), **yorum.ORNEK_ONCEKI}          # kısa: düşüş → bu hafta yükseliş; orta aynı
yz = copy.deepcopy(yorum.ORNEK_YORUM)
kontrol(yorum.denetle(yz, yorum.ORNEK_GELISMELER, onceki=onceki) == [], "örnek yorum denetimden geçer (önceki yorumla)")
kontrol(yorum.yon_degisti(yz, onceki, "kisa") and not yorum.yon_degisti(yz, onceki, "orta"), "yön değişimi doğru")
bos = copy.deepcopy(yz)
bos["kisa"]["degisim"] = ""
kontrol(any(h.startswith("kisa.degisim: boş") for h in yorum.denetle(bos, yorum.ORNEK_GELISMELER, onceki=onceki)),
        "yön değişti ama gerekçe yok → hata")
rakam = copy.deepcopy(yz)
rakam["kisa"]["degisim"] = "Ons yüzde 3 yükseldi."
kontrol(any("kisa.degisim" in h for h in yorum.denetle(rakam, yorum.ORNEK_GELISMELER, onceki=onceki)),
        "gerekçede rakam/yüzde yasağı geçerli")
fazla = copy.deepcopy(yz)
fazla["orta"]["degisim"] = "Model yön değişmediği hâlde yazdı."
kontrol(yorum.denetle(fazla, yorum.ORNEK_GELISMELER, onceki=onceki) == [], "yön aynıysa gerekçe hata sayılmaz")
kontrol(yorum.degisim_temizle(fazla, onceki)["orta"]["degisim"] == "", "yön aynıysa gerekçe boşaltılır")
kontrol(yorum.denetle(yz, yorum.ORNEK_GELISMELER) == [], "önceki yorum yoksa (ilk hafta) gerekçe aranmaz")
kontrol("onceki_yorum" in yorum.model_girdisi(*yorum.ornek_veri(date(2026, 10, 25)), {}, date(2026, 10, 25), "x",
                                                onceki=onceki) and
        "onceki_yorum" not in yorum.model_girdisi(*yorum.ornek_veri(date(2026, 10, 25)), {}, date(2026, 10, 25), "x"),
        "modele önceki yorum yalnızca varsa gider")

# Önceki yorum Instagram açıklamasından okunur: bugünkü sayılmaz, en yenisi alınır
def sahte_medya(yontem, yol, **p):
    satir = "Kısa vade (1–4 hafta): {} ağır basıyor ({} eğilim) · x\nOrta vade (1–6 ay): {} ağır basıyor ({} eğilim) · y"
    return {"data": [
        {"caption": "Haftalık gümüş görünümü | Üst düzey yapay zekâ yorumu · 25 Ekim 2026\n\n"
                    + satir.format("▲ Yükseliş", "belirgin", "▲ Yükseliş", "orta"), "timestamp": "2026-10-25T08:10:00+0000"},
        {"caption": "Gram gümüş fiyatı bugün: 86,33 ₺", "timestamp": "2026-10-23T17:20:00+0000"},
        {"caption": "Haftalık gümüş görünümü | Üst düzey yapay zekâ yorumu · 18 Ekim 2026\n\n"
                    + satir.format("▼ Düşüş", "hafif", "▲ Yükseliş", "orta"), "timestamp": "2026-10-18T08:12:00+0000"},
        {"caption": "Haftalık gümüş görünümü | Yapay zekâ yorumu · 11 Ekim 2026\n\n"
                    + satir.format("▲ Yükseliş", "orta", "▼ Düşüş", "orta"), "timestamp": "2026-10-11T08:12:00+0000"},
    ]}
import os  # noqa: E402
eski_istek, eski_token = main._istek, os.environ.get("IG_TOKEN")
try:
    main._istek, os.environ["IG_TOKEN"] = sahte_medya, "x"
    o = main.onceki_yorum(date(2026, 10, 25))
    kontrol(o == {"tarih": date(2026, 10, 18), "kisa": {"yon": "düşüş", "guc": "zayıf"},
                  "orta": {"yon": "yükseliş", "guc": "orta"}}, f"önceki yorum 18 Ekim'den okunur: {o}")
    # Yeni güç etiketi (28 Ekim 2026: "zayıf / orta güçte / güçlü işaret") de okunur; açıklama yon_metni ile yazılır
    yeni = (f"Kısa vade (1–4 hafta): {yorum.yon_metni({'yon': 'düşüş', 'guc': 'belirgin'})} · x\n"
            f"Orta vade (1–6 ay): {yorum.yon_metni({'yon': 'yükseliş', 'guc': 'zayıf'})} · y")
    main._istek = lambda *a, **k: {"data": [{"caption": "Haftalık gümüş görünümü | Üst düzey yapay zekâ yorumu · "
                                                         "1 Kasım 2026\n\n" + yeni, "timestamp": "2026-11-01T08:10:00+0000"}]}
    o = main.onceki_yorum(date(2026, 11, 8))
    kontrol(o and o["kisa"] == {"yon": "düşüş", "guc": "belirgin"} and o["orta"] == {"yon": "yükseliş", "guc": "zayıf"},
            f"yeni etiketli açıklama da okunur: {o}")
    def patla(*a, **k):
        raise RuntimeError("ağ yok")
    main._istek = patla
    kontrol(main.onceki_yorum(date(2026, 10, 25)) is None, "okunamazsa None (yorum yine yazılır)")
finally:
    main._istek = eski_istek
    if eski_token is None:
        os.environ.pop("IG_TOKEN", None)
    else:
        os.environ["IG_TOKEN"] = eski_token

# Açıklama ve sesli okuma: değişiklik, önceki yorumun tarihi ve gerekçe; 2200 sınırı
vadeler = [{**v, "etiket": v["etiket"], "not": "", "yorum": yz[v["anahtar"]],
            "onceki": ({**onceki["kisa"], "tarih_metni": "18 Ekim"} if v["anahtar"] == "kisa" else None),
            "hucreler": [{"ad": "Gram gümüş", "deg": None}]} for v in yorum.VADELER]
v = {"tarih": "25 Ekim 2026", "gram": "86,33", "gram_deg": {"isaret": "▲", "metin": "%1,2", "yon": "artis"},
     "veri_ani": "25 Ekim Pazar kapanışı", "vadeler": vadeler}
uzun = {**yorum.ORNEK_GELISMELER, "kaynaklar": [{"alan": f"kaynak{i}.com.tr"} for i in range(12)]}
metin = yorum.aciklama(v, yz, "Gram fiyatı … hesaplanmıştır.\nMetal fiyatları: MetalCharts (metalcharts.org)", uzun)
kontrol("Değişiklik · kısa vade: 18 Ekim yorumunda düşüş ağır basıyordu, bu hafta yükseliş. Nedeni: Ons cuma" in metin,
        "açıklamada değişiklik satırı")
kontrol("Değişiklik · orta vade" not in metin, "yön aynıysa açıklamada satır yok")
kontrol("Uyarı: " + EK3 + "\n\n" + yorum.YZ_NOTU + "\n\n" in metin, "açıklamada EK/3 harfi harfine, YZ notu ayrı paragraf")
kontrol(len(metin) <= 2200, f"açıklama 2200 sınırında ({len(metin)})")
okuma = [m for sahne in yorum.seslendirme_parcalari(v) for _, m in sahne]
kontrol(any(m.startswith("Yön değişti. 18 Ekim yorumunda düşüş ağır basıyordu. Nedeni:") for m in okuma),
        "sesli okumada değişiklik")

# Görselde (kaydırmalı ve Reels) yalnız yön değişen vadede not
env = Environment(loader=FileSystemLoader(str(main.SABLONLAR)), autoescape=True)
ortak = {**v, "gun": "Pazar", "hesap": "@gunlukgumus", "veri_tarihi": "25.10.2026", "toplam": 3}
kontrol("Yön değişti." in env.get_template("yorum.html").render(**ortak, sayfa=1)
        and "Yön değişti." not in env.get_template("yorum.html").render(**ortak, sayfa=2), "kaydırmalıda not")
kontrol(env.get_template("yorum-reels.html").render(**ortak, sahne_sureleri=[8, 8, 8]).count("Yön değişti.") == 1,
        "Reels'te not")

# 4) Instagram açıklama sınırı (25 Ekim 2026: Reels açıklaması 2213 karakterle reddedildi)
uzun = "Başlık\n\n" + "x" * 2000 + "\n\nHaber kaynakları (web araması): " + ", ".join(f"kaynak{i}.com.tr" for i in range(12)) + "\n\n#gümüş"
k = main.aciklama_sigdir(uzun)
kontrol(main.ig_uzunluk(k) <= main.IG_HEDEF and "kaynak daha" in k and k.endswith("#gümüş"), "haber kaynakları kısaltılarak sığar")
kontrol(main.aciklama_sigdir("kısa") == "kısa", "kısa açıklamaya dokunulmaz")
kontrol(main.ig_uzunluk("🎙") == 2, "emoji Instagram'da 2 sayılır")
s2 = main._yorum_sesli_metin(uzun.replace("Başlık", "Uyarı: başlık"))
kontrol("🎙" in s2 and main.ig_uzunluk(s2) <= main.IG_SINIR, "seslendirme notu sığdırılarak eklenir")

print(f"test_pazar: {gecen} sınama geçti")
