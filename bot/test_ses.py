"""Rehber kısa Reels seslendirmesinin sınamaları (bot/ses.py). Gemini'ye istek atmaz; ses yapay üretilir.

  python bot/test_ses.py           (videoyu da üretir, ~2-3 dk)
  HIZLI=1 python bot/test_ses.py   (video üretmeden)
"""
import array
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi  # noqa: E402
import kayit  # noqa: E402
import main  # noqa: E402
import ses  # noqa: E402

sayac = 0


def dogrula(kosul, mesaj):
    global sayac
    if not kosul:
        raise AssertionError(mesaj)
    sayac += 1


# ---------------------------------------------------------------- okuma metni
for no, b in enumerate(bilgi.BOLUMLER, 1):
    dogrula(no in ses.OKUMA, f"Bölüm {no} için ses.OKUMA satırı yok (elle yazılmış okuma metni ekleyin)")
    m = ses.okuma_metni(no, b)
    dogrula(set(m) == {"soru", "cevap", "cumle", "cagri"}, f"{no}: parça adları")
    for ad, metin in m.items():
        dogrula(metin and len(metin) <= 160, f"{no}/{ad}: boş ya da çok uzun ({len(metin)})")
        dogrula(not re.search(r"\d", metin), f"{no}/{ad}: rakam var, yazıyla yazılmalı: {metin}")
        dogrula(not re.search(r"[%÷×=→~#/₺·]", metin), f"{no}/{ad}: okunmayacak simge var: {metin}")
    dogrula(m["cevap"].startswith("Kısa cevap:"), f"{no}: cevap 'Kısa cevap:' ile başlamalı")
    toplam = sum(len(x) for x in m.values())
    dogrula(toplam <= 330, f"{no}: okuma metni uzun ({toplam} harf; video ~25 sn'yi aşar)")

# Elle yazılmamış bölüm için yedek metin rakam ve simgeyi okunur hâle getirir
dogrula(ses._sozlu("%50+") == "yüzde 50'den fazla", ses._sozlu("%50+"))
dogrula(ses._sozlu("~31 kg") == "yaklaşık 31 kilogram", ses._sozlu("~31 kg"))
dogrula(ses._sozlu("Au ÷ Ag") == "Au bölü Ag", ses._sozlu("Au ÷ Ag"))
dogrula(ses._sozlu("147×") == "147 kat", ses._sozlu("147×"))
yedek = ses.okuma_metni(99, bilgi.BOLUMLER[4])
dogrula(yedek["cevap"].startswith("Kısa cevap: yüzde 50"), yedek["cevap"])

# ---------------------------------------------------------------- zamanlama
z, bas, toplam = ses.zamanla({"soru": 0.5, "cevap": 0.8, "cumle": 0.9, "cagri": 1.0})
dogrula(z["cevap"] == 1.6 and z["aciklama"] == 3.6, f"kısa seste bugünkü anlar korunmalı: {z}")
dogrula(toplam == 12.0, f"kısa seste süre 12 sn kalmalı: {toplam}")
sureler = {"soru": 2.2, "cevap": 3.4, "cumle": 4.1, "cagri": 3.6}
z, bas, toplam = ses.zamanla(sureler)
dogrula(z["cevap"] < z["aciklama"] < z["isik"] < z["cagri"], f"anlar sıralı olmalı: {z}")
onceki_son = 0
for ad in ("soru", "cevap", "cumle", "cagri"):
    dogrula(bas[ad] >= onceki_son + 0.3, f"{ad} sesi öncekiyle çakışıyor: {bas}")
    onceki_son = bas[ad] + sureler[ad]
dogrula(bas["cevap"] >= z["cevap"] and bas["cumle"] >= z["aciklama"] and bas["cagri"] >= z["cagri"],
        "ses, görsel öğesi gelmeden başlamamalı")
dogrula(toplam >= onceki_son + 1.5, f"sondaki müzik kararması konuşmayı kesmemeli: {toplam} / {onceki_son}")
dogrula(toplam <= 25, f"video çok uzun: {toplam}")
dogrula(ses.VARSAYILAN_ZAMAN == {"cevap": 1.6, "aciklama": 3.6, "cagri": 8.0, "isik": 6.2}, "sessiz anlar değişmemeli")

