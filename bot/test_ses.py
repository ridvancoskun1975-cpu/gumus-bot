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

# Tam okuma: ekrandaki simge ve birimler okunur
for ham, beklenen in (("Dolar/TL 50,00 ₺", "dolar kuru 50,00 lira"), ("19,3 g/cm³", "santimetreküpte 19,3 gram"),
                      ("%50+", "yüzde 50'den fazla"), ("±%10", "artı eksi yüzde 10"), ("#1", "1 numara"),
                      ("1.000 ons (±%10)", "1.000 ons (artı eksi yüzde 10)"),
                      ("Au ÷ Ag", "altın bölü gümüş"), ("~147 kat", "yaklaşık 147 kat"), ("1–4 hafta", "1 ile 4 hafta"),
                      ("Ons gümüş 50,00 $", "Ons gümüş 50,00 dolar"), ("1 kg", "1 kilogram"), ("147×", "147 kat"),
                      ("Parite 80 → 1 ons altın = 80 ons gümüş", "Parite 80, 1 ons altın eşittir 80 ons gümüş")):
    dogrula(ses.okunur(ham) == beklenen, f"okunur({ham!r}) = {ses.okunur(ham)!r}")
import rehber_hikaye as rh_  # noqa: E402
for no_, b_ in enumerate(bilgi.BOLUMLER, 1):
    kareler_ = [rh_._ogeler(s_, False, s_["birimler"]) for s_ in rh_.sayfalari_cikar(b_)]
    m_ = ses.rehber_metinleri(no_, b_, kareler_, "Sonraki")
    dogrula(len(m_) == len(kareler_) + 1 and all(m_), f"#{no_}: her kare için metin")
    dogrula(not re.search(r"[%÷×=→~#₺$±/·•]", " ".join(m_)), f"#{no_}: okunmayacak simge kalmadı")
    dogrula(m_[0].startswith(ses.OKUMA[no_][0]), f"#{no_}: kapakta soru")
    dogrula(m_[-1].endswith("Sıradaki bölüm: Sonraki."), f"#{no_}: kapanış")
    dogrula(400 < len(" ".join(m_)) < 1600, f"#{no_}: okuma uzunluğu {len(' '.join(m_))}")

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

# Denemede yalnızca yedek model (ana modelin günlük kotası paylaşıma kalsın)
dogrula(ses.modeller(deneme=True) == (ses.YEDEK_MODEL,), "denemede yalnızca yedek model")
dogrula(ses.modeller() == (ses.MODEL, ses.YEDEK_MODEL), "paylaşımda önce ana model")
kullanilan.clear()
ses.seslendir = yarida
try:
    with tempfile.TemporaryDirectory() as d:
        sonuc = ses.kisa_seslendir(3, bilgi.BOLUMLER[2], d, anahtar_="x", deneme=True)
        dogrula(sonuc["model"] == ses.YEDEK_MODEL and set(kullanilan) == {ses.YEDEK_MODEL},
                f"deneme ana modele dokunmamalı: {kullanilan}")
finally:
    ses.seslendir = gercek_s

# İş akışı anahtarı hem rehber günü (bilgi) hem elle kısa Reels (kisa) çalıştırmasında almalı
import yaml  # noqa: E402
akis = yaml.safe_load((main.KOK / ".github" / "workflows" / "paylas.yml").read_text(encoding="utf-8"))
adim = next(a_ for a_ in akis["jobs"]["uret"]["steps"] if a_.get("name") == "Seslendirme anahtarı")
dogrula("'bilgi'" in adim["if"] and "'kisa'" in adim["if"], f"anahtar adımı koşulu: {adim['if']}")
dogrula(not any(c.get("cron") == "50 10 * * 6" for c in akis[True]["schedule"]), "cumartesi kısa Reels zamanlaması yok")

# Pazar yorumu: uzun vade yalnızca 1 yıllık veri varken (Rıdvan, 17 Ekim 2026); yoksa kısa ve orta vade
import yorum as _y  # noqa: E402
_tam = _y.aktif_vadeler({"uzun": {"veri_yeterli": True}})
_iki = _y.aktif_vadeler({"uzun": {"veri_yeterli": False}})
dogrula([v["anahtar"] for v in _tam] == ["kisa", "orta", "uzun"] and [v["anahtar"] for v in _iki] == ["kisa", "orta"],
        "uzun vade veriye bağlı")
