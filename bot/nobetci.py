"""Nöbetçi: zamanlı paylaşım gitmediyse başlatır ve haber verir (nobetci.yml).

Rıdvan, 3 Kasım 2026: "Sabah paylaşım olmaması nasıl olur anlamıyorum. Bir daha olmaması için ne yapmamız lazım?",
"Şans eseri öğrendim", "çift paylaşım da olmasın lütfen". O sabah GitHub 09:10'daki zamanlı çalışmayı hiç
başlatmadı (önceki iki haftada her zamanlı çalışma 40–90 dk gecikmeli başlamıştı); GitHub belgeleri zamanlı
çalışmaların yoğunlukta gecikebileceğini, yoğunluk çok yüksekse düşebileceğini yazıyor. Kimse haber vermediği için
Rıdvan rastgele fark etti.

Güvencenin bütünü README → "Zamanlı paylaşım güvencesi" (5 katman). Bu dosyanın payı:
  - Çift paylaşım kilitleri (bot/sinir.py → TEKIL; bot/main.py → instagram_bugun_paylasildi): aynı tür bir günde
    ikinci kez paylaşılmaz; bu yüzden yedek cron'lar (paylas.yml, asıl cron'dan 27 dk sonra) ve nöbetçi güvenlidir.
  - Bu nöbetçi: GitHub'da (nobetci.yml) her paylaşım diliminden ~1 saat sonra, Claude'un zamanlanmış görevinde
    ~20 dk sonra bakar. O dilimin türü bugün paylaşılmadıysa paylas.yml'yi kendisi başlatır (workflow_dispatch,
    deneme kapalı) ve KIRMIZI biter (çıkış 1): GitHub "Run failed" e-postası Rıdvan'a haber olur. Paylaşım
    yerindeyse sessizce biter. Bizim türümüzde bir çalıştırma sürüyorsa en çok BEKLE_DK dakika bekler; türü belli
    olmayan ya da başka bir çalıştırma o sürede bitmezse yine başlatır (sıraya girer, kilit ikinciyi durdurur).
  - Yalnız dilimin penceresinde başlatır: hedef saatten (program.HEDEF_SAATLERI) SON_SAAT'e kadar. Nöbetçi GitHub'da
    saatlerce gecikip ertesi güne kalırsa yeni günün paylaşımını erkenden başlatmaz; dünkü gitmediyse haber verir.

Kullanım: python3 bot/nobetci.py "<cron>"   (nobetci.yml github.event.schedule'ı verir; elle: "reels" gibi tür de olur)
Yalnızca standart kitaplık + botun kendi modülleri; GITHUB_TOKEN (actions: write) ve GITHUB_REPOSITORY gerekir.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import program  # noqa: E402
import sinir  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
# nobetci.yml cron'u → beklenen tür. "gunduz": o gün rehber (bilgi), aylık özet (ay) ya da arşiv Reels'i (kisa);
# üçü de yoksa o gün ~14:00 paylaşımı beklenmez.
DILIMLER = {
    "12 8 * * 1-5": "reels",    # 11:12 TR (sabah Reels'i ~10:00)
    "12 12 * * 1-5": "gunduz",  # 15:12 TR (rehber / aylık özet / arşiv Reels'i ~14:00)
    "12 18 * * 1-5": "post",    # 21:12 TR (akşam özeti ~20:00)
    "12 8 * * 6": "hafta",      # cumartesi 11:12 TR (haftalık özet ~10:00)
    "12 9 * * 0": "yorum",      # pazar 12:12 TR (pazar yorumu ~11:00)
}
# Sürmekte olan çalıştırma için en çok bekleme. Türü üretim (uret) bitene kadar belli olmaz; pazar yorumunun üretimi
# 35 dk'ya kadar sürebildiği için 40 dk. Claude görevi betiği arka planda çalıştırır; nobetci.yml işi 55 dk.
BEKLE_DK = 40
# Nöbetçi de GitHub'ın zamanlayıcısına bağlı, saatlerce gecikebilir. Bu saatten (TR) sonra o dilimin paylaşımını
# başlatmaz (sabah Reels'i akşam özetinin yanında gitmesin), yalnız kırmızı biterek haber verir. Pencere geç kalan
# zamanlı paylaşım çalışmasıyla ortak: bot/sinir.py → SON_SAAT (4 Kasım 2026, gece yarısı kuralı).
SON_SAAT = sinir.SON_SAAT
PAZAR_BEKLET = KOK / "bot" / "PAZAR_BEKLET"


class TakvimHatasi(RuntimeError):
    pass


def _komut(*args):
    s = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=KOK, timeout=60)
    if s.returncode:
        raise TakvimHatasi(f"{' '.join(args)} hata verdi: {(s.stderr or s.stdout).strip()[-300:]}")
    return s.stdout.strip()


def yorum_duraklatildi():
    """main.YORUM_DURAKLAT (zamanlı pazar yorumu duraklatıldı). main.py ağır paketler ister; metinden okunur."""
    return bool(re.search(r"^YORUM_DURAKLAT\s*=\s*True\b", (KOK / "bot" / "main.py").read_text(encoding="utf-8"),
                          re.M))


def gunduz_turu(bolum=None, ay=None, arsiv=None):
    """O günün ~14:00 türü: bilgi / ay / kisa / None. Parametreler sınama için; yoksa botun takviminden okunur
    (paylas.yml "Türü belirle" adımıyla aynı sıra)."""
    bolum = _komut("bot/bilgi.py", "bugun") if bolum is None else bolum
    if bolum:
        return "bilgi"
    ay = _komut("bot/aylik.py", "bugun") if ay is None else ay
    if ay == "ay":
        return "ay"
    arsiv = _komut("bot/bilgi.py", "arsiv") if arsiv is None else arsiv
    return "kisa" if arsiv else None


def beklenen(dilim, **gunduz):
    """Bu dilimde bugün beklenen tür ya da None (beklenen paylaşım yok)."""
    tur = DILIMLER.get(dilim, dilim)   # elle "reels" gibi tür de verilebilir
    if tur == "gunduz":
        tur = gunduz_turu(**gunduz)
    if tur == "yorum" and (PAZAR_BEKLET.exists() or yorum_duraklatildi()):
        return None   # Rıdvan pazar yorumunu bekletiyor ya da duraklattı (yalnız zamanlıda işler); nöbetçi başlatmaz
    return tur if tur in sinir.TEKIL else None


def durum(sayilan, tur):
    """'paylasildi' | 'suruyor' | 'yok' — bugünkü çalıştırmalara göre."""
    if sinir.bugun_paylasildi(sayilan, tur):
        return "paylasildi"
    # Türü henüz belli olmayan (uret başlamamış) ya da aynı türde süren bir çalıştırma varsa bekle
    if any(d == "sürüyor" and t in (None, tur) for _, _, d, t, _ in sayilan):
        return "suruyor"
    return "yok"


def suren_calistirma_var():
    """paylas.yml'nin sırada bekleyen ya da süren bir çalıştırması var mı (türü henüz belli olmasa da)."""
    depo = os.environ["GITHUB_REPOSITORY"]
    for d in ("in_progress", "queued", "waiting", "pending", "requested"):
        v = sinir._github(f"repos/{depo}/actions/workflows/{sinir.IS_AKISI}/runs?status={d}&per_page=5")
        if v.get("total_count") or v.get("workflow_runs"):
            return True
    return False


