"""Rehber kısa Reels'inin kadın sesiyle seslendirmesi (Rıdvan, 16 Ekim 2026: "rehber reelsler sesli olmalı. bayan sesi").

Ses Google'ın Gemini metinden konuşma servisinden gelir (ücretsiz kota; Google üretilen sesin sahipliğini
iddia etmez, ticari kullanım serbest). Resmî olmayan yollar (Edge sesi, Google Çeviri sesi) kullanılmaz.

Anahtar: ortam değişkeni GEMINI_API_KEY (iş akışı aynı adlı GitHub sırrından verir); yoksa özel gumus-kayit deposundaki ANAHTAR_DOSYASI
(iş akışı KAYIT_PAT ile okur; anahtar bu herkese açık depoya ve günlüklere hiç yazılmaz).

Her parça (soru, cevap, cümle, çağrı) ayrı istenir; böylece her sesin süresi bilinir ve görseldeki
öğe tam o anda gelir. Herhangi bir hata SesHatasi verir; bot o zaman Reels'i bugünkü gibi yalnızca
müzikle üretir (yedek yol kaldırılmaz).

Yerelde örnek:  GEMINI_API_KEY=... python bot/ses.py dene --konu 3 --ses Kore --cikti <klasör>
                (denemeler yedek modelle; ana modelle tam önizleme için --ana-model, kotayı yer)
Sesleri listele: GEMINI_API_KEY=... python bot/ses.py sesler
"""
import argparse
import array
import base64
import io
import json
import math
import os
import sys
import time
import wave
from pathlib import Path

import requests

SES_ACIK = True                       # False: kısa Reels yalnızca müzikle (bugünkü gibi)
MODEL = "gemini-3.8-flash-tts"
YEDEK_MODEL = "gemini-3.8-flash-lite-tts"   # ana model kota/servis hatası verirse
SES = "Sulafat"                       # Rıdvan seçti (16 Ekim 2026, 3 önizlemeden "Ses 2"; sıcak ton)
USLUP = ("Warm, trustworthy female narrator. Natural Istanbul Turkish, calm medium pace, "
         "clear articulation, like a friendly finance explainer on Instagram. No exaggeration.")
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
SESLER_URL = "https://generativelanguage.googleapis.com/v1beta/voices"
KAYIT_DEPO = "ridvancoskun1975-cpu/gumus-kayit"
ANAHTAR_DOSYASI = "anahtarlar/gemini.txt"
ORNEKLEME = 24000                     # Gemini tek parça yanıtı: 24 kHz, mono, 16 bit WAV
ACIKLAMA_SATIRI = "🎙 Seslendirme yapay zekâ ile üretilmiştir."

CAGRI = "Rehberin tamamı profilde. Kaydedin, lazım olunca bakarsınız."

