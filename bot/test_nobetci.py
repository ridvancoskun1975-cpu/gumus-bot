"""bot/nobetci.py ve yedek cron sınamaları (ağ yok). Çalıştır: python bot/test_nobetci.py

Rıdvan, 3 Kasım 2026: "Bir daha olmaması için ne yapmamız lazım?", "çift paylaşım da olmasın lütfen".
"""
import contextlib
import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import nobetci  # noqa: E402
import program  # noqa: E402
import sinir  # noqa: E402

gecen = 0
KOK = Path(__file__).resolve().parent.parent


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1
    print(f"TAMAM {ad}")


# 3 Kasım 2026 Salı 11:15 TR = 08:15 UTC
SIMDI = datetime(2026, 11, 3, 8, 15, tzinfo=timezone.utc)
OGLEN = datetime(2026, 11, 3, 12, 15, tzinfo=timezone.utc)    # 15:15 TR
AKSAM = datetime(2026, 11, 3, 18, 15, tzinfo=timezone.utc)    # 21:15 TR
SABAH = (1, SIMDI, "paylaşıldı", "reels", 1)


def calistir(dilim, *, durumlar, suren=lambda: False, baslat_hata=None, simdi=SIMDI, gunduz=None):
    """durumlar: her bakışta say()'ın döndüreceği listeler (sonuncusu tekrarlanır). Döner (kod, başlatılanlar, bekleme)."""
    baslatilan, uyku = [], []
    sira = list(durumlar)

    def say(_simdi=None, **kw):
        return sira.pop(0) if len(sira) > 1 else sira[0]

    def baslatici(tur):
        if baslat_hata:
            raise baslat_hata
        baslatilan.append(tur)

    eski = nobetci.gunduz_turu
    if gunduz is not None:
        nobetci.gunduz_turu = lambda **kw: gunduz
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            kod = nobetci.main(dilim, uyu=lambda sn: uyku.append(sn), say=say, baslatici=baslatici, simdi=simdi,
                               suren=suren)
    finally:
        nobetci.gunduz_turu = eski
    return kod, baslatilan, len(uyku)


# ---- beklenen tür
esit(nobetci.beklenen("12 8 * * 1-5"), "reels", "11:12 dilimi sabah Reels'i")
esit(nobetci.beklenen("12 18 * * 1-5"), "post", "21:12 dilimi akşam özeti")
esit(nobetci.beklenen("12 8 * * 6"), "hafta", "cumartesi haftalık özet")
esit(nobetci.beklenen("post"), "post", "elle tür verilebilir")
esit(nobetci.gunduz_turu(bolum="7", ay="", arsiv=""), "bilgi", "gündüz: rehber günü")
esit(nobetci.gunduz_turu(bolum="", ay="ay", arsiv=""), "ay", "gündüz: aylık özet günü")
esit(nobetci.gunduz_turu(bolum="", ay="", arsiv="4"), "kisa", "gündüz: arşiv Reels'i günü")
esit(nobetci.gunduz_turu(bolum="", ay="", arsiv=""), None, "gündüz: o gün ~14:00 paylaşımı yok")
esit(nobetci.beklenen("hikaye"), None, "kilit dışı tür beklenmez")

# ---- karar
esit(calistir("12 8 * * 1-5", durumlar=[[SABAH]]), (0, [], 0), "Reels gitmiş: sessiz biter, başlatmaz")
esit(calistir("12 8 * * 1-5", durumlar=[[]]), (1, ["reels"], 0), "Reels gitmemiş: başlatır, kırmızı biter (haber)")
esit(calistir("12 18 * * 1-5", durumlar=[[SABAH]], simdi=AKSAM), (1, ["post"], 0),
     "sabah gitti ama akşam gitmedi: akşamı başlatır")
suruyor = [(2, SIMDI, "sürüyor", "reels", 1)]
esit(calistir("12 8 * * 1-5", durumlar=[suruyor, suruyor, [SABAH]]), (0, [], 2),
     "Reels paylaşılıyor: bekler, gidince başlatmadan biter")
esit(calistir("12 8 * * 1-5", durumlar=[suruyor]), (0, [], nobetci.BEKLE_DK),
     "sürüp duran çalıştırma: en çok BEKLE_DK bekler, başlatmaz")