def gec_mi(tur, simdi):
    s, d = SON_SAAT.get(tur, (23, 59))
    yerel = simdi.astimezone(sinir.TR)
    return (yerel.hour, yerel.minute) >= (s, d)


def erken_mi(tur, simdi):
    """Hedef saatten önce mi (o gün henüz beklenmiyor; gecikip ertesi güne kalan nöbetçi de buraya düşer)."""
    yerel = simdi.astimezone(sinir.TR)
    return (yerel.hour, yerel.minute) < program.HEDEF_SAATLERI.get(tur, (0, 0))


def baslat(tur):
    """paylas.yml'yi bu türle, deneme kapalı başlatır (Rıdvan'ın onay işareti kullanılmaz)."""
    depo = os.environ["GITHUB_REPOSITORY"]
    govde = json.dumps({"ref": "main", "inputs": {"tur": tur, "deneme": False, "onay": False}}).encode()
    istek = urllib.request.Request(
        f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/repos/{depo}/actions/workflows/"
        f"{sinir.IS_AKISI}/dispatches", data=govde, method="POST",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=30) as r:
        return r.status


def _ozet(metin):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n")


def main(dilim, uyu=time.sleep, say=None, baslatici=None, simdi=None, suren=None):
    say = say or sinir.say
    baslatici = baslatici or baslat
    suren = suren or suren_calistirma_var
    # simdi verilirse (sınama) sabit; yoksa her bakışta yeniden okunur (bekleme BEKLE_DK dakika sürebilir)
    saat_al = (lambda: simdi) if simdi else (lambda: datetime.now(timezone.utc))
    try:
        tur = beklenen(dilim)
    except (TakvimHatasi, OSError, subprocess.SubprocessError) as e:
        print(f"::error::Nöbetçi bugünün takvimini okuyamadı ({e}); paylaşım denetlenemedi. "
              "Claude'a 'gumus-bot nöbetçi' yaz.")
        return 1
    if not tur:
        print(f"Bu dilimde ({dilim}) bugün beklenen paylaşım yok; nöbetçi bitti.")
        return 0
    if erken_mi(tur, saat_al()):
        h, d = program.HEDEF_SAATLERI[tur]
        yerel = saat_al().astimezone(sinir.TR)
        if dilim not in DILIMLER:   # elle ya da Claude görevi, hedeften önce: henüz beklenmiyor
            print(f"Saat {yerel:%H:%M} TR, {tur} hedefinden ({h:02d}:{d:02d}) önce: bu dilimde şu an beklenen "
                  "paylaşım yok, nöbetçi başlatmadı.")
            return 0
        # Zamanlı nöbetçi hep hedeften sonra kurulu; hedeften önce çalıştıysa GitHub onu ertesi güne geciktirmiştir.
        # Yeni günün paylaşımını başlatmaz; dünkü paylaşıma bakar, gitmediyse haber verir.
        dun = datetime.combine(yerel.date(), datetime.min.time(), sinir.TR) - timedelta(minutes=1)
        try:
            dunku = sinir.bugun_paylasildi(say(dun), tur)
        except sinir.SayilamadiHatasi as e:
            print(f"::error::Nöbetçi ertesi güne kaldı ({yerel:%H:%M} TR) ve dünkü çalıştırmaları okuyamadı ({e}); "
                  f"dünkü {tur} paylaşıldı mı bilinmiyor. Claude'a 'gumus-bot nöbetçi' yaz.")
            return 1
        if dunku:
            print(f"Nöbetçi ertesi güne kaldı ({yerel:%H:%M} TR); dünkü {tur} paylaşılmış, beklenen paylaşım yok.")
            return 0
        print(f"::error::ZAMANLI PAYLAŞIM GELMEDİ: dünkü {tur} paylaşılmadı. Nöbetçi de GitHub'da ertesi güne "
              f"({yerel:%H:%M} TR) kaldığı için başlatmadı. Claude'a 'gumus-bot nöbetçi' yaz.")
        _ozet(f"### ⛔ Dünkü {tur} paylaşılmadı\nNöbetçi {yerel:%H:%M} TR'de (ertesi gün) baktı; başlatmadı.")
        return 1
    bizim = False
    for deneme in range(BEKLE_DK + 1):
        try:
            sayilan = say(saat_al())
        except sinir.SayilamadiHatasi as e:
            print(f"::error::Nöbetçi bugünkü çalıştırmaları okuyamadı ({e}); {tur} paylaşıldı mı bilinmiyor, "
                  "başlatılmadı. Claude'a 'gumus-bot nöbetçi' yaz.")
            return 1
        d = durum(sayilan, tur)
        bizim = d == "suruyor" and any(x[2] == "sürüyor" and x[3] == tur for x in sayilan)
        if d == "yok":
            try:
                if suren():
                    d = "suruyor"   # türü henüz belli olmayan bir çalıştırma (uret işinde) bizimki olabilir
            except (urllib.error.URLError, OSError, ValueError, KeyError):
                pass
        if d == "paylasildi":
            k = sinir.bugun_paylasildi(sayilan, tur)
            print(f"{tur} bugün {k[1].astimezone(sinir.TR):%H:%M} TR'de paylaşılmış; nöbetçi sessizce bitti.")
            return 0
        if d != "suruyor":
            break
        if deneme < BEKLE_DK:
            print(f"Bir çalıştırma sürüyor; {tur} için bekleniyor ({deneme + 1}/{BEKLE_DK} dk).")
            uyu(60)
    else:
        if bizim:
            print(f"::warning::{BEKLE_DK} dk geçti, {tur} çalıştırması hâlâ sürüyor; paylaşım ondan bekleniyor, "
                  "nöbetçi başlatmadı.")
            return 0
        # Süren çalıştırmanın türü belli değil ya da başka bir tür: yine başlat. Yeni çalıştırma sıraya girer;
        # süren bizimkiyse kilit ikincisini paylaşmadan bitirir.
        print(f"{BEKLE_DK} dk geçti, süren çalıştırmanın türü {tur} değil ya da belli değil; nöbetçi yine başlatıyor.")
    simdi = saat_al()
    saat = simdi.astimezone(sinir.TR).strftime("%H:%M")
    if gec_mi(tur, simdi):
        print(f"::error::ZAMANLI PAYLAŞIM GELMEDİ: {tur} bugün {saat} TR'ye kadar paylaşılmadı. Saat geç olduğu için "
              "nöbetçi başlatmadı (nöbetçinin kendisi de gecikti). Claude'a 'gumus-bot nöbetçi' yaz.")
        _ozet(f"### ⛔ {tur} bugün paylaşılmadı\nNöbetçi {saat} TR'de baktı; saat geç olduğu için başlatmadı.")
        return 1
    try:
        baslatici(tur)
    except (urllib.error.URLError, OSError, KeyError) as e:
        print(f"::error::ZAMANLI PAYLAŞIM GELMEDİ: {tur} bugün paylaşılmadı ve nöbetçi başlatamadı ({e}). "
              "Claude'a 'gumus-bot nöbetçi' yaz; elle başlatılması gerekiyor.")
        _ozet(f"### ⛔ {tur} paylaşılmadı, nöbetçi de başlatamadı\n{e}")
        return 1
    print(f"::error::ZAMANLI PAYLAŞIM GELMEDİ: {tur} bugün {saat} TR'ye kadar paylaşılmamıştı (GitHub zamanlı "
          "çalışmayı başlatmadı). Nöbetçi paylaşımı şimdi başlattı; birkaç dakika içinde gider. Bu kırmızı iş yalnızca "
          "haber içindir, yapılacak bir şey yok. Bir sonraki çalıştırma: Actions → Gümüş paylaşımı.")
    _ozet(f"### ⚠️ Zamanlı paylaşım gelmedi: **{tur}**\nNöbetçi {saat} TR'de paylaşımı başlattı. Bu kırmızı iş haber içindir.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "reels"))
