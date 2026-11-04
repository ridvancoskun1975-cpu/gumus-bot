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
    esit(son <= hedef - 10, True, f"{ad}: pencere hedeften en az 10 dk önce biter")
    esit(hedef - bas <= 45, True, f"{ad}: bekleme en çok 45 dk (bekleme adımı 50 dk'da kesilir)")
    esit(hedef - bas < program.EN_COK_BEKLEME_SN / 60, True, f"{ad}: bekleme EN_COK_BEKLEME_SN içinde")
    esit(son - bas >= 20, True, f"{ad}: pencerede en az iki 10 dk'lık deneme var")
    cron_gunleri = sorted({g for p in hg.split(",") for g in (
        range(int(p.split("-")[0]), int(p.split("-")[1]) + 1) if "-" in p else [int(p)])})
    esit(sorted(d["gunler"]), sorted(sum((TR_GUN[g] for g in cron_gunleri), [])), f"{ad}: günler cron'la aynı")
    # Pencerenin herhangi bir anında başlayan dış tetik gec_kalmis'e takılmaz (aynı gün, son saatten önce)
    ornek_gun = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8}[d["gunler"][0]]   # Kasım 2026: 2 Kasım pazartesi
    for an in (bas, son - 1):
        simdi = datetime(2026, 11, ornek_gun, an // 60, an % 60, tzinfo=sinir.TR).astimezone(timezone.utc)
        esit(sinir.gec_kalmis(d["dilim"], tur, simdi), None, f"{ad}: {an // 60:02d}:{an % 60:02d} TR'de paylaşır")
    # Ertesi güne kalan dış tetik paylaşmaz
    simdi = datetime(2026, 11, ornek_gun, 0, 30, tzinfo=sinir.TR).astimezone(timezone.utc) + timedelta(days=1)
    esit(sinir.gec_kalmis(d["dilim"], tur, simdi) is not None, True, f"{ad}: ertesi gün 00:30'da paylaşmaz")

# Denetim (4 Kasım 2026): 23 saat geciken pazartesi 19:10 çalışması salı 18:20'de gelirse paylaşmaz (erken gider ve
# akşamki asıl özeti kilitlerdi)
gec = datetime(2026, 11, 3, 18, 20, tzinfo=sinir.TR).astimezone(timezone.utc)
esit(sinir.gec_kalmis("10 16 * * 1-5", "post", gec) is not None, True, "23 saat geciken çalışma ertesi gün paylaşmaz")
# Haftalık cron 3 gün geciktiyse de tetik bulunur ve paylaşmaz
esit(sinir.gec_kalmis("10 7 * * 0", "yorum", datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)) is not None, True,
     "pazar cron'u çarşamba gelirse paylaşmaz")
esit("ZAMANLI: ${{ (github.event_name == 'schedule' || (inputs.dilim != '' && inputs.deneme == false))" in YML,
     True, "üretim adımı dış tetiği zamanlı sayar (YORUM_DURAKLAT)")
esit("Bilinmeyen dilim: '$DILIM'" in YML, False, "bilinmeyen dilim günlüğe yazılmaz")
MAIN = (KOK / "bot" / "main.py").read_text(encoding="utf-8")
esit('os.environ.get("ZAMANLI") == "true"' in MAIN, True, "YORUM_DURAKLAT dış tetikte de geçerli")
# Bekleme adımı dış tetikte de çalışır, dilimli denemede çalışmaz
esit("if: github.event_name == 'schedule' || (inputs.dilim != '' && inputs.deneme == false)" in YML, True,
     "bekleme adımı: zamanlı + dış tetik")
