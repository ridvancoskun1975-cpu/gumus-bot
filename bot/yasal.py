"""Profilde sabitlenecek yasal bilgilendirme gönderisinin içeriği (kaydırmalı, 6 görsel).

Metni değiştirince "Son güncelleme" tarihini de güncelle, sonra
Actions → Gümüş paylaşımı → Run workflow → tür: yasal ile yeniden üret.
Instagram'da eski gönderinin sabitlemesini kaldırıp yenisini sabitlemek gerekir.
"""

GUNCELLEME = "26 Ekim 2026"

# Kapaktan sonraki sayfalar. Her madde görselde ayrı bir satır olur; kısa tut.
# 26 Ekim 2026 (yasal inceleme 5. madde): sesli Reels, yön değişikliği satırı, aylık özet, çarşamba rehberi, site,
# reklam etiketleri ve müzik künyesi cümlesi güncellendi; yapay zekâ ayrı sayfa oldu.
SAYFALAR = [
    {
        "baslik": "Yatırım tavsiyesi değildir",
        "maddeler": [
            "Bu hesaptaki tüm paylaşımlar yalnızca bilgi amaçlıdır; alım-satım önerisi içermez.",
            "Hiçbir paylaşım yatırım danışmanlığı değildir. Yatırım danışmanlığı, SPK'dan yetkili "
            "kuruluşlarla imzalanan sözleşmeyle verilir.",
            "Değerler mali durumunuza ve risk tercihlerinize göre hazırlanmamıştır; yalnızca "
            "bunlara dayanarak karar vermeyin.",
            "Bu hesap DM'den tavsiye vermez, para ya da yatırım istemez. Hesap adına size "
            "yazanlara itibar etmeyin.",
        ],
    },
    {
        "baslik": "Fiyatlar nasıl hesaplanır",
        "formul": "Gram gümüş = ons gümüş × dolar/TL ÷ 31,1035",
        "maddeler": [
            "Gösterge fiyattır; kuyumcu, banka ve borsa fiyatlarından farklıdır. İşçilik, makas "
            "ve vergiler dahil değildir.",
            "Dolar/TL, Avrupa Merkez Bankası'nın (ECB) orta kurudur. TCMB ve bankaların alış "
            "kurundan genelde biraz (binde birkaç) yüksektir; gram fiyat da aynı oranda farklı çıkar.",
            "ECB kuru iş günleri ~17:00'de yenilenir: ~10:00 paylaşımı önceki iş gününün, "
            "~20:00 özeti o günün kurunu kullanır.",
            "Oklar önceki iş gününe, haftalık ve aylık özette önceki döneme göredir. Veriler "
            "gecikmeli ya da hatalı olabilir.",
        ],
    },
    {
        "baslik": "Kaynaklar",
        "kaynaklar": [
            ("Ons gümüş ve ons altın (USD)", "MetalCharts · metalcharts.org"),
            ("Dolar/TL", "Avrupa Merkez Bankası (ECB) referans kurları · frankfurter.dev"),
            ("Müzik", "Pixabay İçerik Lisansı · künye müzikli paylaşımların açıklamasında"),
            ("Pazar yorumundaki haberler", "Web araması · kaynaklar her yorumun açıklamasında"),
        ],
        "maddeler": [
            "Bu hesabın bu kuruluşlarla bir bağı yoktur; veriler kaynak gösterilerek kullanılır.",
        ],
    },
    {
        "baslik": "Yapay zekâ",
        "maddeler": [
            "Pazar yorumu fiyat ve kur verileri ile haftanın haberlerinden yapay zekâ ile üretilir; "
            "tahmindir, hata içerebilir ve uzman incelemesinden geçmez.",
            "Ağır basan yön önceki yorumdan farklıysa değişiklik, nedeni ve önceki yorumun tarihi "
            "yazılır.",
            "Rehber ve pazar Reels'lerindeki seslendirmeler yapay zekâ ile üretilir; ekranda ve "
            "açıklamada belirtilir.",
        ],
    },
    {
        "baslik": "Otomatik paylaşım",
        "maddeler": [
            "Hafta içi ~10:00 ve ~20:00 fiyat, çarşamba ~14:00 gümüş rehberi, cumartesi ~10:00 "
            "haftalık özet, pazar ~11:00 yorum; ayın ilk günlerinde aylık özet.",
            "gunlukgumus.com (link bio'da) hafta içi günde 4 kez güncellenir; canlı fiyat değildir.",
            "Reklam ve iş birlikleri #Reklam ya da #İşbirliği etiketi ve Instagram'ın ücretli "
            "ortaklık etiketiyle belirtilir; fiyat verileri reklamdan etkilenmez.",
            "Hatalı bir değer görürseniz DM ile bildirebilirsiniz.",
        ],
    },
]