turu_belirsiz = [(3, SIMDI, "sürüyor", None, 2)]
esit(calistir("12 8 * * 1-5", durumlar=[turu_belirsiz, [SABAH]]), (0, [], 1), "türü belli olmayan süren çalıştırma beklenir")
bayrak = iter([True, False])
esit(calistir("12 8 * * 1-5", durumlar=[[], [SABAH]], suren=lambda: next(bayrak)), (0, [], 1),
     "sırada bekleyen çalıştırma varken başlatmaz, bekler")
esit(calistir("12 12 * * 1-5", durumlar=[[]], gunduz=None)[0] in (0, 1), True, "gündüz dilimi takvimden okunur")
esit(calistir("12 12 * * 1-5", durumlar=[[]], gunduz="bilgi", simdi=OGLEN), (1, ["bilgi"], 0),
     "rehber gitmemiş: başlatır")
# Süren çalıştırma 20 dk'da bitmedi ve türü bizim değil / belli değil: yine başlatır (sıraya girer, kilit korur)
esit(calistir("12 8 * * 1-5", durumlar=[turu_belirsiz]), (1, ["reels"], nobetci.BEKLE_DK),
     "türü belli olmayan çalıştırma 20 dk'da bitmezse yine başlatır (sessiz kaçırma yok)")
esit(calistir("12 8 * * 1-5", durumlar=[[]], suren=lambda: True), (1, ["reels"], nobetci.BEKLE_DK),
     "başka bir çalıştırma 20 dk sürerse yine başlatır")
esit(calistir("12 8 * * 1-5", durumlar=[[(4, SIMDI, "sürüyor", "post", 2)]], suren=lambda: True),
     (1, ["reels"], nobetci.BEKLE_DK), "başka türde süren çalıştırma bizimki sayılmaz")

# ---- saat penceresi: hedeften önce başlatmaz (gecikip ertesi güne kalan bakış dahil)
gece = datetime(2026, 11, 6, 21, 15, tzinfo=timezone.utc)   # cumartesi 00:15 TR (cuma 21:12 bakışı 3 saat gecikti)
esit(calistir("12 18 * * 1-5", durumlar=[[]], simdi=gece), (0, [], 0),
     "akşam bakışı gece yarısını geçtiyse yeni günün özetini başlatmaz")
erken = datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc)    # 09:00 TR
esit(calistir("reels", durumlar=[[]], simdi=erken), (0, [], 0), "hedef saatten (09:55) önce başlatmaz")
esit(calistir("12 18 * * 1-5", durumlar=[[]], simdi=SIMDI), (0, [], 0), "akşam özetini sabah başlatmaz")
gec_aksam = datetime(2026, 11, 3, 19, 45, tzinfo=timezone.utc)   # 22:45 TR
esit(calistir("12 18 * * 1-5", durumlar=[[]], simdi=gec_aksam), (1, [], 0),
     "akşam özeti 22:30'dan sonra başlatılmaz (gece yarısını geçmesin), haber verir")
for t in nobetci.SON_SAAT:
    esit(program.HEDEF_SAATLERI[t] < nobetci.SON_SAAT[t] <= (22, 30), True, f"{t}: pencere hedef → son saat")

# ---- pazar yorumu duraklatıldıysa başlatmaz; takvim okunamazsa kırmızı
esit(nobetci.yorum_duraklatildi(), False, "main.YORUM_DURAKLAT şu an kapalı (metinden okunur)")
eski_d = nobetci.yorum_duraklatildi
nobetci.yorum_duraklatildi = lambda: True
esit(nobetci.beklenen("12 9 * * 0"), None, "YORUM_DURAKLAT açıkken nöbetçi pazar yorumunu beklemez")
nobetci.yorum_duraklatildi = eski_d
try:
    nobetci._komut("-c", "import sys; sys.exit(3)")
    esit(True, False, "_komut hata vermeliydi")
except nobetci.TakvimHatasi:
    esit(True, True, "takvim betiği hata verirse _komut 'paylaşım yok' saymaz, hata fırlatır")


def bozuk(**kw):
    raise nobetci.TakvimHatasi("bilgi.py bozuk")