dogrula(_y.vade_basligi(_iki) == "Kısa ve orta vade" and _y.vade_basligi(_tam) == "Kısa, orta ve uzun vade", "başlık")
dogrula("uzun" not in _y.sema(_iki)["required"] and "uzun vadede" not in _y.sistem(_iki)
        and "kısa ve orta vadeli" in _y.sistem(_iki) and _y.sistem(_tam) == _y.SISTEM, "Claude'a giden şema ve talimat")
dogrula("Kısa ve orta vade gümüş görünümü" in _y.kapanis_okuma(_iki), "kapanış okuması")

# Okuma 1,5 kat hızlı (Rıdvan, 17 Ekim 2026: "Sesleri 1,5 hızlandır hepsini"); perde korunur (ffmpeg atempo)
dogrula(ses.HIZ == 1.5, f"okuma hızı {ses.HIZ}")
_ham = array.array("h", [int(8000 * math.sin(i / 9)) for i in range(48000)])   # 2 sn
_hizli = ses.hizlandir(_ham)
dogrula(abs(ses.sure(_hizli) - 2 / 1.5) < 0.08, f"1,5 kat hızlı: {ses.sure(_hizli):.2f} sn")
dogrula(ses.hizlandir(_ham, 1.0) is _ham and ses.hizlandir(array.array("h")) == array.array("h"), "1.0 ve boş dokunulmaz")

# Rehber arşivi Reels'i günleri (bilgi.ARSIV_REELS, Rıdvan 17 Ekim 2026): hafta içi; rehber ya da aylık özet günü
# değil; bölüm o günden önce yayımlanmış ve rehber günü sesli Reels'inden (#6) önce; günlük sınır (4) aşılmaz
from datetime import date  # noqa: E402
import aylik  # noqa: E402
import kart  # noqa: E402
yayim = {no: g for g, no in bilgi.yayim_listesi()}
for g, no in bilgi.arsiv_takvim().items():
    gun = date.fromisoformat(g)
    dogrula(gun.weekday() < 5, f"arşiv günü hafta içi: {g}")
    dogrula(g not in bilgi.takvim(), f"arşiv günü rehber günü olmamalı: {g}")
    dogrula(gun != aylik.ozet_gunu(gun.year, gun.month), f"arşiv günü aylık özet günü olmamalı: {g}")
    dogrula(yayim[no] < gun and no < 6, f"bölüm #{no} önceden yayımlanmış, sesli rehber Reels'i yok: {g}")
    dogrula(2 + (1 if kart.bugunun_karti(gun) else 0) + 1 <= 4, f"günlük sınır: {g}")
dogrula(sorted(bilgi.arsiv_takvim().values()) == [3, 4, 5], f"arşiv bölümleri: {bilgi.arsiv_takvim()}")
dogrula(bilgi.bugunun_arsiv_bolumu(date(2026, 10, 22)) == 3 and bilgi.bugunun_arsiv_bolumu(date(2026, 10, 24)) is None,
        "bugünün arşiv bölümü")
dogrula("'yorum'" in adim["if"], "pazar yorumunda da seslendirme anahtarı alınır")
uret_adimi = next(a_ for a_ in akis["jobs"]["uret"]["steps"] if a_.get("id") == "uret")
dogrula("inputs.deneme && inputs.ornek" in uret_adimi["env"]["ORNEK"] and "--ornek" in uret_adimi["run"],
        "örnek veri yalnız denemede (Claude API isteği yok)")
