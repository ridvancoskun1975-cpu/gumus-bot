"""bot/sinir.py sınamaları (ağ yok). Çalıştır: python bot/test_sinir.py"""
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sinir  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


def is_(ad, durum, sonuc=None, bas=None, bit=None):
    return {"name": ad, "status": durum, "conclusion": sonuc, "started_at": bas, "completed_at": bit}


# 14 Ekim 2026 10:30 TR = 07:30 UTC
SIMDI = datetime(2026, 10, 14, 7, 30, tzinfo=timezone.utc)

calistirmalar = [{"id": i} for i in range(1, 9)]
isler = {
    # dün 22:30 TR paylaşıldı → sayılmaz
    1: [is_("kontrol", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-13T19:30:00Z")],
    # bugün 00:10 TR (13 Ekim 21:10 UTC) paylaşıldı → sayılır (gün TR'ye göre)
    2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:10:00Z")],
    # bugün 04:51 TR rehber hikâyesi → sayılır (bir çalıştırma = bir paylaşım, 5 kare de olsa)
    3: [is_("uret", "completed", "success"), is_("yayinla", "completed", "success", bit="2026-10-14T01:51:28Z")],
    # deneme: yayinla atlandı → sayılmaz
    4: [is_("uret", "completed", "success"), is_("yayinla", "completed", "skipped", bit="2026-10-14T02:00:00Z")],
    # paylaşım hata verdi → sayılmaz
    5: [is_("yayinla", "completed", "failure", bit="2026-10-14T03:00:00Z")],
    # başka çalıştırma şu an paylaşıyor → sayılır
    6: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:00Z")],
    # bu çalıştırma → sayılmaz
    7: [is_("yayinla", "in_progress", bas="2026-10-14T07:29:30Z")],
    # yalnızca kontrol/uret var (onay bekliyor ya da deneme) → sayılmaz
    8: [is_("kontrol", "completed", "success"), is_("onay", "waiting")],
}

say = sinir.paylasim_sayisi(calistirmalar, isler, SIMDI, bu_calistirma=7)
esit([c for c, _, _ in say], [2, 3, 6], "sayılan çalıştırmalar")
esit([d for _, _, d in say], ["paylaşıldı", "paylaşıldı", "sürüyor"], "durumlar")
esit(len(sinir.paylasim_sayisi([], {}, SIMDI, 0)), 0, "boş gün")

# gece yarısı sınırı: 23:59 TR dün, 00:00 TR bugün
gy = {1: [is_("yayinla", "completed", "success", bit="2026-10-13T20:59:59Z")],
      2: [is_("yayinla", "completed", "success", bit="2026-10-13T21:00:00Z")]}
esit([c for c, _, _ in sinir.paylasim_sayisi([{"id": 1}, {"id": 2}], gy, SIMDI, 0)], [2], "gece yarısı")


# kontrol / son: GitHub okuması sahte
def sahte(n):
    def f(simdi=None, **kw):
        return [(i, SIMDI, "paylaşıldı") for i in range(n)]
    return f


def hata(simdi=None, **kw):
    raise sinir.SayilamadiHatasi("bağlantı yok")


def kontrol_ciktisi(sayici, yayin):
    sinir.say = sayici
    with tempfile.TemporaryDirectory() as d:
        os.environ["GITHUB_OUTPUT"] = str(Path(d) / "o")
        os.environ["GITHUB_STEP_SUMMARY"] = str(Path(d) / "s")
        sinir.kontrol(yayin, "bilgi", "3")
        cikti = dict(s.split("=", 1) for s in Path(d, "o").read_text().split())
        ozet = Path(d, "s").read_text() if Path(d, "s").exists() else ""
    return cikti, ozet


asil_say = sinir.say
for n, yayin, beklenen in [(0, True, "false"), (2, True, "false"), (3, True, "true"), (5, True, "true"),
                           (3, False, "false"), (9, False, "false")]:
    c, ozet = kontrol_ciktisi(sahte(n), yayin)
    esit(c["onay"], beklenen, f"kontrol n={n} yayin={yayin}")
    if beklenen == "true":
        esit(f"{n + 1}. paylaşım" in ozet, True, f"özet n={n}")
c, ozet = kontrol_ciktisi(hata, True)
esit(c["onay"], "true", "sayılamazsa onay ister")
c, _ = kontrol_ciktisi(hata, False)
esit(c["onay"], "false", "denemede sayılamazsa da paylaşım yok")

sinir.say = sahte(2)
esit(sinir.son(False), 0, "son: 3. paylaşım geçer")
sinir.say = sahte(3)
esit(sinir.son(False), 1, "son: onaysız 4. paylaşım durur")
esit(sinir.son(True), 0, "son: onaylı 4. paylaşım geçer")
sinir.say = hata
esit(sinir.son(False), 1, "son: sayılamazsa onaysız paylaşılmaz")
sinir.say = asil_say

print(f"Tamam: {gecen} sınama geçti.")