eski = nobetci.gunduz_turu
nobetci.gunduz_turu = bozuk
with contextlib.redirect_stdout(io.StringIO()):
    kod = nobetci.main("12 12 * * 1-5", say=lambda *a, **k: [], baslatici=lambda t: (_ for _ in ()).throw(AssertionError),
                       simdi=OGLEN, suren=lambda: False)
nobetci.gunduz_turu = eski
esit(kod, 1, "takvim okunamazsa kırmızı biter, başlatmaz")


def gunduz_yok(**kw):
    return None


eski = nobetci.gunduz_turu
nobetci.gunduz_turu = gunduz_yok
with contextlib.redirect_stdout(io.StringIO()):
    kod = nobetci.main("12 12 * * 1-5", say=lambda *a, **k: [], baslatici=lambda t: (_ for _ in ()).throw(AssertionError),
                       simdi=SIMDI, suren=lambda: False)
nobetci.gunduz_turu = eski
esit(kod, 0, "o gün ~14:00 paylaşımı yoksa sessiz biter")

aksam = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)   # 19:00 TR
esit(calistir("12 8 * * 1-5", durumlar=[[]], simdi=aksam), (1, [], 0),
     "nöbetçi çok geç çalıştıysa sabah Reels'ini akşam başlatmaz, yalnız haber verir")
esit(calistir("12 18 * * 1-5", durumlar=[[]], simdi=aksam), (0, [], 0), "akşam özeti 19:00'da (hedeften önce) başlatılmaz")
esit(calistir("12 8 * * 1-5", durumlar=[[]], baslat_hata=OSError("ağ yok")), (1, [], 0),
     "başlatılamazsa kırmızı biter")


def sayamaz(*a, **k):
    raise sinir.SayilamadiHatasi("bağlantı yok")


with contextlib.redirect_stdout(io.StringIO()):
    kod = nobetci.main("12 8 * * 1-5", say=sayamaz, baslatici=lambda t: (_ for _ in ()).throw(AssertionError),
                       simdi=SIMDI, suren=lambda: False)
esit(kod, 1, "sayılamazsa başlatmaz (çift paylaşım riski), kırmızı biter")

# ---- iş akışları: yedek cron'lar asıl cron'la aynı türü seçer, hedeften en çok 50 dk önce, takvime girmez
yml = (KOK / ".github/workflows/paylas.yml").read_text(encoding="utf-8")
satirlar = re.findall(r"^\s*-\s*cron:\s*'([^']+)'(.*)$", yml, flags=re.M)
yedekler = [c for c, kuyruk in satirlar if "yedek" in kuyruk]
esit(len(yedekler), 5, "5 yedek cron (sabah, akşam, cumartesi, pazar, gündüz)")
esleme = dict(re.findall(r'github\.event\.schedule \}\}" = "([^"]+)" \]; then\s*\n\s*tur=(\w+)', yml))
asil = dict(program.cronlar(KOK / ".github/workflows/paylas.yml"))
for y in yedekler:
    tur = esleme.get(y, "reels")   # eşlemede olmayan cron "else" kolundan reels
    dk, sa, *_ = y.split()
    gun = y.split(" ", 4)[4]
    karsilik = [c for c, t in asil.items() if t == tur and c.split(" ", 4)[4] == gun]
    esit(len(karsilik), 1, f"yedek {y} → {tur}: aynı günlerde asıl cron var")
    hedef = program.HEDEF_SAATLERI[tur]
    fark = (hedef[0] * 60 + hedef[1]) - ((int(sa) + 3) * 60 + int(dk))
    esit(0 <= fark <= 50, True, f"yedek {y}: hedef saatten {fark} dk önce (bekleme sınırı 50 dk)")
    esit(int(dk) not in (0, 55, 56, 57, 58, 59, 1, 2, 3, 4, 5), True, f"yedek {y}: saat başı yoğunluğundan uzak")
esit(all("yedek" not in c for c, _ in program.cronlar(KOK / ".github/workflows/paylas.yml")), True,
     "yedek cron'lar sitedeki takvime girmez")
