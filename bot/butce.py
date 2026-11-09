# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Üretimin süre bütçesi: takılan üretim paylaşımı kaçırmasın (gözden geçirme, 4 Kasım 2026; Rıdvan, 9 Kasım 2026 "Başla").

4 Kasım 2026'da rehber #8 Reels'inin üretimi iş akışının 15 dakikalık adım sınırına takıldı: Python ffmpeg'i
bekliyordu, ffmpeg bitmedi (iş bittiğinde yalnız ffmpeg yetim kalmıştı; tarayıcı yoktu). Aynı Reels 18 dk sonra 54 sn'de
üretildi; yani yavaşlık değil, tek seferlik takılmaydı. O gün paylaşım yalnız elle kurtarıldı. Adım sınırı üretimi
öldürür ama yedek yola (müzikli Reels, kaydırmalı, durağan video) geçme fırsatı bırakmaz.

Bu modül üretime kod içi bir bütçe verir:

- `baslat(tur)` üretimin başında (main.hazirla) bütçeyi açar; `kalan()` kalan saniye.
- Her ffmpeg çağrısı `ffmpeg_calistir` ile süre sınırlı çalışır: sınır aşılırsa süreç öldürülür ve `SureAsimi` verilir;
  çağıran yer zaten her hatada yedek yola geçiyordu, süre aşımı da aynı yola düşer. Yedek yolun kendi ffmpeg'i bütçeden
  bağımsız sabit bir pay alır (YEDEK_FFMPEG_SN): asıl yol bütçeyi yemiş olsa da yedek üretilebilsin.
- Seslendirme (Gemini; bot/ses.py) için `seslendirme_son_ani()`: istekler ve yeniden denemeler bu andan sonra
  yapılmaz, kalan süre video kodlamasına (KODLAMA_PAYI_SN) kalır. Ses yetişmezse Reels yalnız müzikle gider.
- Bütçe adım sınırının (paylas.yml → "Görseli / videoyu üret") altındadır; aradaki fark yedek yola kalır.

