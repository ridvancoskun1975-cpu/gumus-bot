# © 2026 Günlük Gümüş (gunlukgumus.com) · Tüm hakları saklıdır / All rights reserved. İzinsiz kopyalanamaz ve kullanılamaz; ayrıntı: LICENSE
"""Deneme Reels'i ("vitrin"; Instagram "trial reels"): rehber bölümlerinden 15–20 sn'lik kısa sesli Reels, YALNIZ takip
etmeyenlere gösterilir (büyüme incelemesi #40).

Rıdvan, 12 Kasım 2026 18:57: "takipçiler görmeyecekse uygula." Instagram'ın deneme ayarı (trial_params,
graduation_strategy MANUAL) Reels'i takipçilerin akışına ve Reels sekmesine koymaz, profilde de göstermez; elle
"herkesle paylaş" denmedikçe takipçilere açılmaz. Bu yüzden günlük 4 sınırına (bot/sinir.py) sayılmaz ve paylas.yml'den
ayrı bir iş akışıyla (vitrin.yml) gider; söz verilen paylaşımların akışına dokunmaz. Sınama (12 Kasım 2026, deneme-reels.yml):
hesap bu ayara uygun, kap kabul edildi ve işlendi.

Biçim: 16 Ekim 2026'ya kadarki kısa rehber Reels'i (templates/kisa.html: soru → kısa cevap → tek cümle → "Rehberin tamamı
profilde"), Rıdvan'ın seçtiği kadın sesiyle (Sulafat; ses.kisa_seslendir). Ses alınamazsa yalnız müzikle gider. Yalnız
Instagram'da önceden yayımlanmış bölümlerden seçilir (çağrı "Rehberin tamamı profilde" doğru olsun).

Deneme süresi (Claude önerisi, Rıdvan'ın 18:57 onayı): 3 hafta, salı ve perşembe; sonra sonuç Rıdvan'a sunulur ve devam
kararı onundur. Paylaşım saatleri ve site yenilemesiyle çakışmasın diye yalnız PENCERE içinde paylaşır; GitHub zamanlı işi
geç başlatırsa o gün atlanır.

Kullanım: python bot/vitrin.py bugun            → bugün paylaşılacak bölüm no (yoksa boş)
          python bot/vitrin.py hazirla --cikti site [--konu N]
          python bot/vitrin.py yayinla --cikti site --url <site adresi>
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

TR = ZoneInfo("Europe/Istanbul")
BASLANGIC = date(2026, 11, 17)          # ilk deneme Reels'i (salı)
BITIS = date(2026, 12, 3)               # 3 haftalık denemenin son günü (perşembe); sonrası Rıdvan'ın kararıyla
GUNLER = (1, 3)                         # salı, perşembe (Monday = 0)
# Sabah paylaşımı (~10:00) bittikten sonra, 12:35 gün içi kaydının site yenilemesinden (sayfa.yml) önce.
PENCERE = (time(10, 45), time(12, 10))
DENEME_AYARI = {"graduation_strategy": "MANUAL"}    # takipçilere hiç gösterilmez (yalnız elle paylaşılırsa)
ACIKLAMA_ISARETI = "Gümüş rehberinden kısa bir bilgi"   # bot/rapor.py bu satırdan tanır
ROZET_SINIR_SN = 180   # sn: rozet bindirme ffmpeg'i (≤ 20 sn video; olağan ~10 sn) en çok bu kadar
# Üstteki küçük rozetin yeri: kısa şablonda main.SES_ROZETI_Y (140 px) başlık satırına ve Ag kutusuna biniyor; alt
# başlık (bölüm 1–6 ölçümü: en alt 617 px) ile büyük rakamın çizgisi (~790 px) arasındaki boşluk. 4:5 akış kırpmasında da (285–1635 px) görünür.
ROZET_Y = 660


def gunler(bas=BASLANGIC, bit=BITIS):
    g, liste = bas, []
    while g <= bit:
        if g.weekday() in GUNLER:
            liste.append(g)
        g += timedelta(days=1)
    return liste


def yayimlanmis(gun):
    """O günden ÖNCE Instagram'da yayımlanmış rehber bölümleri (yayım sırasına göre, her biri bir kez)."""
    import bilgi
    gorulen, liste = set(), []
    for t, no in bilgi.yayim_listesi():
        if t < gun and no not in gorulen and 1 <= no <= len(bilgi.BOLUMLER):
            gorulen.add(no)
            liste.append(no)
    return liste


