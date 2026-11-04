"""Günlük paylaşım sınırı (Rıdvan): takipçileri rahatsız etmemek için günde en fazla 4 (14 Ekim 2026 21:23; önce 3).
5. ve sonrası Rıdvan onaylamadan gitmez.

NE SAYILIR (Rıdvan, 19 Ekim 2026: "takipçiler bizden gelecek, bizle ilgili görecekleri post, bildirim, reels,
hikâye sayısından bahsediyorum"): takipçinin bizden gördüğü her şey ayrı ayrı sayılır — akış gönderisi, Reels ve
hikâye. Akşam özetinin hikâye kopyası, rehber hikâye videosu ve pazar yorumunun Reels'i de birer tanedir (önceden
bir çalıştırma = bir paylaşım sayılıyordu, hikâye kopyaları sayılmıyordu).

Bir çalıştırmanın gerçek sayısı: yayinla işi paylaştığı her şeyi sayar (bot/main.py → _GORUNEN) ve iş akışı bunu
"gorunen-<deneme>-<sayı>" adlı küçük bir eser olarak saklar. Eseri olmayan (19 Ekim 2026'dan önceki ya da sayıyı
yazamadan biten) çalıştırmalar türüne göre tahmin edilir (TAHMIN; tür "onizleme-<tür>" eserinden okunur).

HİKÂYE ÖNCE DÜŞER (Rıdvan, 19 Ekim 2026 "uygun"): bir çalıştırmanın tamamı günü 4'ün üstüne çıkaracaksa ama hikâye
kopyası olmadan sığıyorsa, çalıştırma hikâyesiz paylaşır (kontrol işinin "hikaye=yok" çıktısı → yayinla'da HIKAYE).
Hikâye kopyası takipçinin akışta zaten gördüğü videodur. Pratikte rehber gününün ve aylık özet gününün akşam
özeti hikâyesiz gider. Hikâyesiz de sığmıyorsa çalıştırma durur ve Rıdvan'ın onayını bekler.

Gün Türkiye saatine göre. Sayım GitHub'ın çalıştırma geçmişinden yapılır (Instagram'a istek atılmaz); Instagram
uygulamasından elle yapılan paylaşımlar sayılmaz.

Sınır doluysa ve onay yoksa kontrol işi hata verip durur: hiçbir şey üretilmez ve paylaşılmaz, GitHub
"Run failed" e-postası gönderir. Onay yalnızca Claude sohbetinden verilir (Rıdvan GitHub'a girmez):
  - tek paylaşım için: Rıdvan "onayla" der, Claude aynı türü Run workflow → onay: true ile yeniden başlatır
    (onaylı çalıştırma hikâyesiyle birlikte tam gider);
  - bir günün tamamı için: Rıdvan izin verirse Claude GUN_SINIRI'na o günü yazar (aşağıda).
Claude onay işaretini ya da GUN_SINIRI'nı Rıdvan sohbette açıkça onaylamadan KULLANMAZ.

ÇİFT PAYLAŞIM KİLİDİ (Rıdvan, 3 Kasım 2026: "çift paylaşım da olmasın lütfen"): GitHub'ın zamanlı çalışmayı
geç başlatması ya da hiç başlatmaması (3 Kasım 2026 sabah Reels'i hiç başlamadı; önceki günler 40–90 dk gecikme)
yüzünden aynı tür bir günde birden çok kez tetiklenebilir: asıl cron, yedek cron (paylas.yml), nöbetçi (nobetci.yml)
ve elle başlatma. Bu tür (TEKIL) bugün zaten paylaşıldıysa çalıştırma paylaşmadan, HATA VERMEDEN biter
(kontrol çıktısı tekrar=evet → uret ve yayinla atlanır). Yalnız onay=true (Rıdvan sohbette açıkça istedi) kilidi aşar;
pazar Reels'ini yeniden gönderme (tür yorum, konu reels-tekrar) kilide takılmaz.
Paylaşılmış sayılan: bugün yayinla işi başarıyla bitmiş ya da bir şey paylaşıp hata vermiş ("yarım") aynı tür.
Sürmekte olan çalıştırma sayılmaz: concurrency grubu yüzünden aynı anda tek çalıştırma yürür, sürüyor görünen
bizden sonra sıradadır; o kendi sırası gelince bu kilide takılır.

GECE YARISI KURALI (4 Kasım 2026): GitHub 3 Kasım 19:10 TR zamanlı çalışmasını 5,5 saat geç, 4 Kasım 00:43'te
başlattı; gün değiştiği için kilit onu "4 Kasım'ın akşam özeti" saydı ve 00:44'te ikinci bir özet (gönderi + hikâye)
gitti (Rıdvan 3 Kasım'da "çift paylaşım da olmasın lütfen" demişti). İki önlem:
  - Geç kalan zamanlı çalışma (gec_kalmis): cron'un asıl tetik anı (son_tetik) başka bir TR gününe aitse ya da o türün
    son saati (SON_SAAT; nöbetçiyle aynı pencere) geçtiyse zamanlı çalışma paylaşmadan, hata vermeden biter
    (tekrar=evet). Elle ve nöbetçinin başlattığı çalışmalar (workflow_dispatch) etkilenmez. Paylaşım gitmediyse
    nöbetçi haber verir.
  - Kilit, gece 00:00–05:00 (GECE_SONU) arasında giden paylaşımı o günün paylaşımı saymaz: o, bir önceki günün
    gecikmiş işidir ve günün asıl paylaşımını durdurmamalı. Günlük sınır sayımı yine sayar (takipçi onu gördü).

Kullanım (iş akışında): python3 bot/sinir.py --yayin true|false --onay true|false [--tur T] [--konu N] [--cron C]
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

GUNLUK_SINIR = 4
# Rıdvan'ın sohbette onayladığı gün istisnaları: {"YYYY-AA-GG" (TR): o gün izin verilen toplam (görünen içerik)}.
GUN_SINIRI = {
    # 14 Ekim 2026 06:10: gece 2 rehber hikâyesi gitti; 13:50 Rehber #3 ve 19:50 akşam özetine (4. ve 5.) onay verdi.
    # (O günün sayısı eski ölçüyle, çalıştırma başınaydı.)
    "2026-10-14": 5,
}
# Bir çalıştırmanın takipçiye gösterdiği içerik sayısı (gerçek sayı eserde yoksa ve bu çalıştırma için):
# reels sabah Reels'i (hikâyesiz); post akşam özeti + hikâyesi; hafta / ay özet + hikâyesi; yorum kaydırmalı +
# Reels (25 Ekim 2026'dan beri hikâyesiz; main.PAZAR_HIKAYE); bilgi rehber Reels'i + müzikli rehber hikâye videosu (60 sn'yi aşan bölümde 2 video olabilir);
# kisa rehber arşivi Reels'i; kart; yasal kaydırmalı; hikaye elle rehber hikâyesi.
TAHMIN = {"reels": 1, "post": 2, "hafta": 2, "ay": 2, "yorum": 2, "bilgi": 2, "kisa": 1, "kart": 1, "yasal": 1,
          "hikaye": 1, "tanitim": 1}   # tanitim: bilgi sayfasının bir kezlik tanıtım Reels'i (hikâyesiz)
# Günde bir kez giden türler (çift paylaşım kilidi). hikaye (elle, bölüm no ile) ve tanitim kapsam dışı.
TEKIL = {"reels", "post", "hafta", "ay", "yorum", "bilgi", "kisa", "kart", "yasal"}
# Hikâye kopyası düşerse kalan sayı (yalnız bu türlerde hikâye bir kopyadır ve bırakılabilir)
HIKAYESIZ = {"post": 1, "hafta": 1, "ay": 1, "bilgi": 1}   # yorum: 25 Ekim 2026'dan beri hikâyesiz (2)
TR = ZoneInfo("Europe/Istanbul")
IS_AKISI = "paylas.yml"
YAYIN_ISI = "yayinla"
SURUYOR = {"queued", "in_progress", "waiting", "pending", "requested"}
# Kilit bu saatten (TR) önce giden paylaşımı o günün paylaşımı saymaz (gece yarısı kuralı, yukarıda).
GECE_SONU = (5, 0)
# Bir türün o gün başlatılabileceği son saat (TR). Zamanlı çalışma (gec_kalmis) ve nöbetçi (bot/nobetci.py) aynı
# pencereyi kullanır: sabah Reels'i akşam özetinin yanında gitmesin; akşam özeti 22:30 (paylaşım işi Instagram
# engelinde ~3 saate kadar yeniden dener, gece yarısını geçmesin; geçerse main.yayinla durur).
SON_SAAT = {"reels": (18, 30), "bilgi": (18, 30), "ay": (18, 30), "kisa": (18, 30), "post": (22, 30),
            "hafta": (21, 0), "yorum": (21, 0)}


class SayilamadiHatasi(RuntimeError):
    pass


def _zaman(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def bugunun_siniri(gun):
    return GUN_SINIRI.get(gun.isoformat(), GUNLUK_SINIR)


def _eserden(adlar):
    """(gerçek görünen sayı ya da None, tür ya da None) — çalıştırmanın eser adlarından."""
    gorunen, tur = None, None
    for a in adlar:
        if a.startswith("gorunen-"):
            try:
                gorunen = (gorunen or 0) + int(a.rsplit("-", 1)[1])
            except ValueError:
                pass
        elif a.startswith("onizleme-"):
            tur = a[len("onizleme-"):]
    return gorunen, tur


def paylasim_sayisi(calistirmalar, isler, simdi, bu_calistirma, eserler=None):
    """Bugün (TR) bot takipçiye kaç içerik gösterdi ya da göstermek üzere.
    calistirmalar: [{"id": ...}], isler: {calistirma_id: [iş sözlükleri]} (GitHub API biçimi),
    eserler: {calistirma_id: [eser adları]}.
    Döner: [(calistirma_id, zaman, durum, tür, sayı)], zamana göre sıralı. durum: "paylaşıldı", "sürüyor" ya da
    "yarım" (paylaşım işi hata verdi ama bir şey paylaştı)."""
    eserler = eserler or {}
    bugun = simdi.astimezone(TR).date()
    sayilan = []
    for c in calistirmalar:
        if c["id"] == bu_calistirma:
            continue
        gercek, tur = _eserden(eserler.get(c["id"], []))
        for i in isler.get(c["id"], []):
            if i.get("name") != YAYIN_ISI:
                continue
            if i.get("status") in SURUYOR:
                zaman = _zaman(i.get("started_at")) or simdi
                sayilan.append((c["id"], zaman, "sürüyor", tur, gercek or TAHMIN.get(tur, 2)))
            elif i.get("status") == "completed":
                zaman = _zaman(i.get("completed_at"))
                if not zaman or zaman.astimezone(TR).date() != bugun:
                    continue
                if i.get("conclusion") == "success":
                    # gerçek sayı 0 olabilir (ikinci kilit paylaşmadan bitirdi: tür zaten paylaşılmış, gün artmaz)
                    sayilan.append((c["id"], zaman, "paylaşıldı", tur,
                                    gercek if gercek is not None else TAHMIN.get(tur, 2)))
                elif gercek:
                    sayilan.append((c["id"], zaman, "yarım", tur, gercek))
    return sorted(sayilan, key=lambda x: x[1])


def toplam(sayilan):
    return sum(x[4] for x in sayilan)


def bugun_paylasildi(sayilan, tur):
    """Bu tür bugün paylaşıldıysa o kayıt (calistirma_id, zaman, durum, tür, sayı), yoksa None.
    Yalnız bitmiş çalıştırmalar ("paylaşıldı" ya da "yarım"); sürenler sayılmaz (sıradakiler)."""
    for kayit in sayilan:
        if kayit[3] == tur and kayit[2] in ("paylaşıldı", "yarım") and not gece_mi(kayit[1]):
            return kayit
    return None


def gece_mi(zaman):
    """00:00–05:00 TR arası mı (gece yarısı kuralı: bu saatte giden paylaşım bir önceki günün gecikmiş işidir)."""
    yerel = zaman.astimezone(TR)
    return (yerel.hour, yerel.minute) < GECE_SONU


# ---------------------------------------------------------------- geç kalan zamanlı çalışma

def _alan(metin, en_az, en_cok):
    """Cron alanı → izin verilen değerler kümesi ('*', 'n', 'a-b', 'a,b', '*/k', 'a-b/k')."""
    degerler = set()
    for parca in metin.split(","):
        adim = 1
        if "/" in parca:
            parca, a = parca.split("/", 1)
            adim = int(a)
        if parca == "*":
            bas, son = en_az, en_cok
        elif "-" in parca:
            bas, son = (int(x) for x in parca.split("-", 1))
        else:
            bas = son = int(parca)
        degerler.update(range(bas, son + 1, adim))
    return degerler


def son_tetik(cron, simdi, geri_saat=72):
    """cron'un (UTC, GitHub gibi) simdi'den önceki ya da ona eşit son tetik anı; bulunamaz ya da okunamazsa None."""
    try:
        dk, sa, gun, ay, hg = cron.split()
        dakikalar, saatler = _alan(dk, 0, 59), _alan(sa, 0, 23)
        gunler, aylar = _alan(gun, 1, 31), _alan(ay, 1, 12)
        haftagunleri = {g % 7 for g in _alan(hg, 0, 7)}   # 0 ve 7 pazar
    except ValueError:
        return None
    gun_serbest, hg_serbest = gun == "*", hg == "*"
    t = simdi.astimezone(timezone.utc).replace(second=0, microsecond=0)
    for _ in range(geri_saat * 60 + 1):
        if t.minute in dakikalar and t.hour in saatler and t.month in aylar:
            g_ok, h_ok = t.day in gunler, (t.isoweekday() % 7) in haftagunleri
            # Cron kuralı: gün ve haftagünü ikisi de kısıtlıysa biri yeter
            if (g_ok and h_ok) if (gun_serbest or hg_serbest) else (g_ok or h_ok):
                return t
        t -= timedelta(minutes=1)
    return None


def gec_kalmis(cron, tur, simdi):
    """Zamanlı çalışma paylaşmamalı mı: neden metni ya da None. cron boşsa (elle/nöbetçi) ya da okunamazsa None."""
    if not cron:
        return None
    tetik = son_tetik(cron, simdi)
    if tetik is None:
        return None
    yerel, asil = simdi.astimezone(TR), tetik.astimezone(TR)
    gecikme = int((simdi - tetik).total_seconds() // 60)
    if asil.date() != yerel.date():
        return (f"{asil:%d.%m %H:%M} TR zamanlı çalışması {gecikme // 60} sa {gecikme % 60} dk geç başladı "
                f"(ertesi gün, {yerel:%H:%M}); gece yarısı kuralı")
    s, d = SON_SAAT.get(tur, (23, 59))
    if (yerel.hour, yerel.minute) >= (s, d):
        return (f"{asil:%H:%M} TR zamanlı çalışması {gecikme // 60} sa {gecikme % 60} dk geç başladı "
                f"({yerel:%H:%M}); {tur} için son saat {s:02d}:{d:02d}")
    return None


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
    isler, eserler = {}, {}
    for c in calistirmalar:
        isler[c["id"]] = _github(f"repos/{depo}/actions/runs/{c['id']}/jobs?per_page=100").get("jobs", [])
        # Eserler yalnızca paylaşım işi gerçekten çalışmış (atlanmamış) çalıştırmalar için okunur
        if any(i.get("name") == YAYIN_ISI and i.get("conclusion") != "skipped" for i in isler[c["id"]]):
            eserler[c["id"]] = [a["name"] for a in _github(
                f"repos/{depo}/actions/runs/{c['id']}/artifacts?per_page=100").get("artifacts", [])]
    return calistirmalar, isler, eserler


def say(simdi=None, deneme_sayisi=3, ara_sn=20):
    simdi = simdi or datetime.now(timezone.utc)
    bu = int(os.environ.get("GITHUB_RUN_ID", "0"))
    son_hata = None
    for d in range(deneme_sayisi):
        try:
            calistirmalar, isler, eserler = _veriyi_al(simdi)
            return paylasim_sayisi(calistirmalar, isler, simdi, bu, eserler)
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
    return ", ".join(f"{z.astimezone(TR):%H:%M} {t or '?'} {n} ({d})" for _, z, d, t, n in sayilan) or "yok"


def _cikti(hikaye, tekrar="hayir"):
    """kontrol işinin çıktısı: hikaye=tam ya da yok (yayinla işi buna göre hikâye kopyasını paylaşır);
    tekrar=evet ise bu tür bugün zaten paylaşılmıştır, uret ve yayinla atlanır (çift paylaşım kilidi)."""
    yol = os.environ.get("GITHUB_OUTPUT")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(f"hikaye={hikaye}\ntekrar={tekrar}\n")


def kontrol(yayin, onay, tur, konu, simdi=None, cron=""):
    """0: devam, 1: dur (paylaşılmaz). Sınır doluysa önce hikâye kopyası düşer; o da yetmezse onay olmadan durur;
    sayılamazsa da durur. GITHUB_OUTPUT'a hikaye=tam|yok yazar."""
    simdi = simdi or datetime.now(timezone.utc)
    ne = tur + (f" #{konu}" if konu else "")
    sinir = bugunun_siniri(simdi.astimezone(TR).date())
    plan = TAHMIN.get(tur, 1)
    # Pazar Reels'ini yeniden gönderme (main.pazar_reels_tekrar; elle, tür: yorum, konu: reels-tekrar): o gün yorum
    # zaten paylaşılmıştır, yalnız gitmeyen Reels gider. Kilit bunu durdurmaz; sayısı 1.
    reels_tekrar = tur == "yorum" and konu == "reels-tekrar"
    if reels_tekrar:
        plan = 1
    # Geç kalan zamanlı çalışma (gece yarısı kuralı): onay işareti zamanlı çalışmada yoktur; deneme etkilenmez.
    gec = gec_kalmis(cron, tur, simdi) if yayin else None
    if gec:
        print(f"::notice::Geç kalan zamanlı çalışma: {gec}. {ne} paylaşılmadan bitiyor; bu bir hata değil. "
              "Paylaşım o gün gitmediyse nöbetçi haber verir.")
        _ozet(f"Geç kalan zamanlı çalışma: {gec}. **{ne}** paylaşılmadı.")
        _cikti("tam", "evet")
        return 0
    try:
        sayilan = say(simdi)
    except SayilamadiHatasi as e:
        if not yayin or onay:
            print(f"::warning::Bugünkü paylaşımlar sayılamadı ({e}); "
                  + ("deneme çalıştırması, paylaşım yok." if not yayin else "onaylı paylaşım, devam."))
            _cikti("tam")
            return 0
        print(f"::error::Bugünkü paylaşımlar sayılamadı ({e}). Güvenli taraf: {ne} onaysız paylaşılmadı. "
              "Paylaşılsın istersen Claude'a 'onayla' de.")
        _ozet(f"### ⛔ Paylaşılmadı: {ne}\nBugünkü paylaşımlar sayılamadı. Paylaşılsın istersen Claude'a "
              "**onayla** de.")
        _cikti("tam")
        return 1
    n = toplam(sayilan)
    print(f"Bugün (TR) takipçinin gördüğü içerik: {n} ({_liste(sayilan)}). Günlük sınır {sinir} "
          "(akış + Reels + hikâye birlikte).")
    onceki = bugun_paylasildi(sayilan, tur) if tur in TEKIL and not reels_tekrar else None
    if onceki and yayin and not onay:
        saat = onceki[1].astimezone(TR).strftime("%H:%M")
        print(f"::notice::Çift paylaşım kilidi: {ne} bugün {saat} TR'de zaten paylaşıldı (çalıştırma {onceki[0]}). "
              "Bu çalıştırma paylaşmadan bitiyor; bu bir hata değil. Yeniden paylaşılması gerçekten isteniyorsa "
              "Run workflow → onay: true (yalnız Rıdvan sohbette açıkça isterse).")
        _ozet(f"Çift paylaşım kilidi: **{ne}** bugün {saat} TR'de zaten paylaşıldı; bu çalıştırma paylaşmadı.")
        _cikti("tam", "evet")
        return 0
    if onceki and yayin and onay:
        print(f"Dikkat: {ne} bugün {onceki[1].astimezone(TR):%H:%M} TR'de zaten paylaşılmıştı; onay verildiği için "
              "ikinci kez paylaşılacak.")
    if not yayin:
        print(f"Deneme çalıştırması: paylaşım yok, sınır uygulanmaz (bu tür tam giderse {plan} içerik).")
        _cikti("tam")
        return 0
    if n + plan <= sinir:
        print(f"Sınır tamam: bu çalıştırma {plan} içerik gösterecek, gün {n + plan} olacak.")
        _cikti("tam")
        return 0
    if onay:
        print(f"Bu çalıştırmayla gün {n + plan} olacak; Rıdvan onayladı, devam (hikâyesiyle tam).")
        _ozet(f"Bugün {n + plan}. içeriğe kadar (**{ne}**), Rıdvan'ın onayıyla.")
        _cikti("tam")
        return 0
    if tur in HIKAYESIZ and n + HIKAYESIZ[tur] <= sinir:
        print(f"::notice::Günlük sınır: hikâye kopyası düşüyor. Bugün {n} içerik gösterildi; {ne} hikâyesiyle "
              f"{n + plan} yapacaktı, hikâyesiz {n + HIKAYESIZ[tur]}. Paylaşım gidiyor, hikâye BİLEREK gitmiyor "
              "(Rıdvan, 19 Ekim 2026: önce hikâye kopyası düşer). Bu bir hata değil.")
        _ozet(f"Günlük sınır: **{ne}** hikâyesiz gidiyor (bugün {n} içerik gösterildi, sınır {sinir}).")
        _cikti("yok")
        return 0
    print(f"::error::Günlük sınır: bugün takipçiye {n} içerik gösterildi ({_liste(sayilan)}). Bu çalıştırma "
          f"({ne}) günü {n + HIKAYESIZ.get(tur, plan)}'e çıkaracaktı; onayın olmadan paylaşılmadı. "
          "Paylaşılsın istersen Claude'a 'onayla' de.")
    _ozet(f"### ⛔ Paylaşılmadı: günlük sınır ({sinir}) aşılacaktı\n"
          f"Bugün gösterilenler (TR saati, tür, sayı): {_liste(sayilan)}.\n\n"
          f"Bu çalıştırma: **{ne}**. Hiçbir şey üretilmedi, paylaşılmadı. "
          "Paylaşılsın istersen Claude'a **onayla** de.")
    _cikti("tam")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yayin", choices=["true", "false"], required=True)
    ap.add_argument("--onay", choices=["true", "false"], default="false")
    ap.add_argument("--tur", default="")
    ap.add_argument("--konu", default="")
    ap.add_argument("--cron", default="", help="zamanlı çalışmanın cron'u (github.event.schedule); elle boş")
    a = ap.parse_args()
    return kontrol(a.yayin == "true", a.onay == "true", a.tur, a.konu, cron=a.cron.strip())


if __name__ == "__main__":
    sys.exit(main())