Seslendirmeyi, görseli ya da takvimi değiştirmez; yalnız ne kadar beklenecek onu belirler. Olağan üretimler bütçenin çok
altında biter (rehber Reels'i ~1 dk, pazar yorumu ~6 dk, fiyat videoları ~30 sn). Yalnızca standart kütüphane.
Sınama: python bot/test_butce.py
"""
import os
import subprocess
import time

# Adım sınırı (paylas.yml): bilgi/kisa 15 dk, yorum 35 dk, diğerleri 5 dk. Bütçe asıl yolun (sesli Reels, hareketli
# video) bitmesi gereken süre; adım sınırına kalan süre yedek yolun (müzikli Reels ≤ YEDEK_FFMPEG_SN, kaydırmalı ya da
# durağan video) payıdır.
ADIM_SINIRI_SN = {"bilgi": 900, "kisa": 900, "yorum": 2100, "varsayilan": 300}
BUTCE_SN = {"bilgi": 600, "kisa": 600, "yorum": 1800, "varsayilan": 240}
# Seslendirmeden sonra video kodlamasına ayrılan pay: seslendirme en geç bütçenin bitimine bu kadar kala biter.
# Rehber: ≤ 240 sn'lik video tek ffmpeg geçişi (~1–2 dk). Pazar: ses süresi kadar kare tarayıcıda çizilir
# (87 sn'lik Reels ~4 dk; ses en çok 300 sn → ~15 dk).
KODLAMA_PAYI_SN = {"bilgi": 180, "kisa": 180, "yorum": 900, "varsayilan": 60}
YEDEK_FFMPEG_SN = 180      # sn: yedek yolun ffmpeg'i (müzikli rehber Reels'i ≤ 240 sn video) en çok bu kadar
DURAGAN_FFMPEG_SN = 60     # sn: durağan video (tek görsel, ≤ 13 sn; olağan ~5 sn) en çok bu kadar
HIZLANDIRMA_SN = 60        # sn: ses hızlandırma (ffmpeg atempo, ≤ 5 dk ses için birkaç sn)
EN_AZ_SN = 5               # sn: bundan az kalmışsa ffmpeg hiç başlatılmaz, doğrudan SureAsimi


class SureAsimi(RuntimeError):
    """Üretimin bir adımı bütçesini aştı; çağıran yer yedek yola geçer."""


class Butce:
    def __init__(self, toplam_sn, tur="varsayilan"):
        self.tur = tur
        self.toplam = float(toplam_sn)
        self.baslangic = time.monotonic()

    def gecen(self):
        return time.monotonic() - self.baslangic

    def kalan(self):
        return self.toplam - self.gecen()


_BUTCE = None


def baslat(tur):
    """Üretimin başında çağrılır (main.hazirla). Türün bütçesini açar ve günlüğe yazar."""
    global _BUTCE
    toplam = BUTCE_SN.get(tur, BUTCE_SN["varsayilan"])
    if os.environ.get("URETIM_BUTCE_SN"):   # yalnız yerel deneme / sınama: bütçeyi kısaltıp yedek yolu göstermek için
        toplam = float(os.environ["URETIM_BUTCE_SN"])
    _BUTCE = Butce(toplam, tur)
    print(f"Üretim süre bütçesi: {toplam:.0f} sn (adım sınırı "
          f"{ADIM_SINIRI_SN.get(tur, ADIM_SINIRI_SN['varsayilan']) // 60} dk; aşılırsa yedek yol).")
    return _BUTCE


def _butce():
    global _BUTCE
    if _BUTCE is None:        # baslat çağrılmadı (sınama, goril-ciz alt süreci): varsayılan bütçe o anda açılır
        _BUTCE = Butce(BUTCE_SN["varsayilan"])
    return _BUTCE


def tur():
    return _butce().tur


def kalan():
    """Kalan bütçe (sn); eksi olabilir."""
    return _butce().kalan()


def kalan_veya_hata(ne, en_az=EN_AZ_SN):
    """Kalan bütçe; en_az saniyeden azsa SureAsimi (adım hiç başlatılmaz, yedek yola geçilir)."""
    k = kalan()
    if k < en_az:
        raise SureAsimi(f"{ne} için üretim bütçesi bitti ({_butce().gecen():.0f} sn geçti)")
    return k


def seslendirme_son_ani(pay_sn=None):
    """Seslendirmenin (istekler + yeniden denemeler) bitmesi gereken an (time.monotonic). Kodlama payı düşülür; pay
    kalmadıysa geçmiş bir an döner, ses.seslendir ilk istekten önce SesHatasi verir (Reels müzikle gider)."""
    b = _butce()
    pay = KODLAMA_PAYI_SN.get(b.tur, KODLAMA_PAYI_SN["varsayilan"]) if pay_sn is None else pay_sn
    return time.monotonic() + b.kalan() - pay


def ffmpeg_calistir(komut, ne, sinir_sn=None, **kw):
    """ffmpeg'i (ya da herhangi bir komutu) süre sınırıyla çalıştırır; `check=True` varsayılır.

    sinir_sn verilmezse kalan bütçe kullanılır (EN_AZ_SN'den azsa başlatılmaz). Sınır aşılırsa subprocess.run süreci
    öldürür (yetim ffmpeg kalmaz) ve SureAsimi verilir. Diğer hatalar (CalledProcessError) olduğu gibi yükselir."""
    sinir = kalan_veya_hata(ne) if sinir_sn is None else float(sinir_sn)
    kw.setdefault("check", True)
    try:
        return subprocess.run(komut, timeout=sinir, **kw)
    except subprocess.TimeoutExpired:
        raise SureAsimi(f"{ne} {sinir:.0f} sn içinde bitmedi; ffmpeg öldürüldü") from None


def surec_bitir(p):
    """Popen ile açılmış süreci öldürür ve bekler (hata ya da süre aşımında yetim kalmasın)."""
    try:
        if p.poll() is None:
            p.kill()
        p.wait(timeout=10)
    except Exception:
        pass