esit("CRON: ${{ github.event.schedule || inputs.dilim }}" in YML, True, "sınır adımı dilimi gec_kalmis'e verir")
esit("DILIM_GIRDI: ${{ inputs.dilim }}" in YML, True, "dilim girdisi betiğe ortam değişkeniyle girer (enjeksiyon yok)")
esit("${{ inputs.dilim }}\"" in YML, False, "dilim girdisi betik metnine doğrudan yazılmaz")
# Dış tetik deneme kapalı ve onaysız başlatır; true/false yazı değil (gözden geçirme, 4 Kasım 2026)
esit("{dilim: dilim, deneme: !!deneme, onay: false}" in GS, True, "onay hep kapalı, gerçek true/false")
esit("onay: 'false'}" in GS and "onay: 'true'" not in GS and "onay: true" not in GS, True,
     "422 yedeğinde de onay kapalı; Kod.gs hiçbir yolda onay açmaz")
# Pencere sonu denetimi: yeniden başlatma da hedef saatin en geç 5 dk sonrasına kadar olur (söz verilen saat)
DENETIM_DK = int(re.search(r"var DENETIM_DK = (\d+);", GS).group(1))
for d in DILIMLER:
    hs, hd = program.HEDEF_SAATLERI[TUR[d["dilim"]]]
    esit(dk(d["son"]) + DENETIM_DK <= hs * 60 + hd + 5, True, f"{d['ad']}: denetim hedeften en geç 5 dk sonra biter")
    esit(DENETIM_DK > 10, True, f"{d['ad']}: denetim penceresine en az bir 10 dk'lık tetik düşer")

# Paylaşmayan işler (Rıdvan, 4 Kasım 2026 "yap ekle"): Kod.gs → KAYITLAR, kaydet.yml ve sayfa.yml cron'larıyla aynı
import main as bot  # noqa: E402
KAYITLAR = [m.groupdict() for m in re.finditer(
    r"\{ad: '(?P<ad>[^']+)', is: '(?P<is_>[^']+)', (?:gunler: \[(?P<gunler>[\d, ]+)\]|tarih: '(?P<tarih>[\d-]+)'), "
    r"bas: '(?P<bas>\d\d:\d\d)', son: '(?P<son>\d\d:\d\d)'\}", GS)]
esit(len(KAYITLAR), 5, "Kod.gs'te 5 paylaşmayan iş okunur")
KAYDET = (KOK / ".github" / "workflows" / "kaydet.yml").read_text(encoding="utf-8")
k_cron = re.search(r"- cron: '([^']+)'", KAYDET).group(1)
k_dk, k_saat, _, _, k_gun = k_cron.split()
esit(k_gun, "1-5", "kaydet.yml hafta içi")
k_saatler = sorted(f"{int(h) + 3:02d}:{int(k_dk):02d}" for h in k_saat.split(","))
kayit = [k for k in KAYITLAR if k["is_"] == "kaydet.yml"]
esit(sorted(k["bas"] for k in kayit), k_saatler, "dış tetik kayıt saatleri kaydet.yml cron'uyla aynı (TR)")
for k in kayit:
    esit(k["gunler"].replace(" ", ""), "1,2,3,4,5", f"{k['ad']}: hafta içi")
    esit(dk(k["son"]) - dk(k["bas"]) >= 20, True, f"{k['ad']}: pencerede en az iki 10 dk'lık deneme")
    esit(bot.GUN_ICI_PENCERE[0] <= k["bas"] and dk(k["son"]) + 5 <= dk(bot.GUN_ICI_PENCERE[1]), True,
         f"{k['ad']}: main.GUN_ICI_PENCERE içinde (kayıt atlanmaz)")
    for d in DILIMLER:   # paylaşım penceresiyle çakışmaz (önbellek sırası)
        esit(dk(k["son"]) + 5 <= dk(d["bas"]) or dk(k["bas"]) >= dk(d["son"]) + DENETIM_DK, True,
             f"{k['ad']} ile {d['ad']} penceresi çakışmaz")
# 12:35 ve 16:35 kaydı siteyi de yeniler: kaydet.yml'deki saat aralıkları dış tetik penceresini (+5 dk iş) kapsar
araliklar = [(int(a[:2]) * 60 + int(a[2:]), int(b[:2]) * 60 + int(b[2:])) for a, b in re.findall(
    r'"\$saat" -ge (\d{4}) \] && \[ "\$saat" -le (\d{4})', KAYDET)]
