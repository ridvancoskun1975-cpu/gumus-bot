"""Ücretli reklam dönemleri: takipçi ve erişim hesaplarında reklamın etkisi ayrı tutulsun diye (Rıdvan, 17 Ekim 2026:
"Dün Instagram reklamı başladı. Bunu reklam etki hesaplarında göz önünde bulundur.").

Haftalık rapor (bot/rapor.py) dönemle kesişen reklamı özette yazar, takipçi artışını reklamlı ve reklamsız günlere
ayırır, günlük takipçi tablosunda reklam günlerini işaretler, goril kıyasında reklam günlerini ayrıca gösterir.

Yeni reklam verildiğinde bu listeye bir satır eklenir: ad, ilk gün, son gün (dahil), hedef, Instagram'daki reklam
gönderisinin kısa kodu (instagram.com/p/<kod>) ve Rıdvan söylerse reklam günlerinde gelen tanıdık sayısı
("tanidik": (en az, en çok)). Bütçe ve harcama bu herkese açık depoya yazılmaz; yalnızca
Instagram'ın reklam araçlarında ve Rıdvan'la sohbette durur. Yalnızca standart kütüphane.
"""
from datetime import date, timedelta

REKLAMLAR = [
    {"ad": "Reklam 1", "bas": date(2026, 10, 16), "bit": date(2026, 10, 19), "hedef": "profil ziyareti",
     "kod": "DekCe04AOmh",
     "not": "Profilde görünmeyen reklam, 8 sn hareketli video (fiyat saatleri, pazar analizi, rehber; istifçi "
            "goril); 3 gün; Türkiye, 25–65, erkek; ilgi alanı gümüş, yatırım, altın, borsa",
     # Rıdvan, 17 Ekim 2026 20:52: "Buradaki 4, 5 kişi tanıdık, geri kalanları reklam." (reklam günlerinde gelen
     # takipçilerden 4–5'i tanıdık; rapor reklamla gelen takipçiyi bunu düşerek aralık olarak verir)
     "tanidik": (4, 5)},
    # Rıdvan, 21 Ekim 2026: "Ekle." İlk gün 18 Ekim (reklam Reels'inin tarihi), 6 gün; 21 Ekim 21:15'te "3 gün sonra
    # sona eriyor". Reklam 1 ile 18–19 Ekim'de üst üste biner. Profilde görünmeyen reklam, kısa kod yok.
    # Rıdvan, 23 Ekim 2026: "Uzat". Reklam 12 güne uzatıldı; 23 Ekim 11:41'de "7 gün sonra sona eriyor" → son gün 30 Ekim.
    {"ad": "Reklam 2", "bas": date(2026, 10, 18), "bit": date(2026, 10, 30), "hedef": "optimize edilmiş karma",
     "not": "Profilde görünmeyen reklam, 13 sn hareketli video (fiyat saatleri, cumartesi haftalık rapor, pazar üst "
            "düzey yapay zekâ analizi, sesli rehber; istifçi goril; müzik Motivate); önce 6 gün, 23 Ekim'de 12 güne "
            "uzatıldı (son gün 30 Ekim); hedef kitle \"gümüş\". "
            "21 Ekim ~21:35'ten sonra profil değişti (biyografi, sabitlenen tanıtım Reels'i); oran kıyası bu andan önce "
            "ve sonra ayrı yapılır"},
    # Rıdvan, 29 Ekim 2026 22:51: "Yeni reklam verdim"; 22:53: "Başka reklam vermeyeceğim. Yeni reklam gününe göre
    # gerekli ayarlamaları yap. Onaylıyorum." Reklam araçları ekranı 29 Ekim 22:50'de "5 gün sonra sona eriyor" → son
    # gün 3 Kasım (4 Kasım'a sarkarsa Rıdvan "uzat" der). Reklam 2 ile 29–30 Ekim'de üst üste biner. Profilde
    # görünmeyen reklam, kısa kod yok. Rıdvan'ın dediğine göre bundan sonra reklam yok: 4 Kasım'dan itibaren
    # reklamsız dönem; ilk tam reklamsız hafta 9–15 Kasım (16 Kasım raporu).
    {"ad": "Reklam 3", "bas": date(2026, 10, 29), "bit": date(2026, 11, 3), "hedef": "çeşitli eylemler",
     "not": "Profilde görünmeyen reklam, Reklam 2 ile aynı 13 sn video (fiyat saatleri, cumartesi haftalık rapor, "
            "pazar üst düzey yapay zekâ analizi, sesli rehber; istifçi goril; müzik Motivate); 5 gün; hedef kitle "
            "\"gümüş\""},
]


def o_gun(g, reklamlar=None):
    """O gün yayında olan reklamların adları (liste; yoksa boş)."""
    return [r["ad"] for r in (REKLAMLAR if reklamlar is None else reklamlar) if r["bas"] <= g <= r["bit"]]


def kesisen(bas, bit, reklamlar=None):
    """[bas, bit] dönemiyle kesişen reklamlar."""
    return [r for r in (REKLAMLAR if reklamlar is None else reklamlar) if r["bas"] <= bit and r["bit"] >= bas]


def gunleri(r):
    g, son = r["bas"], r["bit"]
    while g <= son:
        yield g
        g += timedelta(days=1)