dogrula(ses.YORUM_SES is None or ses.YORUM_SES != ses.SES, "pazar sesi rehberin kadın sesinden ayrı (erkek)")
tur_adimi = next(a_ for a_ in akis["jobs"]["kontrol"]["steps"] if a_.get("id") == "tur")["run"]
dogrula("bot/bilgi.py arsiv" in tur_adimi and "tur=kisa" in tur_adimi, "13:50 çalışması rehbersiz günde arşivi seçer")
for is_ in ("uret",):
    dogrula("'kisa'" in str(akis["jobs"][is_]["timeout-minutes"]), "kisa türüne de uzun süre (tam okuma)")

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
    # Rehber arşivi Reels'i (tür kisa; Rıdvan 17 Ekim 2026): yalnız Reels, bölümün TAMAMI okunur, hikâye gitmez
    ses.seslendir = yapay_ses
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.kisa_hazirla(d, 3)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        b3 = bilgi.BOLUMLER[2]
        dogrula(meta["tur"] == "kisa" and meta["dosya"].endswith(".mp4"), f"arşiv Reels: {meta.get('dosya')}")
        dogrula("hikayeler" not in meta and "hikaye_videolari" not in meta and "dosyalar" not in meta,
                "arşiv Reels'inde hikâye ve kaydırmalı yok")
        dogrula(meta["kapak"].endswith("-reels-kapak.jpg") and (d / meta["kapak"]).exists(), "Reels kapağı (Dokunun'suz)")
        dogrula(meta["seslendirme"] == ses.SES, f"meta seslendirme: {meta['seslendirme']}")
        dogrula(isinstance(meta["ses_metni"], list) and len(meta["ses_metni"]) >= 3, "kare kare okuma metni")
        tum = " ".join(meta["ses_metni"])
        for sf in b3["sayfalar"]:
            dogrula(ses.okunur(sf["baslik"]) in tum, f"sayfa başlığı okunur: {sf['baslik']}")
            for mm in sf.get("maddeler", []):
                dogrula(ses.okunur(mm).rstrip(".") in tum, f"madde okunur: {mm[:40]}")
        a_ = meta["aciklama"]
        dogrula(a_.startswith(b3["baslik"] + " Kısa cevap:") and ses.ACIKLAMA_SATIRI in a_ and "Müzik:" in a_,
                "açıklama rehber günü Reels'iyle aynı biçimde")
        dogrula(len(a_) <= 2200, "açıklama sınırı")
        sn, ses_var = sure_olc(d / meta["dosya"])
        dogrula(ses_var and sn > 3 + 4 * (len(meta["ses_metni"]) - 1), f"tam okuma uzun sürer ({sn:.0f} sn)")
        dogrula(not list(d.glob("*-hikaye-*.jpg")), "hikâye kareleri yayına çıkmaz")
        dogrula(not list(d.glob("_ses-*")) and not list(d.glob("_reels-*")), "ara dosyalar kalmaz")
        dogrula(kayit.paylasim_adi("kisa", meta_yolu=d / "meta.json") == "Rehber Reels · sesli", "kayıt adı")
    os.environ["DENEME"] = "true"
    modeller_ = []
    ses.seslendir = lambda *a, model=None, **k: (modeller_.append(model), yapay_ses(*a, **k))[1]
    with tempfile.TemporaryDirectory() as d:
        main.kisa_hazirla(Path(d), 3)
        dogrula(set(modeller_) == {ses.YEDEK_MODEL}, f"elle denemede yalnızca yedek model: {set(modeller_)}")
    del os.environ["DENEME"]

    def bozuk(*a, **k):
        raise ses.SesHatasi("kota doldu")

    ses.seslendir = bozuk
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.kisa_hazirla(d, 3)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sn, ses_var = sure_olc(d / meta["dosya"])
        dogrula(meta["seslendirme"] is None and meta["ses_metni"] is None, "hata olunca seslendirme yok")
        dogrula(ses.ACIKLAMA_SATIRI not in meta["aciklama"], "sessizde seslendirme satırı olmamalı")
        dogrula(ses_var and sn >= 9 and abs((sn - 3) % 6) < 0.3, f"yedek yol: kapak 3 + kare 6 sn, müzikli ({sn})")
        dogrula(kayit.paylasim_adi("kisa", meta_yolu=d / "meta.json") == "Rehber Reels", "sessiz kayıt adı")
    ses.seslendir = yapay_ses

    # Reels hiç üretilemezse arşiv günü paylaşım atlanır (yedek gönderi yok; kaydırmalı ve hikâye zaten gitti)
    gercek_uret = main.rehber_reels_tam_uret
    main.rehber_reels_tam_uret = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("deneme hatası"))
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            main.kisa_hazirla(d, 3)
            dogrula(not (d / "meta.json").exists(), "Reels yoksa paylaşım yok")
            dogrula(not list(d.glob("*.jpg")) and not list(d.glob("*.mp4")), f"artık dosya yok: {list(d.iterdir())}")
    finally:
        main.rehber_reels_tam_uret = gercek_uret

    # Zamanlı çalışma: konu verilmezse bugünün arşiv bölümü; arşiv günü değilse hiçbir şey üretilmez
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        gercek_bugun = bilgi.bugunun_arsiv_bolumu
        bilgi.bugunun_arsiv_bolumu = lambda gun=None: None
        try:
            main.hazirla("kisa", d, False)
            dogrula(not (d / "meta.json").exists(), "arşiv günü değilse paylaşım yok")
        finally:
            bilgi.bugunun_arsiv_bolumu = gercek_bugun

    # Rehber günü (Rıdvan, 16–17 Ekim 2026): kaydırmalı yerine bölümün TAMAMINI okuyan sesli Reels,
    # hikâyeye müzikli rehber videosu
    ses.seslendir = yapay_ses
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.bilgi_hazirla(d, 7)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        dogrula("dosyalar" not in meta and meta["dosya"].endswith(".mp4"), f"rehber günü Reels: {meta.get('dosya')}")
        dogrula(meta["kapak"].endswith("-reels-kapak.jpg") and (d / meta["kapak"]).exists(), "Reels kapağı (Dokunun'suz)")
        dogrula(meta["seslendirme"] == ses.SES, "rehber Reels sesli")
        dogrula(isinstance(meta["ses_metni"], list) and len(meta["ses_metni"]) == len(meta["hikayeler"]),
                "her kare için bir okuma")
        b7 = bilgi.BOLUMLER[6]
        tum = " ".join(meta["ses_metni"])
        for sf in b7["sayfalar"]:
            dogrula(ses.okunur(sf["baslik"]) in tum, f"sayfa başlığı okunur: {sf['baslik']}")
            for mm in sf.get("maddeler", []):
                dogrula(ses.okunur(mm).rstrip(".") in tum, f"madde okunur: {mm[:40]}")
        dogrula(meta["hikaye_videolari"] and all((d / v).exists() for v in meta["hikaye_videolari"]),
                "müzikli rehber hikâye videosu yine üretilir")
        a_ = meta["aciklama"]
        dogrula(a_.startswith(b7["baslik"] + " Kısa cevap:"), "açıklama kısa cevapla başlar")
        dogrula(ses.ACIKLAMA_SATIRI in a_ and "Müzik:" in a_ and "kaydırmalı" not in a_, "açıklama satırları")
        dogrula(len(a_) <= 2200, "açıklama sınırı")
        sn, ses_var = sure_olc(d / meta["dosya"])
        beklenen = sum(ses.KARE_EN_AZ["kapak" if i == 0 else "kare"] for i in range(len(meta["hikayeler"])))
        dogrula(ses_var and sn > beklenen + 10, f"tam okuma uzun sürer ({sn:.0f} sn)")
        dogrula(kayit.paylasim_adi("bilgi", meta_yolu=d / "meta.json") == "Rehber Reels · sesli", "kayıt adı")
        dogrula(not list(d.glob("_ses-*")) and not list(d.glob("_reels-*")), "ara dosyalar kalmaz")

    # Ses alınamazsa Reels yine gider: kareler hikâye süreleriyle (kapak 3, kare 6 sn), yalnızca müzik
    def bozuk2(*a, **k):
        raise ses.SesHatasi("kota doldu")
    ses.seslendir = bozuk2
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main.bilgi_hazirla(d, 7)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sn, ses_var = sure_olc(d / meta["dosya"])
        n = len(meta["hikayeler"])
        dogrula(meta["seslendirme"] is None and abs(sn - (3 + 6 * (n - 1))) < 0.3 and ses_var,
                f"sessiz yedek: müzikli Reels {sn}")
        dogrula(ses.ACIKLAMA_SATIRI not in meta["aciklama"], "sessizde seslendirme satırı yok")
        dogrula(kayit.paylasim_adi("bilgi", meta_yolu=d / "meta.json") == "Rehber Reels", "sessiz kayıt adı")
    ses.seslendir = yapay_ses

    # Reels üretilemezse aynı gün eski kaydırmalı gönderi gider
    gercek_uret = main.rehber_reels_tam_uret
    main.rehber_reels_tam_uret = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("deneme hatası"))
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            main.bilgi_hazirla(d, 7)
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            dogrula(len(meta.get("dosyalar", [])) == len(bilgi.BOLUMLER[6]["sayfalar"]) + 1 and "dosya" not in meta,
                    "yedek yol: kaydırmalı")
            dogrula(meta["aciklama"] == bilgi.aciklama(7), "yedek yolda eski açıklama")
            dogrula(meta["hikaye_videolari"], "yedek yolda hikâye videosu yine var")
            dogrula(kayit.paylasim_adi("bilgi", meta_yolu=d / "meta.json") == "Rehber", "yedek yolda kayıt adı")
    finally:
        main.rehber_reels_tam_uret = gercek_uret

    # Yayın: rehber Reels'i Reels olarak gider, ardından müzikli rehber hikâyesi; Reels'in kendisi hikâyeye gitmez
    olaylar = []
    yedek = {k: getattr(main, k) for k in ("_url_hazir_mi", "hesap_bilgisi", "_reels_konteyneri", "_istek",
                                            "rehber_hikayeleri", "hikaye_paylas")}
    main._url_hazir_mi = lambda *a, **k: True
    main.hesap_bilgisi = lambda: {"user_id": "1"}
    main._reels_konteyneri = lambda kid, url, meta, taban: (olaylar.append(("reels", url.rsplit("/", 1)[1])), {"id": "k"})[1]
    main._istek = lambda yontem, yol, **p: (olaylar.append(("istek", yol)), {"id": "m"})[1]
    main.rehber_hikayeleri = lambda kid, meta, taban: olaylar.append(("rehber-hikaye", tuple(meta["hikaye_videolari"])))
    main.hikaye_paylas = lambda kid, url: olaylar.append(("hikaye", url))
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "meta.json").write_text(json.dumps({"tur": "bilgi", "konu": 7, "dosya": "bilgi7-x.mp4", "kapak": "k.jpg",
                                                     "kapak_ms": 15000, "aciklama": "x", "hikayeler": ["h1.png"],
                                                     "hikaye_videolari": ["bilgi7-x-hikaye-video-1.mp4"]}), encoding="utf-8")
            main._yayinla(d, "https://ornek/")
        dogrula(olaylar[0] == ("reels", "bilgi7-x.mp4"), f"önce Reels: {olaylar}")
        dogrula(("rehber-hikaye", ("bilgi7-x-hikaye-video-1.mp4",)) in olaylar, "sonra müzikli rehber hikâyesi")
        dogrula(not any(o[0] == "hikaye" for o in olaylar), "Reels'in kendisi hikâyeye gitmez")
    finally:
        for k, v in yedek.items():
            setattr(main, k, v)

    # Pazar Reels'i sesli (Rıdvan 17 Ekim 2026): erkek sesi, analizin TAMAMI; hikâyeye 32 sn'lik müzikli sürüm
    import yorum  # noqa: E402
    eski_yorum_ses = ses.YORUM_SES
    okumalar = []

    def kayitli(metin, ses=None, uslup=None, anahtar_=None, model=None):
        okumalar.append((ses, uslup, metin))
        return yapay_ses(metin)

    try:
        ses.YORUM_SES = "Charon"
        ses.seslendir = kayitli
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            main.yorum_hazirla(d, ornek=True)
            r = json.loads((d / "meta.json").read_text(encoding="utf-8"))["reels"]
            dogrula(r["seslendirme"] == "Charon" and r["dosya"].startswith("yorum-reels-sesli-"), f"sesli Reels: {r}")
            dogrula(len(okumalar) == 5 and all(s_ == "Charon" and u == ses.USLUP_ERKEK for s_, u, _ in okumalar),
                    "5 sahne, erkek sesi ve üslubu")
            sn, ses_var = sure_olc(d / r["dosya"])
            dogrula(ses_var and sn > 60 and abs(sn - r["sure"]) < 0.5, f"analizin tamamı okunur ({sn:.0f} sn)")
            hs, h_ses = sure_olc(d / r["hikaye_dosya"])
            dogrula(h_ses and abs(hs - 32) < 0.3, f"hikâyeye 32 sn'lik müzikli sürüm ({hs})")
            tum = " ".join(r["ses_metni"])
            for vk, vy in yorum.ORNEK_YORUM.items():
                for alan in ("ozet", "durum", "seyir", "izlenecek"):
                    dogrula(ses.okunur(vy[alan]).rstrip(".") in tum, f"{vk}/{alan} okunur")
            dogrula("yatırım tavsiyesi değildir" in tum and "her pazar saat on birde" in tum, "kapanış okunur")
            dogrula(not re.search(r"[%÷×=→~#₺$±/·•]", tum), "okunmayacak simge yok")
            dogrula(ses.ACIKLAMA_SATIRI in r["aciklama"] and len(r["aciklama"]) <= 2200, "açıklamada seslendirme notu")
            dogrula(r["kapak"] and (d / r["kapak"]).exists() and 0 < r["kapak_ms"] < r["sure"] * 1000, "kapak")
            dogrula(not list(d.glob("_ses-*")), "ara ses dosyası kalmaz")

        def bozuk3(*a, **k):
            raise ses.SesHatasi("kota doldu")

        ses.seslendir = bozuk3
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            main.yorum_hazirla(d, ornek=True)
            r = json.loads((d / "meta.json").read_text(encoding="utf-8"))["reels"]
            sn, ses_var = sure_olc(d / r["dosya"])
            dogrula(r["seslendirme"] is None and "hikaye_dosya" not in r and abs(sn - 32) < 0.3 and ses_var,
                    f"ses yoksa 32 sn müzikli Reels ({sn})")
            dogrula(ses.ACIKLAMA_SATIRI not in r["aciklama"], "sessizde seslendirme notu yok")
        okumalar.clear()
        ses.seslendir = kayitli
        ses.YORUM_SES = None
        with tempfile.TemporaryDirectory() as d:
            main.yorum_hazirla(Path(d), ornek=True)
            dogrula(not okumalar, "ses seçilmeden okuma yapılmaz")
    finally:
        ses.YORUM_SES = eski_yorum_ses
        ses.seslendir = yapay_ses

    # Yayın: sesli Reels Reels olarak, hikâyeye 32 sn'lik müzikli sürüm
    olaylar = []
    yedek = {k: getattr(main, k) for k in ("_url_hazir_mi", "_reels_konteyneri", "_istek", "hikaye_paylas")}
    main._url_hazir_mi = lambda *a, **k: True
    main._reels_konteyneri = lambda kid, url, meta, taban: (olaylar.append(("reels", url)), {"id": "k"})[1]
    main._istek = lambda yontem, yol, **p: {"id": "m"}
    main.hikaye_paylas = lambda kid, url: olaylar.append(("hikaye", url))
    try:
        main.yorum_reelsi("1", {"dosya": "yorum-reels-sesli-x.mp4", "hikaye_dosya": "yorum-reels-x.mp4"}, "https://o/")
        dogrula(olaylar == [("reels", "https://o/yorum-reels-sesli-x.mp4"), ("hikaye", "https://o/yorum-reels-x.mp4")],
                f"pazar yayını: {olaylar}")
    finally:
        for k, v in yedek.items():
            setattr(main, k, v)

    # Ses seçimi örnekleri: ses başına 1 okuma, yalnızca yedek model; günlük kota dolunca kalanlar atlanır
    cagri_ = []

    def ornek_ses(metin, ses=None, uslup=None, anahtar_=None, model=None):
        cagri_.append((ses, model, uslup))
        if ses == "Dolu":
            raise ses_mod.SesHatasi("429 limit: 10 requests per day")
        return yapay_ses(metin)

    ses.seslendir = ornek_ses
    with tempfile.TemporaryDirectory() as d:
        sonuc = ses.ornek_sesler(["Charon", "Orus", "Dolu", "Sonraki"], d, anahtar_="x")
        dogrula([s_[1] for s_ in sonuc] == ["Charon", "Orus"], f"örnek sesler: {sonuc}")
        dogrula(all(m == ses.YEDEK_MODEL and u == ses.USLUP_ERKEK for _, m, u in cagri_), f"yedek model: {cagri_}")
        dogrula([c[0] for c in cagri_] == ["Charon", "Orus", "Dolu"], "günlük kota dolunca durur")
        dogrula(sorted(p_.name for p_ in Path(d).iterdir()) == ["ses-1.mp4", "ses-2.mp4"], "telefonda açılır mp4")
        sn, ses_var = sure_olc(Path(d) / "ses-1.mp4")
        dogrula(ses_var and sn > 5, f"örnek süresi {sn}")
    ses.seslendir = yapay_ses
finally:
    ses.seslendir = gercek
    del os.environ["GEMINI_API_KEY"]
    if gecici_muzik:
        muzik.unlink(missing_ok=True)

print(f"Tamam: {sayac} sınama geçti.")
