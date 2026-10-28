"""Günlük sınırda hikâye kopyasının düşmesi ve görünen içerik sayımı (bot/main.py → _hikaye_izinli, _GORUNEN).
Ağ yok. Çalıştır: python bot/test_hikaye_siniri.py

Rıdvan, 19 Ekim 2026: günlük sınır (4) takipçinin gördüğü her şeyi sayar (akış + Reels + hikâye); gün aşılacaksa
önce hikâye kopyası düşer. kontrol işi HIKAYE=yok verince yayinla hikâye paylaşmaz; paylaşılan her şey sayılır.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

gecen = 0


def esit(a, b, ad):
    global gecen
    assert a == b, f"{ad}: {a!r} != {b!r}"
    gecen += 1


cagrilar = []


def sahte_istek(yontem, yol, **kw):
    cagrilar.append((yol, kw.get("media_type")))
    if yol.endswith("/media_publish"):
        return {"id": "m"}
    return {"id": "k", "permalink": "p"}


main._istek = sahte_istek
main.hesap_bilgisi = lambda: {"user_id": "u"}
main._url_hazir_mi = lambda *a, **k: None
main._hazir_olmasini_bekle = lambda *a, **k: None
main._reels_konteyneri = lambda kid, url, meta, taban: sahte_istek("POST", f"{kid}/media", media_type="REELS")
main.HIKAYE_ARA_SN = 0


def calistir(meta, hikaye):
    cagrilar.clear()
    main._GORUNEN[0] = 0
    main._PAYLASILAN_HIKAYELER.clear()
    if hikaye is None:
        os.environ.pop("HIKAYE", None)
    else:
        os.environ["HIKAYE"] = hikaye
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            main._yayinla(Path(d), "https://ornek.test/")
    os.environ.pop("HIKAYE", None)
    hikayeler = sum(1 for y, t in cagrilar if t == "STORIES" and not y.endswith("media_publish"))
    return main._GORUNEN[0], hikayeler, cikti.getvalue()


post = {"tur": "post", "dosya": "post.mp4", "aciklama": "a"}
esit(calistir(post, None)[:2], (2, 1), "akşam özeti: Reels + hikâye = 2")
esit(calistir(post, "tam")[:2], (2, 1), "hikaye=tam: hikâyeli")
n, h, cikti = calistir(post, "yok")
esit((n, h), (1, 0), "hikaye=yok: yalnız Reels, hikâye yok")
esit("BİLEREK" in cikti and "hata değil" in cikti, True, "günlükte bilerek atlandığı yazar (gece kontrolü yanlış alarm vermesin)")

reels = {"tur": "reels", "dosya": "reels.mp4", "aciklama": "a"}
esit(calistir(reels, None)[:2], (1, 0), "sabah Reels'i hikâyesiz: 1")

bilgi = {"tur": "bilgi", "konu": 8, "dosya": "bilgi8.mp4", "aciklama": "a", "hikayeler": ["k1.png"],
         "hikaye_videolari": ["h1.mp4"]}
esit(calistir(bilgi, None)[:2], (2, 1), "rehber: Reels + hikâye videosu = 2")
bilgi2 = {**bilgi, "hikaye_videolari": ["h1.mp4", "h2.mp4"]}
esit(calistir(bilgi2, None)[:2], (3, 2), "60 sn'yi aşan bölüm: 2 hikâye videosu, 3 sayılır")
n, h, cikti = calistir(bilgi, "yok")
esit((n, h), (1, 0), "rehber hikaye=yok: hikâye yok")
esit("tür: hikaye, konu: 8" in cikti, True, "rehber hikâyesinin sonradan nasıl gönderileceği yazar")

yorum = {"tur": "yorum", "dosyalar": ["y1.png", "y2.png", "y3.png"], "aciklama": "a",
         "reels": {"dosya": "yorum.mp4", "hikaye_dosya": "yorum-h.mp4", "aciklama": "a"}}
main._kaydirmali_konteyner = lambda kid, urller, aciklama: sahte_istek("POST", f"{kid}/media", media_type="CAROUSEL")
if main.PAZAR_HIKAYE:
    esit(calistir(yorum, None)[:2], (3, 1), "pazar: kaydırmalı + Reels + hikâye = 3")
else:  # Pazar hikâyesi 25 Ekim 2026'dan beri kapalı (Rıdvan: "Hikayeyi kaldıralım")
    esit(calistir(yorum, None)[:2], (2, 0), "pazar: kaydırmalı + Reels = 2 (hikâye kapalı)")
esit(calistir(yorum, "yok")[:2], (2, 0), "pazar hikaye=yok: kaydırmalı + Reels")

hikaye = {"tur": "hikaye", "konu": 6, "hikaye_videolari": ["h1.mp4"]}
esit(calistir(hikaye, "yok")[:2], (1, 1), "elle rehber hikâyesi HIKAYE'den etkilenmez (kendisi hikâye)")

# İş akışı: kontrol çıktısı yayinla'ya ulaşır, sayı eser olarak saklanır
akis = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "paylas.yml").read_text(encoding="utf-8")
esit("hikaye: ${{ steps.sinir.outputs.hikaye }}" in akis, True, "kontrol çıktısı hikaye")
esit("hikaye: ${{ needs.kontrol.outputs.hikaye }}" in akis, True, "uret çıktısından geçer")
esit("HIKAYE: ${{ needs.uret.outputs.hikaye }}" in akis, True, "yayinla HIKAYE alır")
esit("name: gorunen-${{ github.run_attempt }}-${{ steps.gorunen.outputs.n }}" in akis, True, "görünen sayı eseri")

print(f"Tamam: {gecen} sınama geçti.")