def gunun_bolumu(gun):
    """Deneme günüyse bölüm no, değilse None. Yayımlanmış bölümler sırayla döner (en eski önce)."""
    takvim = gunler()
    if gun not in takvim:
        return None
    liste = yayimlanmis(gun)
    if not liste:
        return None
    return liste[takvim.index(gun) % len(liste)]


def bugun(simdi=None):
    """Zamanlı çalışma için: bugün deneme günü ve saat pencerenin içindeyse bölüm no, değilse None (sebebini yazar)."""
    simdi = simdi or datetime.now(TR)
    no = gunun_bolumu(simdi.date())
    if no is None:
        print("Bugün deneme Reels'i günü değil.", file=sys.stderr)
        return None
    if not PENCERE[0] <= simdi.time() <= PENCERE[1]:
        print(f"::warning::Deneme Reels'i atlandı: saat {simdi:%H:%M} pencerenin dışında "
              f"({PENCERE[0]:%H:%M}–{PENCERE[1]:%H:%M}; paylaşım ve site yenilemesiyle çakışmasın).", file=sys.stderr)
        return None
    return no


def _sayilabilir(metin):
    """Kısa Reels'te sayarak gelecek büyük cevap: ["önek", "31,1035", " g"] ya da None (templates/kisa.html)."""
    import re
    m = re.match(r"^([%~]?)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)([^\d/]*)$", metin.strip())
    return [m.group(1), m.group(2), m.group(3)] if m else None


def _seslendirme(konu, bolum, cikti, deneme):
    import ses
    if not ses.SES_ACIK or os.environ.get("SES_KAPALI"):
        return None
    try:
        return ses.kisa_seslendir(konu, bolum, cikti, ses=ses.SES, deneme=deneme)
    except Exception as e:
        print(f"::warning::Seslendirme yapılamadı ({type(e).__name__}: {str(e)[:200]}); deneme Reels'i yalnızca müzikle.")
        return None


def rozet_ekle(mp4):
    """Sesli deneme Reels'ine sesli rehber Reels'iyle aynı rozetleri ekler (CLAUDE.md; Rıdvan 17 ve 19 Ekim 2026,
    26 Ekim 2026 "Uygun"): üst ortada hareketli "Sesi açın" rozeti ve yanında "Seslendirme: yapay zekâ" satırı
    (main.SES_NOTU) videonun tamamında (yeri ROZET_Y); ilk main.SES_ROZETI_ORTA_SN saniye zemin kararır, rozet ortada büyük çıkar.
    Çizilemezse uyarı yazar, video rozetsiz kalır (paylaşım durmaz; açıklamadaki yapay zekâ satırı ve AI etiketi kalır)."""
    import shutil
    import tempfile
    import butce
    import main
    mp4 = Path(mp4)
    klasor = Path(tempfile.mkdtemp(prefix="vitrin-rozet-"))   # yayına çıkmasın diye çıktı klasörü dışında
    gecici = mp4.with_name("_rozetli-" + mp4.name)
    try:
        ust = main._ses_rozeti_kareleri(klasor / "ust", yan=True)
        orta = main._ses_rozeti_kareleri(klasor / "orta", yazi=main.SES_ROZETI_ORTA_YAZI, opak=True)
        fps = main.VIDEO_FPS
        acik = f"enable='lt(t,{main.SES_ROZETI_ORTA_SN})'"
        filtre = (f"[0:v]scale=1080:1920,fps={fps}[zemin];[1:v]format=rgba[rozet];"
                  f"[zemin][rozet]overlay=x=(W-w)/2:y={ROZET_Y}:shortest=1[ust];"
                  f"[ust]drawbox=x=0:y=0:w=iw:h=ih:color=black@{main.SES_ROZETI_KARARTMA}:t=fill:{acik}[kara];"
                  f"[2:v]format=rgba[orta];[kara][orta]overlay=x=(W-w)/2:y=(H-h)/2-40:{acik}:shortest=1,"
                  f"format=yuv420p[v]")
        komut = [main.ffmpeg_yolu(), "-y", "-loglevel", "error", "-i", str(mp4),
                 "-stream_loop", "-1", "-framerate", str(fps), "-i", ust,
                 "-stream_loop", "-1", "-framerate", str(fps), "-i", orta,
                 "-filter_complex", filtre, "-map", "[v]", "-map", "0:a?", "-c:a", "copy",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(fps),
                 "-movflags", "+faststart", str(gecici)]
        butce.ffmpeg_calistir(komut, "deneme Reels'i ses rozeti", sinir_sn=ROZET_SINIR_SN)
        gecici.replace(mp4)
        print("Ses rozeti eklendi (Sesi açın + Seslendirme: yapay zekâ).")
        return True
    except Exception as e:
        gecici.unlink(missing_ok=True)
        print(f"::warning::Deneme Reels'ine ses rozeti eklenemedi ({type(e).__name__}: {str(e)[:150]}); rozetsiz.")
        return False
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def aciklama(konu, bolum, sesli):
    import ses
    import main
    ilk = bolum["sayfalar"][0]
    cumle = (ilk.get("maddeler") or [bolum["alt"]])[0]
    satirlar = [f"{bolum['baslik']}",
                f"Kısa cevap: {bolum['buyuk']}, {bolum['buyuk_alt']}.",
                "",
                cumle,
                "",
                f"{ACIKLAMA_ISARETI} (Gümüş rehberi #{konu}). Bölümün tamamı ve hafta içi her gün gram gümüş fiyatı "
                f"profilde: {main.hesap_adi()}"]
    if sesli:
        satirlar.append(ses.ACIKLAMA_SATIRI)
    satirlar.append("Bilgi amaçlıdır, yatırım tavsiyesi değildir.")
    kunye = main.muzik_kunyesi()
    if kunye:
        satirlar.append(f"Müzik: {kunye}")
    satirlar.append(bolum["hashtag"])
    return "\n".join(satirlar)


