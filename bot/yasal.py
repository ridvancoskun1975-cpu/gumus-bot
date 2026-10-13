"""Profilde sabitlenecek yasal bilgilendirme gönderisinin içeriği (kaydırmalı, 5 görsel).

Metni değiştirince "Son güncelleme" tarihini de güncelle, sonra
Actions → Gümüş paylaşımı → Run workflow → tür: yasal ile yeniden üret.
Instagram'da eski gönderinin sabitlemesini kaldırıp yenisini sabitlemek gerekir.
"""

GUNCELLEME = "13 Ekim 2026"

# Kapaktan sonraki sayfalar. Her madde görselde ayrı bir satır olur; kısa tut.
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
            "ECB kuru iş günleri ~17:00'de yenilenir: ~10:00 ve ~17:00 paylaşımları önceki iş "
            "gününün, ~20:00 özeti o günün kurunu kullanır.",
            "Oklar önceki iş gününe, haftalık özette önceki haftaya göredir. Veriler gecikmeli ya "
            "da hatalı olabilir.",
        ],
    },
    {
        "baslik": "Kaynaklar",
        "kaynaklar": [
            ("Ons gümüş ve ons altın (USD)", "MetalCharts · metalcharts.org"),
            ("Dolar/TL", "Avrupa Merkez Bankası (ECB) referans kurları · frankfurter.dev"),
            ("Müzik", "Pixabay İçerik Lisansı · künye her paylaşımın açıklamasında"),
        ],
        "maddeler": [
            "Bu hesabın bu kuruluşlarla bir bağı yoktur; veriler kaynak gösterilerek kullanılır.",
        ],
    },
    {
        "baslik": "Otomatik paylaşım",
        "maddeler": [
            "Paylaşımlar otomatik üretilir: hafta içi ~10:00, ~17:00 ve ~20:00; cumartesi ~10:00 "
            "haftalık özet. Saatler birkaç dakika kayabilir.",
            "Hafta sonu günlük paylaşım yapılmaz. Kur yayımlanmayan günlerde dolar/TL son "
            "yayımlanan ECB kurudur.",
            "Reklam ya da iş birliği içeren paylaşımlar #reklam etiketiyle açıkça belirtilir; "
            "fiyat verileri reklamdan etkilenmez.",
            "Hatalı bir değer görürseniz DM ile bildirebilirsiniz.",
        ],
    },
]

ACIKLAMA = f"""Yasal bilgilendirme | Son güncelleme: {GUNCELLEME}

1) Yatırım tavsiyesi değildir
Bu hesaptaki tüm paylaşımlar yalnızca bilgi amaçlıdır ve alım-satım önerisi içermez. Hiçbir paylaşım yatırım danışmanlığı kapsamında değildir; yatırım danışmanlığı, SPK'dan yetki almış kuruluşlarla imzalanan yatırım danışmanlığı sözleşmesi çerçevesinde sunulur. Paylaşılan değerler mali durumunuza, risk ve getiri tercihlerinize uygun olmayabilir; yalnızca bu bilgilere dayanarak yatırım kararı vermeyin. Bu hesap DM üzerinden tavsiye vermez, para ya da yatırım talep etmez; hesap adına size ulaşan kişilere itibar etmeyin.

2) Fiyatlar nasıl hesaplanır
Gram gümüş = ons gümüş (USD) × dolar/TL ÷ 31,1035. Bu bir gösterge fiyattır; kuyumcu, banka ve borsa alış-satış fiyatlarından farklıdır, işçilik, makas ve vergiler dahil değildir. Dolar/TL, Avrupa Merkez Bankası'nın (ECB) euro referans kurlarından EUR çaprazıyla hesaplanan orta kurdur; TCMB'nin ve bankaların döviz alış kurundan genelde biraz (binde birkaç) yüksektir, gram gümüş de aynı oranda farklı çıkar. ECB kuru her iş günü yaklaşık 17:00'de yenilenir: 10:00 ve 17:00 paylaşımlarında önceki iş gününün, 20:00 özetinde o günün kuru kullanılır. Değişimler önceki iş gününe, haftalık özette önceki haftaya göredir. Veriler gecikmeli, eksik ya da hatalı olabilir; doğruluğu garanti edilmez.

3) Kaynaklar
Metal fiyatları: MetalCharts (metalcharts.org)
Dolar/TL: Avrupa Merkez Bankası (ECB) euro referans kurları, Frankfurter (frankfurter.dev) üzerinden
Müzik: Pixabay İçerik Lisansı; künye her paylaşımın açıklamasında.
Bu hesabın bu kuruluşlarla bir bağı yoktur.

4) Otomatik paylaşım
Paylaşımlar otomatik olarak üretilir: hafta içi yaklaşık 10:00, 17:00 ve 20:00'de, cumartesi 10:00'da haftalık özet. Saatler birkaç dakika kayabilir. Reklam ya da iş birliği içeren paylaşımlar #reklam etiketiyle açıkça belirtilir; fiyat verileri ve hesaplama yöntemi reklamdan etkilenmez. Hatalı bir değer görürseniz DM ile bildirebilirsiniz.

#gümüş #gramgümüş #gümüşfiyatları"""