for bas in ("12:35", "16:35"):
    k = next(x for x in kayit if x["bas"] == bas)
    esit(any(a <= dk(k["bas"]) and dk(k["son"]) + 5 <= b for a, b in araliklar), True, f"{bas} kaydı siteyi yeniler")
SAYFA = (KOK / ".github" / "workflows" / "sayfa.yml").read_text(encoding="utf-8")
s_dk, s_saat, s_gun, s_ay, _ = re.search(r"- cron: '([^']+)'", SAYFA).group(1).split()
yil_sonu = datetime(2026, int(s_ay), int(s_gun), int(s_saat), int(s_dk), tzinfo=timezone.utc).astimezone(sinir.TR)
site = next(x for x in KAYITLAR if x["is_"] == "sayfa.yml")
esit((site["tarih"], site["bas"]), (yil_sonu.strftime("%m-%d"), yil_sonu.strftime("%H:%M")),
     "site yenilemesi sayfa.yml cron'uyla aynı an (1 Ocak 00:07 TR)")
esit("workflow_dispatch:" in KAYDET and "workflow_dispatch:" in SAYFA, True, "kaydet.yml ve sayfa.yml dışarıdan başlatılabilir")

# Takılma dökümü (gözden geçirme, 4 Kasım 2026): her adımda süre sınırından tam 1 dk önce
uret_sure = re.search(r"- name: Görseli / videoyu üret\n.*?timeout-minutes: \$\{\{ .*?'yorum' && (\d+) \|\| .*?&& (\d+) \|\| "
                      r"(\d+) \}\}", YML, re.S)
uret_dokum = re.search(r"TAKILMA_DOKUM_SN: \$\{\{ .*?'yorum' && (\d+) \|\| .*?&& (\d+) \|\| (\d+) \}\}", YML)
esit([int(x) * 60 - 60 for x in uret_sure.groups()], [int(x) for x in uret_dokum.groups()],
     "üretim adımı: döküm süre sınırından 1 dk önce (yorum, rehber, diğer)")
paylas_sure = re.search(r"- name: Instagram'a paylaş\n\s+timeout-minutes: (\d+)", YML).group(1)
esit(f"TAKILMA_DOKUM_SN: {int(paylas_sure) * 60 - 60} " in YML, True, "paylaşım adımı: döküm süre sınırından 1 dk önce")
esit("inputs.onay == true && '1'" in YML, True, "ONAY_TEKRAR yalnız gerçek true ile açılır")
import faulthandler  # noqa: E402
import os  # noqa: E402
cagri = []
asil_dokum = faulthandler.dump_traceback_later
faulthandler.dump_traceback_later = lambda sn, **kw: cagri.append((sn, kw.get("exit"), kw.get("repeat")))
try:
    for deger in ("840", "", "bozuk"):
        os.environ["TAKILMA_DOKUM_SN"] = deger
        bot._takilma_dokumu()
finally:
    faulthandler.dump_traceback_later = asil_dokum
    os.environ.pop("TAKILMA_DOKUM_SN", None)
esit(cagri, [(840, False, False)], "takılma dökümü: yalnız süre verilince, çalışmayı durdurmadan")

# Davranış sınaması (Apps Script hizmetleri sahte): node dis-tetik/test_kod.js
import shutil  # noqa: E402
import subprocess  # noqa: E402
if shutil.which("node"):
    r = subprocess.run(["node", str(KOK / "dis-tetik" / "test_kod.js")], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-2000:])
    esit(r.returncode, 0, "Kod.gs davranış sınaması (node dis-tetik/test_kod.js)")
else:
    print("UYARI: node yok; Kod.gs davranış sınaması atlandı (node dis-tetik/test_kod.js).")

print(f"test_dis_tetik: {gecen} sınama geçti.")