def hazirla(cikti, konu, deneme=False):
    """Videoyu, kapağı ve meta.json'u cikti klasörüne yazar. Hiç üretilemezse meta yazılmaz (paylaşım atlanır)."""
    import bilgi
    import main
    import ses
    if not 1 <= konu <= len(bilgi.BOLUMLER):
        raise RuntimeError(f"Konu 1-{len(bilgi.BOLUMLER)} arasında olmalı (verilen: {konu})")
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "vitrin.json").unlink(missing_ok=True)
    b = bilgi.BOLUMLER[konu - 1]
    ilk = b["sayfalar"][0]
    sayi = _sayilabilir(b["buyuk"])
    veri = {"b": b, "no": konu, "seri": bilgi.SERI, "hesap": main.hesap_adi(),
            "sayi": json.dumps(sayi, ensure_ascii=False) if sayi else "",
            "formul": ilk.get("formul"), "cumle": (ilk.get("maddeler") or [b["alt"]])[0]}
    damga = datetime.now(TR).strftime("%Y%m%d-%H%M")
    mp4 = cikti / f"vitrin{konu}-{damga}.mp4"
    sl = _seslendirme(konu, b, cikti, deneme)
    try:
        if sl:
            try:
                tamam = main.hareketli_video_uret("kisa", dict(veri, zaman=sl["zaman"]), mp4, sure=sl["sure"],
                                                  seslendirme=sl["wav"])
            except Exception as e:
                print(f"::warning::Seslendirmeli video üretilemedi ({type(e).__name__}: {str(e)[:200]}); yalnızca müzikle.")
                sl = None
                tamam = main.hareketli_video_uret("kisa", dict(veri, zaman=ses.VARSAYILAN_ZAMAN), mp4,
                                                  sure=ses.VARSAYILAN_SURE)
        else:
            tamam = main.hareketli_video_uret("kisa", dict(veri, zaman=ses.VARSAYILAN_ZAMAN), mp4,
                                              sure=ses.VARSAYILAN_SURE)
    finally:
        (cikti / f"_ses-kisa{konu}.wav").unlink(missing_ok=True)   # ara dosya yayına çıkmasın
    if not tamam:
        raise RuntimeError("Deneme Reels'i üretilemedi (şablonda hareket yok)")
    if sl:
        rozet_ekle(mp4)
    kapak = cikti / f"kapak-vitrin{konu}-{damga}.jpg"
    main.gorsel_uret("kisa", dict(veri, zaman=(sl or {}).get("zaman") or ses.VARSAYILAN_ZAMAN), kapak)
    metin = aciklama(konu, b, bool(sl))
    if len(metin) > 2200:
        raise RuntimeError(f"Açıklama Instagram sınırını aşıyor ({len(metin)} > 2200)")
    meta = {"tur": "vitrin", "konu": konu, "dosya": mp4.name, "kapak": kapak.name, "kapak_ms": 1000, "aciklama": metin,
            "seslendirme": sl["ses"] if sl else None, "sure": sl["sure"] if sl else ses.VARSAYILAN_SURE}
    (cikti / "vitrin.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if sl:
        print(f"Seslendirme: {sl['ses']} ({sl['model']}), {sl['sure']} sn, parçalar {sl['parca_sn']}")
    print(metin)
    print(f"\nDeneme Reels'i hazır: {mp4.name}, {kapak.name} ({len(metin)} karakter açıklama)")
    return meta


def yayinla(cikti, taban_url):
    """Deneme ayarıyla (takipçilere gösterilmez) paylaşır. Sesliyse Instagram'ın yapay zekâ etiketiyle (main.AI_ETIKETI)."""
    import main
    meta_yolu = Path(cikti) / "vitrin.json"
    if not meta_yolu.exists():
        print("Paylaşılacak deneme Reels'i yok (vitrin.json yok).")
        return None
    meta = json.loads(meta_yolu.read_text(encoding="utf-8"))
    taban = taban_url.rstrip("/")
    video_url = f"{taban}/{meta['dosya']}"
    main._url_hazir_mi(video_url)
    kid = main.hesap_bilgisi()["user_id"]
    ortak = {"media_type": "REELS", "video_url": video_url, "caption": main.aciklama_telif(meta["aciklama"]),
             "trial_params": json.dumps(DENEME_AYARI)}
    etiketli = bool(main.AI_ETIKETI and meta.get("seslendirme"))
    kap = None
    if etiketli:
        try:
            kap = main._reels_kabi(kid, dict(ortak, is_ai_generated="true"), meta, taban)
        except main.ErisimEngeli:
            raise
        except RuntimeError as e:
            print(f"::warning::Yapay zekâ etiketiyle kurulamadı ({e}); etiketsiz yeniden deneniyor.")
    if kap is None:
        kap = main._reels_kabi(kid, ortak, meta, taban)
    sonuc = main._istek("POST", f"{kid}/media_publish", creation_id=kap["id"])
    mid = sonuc.get("id")
    bilgi_ = main._istek("GET", mid, fields="permalink,media_product_type") if mid else {}
    print(f"Paylaşıldı: deneme Reels'i (yalnız takip etmeyenler) · bölüm #{meta['konu']} · {bilgi_.get('permalink', mid)}")
    if etiketli and mid:
        main._ai_etiketi_bildir(mid, meta)   # etiketin gerçekten konduğunu günlüğe yazar; hata vermez
    return mid


def main_():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("bugun")
    h = alt.add_parser("hazirla")
    h.add_argument("--cikti", required=True)
    h.add_argument("--konu", type=int)
    y = alt.add_parser("yayinla")
    y.add_argument("--cikti", required=True)
    y.add_argument("--url", required=True)
    alt.add_parser("takvim")
    a = ap.parse_args()
    if a.komut == "bugun":
        no = bugun()
        if no:
            print(no)
    elif a.komut == "takvim":
        for g in gunler():
            print(g.isoformat(), ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"][g.weekday()], gunun_bolumu(g))
    elif a.komut == "hazirla":
        konu = a.konu or gunun_bolumu(datetime.now(TR).date())
        if not konu:
            print("::warning::Bugün deneme Reels'i günü değil ve konu verilmedi; üretilmedi.")
            return
        hazirla(a.cikti, konu, deneme=os.environ.get("DENEME", "").lower() == "true")
    elif a.komut == "yayinla":
        yayinla(a.cikti, a.url)


if __name__ == "__main__":
    main_()