# Kısa Reels'te okunacak metin: (soru, kısa cevap, cümle). Ekrandaki yazıyla aynı bilgiyi verir; rakamlar
# yanlış okunmasın diye yazıyla yazılır. Yeni bölüm eklenince buraya da satır eklenir; eklenmezse
# okuma_metni() bölümden kendisi üretir (sınama uyarır: python bot/test_ses.py).
OKUMA = {
    1: ("Ons nedir?",
        "Kısa cevap: bir troy ons, otuz bir virgül bin otuz beş gram.",
        "Altın, gümüş ve platin gibi değerli metaller, dünyada troy ons ile fiyatlanır."),
    2: ("Gram gümüş nasıl hesaplanır?",
        "Kısa cevap: otuz bir virgül bin otuz beşe bölün. Bu sayı, bir onstaki gram.",
        "Formül şu: ons gümüş, çarpı dolar kuru, bölü otuz bir virgül bin otuz beş."),
    3: ("Külçede dokuz yüz doksan dokuz ne demek?",
        "Kısa cevap: binde dokuz yüz doksan dokuz saf gümüş.",
        "Gümüşün saflığı binde, yani milyem olarak yazılır."),
    4: ("Altın gümüş paritesi ne anlatır?",
        "Kısa cevap: bir ons altının kaç ons gümüş ettiğini.",
        "Formül basit: ons altın, bölü ons gümüş."),
    5: ("Gümüş fiyatını ne hareket ettirir?",
        "Kısa cevap: gümüş talebinin yüzde ellisinden fazlası sanayiden gelir.",
        "Örneğin elektronik, güneş paneli ve otomotiv."),
    6: ("Kuyumcudaki fiyat neden farklı?",
        "Kısa cevap: farkı dört kalem açar. Makas, işçilik, vergi ve kur.",
        "Gösterge fiyat tek bir orta değerdir; alış ya da satış fiyatı değildir."),
    7: ("Gümüş nerede kullanılır?",
        "Kısa cevap: elektriği ve ısıyı en iyi ileten metal, gümüştür.",
        "Anahtar, devre kartı ve bağlantı noktalarında kullanılır."),
    8: ("Gümüş nereden gelir?",
        "Kısa cevap: dünyanın en büyük gümüş üreticisi Meksika.",
        "Gümüşün büyük kısmı kurşun çinko, bakır ve altın madenlerinden yan ürün olarak çıkar."),
    9: ("Gümüş fiyatı nerede belirlenir?",
        "Kısa cevap: tek bir borsa yok. Gümüş, hafta içi neredeyse yirmi dört saat alınıp satılır.",
        "Ekranlarda görülen ons fiyatı, bu işlemlerden oluşan anlık fiyattır."),
    10: ("Gümüş neden kararır?",
         "Kısa cevap: kükürt. Kararmanın asıl sebebi bu.",
         "Gümüş havadaki kükürtlü gazlarla tepkimeye girer; yüzeyde ince bir gümüş sülfür tabakası oluşur."),
    11: ("Külçe gümüş hangi boylarda olur?",
         "Kısa cevap: uluslararası piyasanın standart külçesi yaklaşık otuz bir kilo, yani bin ons kadar.",
         "Bireysel alımlarda genelde bir ons ile bir kilo arası boylar görülür."),
    12: ("Parite seksen iken, aynı değerdeki gümüş ne kadar yer kaplar?",
         "Kısa cevap: altının yüz kırk yedi katı hacim.",
         "Aynı değer için gümüş, altından parite kadar kat ağırdır."),
    13: ("Akçeden kuruşa, gümüş para.",
         "Kısa cevap: akçe, Osmanlı'nın gümüş sikkesiydi.",
         "İlk akçeler Orhan Gazi döneminde basıldı."),
    14: ("Gerçek gümüş nasıl anlaşılır?",
         "Kısa cevap: damga ilk ipucudur, ama kesin kanıt değildir.",
         "Gerçek gümüş ürünlerde genelde dokuz yüz yirmi beş ya da dokuz yüz doksan dokuz gibi bir saflık damgası bulunur."),
}


class SesHatasi(Exception):
    pass


# ---------------------------------------------------------------- metin

def _sozlu(metin):
    """Elle yazılmamış bölüm için kaba sözlü biçim: simgeleri kelimeye çevirir (rakamlar Gemini'ye kalır)."""
    import re
    m = metin.strip()
    m = re.sub(r"%\s*(\d[\d.,]*)\+", r"yüzde \1'den fazla", m)
    m = re.sub(r"%\s*(\d[\d.,]*)", r"yüzde \1", m)
    m = re.sub(r"(\d[\d.,]*)×", r"\1 kat", m)
    m = re.sub(r"(\d)\s*kg\b", r"\1 kilogram", m)
    m = re.sub(r"(\d)\s*g\b", r"\1 gram", m)
    for a, b in (("~", "yaklaşık "), ("÷", " bölü "), ("×", " çarpı "), ("=", " eşittir "), ("→", ", "),
                 ("₺", " lira"), ("/", " "), ("·", ","), ("#", "")):
        m = m.replace(a, b)
    return re.sub(r"\s+", " ", m).strip()


def okuma_metni(konu, bolum):
    """Kısa Reels'in dört okuma parçası: soru, cevap, cümle, çağrı."""
    if konu in OKUMA:
        soru, cevap, cumle = OKUMA[konu]
    else:
        ilk = bolum["sayfalar"][0]
        soru = _sozlu(bolum["baslik"])
        cevap = f"Kısa cevap: {_sozlu(bolum['buyuk'])}, {_sozlu(bolum['buyuk_alt'])}."
        cumle = _sozlu((ilk.get("maddeler") or [bolum["alt"]])[0])
    return {"soru": soru, "cevap": cevap, "cumle": cumle, "cagri": CAGRI}


# ---------------------------------------------------------------- anahtar

def anahtar():
    a = os.environ.get("GEMINI_API_KEY", "").strip()
    if a:
        return a
    pat = os.environ.get("KAYIT_PAT", "").strip()
    if not pat:
        raise SesHatasi("GEMINI_API_KEY ya da KAYIT_PAT tanımlı değil")
    try:
        r = requests.get(f"https://api.github.com/repos/{KAYIT_DEPO}/contents/{ANAHTAR_DOSYASI}",
                         headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github.raw"},
                         timeout=30)
    except requests.RequestException as e:
        raise SesHatasi(f"anahtar dosyasına ulaşılamadı ({type(e).__name__})")
    if r.status_code == 404:
        raise SesHatasi(f"{KAYIT_DEPO} içinde {ANAHTAR_DOSYASI} yok")
    if r.status_code != 200:
        raise SesHatasi(f"anahtar dosyası okunamadı ({r.status_code})")
    a = r.text.strip()
    if not a:
        raise SesHatasi("anahtar dosyası boş")
    return a


