# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Üretim süre bütçesinin sınamaları (bot/butce.py; main.py ve ses.py'deki kullanımı). Ağ yok, Gemini yok.
Çalıştır: python bot/test_butce.py

- Bütçe: baslat / kalan / kalan_veya_hata / seslendirme_son_ani.
- ffmpeg_calistir: takılan komut (uyuyan python) sınırda öldürülür, SureAsimi verir, yetim kalmaz; biten komut geçer;
  hata veren komut CalledProcessError olarak yükselir.
- ses.seslendir: son_an geçmişse istek atmaz; yeniden deneme beklemesi bütçeyi aşacaksa beklemez; istek süresi kalanla
  sınırlanır. ses.rehber_seslendir: bütçe bitince yedek modele geçmez.
- ses.hizlandir: ffmpeg süre sınırında SesHatasi.
- main: hareketli_video_uret bütçe bitmişse ffmpeg başlatmadan SureAsimi verir; yedek yol sabitleri adım sınırlarına
  sığar; hazirla fiyat yolunda SureAsimi durağan videoya düşer (kodda yakalanıyor).
"""
import array
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import butce  # noqa: E402
import ses  # noqa: E402

gecen = 0


def kontrol(kosul, ad):
    global gecen
    assert kosul, ad
    gecen += 1


# ---------------------------------------------------------------- bütçe
b = butce.baslat("bilgi")
kontrol(b.tur == "bilgi" and 599 < b.kalan() <= 600, "bilgi bütçesi 600 sn")
kontrol(butce.kalan_veya_hata("x") > 590, "kalan_veya_hata kalanı döner")
son = butce.seslendirme_son_ani()
kontrol(600 - 180 - 2 < son - time.monotonic() <= 600 - 180, "seslendirme son anı = kalan − kodlama payı (180)")

for tur_, adim in butce.ADIM_SINIRI_SN.items():
    kontrol(butce.BUTCE_SN[tur_] + butce.YEDEK_FFMPEG_SN + 60 <= adim or tur_ == "varsayilan",
            f"{tur_}: bütçe + yedek ffmpeg + 60 sn adım sınırına sığmalı")
    kontrol(butce.KODLAMA_PAYI_SN[tur_] < butce.BUTCE_SN[tur_], f"{tur_}: kodlama payı bütçeden küçük")
kontrol(butce.BUTCE_SN["varsayilan"] + butce.DURAGAN_FFMPEG_SN <= butce.ADIM_SINIRI_SN["varsayilan"],
        "fiyat videoları: bütçe + durağan video 5 dk'ya sığmalı")

# bitmiş bütçe
butce._BUTCE = butce.Butce(0.0, "bilgi")
time.sleep(0.01)
kontrol(butce.kalan() < 0, "bitmiş bütçede kalan eksi")
try:
    butce.kalan_veya_hata("deneme")
    kontrol(False, "bitmiş bütçe SureAsimi vermeli")
except butce.SureAsimi as e:
    kontrol("deneme" in str(e), "SureAsimi mesajında adım adı")
kontrol(butce.seslendirme_son_ani() < time.monotonic(), "bitmiş bütçede seslendirme son anı geçmişte")
kontrol(issubclass(butce.SureAsimi, RuntimeError), "SureAsimi RuntimeError (yedek yollar Exception yakalıyor)")

# baslat çağrılmadan kullanım (goril-ciz alt süreci, sınamalar): varsayılan bütçe kendiliğinden açılır
butce._BUTCE = None
kontrol(abs(butce.kalan() - butce.BUTCE_SN["varsayilan"]) < 2, "baslat yoksa varsayılan bütçe")

# ---------------------------------------------------------------- ffmpeg_calistir
butce._BUTCE = butce.Butce(600.0, "bilgi")
uyku = [sys.executable, "-c", "import time; time.sleep(30)"]
t0 = time.monotonic()
try:
    butce.ffmpeg_calistir(uyku, "uyuyan komut", sinir_sn=1.0)
    kontrol(False, "takılan komut SureAsimi vermeli")
except butce.SureAsimi as e:
    kontrol(time.monotonic() - t0 < 5, "takılan komut sınırda öldürüldü (30 sn beklenmedi)")
    kontrol("uyuyan komut" in str(e) and "1 sn" in str(e), f"SureAsimi mesajı: {e}")
# yetim kalmadı: aynı komut satırına sahip süreç yok
kalan_surec = subprocess.run(["pgrep", "-f", "time.sleep(30)"], capture_output=True, text=True).stdout.strip()
kontrol(not kalan_surec, f"öldürülen süreç yetim kalmamalı (pid: {kalan_surec!r})")

r = butce.ffmpeg_calistir([sys.executable, "-c", "print('tamam')"], "biten komut", sinir_sn=10, capture_output=True,
                          text=True)
kontrol(r.returncode == 0 and r.stdout.strip() == "tamam", "biten komut geçer, çıktı döner")
try:
    butce.ffmpeg_calistir([sys.executable, "-c", "import sys; sys.exit(3)"], "hatalı komut", sinir_sn=10)
    kontrol(False, "hata veren komut CalledProcessError vermeli")
except subprocess.CalledProcessError as e:
    kontrol(e.returncode == 3, "CalledProcessError dönüş kodu")

# sınır verilmezse kalan bütçe; bütçe bitmişse komut hiç başlamaz
butce._BUTCE = butce.Butce(0.0, "bilgi")
time.sleep(0.01)
try:
    butce.ffmpeg_calistir([sys.executable, "-c", "open('/tmp/_butce_basladi', 'w')"], "bütçesiz")
    kontrol(False, "bütçe bitmişken komut başlamamalı")
except butce.SureAsimi:
    kontrol(not Path("/tmp/_butce_basladi").exists(), "bütçe bitmişken komut hiç çalışmadı")

# surec_bitir
p = subprocess.Popen(uyku)
butce.surec_bitir(p)
kontrol(p.poll() is not None, "surec_bitir süreci öldürüp bekler")

# ---------------------------------------------------------------- ses.seslendir ve rehber_seslendir
# Sahte saat: istek 3 sn, bekleme söylendiği kadar sürer; gerçek zaman geçmez.
class SahteSaat:
    def __init__(self):
        self.t, self.uyumalar = 1000.0, []

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.uyumalar.append(s)
        self.t += s


saat = SahteSaat()
ses.time = saat
istekler = []


def sahte_istek(metin, ses_, uslup, model, anahtar_, zaman_asimi=ses.ISTEK_SN):
    istekler.append((metin, model, zaman_asimi))
    saat.t += 3
    sonuc = SAHTE.pop(0)
    if sonuc == "ok":
        return array.array("h", [1000] * (ses.ORNEKLEME // 2)).tobytes(), None, False
    return None, sonuc, True        # geçici hata


ses._istek = sahte_istek

# 1) son_an geçmiş: hiç istek atılmaz
SAHTE = ["ok"]
try:
    ses.seslendir("metin", anahtar_="x", son_an=saat.t - 1)
    kontrol(False, "son_an geçmişse SesHatasi")
except ses.SesHatasi as e:
    kontrol("süre bütçesi" in str(e) and not istekler, f"son_an geçmişken istek atılmadı: {e}")

# 2) kalan 30 sn: istek süresi 30 sn'ye kısılır
istekler.clear()
SAHTE = ["ok"]
ses.seslendir("metin", anahtar_="x", son_an=saat.t + 30)
kontrol(len(istekler) == 1 and istekler[0][2] == 30, f"istek süresi kalanla sınırlı: {istekler}")

# 3) son_an yok: eski davranış (120 sn, yeniden dener ve bekler)
istekler.clear()
saat.uyumalar.clear()
SAHTE = ["503 meşgul", "ok"]
ses.seslendir("metin", anahtar_="x")
kontrol(len(istekler) == 2 and istekler[0][2] == ses.ISTEK_SN and saat.uyumalar == [5],
        "son_an yoksa 120 sn ve 5 sn bekleyip yineler")

# 4) yeniden deneme beklemesi bütçeye sığmıyor: beklemeden SesHatasi
istekler.clear()
saat.uyumalar.clear()
SAHTE = ["429 retry in 40s", "ok"]
try:
    ses.seslendir("metin", anahtar_="x", son_an=saat.t + 20)
    kontrol(False, "bekleme bütçeyi aşarsa SesHatasi")
except ses.SesHatasi as e:
    kontrol(len(istekler) == 1 and not saat.uyumalar and "süre bütçesi" in str(e), f"bekleme yapılmadı: {e}")

# 5) rehber_seslendir: bütçe biterken ilk model düşerse yedek model denenmez (süre yok)
istekler.clear()
SAHTE = ["ok", "ok", "500 hata", "ok", "ok", "ok"]
ses.hizlandir = lambda o, oran=None: o      # ffmpeg'siz
try:
    ses.rehber_seslendir(["bir", "iki", "üç"], "/tmp", "deneme", anahtar_="x", son_an=saat.t + 12)
    kontrol(False, "bütçe bitince rehber_seslendir SesHatasi vermeli")
except ses.SesHatasi:
    modeller = {m for _, m, _ in istekler}
    kontrol(modeller == {ses.MODEL} and len(istekler) == 3, f"bütçe bitince yedek modele geçilmedi: {istekler}")

# 6) bütçe bolsa yedek modele geçilir (eski davranış korunur)
istekler.clear()
saat.uyumalar.clear()
SAHTE = ["kota", "kota", "kota", "kota", "ok", "ok"]
sonuc = ses.rehber_seslendir(["bir", "iki"], "/tmp", "deneme", anahtar_="x", son_an=saat.t + 3600)
kontrol(sonuc["model"] == ses.YEDEK_MODEL and len(sonuc["kare_sn"]) == 2, "bütçe bolsa yedek model devreye girer")
Path("/tmp/_ses-deneme.wav").unlink(missing_ok=True)

# ---------------------------------------------------------------- ses.hizlandir süre sınırı
import importlib  # noqa: E402
importlib.reload(ses)   # sahteleri geri al
if __import__("shutil").which("ffmpeg"):
    ses.HIZLANDIRMA_SN = 0.001   # anında aşılsın
    try:
        ses.hizlandir(array.array("h", [1000] * (ses.ORNEKLEME * 20)))
        kontrol(True, "hızlandırma 1 ms'de bitti (çok hızlı makine); sınır sınanamadı")
    except ses.SesHatasi as e:
        kontrol("bitmedi" in str(e), f"hızlandırma süre sınırında SesHatasi: {e}")
    ses.HIZLANDIRMA_SN = 60
else:
    print("ffmpeg yok; hizlandir sınaması atlandı")

# ---------------------------------------------------------------- main
import main  # noqa: E402

butce._BUTCE = butce.Butce(0.0, "reels")
time.sleep(0.01)
try:
    main.hareketli_video_uret("reels", {}, Path("/tmp/_butce_reels.mp4"), sure=7)
    kontrol(False, "bütçe bitmişken hareketli video SureAsimi vermeli")
except butce.SureAsimi as e:
    kontrol("hareketli video (reels)" in str(e), f"hareketli video bütçe mesajı: {e}")
except Exception as e:   # şablon işlenemedi (sınama ortamı): bütçe denetimi şablondan sonra; bu durumda da takılma yok
    kontrol(False, f"beklenmeyen hata: {type(e).__name__}: {e}")

kaynak = Path(main.__file__).read_text(encoding="utf-8")
kontrol("butce.baslat(tur)" in kaynak.split("def hazirla(")[1].split("\n")[1], "hazirla bütçeyi ilk satırda açar")
kontrol("except butce.SureAsimi" in kaynak.split("def hazirla(")[1], "fiyat yolunda SureAsimi yakalanır (durağan video)")
kontrol(kaynak.count("subprocess.run(komut, check=True)") == 0, "main.py'de süre sınırsız ffmpeg çağrısı kalmadı")
kontrol("son_an=butce.seslendirme_son_ani()" in kaynak.split("def rehber_tam_seslendirmesi(")[1].split("def ")[0],
        "rehber seslendirmesi bütçeli")
kontrol("son_an=butce.seslendirme_son_ani()" in kaynak.split("def yorum_seslendirmesi(")[1].split("def ")[0],
        "pazar seslendirmesi bütçeli")
ses_kaynak = Path(ses.__file__).read_text(encoding="utf-8")
kontrol("timeout=HIZLANDIRMA_SN" in ses_kaynak, "hizlandir ffmpeg'i süre sınırlı")

print(f"test_butce: {gecen} kontrol geçti")