ACIKLAMA = f"""Yasal bilgilendirme | Son güncelleme: {GUNCELLEME}

1) Yatırım tavsiyesi değildir
Bu hesaptaki tüm paylaşımlar yalnızca bilgi amaçlıdır, alım-satım önerisi içermez ve yatırım danışmanlığı kapsamında değildir; yatırım danışmanlığı, SPK'dan yetki almış kuruluşlarla imzalanan sözleşme çerçevesinde sunulur. Paylaşılan değerler mali durumunuza, risk ve getiri tercihlerinize uygun olmayabilir; yalnızca bunlara dayanarak yatırım kararı vermeyin. Bu hesap DM'den tavsiye vermez, para ya da yatırım istemez; hesap adına size ulaşanlara itibar etmeyin.

2) Fiyatlar nasıl hesaplanır
Gram gümüş = ons gümüş (USD) × dolar/TL ÷ 31,1035. Gösterge fiyattır; kuyumcu, banka ve borsa fiyatlarından farklıdır, işçilik, makas ve vergiler dahil değildir. Dolar/TL, ECB euro referans kurlarından EUR çaprazıyla hesaplanan orta kurdur; ECB kuru iş günleri ~17:00'de yenilenir: 10:00 paylaşımında önceki iş gününün, 20:00 özetinde o günün kuru kullanılır. Değişimler önceki iş gününe, haftalık ve aylık özette önceki döneme göredir. Veriler gecikmeli ya da hatalı olabilir.

3) Kaynaklar
Metal fiyatları: MetalCharts (metalcharts.org)
Dolar/TL: ECB euro referans kurları, Frankfurter (frankfurter.dev) üzerinden
Müzik: Pixabay İçerik Lisansı; künye müzikli paylaşımların açıklamasında.
Bu hesabın bu kuruluşlarla bir bağı yoktur.

4) Yapay zekâ
Pazar yorumu fiyat, kur ve haftanın haberlerinden yapay zekâ ile üretilir (kaynaklar açıklamada); tahmindir, hata içerebilir, uzman incelemesinden geçmez. Ağır basan yön önceki yorumdan farklıysa değişiklik, nedeni ve önceki tarih yazılır. Rehber ve pazar Reels'lerindeki seslendirmeler yapay zekâ ile üretilir; ekranda ve açıklamada belirtilir.

5) Otomatik paylaşım
Hafta içi ~10:00 ve ~20:00 fiyat, çarşamba ~14:00 gümüş rehberi, cumartesi ~10:00 haftalık özet, pazar ~11:00 yorum; ayın ilk günlerinde aylık özet. gunlukgumus.com (link bio'da) hafta içi günde 4 kez güncellenir; canlı fiyat değildir. Reklam ve iş birlikleri #Reklam ya da #İşbirliği etiketi ve Instagram'ın ücretli ortaklık etiketiyle belirtilir; fiyat verileri reklamdan etkilenmez. Hatalı bir değer görürseniz DM ile bildirebilirsiniz.

#gümüş #gramgümüş #gümüşfiyatları"""