# ---------------------------------------------------------------- Gemini

def _istek(metin, ses, uslup, model, anahtar_):
    govde = {
        "model": model,
        "input": [{"type": "user_input",
                   "content": [{"type": "text", "text": metin,
                                "annotations": [{"type": "speech_metadata", "style": uslup}]}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": ses}]},
    }
    try:
        r = requests.post(URL, json=govde, timeout=120,
                          headers={"x-goog-api-key": anahtar_, "Content-Type": "application/json"})
    except requests.RequestException as e:
        return None, f"bağlantı hatası ({type(e).__name__})", True
    if r.status_code != 200:
        try:
            mesaj = r.json().get("error", {}).get("message", "")[:200]
        except ValueError:
            mesaj = r.text[:200]
        gunluk = r.status_code == 429 and "per day" in mesaj   # günlük kota: beklemek işe yaramaz
        return None, f"{r.status_code} {mesaj}", r.status_code in (429, 500, 502, 503, 504) and not gunluk
    try:
        veri = r.json()
        sesler = [c for s in veri.get("steps", []) if s.get("type") == "model_output"
                  for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
        if not sesler:
            return None, "yanıtta ses yok", False
        return base64.b64decode(sesler[-1]["data"]), None, False
    except (ValueError, KeyError, TypeError) as e:
        return None, f"yanıt çözülemedi ({type(e).__name__})", False


def seslendir(metin, ses=SES, uslup=USLUP, anahtar_=None, model=MODEL):
    """Metni tek modelle sese çevirir; 24 kHz mono 16 bit PCM örneklerini (array('h')) döndürür.
    Geçici hatada (meşgul, dakikalık sınır) iki kez daha dener; günlük kota dolduysa beklemez."""
    anahtar_ = anahtar_ or anahtar()
    son_hata = None
    for deneme in range(3):
        ham, hata, gecici = _istek(metin, ses, uslup, model, anahtar_)
        if ham is not None:
            return _pcm(ham)
        son_hata = f"{model}: {hata}"
        print(f"Uyarı: seslendirme denemesi başarısız ({son_hata})", file=sys.stderr)
        if not gecici:
            break
        time.sleep(5 * (deneme + 1))
    raise SesHatasi(son_hata or "bilinmeyen hata")


def _pcm(ham):
    """WAV (RIFF) ya da başlıksız 16 bit PCM'i örnek dizisine çevirir."""
    if ham[:4] == b"RIFF":
        with wave.open(io.BytesIO(ham)) as w:
            if w.getsampwidth() != 2 or w.getnchannels() != 1:
                raise SesHatasi(f"beklenmeyen ses biçimi ({w.getnchannels()} kanal, {w.getsampwidth() * 8} bit)")
            if w.getframerate() != ORNEKLEME:
                raise SesHatasi(f"beklenmeyen örnekleme hızı ({w.getframerate()})")
            ham = w.readframes(w.getnframes())
    ornek = array.array("h")
    ornek.frombytes(ham[: len(ham) // 2 * 2])
    if sys.byteorder == "big":
        ornek.byteswap()
    if len(ornek) < ORNEKLEME // 4:
        raise SesHatasi("ses çok kısa")
    return ornek


def kirp(ornek, esik=500, pay=0.05):
    """Baştaki ve sondaki sessizliği atar (pay kadar bırakır)."""
    p = int(pay * ORNEKLEME)
    ilk = next((i for i, x in enumerate(ornek) if abs(x) > esik), 0)
    son = next((i for i in range(len(ornek) - 1, -1, -1) if abs(ornek[i]) > esik), len(ornek) - 1)
    return ornek[max(0, ilk - p): min(len(ornek), son + p)]


def sure(ornek):
    return len(ornek) / ORNEKLEME


def iz_yaz(parcalar, toplam_sn, yol):
    """[(başlangıç_sn, örnekler)] parçalarını sessiz bir iz üstüne yerleştirip mono WAV yazar."""
    iz = array.array("h", bytes(2 * int(toplam_sn * ORNEKLEME)))
    for bas, ornek in parcalar:
        i = int(bas * ORNEKLEME)
        if i + len(ornek) > len(iz):
            raise SesHatasi("ses parçası videonun sonunu aşıyor")
        iz[i:i + len(ornek)] = ornek
    if sys.byteorder == "big":
        iz.byteswap()
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ORNEKLEME)
        w.writeframes(iz.tobytes())


# ---------------------------------------------------------------- kısa Reels zamanlaması

VARSAYILAN_ZAMAN = {"cevap": 1.6, "aciklama": 3.6, "cagri": 8.0, "isik": 6.2}   # sessiz Reels (bugünkü)
VARSAYILAN_SURE = 12


def zamanla(sureler):
    """Ses parçalarının sürelerinden görsel geliş anlarını, ses başlangıçlarını ve video süresini hesaplar.

    Görsel öğe sesiyle birlikte gelir; ses kısaysa bugünkü anlar korunur (öğeler daha erken gelmez).
    """
    bas = {"soru": 0.4}
    z = {}
    z["cevap"] = round(max(VARSAYILAN_ZAMAN["cevap"], bas["soru"] + sureler["soru"] + 0.35), 2)
    bas["cevap"] = z["cevap"] + 0.15
    z["aciklama"] = round(max(VARSAYILAN_ZAMAN["aciklama"], bas["cevap"] + sureler["cevap"] + 0.45), 2)
    bas["cumle"] = z["aciklama"] + 0.2
    z["cagri"] = round(max(VARSAYILAN_ZAMAN["cagri"] - 2.0, bas["cumle"] + sureler["cumle"] + 0.5), 2)
    bas["cagri"] = z["cagri"] + 0.1
    z["isik"] = round(z["aciklama"] + (z["cagri"] - z["aciklama"]) * 0.6, 2)
    toplam = max(VARSAYILAN_SURE, bas["cagri"] + sureler["cagri"] + 1.6)
    return z, bas, math.ceil(round(toplam, 3) * 10) / 10


def modeller(deneme=False):
    """Denemede (paylaşmayan çalıştırma, yerel örnek) yalnızca yedek model: ana modelin günlük kotası cumartesi
    paylaşımına kalsın (Rıdvan, 16 Ekim 2026: "google ses denemeleri yedek model ile yapılmalı")."""
    return (YEDEK_MODEL,) if deneme else (MODEL, YEDEK_MODEL)


def kisa_seslendir(konu, bolum, klasor, ses=SES, anahtar_=None, deneme=False):
    """Kısa Reels için ses izi üretir. {"zaman", "sure", "wav", "ses", "metin", "model"} ya da SesHatasi."""
    metin = okuma_metni(konu, bolum)
    anahtar_ = anahtar_ or anahtar()
    # Bir Reels'in bütün parçaları aynı modelden: ana model yarıda kalırsa (ör. günlük kota) hepsi yedek
    # modelle baştan okunur, ses tonu parça parça değişmesin. Ücretsiz kota ~10 istek/gün/model; Reels 4 ister.
    hata = None
    for model in modeller(deneme):
        try:
            ornekler = {ad: kirp(seslendir(metin[ad], ses=ses, anahtar_=anahtar_, model=model))
                        for ad in ("soru", "cevap", "cumle", "cagri")}
            break
        except SesHatasi as e:
            hata = e
    else:
        raise hata
    sureler = {ad: sure(o) for ad, o in ornekler.items()}
    if sum(sureler.values()) > 40:
        raise SesHatasi(f"seslendirme çok uzun ({sum(sureler.values()):.1f} sn)")
    zaman, bas, toplam = zamanla(sureler)
    wav = Path(klasor) / f"_ses-kisa{konu}.wav"
    iz_yaz([(bas[ad], ornekler[ad]) for ad in ornekler], toplam, wav)
    return {"zaman": zaman, "sure": toplam, "wav": wav, "ses": ses, "metin": metin, "model": model,
            "parca_sn": {ad: round(s, 2) for ad, s in sureler.items()}}


# ---------------------------------------------------------------- komut satırı

def _sesler(dil="tr-TR"):
    r = requests.get(SESLER_URL, headers={"x-goog-api-key": anahtar()},
                     params={"language_code": dil, "gender": "female", "page_size": 200}, timeout=60)
    r.raise_for_status()
    for v in r.json().get("voices", []):
        print(v.get("id"), "|", v.get("display_name"), "|", v.get("language_code"), "|", v.get("gender"),
              "|", v.get("pitch"), "|", (v.get("description") or "")[:120])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["dene", "sesler", "metin"])
    ap.add_argument("--konu", type=int, default=3)
    ap.add_argument("--ses", default=SES)
    ap.add_argument("--dil", default="tr-TR")
    ap.add_argument("--cikti", default=".")
    ap.add_argument("--ana-model", action="store_true", help="denemede de ana modeli kullan (günlük kotayı yer)")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bilgi
    if a.komut == "sesler":
        _sesler(a.dil)
        return
    b = bilgi.BOLUMLER[a.konu - 1]
    if a.komut == "metin":
        print(json.dumps(okuma_metni(a.konu, b), ensure_ascii=False, indent=2))
        return
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    s = kisa_seslendir(a.konu, b, a.cikti, ses=a.ses, deneme=not a.ana_model)
    print(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in s.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
