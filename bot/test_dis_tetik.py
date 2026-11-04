"""Dış tetik (dis-tetik/Kod.gs, Google Apps Script) ile paylas.yml ve hedef saatlerin uyumu. Ağ yok.
Çalıştır: python bot/test_dis_tetik.py

Rıdvan, 4 Kasım 2026 ("A başla. Kontrollü git"): GitHub'ın zamanlayıcısı 3–4 Kasım'da paylaşımları saatlerce
geciktirdi ya da hiç başlatmadı; paylaşımları dışarıdan workflow_dispatch ile başlatan Apps Script eklendi.
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import program  # noqa: E402
import sinir  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
GS = (KOK / "dis-tetik" / "Kod.gs").read_text(encoding="utf-8")
YML = (KOK / ".github" / "workflows" / "paylas.yml").read_text(encoding="utf-8")

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


def dk(hhmm):
    s, d = hhmm.split(":")
    return int(s) * 60 + int(d)


DILIMLER = [
    {"ad": m.group(1), "gunler": [int(x) for x in m.group(2).split(",")], "bas": m.group(3), "son": m.group(4),
     "dilim": m.group(5)}
    for m in re.finditer(r"\{ad: '([^']+)', gunler: \[([\d, ]+)\], bas: '(\d\d:\d\d)', son: '(\d\d:\d\d)', "
                         r"dilim: '([^']+)'\}", GS)
]
esit(len(DILIMLER), 5, "Kod.gs'te 5 dilim okunur")

# paylas.yml'deki asıl (yedek olmayan) cron'lar
ASIL = [m.group(1) for m in re.finditer(r"- cron: '([^']+)'(?![^\n]*yedek)", YML)]
# Kontrol işinin kabul ettiği dilimler (bilinmeyen dilim hata verir)
KABUL = re.search(r'case "\$DILIM" in\n\s*(.+?)\) ;;', YML).group(1)
KABUL = set(re.findall(r'"([^"]+)"', KABUL))
# dilim → tür (paylas.yml kontrol eşlemesi; "10 6 * * 1-5" eşlemede yok, else → reels)
TUR = {"10 6 * * 1-5": "reels", "10 16 * * 1-5": "post", "10 6 * * 6": "hafta", "10 7 * * 0": "yorum",
       "10 10 * * 1-5": "bilgi"}
for c, t in TUR.items():
    if t != "reels":
        esit(f'elif [ "$DILIM" = "{c}" ]; then\n            tur={t}' in YML, True, f"paylas.yml eşlemesi {c} → {t}")

esit({d["dilim"] for d in DILIMLER}, set(ASIL), "her asıl cron'un dış tetiği var, fazlası yok")
esit({d["dilim"] for d in DILIMLER}, KABUL, "kontrol işi dış tetiğin bütün dilimlerini kabul eder")

TR_GUN = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 0: [7], 7: [7]}
for d in DILIMLER:
    dakika, saat, _, _, hg = d["dilim"].split()
    cron_tr = (int(saat) + 3) * 60 + int(dakika)          # UTC+3, Türkiye'de yaz saati yok
    tur = TUR[d["dilim"]]
    hs, hd = program.HEDEF_SAATLERI[tur]
    hedef = hs * 60 + hd
    bas, son = dk(d["bas"]), dk(d["son"])
    ad = d["ad"]
    esit(bas >= cron_tr, True, f"{ad}: pencere cron saatinden sonra başlar (gec_kalmis onu bugünün dilimi sayar)")
    esit(bas - cron_tr <= sinir.ERKEN_TETIK.total_seconds() / 60, True, f"{ad}: erken tetik sınırı içinde")
    esit(son <= hedef - 10, True, f"{ad}: pencere hedeften en az 10 dk önce biter")
    esit(hedef - bas <= 45, True, f"{ad}: bekleme en çok 45 dk (bekleme adımı 50 dk'da kesilir)")
    esit(hedef - bas < program.EN_COK_BEKLEME_SN / 60, True, f"{ad}: bekleme EN_COK_BEKLEME_SN içinde")
    esit(son - bas >= 20, True, f"{ad}: pencerede en az iki 10 dk'lık deneme var")
    cron_gunleri = sorted({g for p in hg.split(",") for g in (
        range(int(p.split("-")[0]), int(p.split("-")[1]) + 1) if "-" in p else [int(p)])})
    esit(sorted(d["gunler"]), sorted(sum((TR_GUN[g] for g in cron_gunleri), [])), f"{ad}: günler cron'la aynı")
    # Pencerenin herhangi bir anında başlayan dış tetik gec_kalmis'e takılmaz (aynı gün, son saatten önce)
    ornek_gun = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8}[d["gunler"][0]]   # Kasım 2026: 2 Kasım pazartesi
    for an in (bas - 5, bas, son - 1):
        simdi = datetime(2026, 11, ornek_gun, an // 60, an % 60, tzinfo=sinir.TR).astimezone(timezone.utc)
        esit(sinir.gec_kalmis(d["dilim"], tur, simdi), None, f"{ad}: {an // 60:02d}:{an % 60:02d} TR'de paylaşır")
    # Ertesi güne kalan dış tetik paylaşmaz
    simdi = datetime(2026, 11, ornek_gun, 0, 30, tzinfo=sinir.TR).astimezone(timezone.utc) + timedelta(days=1)
    esit(sinir.gec_kalmis(d["dilim"], tur, simdi) is not None, True, f"{ad}: ertesi gün 00:30'da paylaşmaz")

# Bekleme adımı dış tetikte de çalışır, dilimli denemede çalışmaz
esit("if: github.event_name == 'schedule' || (inputs.dilim != '' && inputs.deneme == false)" in YML, True,
     "bekleme adımı: zamanlı + dış tetik")
esit("CRON: ${{ github.event.schedule || inputs.dilim }}" in YML, True, "sınır adımı dilimi gec_kalmis'e verir")
esit("DILIM_GIRDI: ${{ inputs.dilim }}" in YML, True, "dilim girdisi betiğe ortam değişkeniyle girer (enjeksiyon yok)")
esit("${{ inputs.dilim }}\"" in YML, False, "dilim girdisi betik metnine doğrudan yazılmaz")
# Dış tetik deneme kapalı ve onaysız başlatır
esit("inputs: {dilim: dilim, deneme: deneme ? 'true' : 'false', onay: 'false'}" in GS, True, "onay hep kapalı")

print(f"test_dis_tetik: {gecen} sınama geçti.")
