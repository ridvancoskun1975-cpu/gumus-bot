# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Özet sayfası sınaması (#50; bot/ozet_sayfa.py, templates/ozet.html). Ağa çıkmaz: özel depo sahte.
Çalıştırma: python bot/test_ozet_sayfa.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main  # noqa: E402
import ozet_sayfa  # noqa: E402
import sayfa  # noqa: E402

sayac = 0


def kontrol(kosul, ad):
    global sayac
    sayac += 1
    assert kosul, ad


gecici = Path(tempfile.mkdtemp())
ozet_sayfa.YEREL = gecici / "veri-ozet"

# 1) Kayıt: rakamlar görseldekiyle aynı işlevlerden (haftalık özet meta.json'u gibi)
f = main.ornek_haftalik()
f.pop("gecmis_gram", None)
meta = {"tur": "hafta", "dosya": "hafta-20261121-0955.mp4", "baslik": {"tur": "buyuk-hareket", "metin": "Gümüş bu hafta %15,4 düştü"},
        "fiyatlar": f}
v = main.haftalik_veri_hazirla(dict(f), "@gunlukgumus")
k = ozet_sayfa.kayit_kur(meta)
kontrol(k["paylasim"] == "2026-11-21", "paylaşım tarihi dosya adından")
kontrol(k["gram"] == v["gram"] and k["en_yuksek"] == v["en_yuksek"] and k["dolar"] == v["dolar"] and k["parite"] == v["parite"],
        "rakamlar görseldekiyle aynı")
kontrol(k["donem"] == v["aralik"] and k["baslik"] == "Gümüş bu hafta %15,4 düştü", "dönem ve başlık")
try:
    ozet_sayfa.kayit_kur({**meta, "tur": "post"})
    kontrol(False, "özet olmayan tür reddedilir")
except ValueError:
    kontrol(True, "özet olmayan tür reddedilir")

a = main.ornek_aylik()
ka = ozet_sayfa.kayit_kur({"tur": "ay", "dosya": "ay-20261201-1955.mp4", "fiyatlar": a})
va = main.aylik_veri_hazirla(dict(a), "@gunlukgumus")
kontrol(ka["donem"] == va["ay_adi"] and ka["en_yuksek_gun"] == va["en_yuksek_gun"], "aylık kayıt")

# 2) kaydet: deneme yalnız yerel; gerçek çalıştırmada önce görsel, sonra json özel depoya
cikti = gecici / "site"
cikti.mkdir()
(cikti / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
(cikti / "hafta-20261121-0955.png").write_bytes(b"\x89PNG sahte")
yazilan = []
ozet_sayfa._uzaga_koy = lambda yol, icerik, mesaj: yazilan.append((yol, icerik))
ozet_sayfa.kaydet(cikti, deneme=True)
kontrol(not yazilan and (ozet_sayfa.YEREL / "hafta.json").exists() and (ozet_sayfa.YEREL / "hafta.png").exists(),
        "deneme yalnız yerel")
ozet_sayfa.kaydet(cikti)
kontrol([y for y, _ in yazilan] == ["ozet/hafta.png", "ozet/hafta.json"], f"önce görsel sonra kayıt: {yazilan}")
(cikti / "meta.json").write_text(json.dumps({"tur": "post"}), encoding="utf-8")
yazilan.clear()
ozet_sayfa.kaydet(cikti)
kontrol(not yazilan, "akşam özetinde kayıt yok")

# 3) indir: uzaktaki daha yeni kayıt iner; yerelde daha yeni (aynı işte üretilmiş) kayıt korunur
uzak = {"ozet/hafta.json": json.dumps({**k, "paylasim": "2026-11-14"}).encode(), "ozet/hafta.png": b"eski",
        "ozet/ay.json": json.dumps({**ka, "gorsel": None}).encode(), "ozet/ay.png": b"ay"}
ozet_sayfa._uzaktan_al = lambda yol: uzak.get(yol)
ozet_sayfa.indir()
o = ozet_sayfa.oku()
kontrol(o["hafta"]["paylasim"] == "2026-11-21", "yerelde daha yeni haftalık korunur")
kontrol(o["ay"]["paylasim"] == "2026-12-01" and o["ay"]["gorsel"], "aylık indi")

# 4) Sayfa: menüde "Özetler" yalnız kayıt varken; kartlar, ekler, tarihli görsel adı
g = sayfa.ornek_gecmis()
s1 = gecici / "s1"
s1.mkdir()
sayfa.uret(s1, g, euro={x["kur_tarihi"]: x["dolar"] * 1.16 for x in g.values()}, ozet_kayitlar=ozet_sayfa.oku())
import html as html_mod  # noqa: E402
html = html_mod.unescape((s1 / "ozet" / "index.html").read_text(encoding="utf-8"))
ana = (s1 / "index.html").read_text(encoding="utf-8")
kontrol('href="ozet/">Özetler</a>' in ana and "Haftalık ve aylık özet</a>" in ana, "menüde ve altta Özetler")
kontrol("Bu hafta" in html and "Bu ay" in html and k["gram"] + " ₺" in html, "iki kart ve rakam")
kontrol("Instagram'da 21 Kasım'da paylaşılan görsel" in html and "1 Aralık'ta paylaşılan" in html, "bulunma eki")
kontrol((s1 / "ozet" / "hafta-2026-11-21.png").exists() and 'src="hafta-2026-11-21.png"' in html, "tarihli görsel")
kontrol("metalcharts.org" in html and "yatırım tavsiyesi değildir" in html, "kaynak ve uyarı")
kontrol("ozet/</loc>" in (s1 / "sitemap.xml").read_text(encoding="utf-8"), "site haritasında")
kontrol("Claude" not in html and "Anthropic" not in html, "model/şirket adı yok")

(ozet_sayfa.YEREL / "ay.json").unlink()
s2 = gecici / "s2"
s2.mkdir()
sayfa.uret(s2, g, euro={x["kur_tarihi"]: x["dolar"] * 1.16 for x in g.values()}, ozet_kayitlar=ozet_sayfa.oku())
kontrol("Aylık özet her ayın ilk iş günü burada." in (s2 / "ozet" / "index.html").read_text(encoding="utf-8"),
        "aylık yoksa bekleme notu")

s3 = gecici / "s3"
s3.mkdir()
sayfa.uret(s3, g, euro={x["kur_tarihi"]: x["dolar"] * 1.16 for x in g.values()}, ozet_kayitlar={})
kontrol("Özetler</a>" not in (s3 / "index.html").read_text(encoding="utf-8") and not (s3 / "ozet").exists(),
        "kayıt yoksa sekme ve sayfa yok")

kontrol(ozet_sayfa._uzun_tarih("2026-01-05") == "5 Ocak'ta" and ozet_sayfa._uzun_tarih("2026-09-01") == "1 Eylül'de",
        "ekler")
print(f"test_ozet_sayfa: {sayac} sınama geçti")
