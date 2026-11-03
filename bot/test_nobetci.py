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
esit(calistir("12 18 * * 1-5", durumlar=[[SABAH]]), (1, ["post"], 0), "sabah gitti ama akşam gitmedi: akşamı başlatır")
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
esit(calistir("12 12 * * 1-5", durumlar=[[]], gunduz="bilgi"), (1, ["bilgi"], 0), "rehber gitmemiş: başlatır")


class _Yok:
    pass


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
esit(calistir("12 18 * * 1-5", durumlar=[[]], simdi=aksam), (1, ["post"], 0), "akşam özeti 19:00'da hâlâ başlatılır")
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

print(f"\ntest_nobetci: {gecen} sınama geçti")