nb = (KOK / ".github/workflows/nobetci.yml").read_text(encoding="utf-8")
nb_cron = re.findall(r"^\s*-\s*cron:\s*'([^']+)'", nb, flags=re.M)
esit(sorted(nb_cron), sorted(nobetci.DILIMLER), "nobetci.yml cron'ları nobetci.DILIMLER ile aynı")
esit("onay" not in re.sub(r"#.*", "", nb), True, "nöbetçi onay işaretini kullanmaz")
esit('"onay": False' in (KOK / "bot/nobetci.py").read_text(encoding="utf-8"), True, "nöbetçi onay: false ile başlatır")

# ---- ikinci çift paylaşım kilidi: Instagram'ın kendisine bakar (bot/main.py → instagram_bugun_paylasildi)
import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402
import main as bot  # noqa: E402

BUGUN = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)   # 11:00 TR


def ig(*ogeler):
    """ogeler: (açıklama, Instagram zaman damgası)"""
    def istek(yontem, yol, **kw):
        esit((yontem, yol), ("GET", "me/media"), "ikinci kilit yalnız okur")
        return {"data": [{"id": str(i), "caption": a, "timestamp": z} for i, (a, z) in enumerate(ogeler)]}
    return istek


sabah_ig = ("Gram gümüş fiyatı bugün: 78,92 ₺ (▼ %3,63)\nGüncel gümüş fiyatları · 3 Kasım 2026 Salı 10:48", "2026-11-03T07:49:12+0000")
aksam_dun = ("Gram gümüş fiyatı bugün: 81,89 ₺\nGünün gümüş özeti · 2 Kasım 2026", "2026-11-02T17:12:00+0000")
esit(bot.instagram_bugun_paylasildi({"tur": "reels"}, BUGUN, ig(sabah_ig, aksam_dun)), ("0", "10:49"),
     "ikinci kilit: bugünkü Reels Instagram'da bulunur")
esit(bot.instagram_bugun_paylasildi({"tur": "post"}, BUGUN, ig(sabah_ig, aksam_dun)), None,
     "ikinci kilit: dünkü akşam özeti bugünü kilitlemez")
gece = ("x\nGüncel gümüş fiyatları · 3 Kasım", "2026-11-02T21:30:00+0000")   # 3 Kasım 00:30 TR
esit(bot.instagram_bugun_paylasildi({"tur": "reels"}, BUGUN, ig(gece)), ("0", "00:30"), "ikinci kilit: gün TR saatine göre")
rehber14 = ("Gerçek gümüş nasıl anlaşılır? | Gümüş rehberi #14", "2026-11-03T07:00:00+0000")
esit(bot.instagram_bugun_paylasildi({"tur": "bilgi", "konu": 1}, BUGUN, ig(rehber14)), None, "ikinci kilit: #1 ile #14 karışmaz")
esit(bot.instagram_bugun_paylasildi({"tur": "bilgi", "konu": 14}, BUGUN, ig(rehber14))[0], "0", "ikinci kilit: rehber #14 bulunur")
esit(bot.instagram_bugun_paylasildi({"tur": "hikaye", "konu": 3}, BUGUN, ig(rehber14)), None, "ikinci kilit: hikâye kapsam dışı")
yorum = ("Haftalık gümüş görünümü | Üst düzey yapay zekâ yorumu · 1 Kasım", "2026-11-01T08:01:00+0000")
esit(bot.instagram_bugun_paylasildi({"tur": "yorum"}, datetime(2026, 11, 1, 9, tzinfo=timezone.utc), ig(yorum))[0], "0",
     "ikinci kilit: pazar yorumu bulunur")


def bozuk(*a, **k):
    raise RuntimeError("Instagram API hatası (400)")


def engel(*a, **k):
    raise bot.ErisimEngeli("API access blocked")


with contextlib.redirect_stdout(io.StringIO()):
    esit(bot.instagram_bugun_paylasildi({"tur": "reels"}, BUGUN, bozuk), None,
         "ikinci kilit: Instagram okunamazsa paylaşımı durdurmaz (birinci kilit geçti)")
try:
    bot.instagram_bugun_paylasildi({"tur": "reels"}, BUGUN, engel)
    esit(True, False, "ErisimEngeli yukarı çıkmalı")
