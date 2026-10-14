"""Günlük paylaşım sınırı (14 Ekim 2026, Rıdvan): takipçileri rahatsız etmemek için günde en fazla 3 paylaşım.
4. ve sonrası onaysız gitmez: iş akışı "onay" ortamında bekler, GitHub Rıdvan'a bildirim gönderir; yalnızca
o onaylarsa içerik üretilip paylaşılır, reddederse hiçbir şey paylaşılmaz.

Bir paylaşım = botun Instagram'a bir kez paylaşım yapan çalıştırması (paylas.yml'de "yayinla" işi başarıyla
bitmiş ya da şu an sürüyor): bir Reels, bir gönderi ya da bir seferde giden rehber hikâye kareleri. Gönderiyle
birlikte hikâyeye konan kopyası (günlük özet) ayrıca sayılmaz. Gün Türkiye saatine göre. Sayım GitHub'ın
çalıştırma geçmişinden yapılır (Instagram'a istek atılmaz); Instagram uygulamasından elle yapılan paylaşımlar
sayılmaz.

Kullanım (iş akışında):
  python3 bot/sinir.py kontrol --yayin true|false   # paylaşımdan önce: onay gerekir mi (GITHUB_OUTPUT: onay)
  python3 bot/sinir.py son --onayli true|false      # paylaşım adımından hemen önce: onaysız 4. paylaşımı durdurur
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
TR = ZoneInfo("Europe/Istanbul")
IS_AKISI = "paylas.yml"
YAYIN_ISI = "yayinla"
SURUYOR = {"queued", "in_progress", "waiting", "pending", "requested"}


class SayilamadiHatasi(RuntimeError):
    pass


def _zaman(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


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

def _cikti(**kv):
    yol = os.environ.get("GITHUB_OUTPUT")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def _ozet(metin):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n")


def _liste(sayilan):
    return ", ".join(f"{z.astimezone(TR):%H:%M} ({d})" for _, z, d in sayilan) or "yok"


def kontrol(yayin, tur, konu):
    """Paylaşımdan önce: bugün GUNLUK_SINIR paylaşım olduysa onay ister. Sayılamazsa da onay ister."""
    ne = tur + (f" #{konu}" if konu else "")
    try:
        sayilan = say()
    except SayilamadiHatasi as e:
        if not yayin:
            print(f"::warning::Bugünkü paylaşımlar sayılamadı ({e}). Deneme çalıştırması, paylaşım yok.")
            _cikti(onay="false", sayi="?")
            return
        print(f"::warning::Bugünkü paylaşımlar sayılamadı ({e}); güvenli taraf: paylaşım onayını bekleyecek.")
        _ozet(f"### ⚠️ Onay gerekiyor\nBugünkü paylaşımlar sayılamadı. Bu paylaşım (**{ne}**) "
              "onaylarsan üretilip paylaşılacak; reddedersen hiçbir şey paylaşılmaz.")
        _cikti(onay="true", sayi="?")
        return
    n = len(sayilan)
    print(f"Bugün (TR) {n} paylaşım: {_liste(sayilan)}. Günlük sınır {GUNLUK_SINIR}.")
    if yayin and n >= GUNLUK_SINIR:
        print(f"::warning::Bugün {n} paylaşım yapıldı; bu {n + 1}. olur ({ne}). Paylaşım için onayın bekleniyor.")
        _ozet(f"### ⚠️ Onay gerekiyor: bugünün {n + 1}. paylaşımı\n"
              f"Bugün yapılan paylaşımlar (TR saati): {_liste(sayilan)}.\n\n"
              f"Bu çalıştırma: **{ne}**. Onaylarsan üretilip paylaşılacak; reddedersen hiçbir şey paylaşılmaz.")
        _cikti(onay="true", sayi=n)
    else:
        if not yayin:
            print("Deneme çalıştırması: paylaşım yok, onay gerekmez.")
        _cikti(onay="false", sayi=n)


def son(onayli):
    """Paylaşım adımından hemen önce: aynı anda başlayan iki çalıştırma sınırı birlikte aşmasın."""
    if onayli:
        print("Bu paylaşım onaylandı; günlük sınır denetimi atlandı.")
        return 0
    try:
        sayilan = say()
    except SayilamadiHatasi as e:
        print(f"::error::Bugünkü paylaşımlar sayılamadı ({e}); onaysız paylaşılmadı. "
              "Paylaşmak istersen Run workflow ile yeniden başlat.")
        return 1
    n = len(sayilan)
    if n >= GUNLUK_SINIR:
        print(f"::error::Bugün {n} paylaşım yapılmış ({_liste(sayilan)}); bu {n + 1}. paylaşım onaysız "
              "gönderilmedi. Paylaşmak istersen Run workflow ile yeniden başlat; onayın istenecek.")
        return 1
    print(f"Günlük sınır tamam: bugün {n} paylaşım, bu {n + 1}. olacak.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kontrol")
    k.add_argument("--yayin", choices=["true", "false"], required=True)
    k.add_argument("--tur", default="")
    k.add_argument("--konu", default="")
    s = alt.add_parser("son")
    s.add_argument("--onayli", choices=["true", "false"], required=True)
    a = ap.parse_args()
    if a.komut == "kontrol":
        kontrol(a.yayin == "true", a.tur, a.konu)
        return 0
    return son(a.onayli == "true")


if __name__ == "__main__":
    sys.exit(main())
