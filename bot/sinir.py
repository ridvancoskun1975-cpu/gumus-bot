"""Günlük paylaşım sınırı (14 Ekim 2026, Rıdvan): takipçileri rahatsız etmemek için günde en fazla 3 paylaşım.
4. ve sonrası Rıdvan onaylamadan gitmez.

Bir paylaşım = botun Instagram'a bir kez paylaşım yapan çalıştırması (paylas.yml'de "yayinla" işi başarıyla
bitmiş ya da şu an sürüyor): bir Reels, bir gönderi ya da bir seferde giden rehber hikâye kareleri. Gönderiyle
birlikte hikâyeye konan kopyası (günlük özet) ayrıca sayılmaz. Gün Türkiye saatine göre. Sayım GitHub'ın
çalıştırma geçmişinden yapılır (Instagram'a istek atılmaz); Instagram uygulamasından elle yapılan paylaşımlar
sayılmaz.

Sınır doluysa ve onay yoksa kontrol işi hata verip durur: hiçbir şey üretilmez ve paylaşılmaz, GitHub
"Run failed" e-postası gönderir. Onay yalnızca Claude sohbetinden verilir (Rıdvan GitHub'a girmez):
  - tek paylaşım için: Rıdvan "onayla" der, Claude aynı türü Run workflow → onay: true ile yeniden başlatır;
  - bir günün tamamı için: Rıdvan izin verirse Claude GUN_SINIRI'na o günü yazar (aşağıda).
Claude onay işaretini ya da GUN_SINIRI'nı Rıdvan sohbette açıkça onaylamadan KULLANMAZ.

Kullanım (iş akışında): python3 bot/sinir.py --yayin true|false --onay true|false [--tur T] [--konu N]
Yalnızca standart kitaplık kullanır (kontrol işi Python paketi kurmadan çalışır).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

GUNLUK_SINIR = 3
# Rıdvan'ın sohbette onayladığı gün istisnaları: {"YYYY-AA-GG" (TR): o gün izin verilen toplam paylaşım}.
GUN_SINIRI = {
    # 14 Ekim 2026 06:10: gece 2 rehber hikâyesi gitti; 13:50 Rehber #3 ve 19:50 akşam özetine (4. ve 5.) onay verdi.
    "2026-10-14": 5,
}
TR = ZoneInfo("Europe/Istanbul")
IS_AKISI = "paylas.yml"
YAYIN_ISI = "yayinla"
SURUYOR = {"queued", "in_progress", "waiting", "pending", "requested"}


class SayilamadiHatasi(RuntimeError):
    pass


def _zaman(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def bugunun_siniri(gun):
    return GUN_SINIRI.get(gun.isoformat(), GUNLUK_SINIR)


def paylasim_sayisi(calistirmalar, isler, simdi, bu_calistirma):
    """Bugün (TR) bot kaç paylaşım yaptı ya da yapmak üzere.
    calistirmalar: [{"id": ...}], isler: {calistirma_id: [iş sözlükleri]} (GitHub API biçimi).
    Döner: [(calistirma_id, zaman, durum)] sayılan paylaşımlar, zamana göre sıralı."""
    bugun = simdi.astimezone(TR).date()
    sayilan = []
    for c in calistirmalar:
        if c["id"] == bu_calistirma:
            continue
        for i in isler.get(c["id"], []):
            if i.get("name") != YAYIN_ISI:
                continue
            if i.get("status") in SURUYOR:
                zaman = _zaman(i.get("started_at")) or simdi
                sayilan.append((c["id"], zaman, "sürüyor"))
            elif i.get("status") == "completed" and i.get("conclusion") == "success":
                zaman = _zaman(i.get("completed_at"))
                if zaman and zaman.astimezone(TR).date() == bugun:
                    sayilan.append((c["id"], zaman, "paylaşıldı"))
    return sorted(sayilan, key=lambda x: x[1])


# ---------------------------------------------------------------- GitHub

def _github(yol):
    istek = urllib.request.Request(
        f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/{yol}",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(istek, timeout=30) as r:
        return json.load(r)


def _veriyi_al(simdi):
    depo = os.environ["GITHUB_REPOSITORY"]
    # Dünün TR gece yarısından beri başlayanlar: gece yarısından önce başlayıp sonra paylaşan da yakalanır.
    bas = (datetime.combine(simdi.astimezone(TR).date() - timedelta(days=1), datetime.min.time(), TR)
           .astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    calistirmalar, sayfa = [], 1
    while True:
        v = _github(f"repos/{depo}/actions/workflows/{IS_AKISI}/runs?created=%3E%3D{bas}&per_page=100&page={sayfa}")
        calistirmalar += v.get("workflow_runs", [])
        if len(v.get("workflow_runs", [])) < 100:
            break
        sayfa += 1
    isler = {}
    for c in calistirmalar:
        isler[c["id"]] = _github(f"repos/{depo}/actions/runs/{c['id']}/jobs?per_page=100").get("jobs", [])
    return calistirmalar, isler


def say(simdi=None, deneme_sayisi=3, ara_sn=20):
    simdi = simdi or datetime.now(timezone.utc)
    bu = int(os.environ.get("GITHUB_RUN_ID", "0"))
    son_hata = None
    for d in range(deneme_sayisi):
        try:
            calistirmalar, isler = _veriyi_al(simdi)
            return paylasim_sayisi(calistirmalar, isler, simdi, bu)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            son_hata = e
            if d + 1 < deneme_sayisi:
                time.sleep(ara_sn)
    raise SayilamadiHatasi(f"GitHub çalıştırma geçmişi okunamadı: {son_hata}")


# ---------------------------------------------------------------- iş akışı

def _ozet(metin):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n")


def _liste(sayilan):
    return ", ".join(f"{z.astimezone(TR):%H:%M} ({d})" for _, z, d in sayilan) or "yok"


def kontrol(yayin, onay, tur, konu, simdi=None):
    """0: devam, 1: dur (paylaşılmaz). Sınır doluysa onay olmadan durur; sayılamazsa da durur."""
    simdi = simdi or datetime.now(timezone.utc)
    ne = tur + (f" #{konu}" if konu else "")
    sinir = bugunun_siniri(simdi.astimezone(TR).date())
    try:
        sayilan = say(simdi)
    except SayilamadiHatasi as e:
        if not yayin or onay:
            print(f"::warning::Bugünkü paylaşımlar sayılamadı ({e}); "
                  + ("deneme çalıştırması, paylaşım yok." if not yayin else "onaylı paylaşım, devam."))
            return 0
        print(f"::error::Bugünkü paylaşımlar sayılamadı ({e}). Güvenli taraf: {ne} onaysız paylaşılmadı. "
              "Paylaşılsın istersen Claude'a 'onayla' de.")
        _ozet(f"### ⛔ Paylaşılmadı: {ne}\nBugünkü paylaşımlar sayılamadı. Paylaşılsın istersen Claude'a "
              "**onayla** de.")
        return 1
    n = len(sayilan)
    print(f"Bugün (TR) {n} paylaşım: {_liste(sayilan)}. Günlük sınır {sinir}.")
    if not yayin:
        print("Deneme çalıştırması: paylaşım yok, sınır uygulanmaz.")
        return 0
    if n < sinir:
        print(f"Sınır tamam: bu, bugünün {n + 1}. paylaşımı.")
        return 0
    if onay:
        print(f"Bu, bugünün {n + 1}. paylaşımı; Rıdvan onayladı, devam.")
        _ozet(f"Bugünün {n + 1}. paylaşımı (**{ne}**), Rıdvan'ın onayıyla.")
        return 0
    print(f"::error::Günlük sınır: bugün {n} paylaşım yapıldı ({_liste(sayilan)}). Bu {n + 1}. paylaşım "
          f"({ne}) onayın olmadan paylaşılmadı. Paylaşılsın istersen Claude'a 'onayla' de.")
    _ozet(f"### ⛔ Paylaşılmadı: bugünün {n + 1}. paylaşımı olacaktı\n"
          f"Bugün yapılan paylaşımlar (TR saati): {_liste(sayilan)}.\n\n"
          f"Bu çalıştırma: **{ne}**. Hiçbir şey üretilmedi, paylaşılmadı. "
          "Paylaşılsın istersen Claude'a **onayla** de.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yayin", choices=["true", "false"], required=True)
    ap.add_argument("--onay", choices=["true", "false"], default="false")
    ap.add_argument("--tur", default="")
    ap.add_argument("--konu", default="")
    a = ap.parse_args()
    return kontrol(a.yayin == "true", a.onay == "true", a.tur, a.konu)


if __name__ == "__main__":
    sys.exit(main())