except bot.ErisimEngeli:
    esit(True, True, "ikinci kilit: geçici engel yayinla()'ya gider, bekleyip yeniden dener")

# _yayinla: bugünkü Reels Instagram'da varsa hiçbir şey paylaşmaz; o gönderiyi hiçbir çalıştırma saymadığı için 1 sayılır
cagrilar = []


def sahte_istek(yontem, yol, **kw):
    cagrilar.append((yontem, yol))
    if (yontem, yol) == ("GET", "me/media"):
        return {"data": [{"id": "9", "caption": sabah_ig[0],
                          "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")}]}
    raise AssertionError(f"paylaşım isteği gitmemeli: {yontem} {yol}")


asil_istek = bot._istek
bot._istek = sahte_istek
bot._GORUNEN[0] = 0
with tempfile.TemporaryDirectory() as d:
    Path(d, "meta.json").write_text(json.dumps({"tur": "reels", "dosya": "x.mp4", "aciklama": sabah_ig[0]}))
    os.environ.pop("ONAY_TEKRAR", None)
    with contextlib.redirect_stdout(io.StringIO()) as cikti:
        bot.yayinla(Path(d), "https://ornek.invalid/", bekle_dk=0)
    esit(cagrilar, [("GET", "me/media")], "ikinci kilit: _yayinla yalnız okudu, paylaşmadı")
    esit(bot._GORUNEN[0], 1, "ikinci kilit: bulunan gönderi (sayılmamıştı) günlük sınırda 1 sayılır")
    esit("zaten var" in cikti.getvalue(), True, "ikinci kilit: günlükte nedeni yazar")
    # onay: true (ONAY_TEKRAR) ikinci kilidi aşar: Instagram'a bakılmadan paylaşıma geçilir
    cagrilar.clear()
    os.environ["ONAY_TEKRAR"] = "1"
    asil_url = bot._url_hazir_mi

    class Dur(Exception):
        pass

    def dur(*a, **k):
        raise Dur()
    bot._url_hazir_mi = dur
    try:
        bot.yayinla(Path(d), "https://ornek.invalid/", bekle_dk=0)
        esit(True, False, "paylaşıma geçmeliydi")
    except Dur:
        esit(cagrilar, [], "onay: true iken ikinci kilit Instagram'a bakmadan geçer")
    finally:
        bot._url_hazir_mi = asil_url
        os.environ.pop("ONAY_TEKRAR", None)
bot._istek = asil_istek
w = (KOK / ".github/workflows/paylas.yml").read_text(encoding="utf-8")
esit("ONAY_TEKRAR: ${{ github.event_name == 'workflow_dispatch' && inputs.onay && '1' || '' }}" in w, True,
     "iş akışı: ikinci kilidi yalnız elle onay: true aşar")
esit("steps.gorunen.outputs.n != '0'" not in w, True, "iş akışı: 0 sayısı da saklanır (paylaşmayan çalıştırma günü artırmaz)")

# yayinla: Instagram engeli sürerken bir sonraki deneme gece yarısını geçecekse vazgeçer (dünün içeriği yeni günde gitmez)
asil_y, asil_sn, asil_uyku = bot._yayinla, bot.YENIDEN_DENEME_SN, bot.time.sleep
bot._yayinla = lambda *a: (_ for _ in ()).throw(bot.ErisimEngeli("API access blocked"))
bot.YENIDEN_DENEME_SN = 2 * 86400
bot.time.sleep = lambda sn: (_ for _ in ()).throw(AssertionError("beklememeliydi"))
try:
    with contextlib.redirect_stdout(io.StringIO()) as cikti:
        bot.yayinla(Path("."), "https://ornek.invalid/", bekle_dk=5 * 24 * 60)
    esit(True, False, "vazgeçmeliydi")
except bot.ErisimEngeli:
    esit("gece yarısını geçecek" in cikti.getvalue(), True, "yeniden deneme gece yarısını geçmez, kırmızı biter")
finally:
    bot._yayinla, bot.YENIDEN_DENEME_SN, bot.time.sleep = asil_y, asil_sn, asil_uyku

print(f"\ntest_nobetci: {gecen} sınama geçti")