# ---------------------------------------------------------------- ses işleme
ton = array.array("h", [0] * 2400 + [int(8000 * math.sin(i / 10)) for i in range(24000)] + [0] * 4800)
kirpik = ses.kirp(ton)
dogrula(abs(ses.sure(kirpik) - 1.1) < 0.02, f"kırpma: {ses.sure(kirpik)}")
with tempfile.TemporaryDirectory() as d:
    yol = Path(d) / "iz.wav"
    ses.iz_yaz([(0.4, kirpik), (2.0, kirpik)], 4.0, yol)
    import wave
    with wave.open(str(yol)) as w:
        dogrula(w.getframerate() == 24000 and abs(w.getnframes() / 24000 - 4.0) < 0.01, "iz süresi")
    try:
        ses.iz_yaz([(3.5, kirpik)], 4.0, yol)
        dogrula(False, "videonun sonunu aşan ses hata vermeli")
    except ses.SesHatasi:
        dogrula(True, "")
# WAV ve başlıksız PCM ikisi de okunur
import io
import wave
b_ = io.BytesIO()
with wave.open(b_, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(ton.tobytes())
dogrula(len(ses._pcm(b_.getvalue())) == len(ton), "WAV okunmalı")
dogrula(len(ses._pcm(ton.tobytes())) == len(ton), "başlıksız PCM okunmalı")

# Anahtar yoksa hata (bot yedek yola düşer), anahtar ortamdan okunur
eski_ortam = {k: os.environ.pop(k, None) for k in ("GEMINI_API_KEY", "KAYIT_PAT")}
try:
    ses.anahtar()
    dogrula(False, "anahtar yokken SesHatasi bekleniyordu")
except ses.SesHatasi:
    dogrula(True, "")
os.environ["GEMINI_API_KEY"] = " deneme-anahtar \n"
dogrula(ses.anahtar() == "deneme-anahtar", "ortamdaki anahtar")
del os.environ["GEMINI_API_KEY"]
for k, v in eski_ortam.items():
    if v is not None:
        os.environ[k] = v

# Yanıt çözme: ses steps → model_output → audio.data
import base64


class Yanit:
    def __init__(self, kod, veri):
        self.status_code, self._veri, self.text = kod, veri, json.dumps(veri)

    def json(self):
        return self._veri


cagrilar = []


def sahte_post(url, json=None, timeout=None, headers=None):
    cagrilar.append(json)
    if len(cagrilar) == 1:
        return Yanit(503, {"error": {"message": "meşgul"}})
    return Yanit(200, {"steps": [{"type": "thought"}, {"type": "model_output", "content": [
        {"type": "text", "text": "x"}, {"type": "audio", "data": base64.b64encode(b_.getvalue()).decode()}]}]})


gercek_post, gercek_uyku = ses.requests.post, ses.time.sleep
ses.requests.post, ses.time.sleep = sahte_post, lambda s: None
try:
    sonuc = ses.seslendir("Merhaba", ses="Kore", anahtar_="x")
    dogrula(len(sonuc) == len(ton), "yeniden denemeden sonra ses gelmeli")
    dogrula(cagrilar[-1]["generation_config"]["speech_config"] == [{"voice": "Kore"}], "ses adı istekte")
    dogrula(cagrilar[-1]["input"][0]["content"][0]["annotations"][0]["style"] == ses.USLUP, "üslup istekte")
    # Günlük kota (429 "per day") beklenmez, aynı model yeniden denenmez
    cagrilar.clear()
    ses.requests.post = lambda *a, **k: (cagrilar.append(1), Yanit(429, {"error": {"message":
        "Rate limit exceeded (limit: 10 requests per day on Free Tier)"}}))[1]
    try:
        ses.seslendir("Merhaba", anahtar_="x")
        dogrula(False, "kota dolunca SesHatasi bekleniyordu")
    except ses.SesHatasi:
        dogrula(len(cagrilar) == 1, f"günlük kotada yeniden deneme olmamalı ({len(cagrilar)} istek)")
finally:
    ses.requests.post, ses.time.sleep = gercek_post, gercek_uyku

# Ana model yarıda kalırsa bütün parçalar yedek modelle baştan okunur (ses tonu karışmasın)
kullanilan = []


def yarida(metin, ses=None, uslup=None, anahtar_=None, model=None):
    kullanilan.append(model)
    if model == ses_mod_ana and kullanilan.count(model) == 3:
        raise ses_mod_hata("kota")
    return array.array("h", [0] * 1200 + [9000] * 24000 + [0] * 1200)


ses_mod_ana, ses_mod_hata = ses.MODEL, ses.SesHatasi
gercek_s = ses.seslendir
ses.seslendir = yarida
try:
    with tempfile.TemporaryDirectory() as d:
        sonuc = ses.kisa_seslendir(3, bilgi.BOLUMLER[2], d, anahtar_="x")
        dogrula(sonuc["model"] == ses.YEDEK_MODEL, f"yedek model: {sonuc['model']}")
        dogrula(kullanilan == [ses.MODEL] * 3 + [ses.YEDEK_MODEL] * 4, f"parçalar tek modelden: {kullanilan}")
finally:
    ses.seslendir = gercek_s

# ---------------------------------------------------------------- kayıt adı
with tempfile.TemporaryDirectory() as d:
    m = Path(d) / "meta.json"
    m.write_text(json.dumps({"tur": "kisa", "seslendirme": "Kore"}), encoding="utf-8")
    dogrula(kayit.paylasim_adi("kisa", meta_yolu=m) == "Rehber Reels · sesli", kayit.paylasim_adi("kisa", meta_yolu=m))
    m.write_text(json.dumps({"tur": "kisa", "seslendirme": None}), encoding="utf-8")
    dogrula(kayit.paylasim_adi("kisa", meta_yolu=m) == "Rehber Reels", "sessizde ad değişmemeli")
    dogrula(kayit.paylasim_adi("kisa", meta_yolu=Path(d) / "yok.json") == "Rehber Reels", "meta yoksa")

if os.environ.get("HIZLI"):
    print(f"Tamam (hızlı): {sayac} sınama geçti.")
    sys.exit(0)


# ---------------------------------------------------------------- uçtan uca (yapay sesle)
def yapay_ses(metin, ses=None, uslup=None, anahtar_=None, model=None):
    """Harf sayısına orantılı, konuşma benzeri genlikli ton (Gemini yerine)."""
    n = int(len(metin) * 0.065 * ses_mod.ORNEKLEME)
    return array.array("h", [0] * 2400 + [int(9000 * math.sin(i / 7) * (0.6 + 0.4 * math.sin(i / 900)))
                                          for i in range(n)] + [0] * 2400)


ses_mod = ses


def sure_olc(mp4):
    r = subprocess.run([main.ffmpeg_yolu(), "-i", str(mp4)], capture_output=True, text=True)
    h, dk, sn = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(dk) * 60 + float(sn), "Audio:" in r.stderr


muzik = main.KOK / "assets" / "muzik.mp3"
gecici_muzik = not muzik.exists()
if gecici_muzik:   # yerelde müzik yok: müzikli karışımı da sınamak için kısa bir ton (.gitignore'da)
    subprocess.run([main.ffmpeg_yolu(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=330:duration=30", "-ac", "2", str(muzik)], check=True)
gercek = ses.seslendir
os.environ["GEMINI_API_KEY"] = "sahte"
try:
    ses.seslendir = yapay_ses
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.kisa_hazirla(d, 3)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sn, ses_var = sure_olc(d / meta["dosya"])
        dogrula(meta["seslendirme"] == ses.SES, f"meta seslendirme: {meta['seslendirme']}")
        dogrula(ses.ACIKLAMA_SATIRI in meta["aciklama"], "açıklamada seslendirme satırı olmalı")
        dogrula(ses_var and 12 <= sn <= 25, f"seslendirmeli video süresi {sn}")
        dogrula(abs(meta["kapak_ms"] / 1000 - (sn - 0.5)) < 0.3, "kapak anı videonun sonuna yakın")
        dogrula(not list(d.glob("_ses-*")), "ara ses dosyası silinmeli")
        dogrula(meta["ses_metni"]["soru"] == ses.OKUMA[3][0], "okunan metin metada")

    def bozuk(*a, **k):
        raise ses.SesHatasi("kota doldu")

    ses.seslendir = bozuk
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.kisa_hazirla(d, 3)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sn, ses_var = sure_olc(d / meta["dosya"])
        dogrula(meta["seslendirme"] is None, "hata olunca seslendirme yok")
        dogrula(ses.ACIKLAMA_SATIRI not in meta["aciklama"], "sessizde seslendirme satırı olmamalı")
        dogrula(abs(sn - 12) < 0.2 and ses_var, f"yedek yol: 12 sn müzikli video ({sn})")
finally:
    ses.seslendir = gercek
    del os.environ["GEMINI_API_KEY"]
    if gecici_muzik:
        muzik.unlink(missing_ok=True)

print(f"Tamam: {sayac} sınama geçti.")
