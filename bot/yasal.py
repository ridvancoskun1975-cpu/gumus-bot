"""Profilde sabitlenecek yasal bilgilendirme gönderisinin içeriği (kaydırmalı, 5 görsel).

Metni değiştirince "Son güncelleme" tarihini de güncelle, sonra
Actions → Gümüş paylaşımı → Run workflow → tür: yasal ile yeniden üret.
Instagram'da eski gönderinin sabitlemesini kaldırıp yenisini sabitlemek gerekir.
"""

GUNCELLEME = "20 Ekim 2026"

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
            "ECB kuru iş günleri ~17:00'de yenilenir: ~10:00 paylaşımı önceki iş gününün, "
            "~20:00 özeti o günün kurunu kullanır.",
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
            ("Pazar yorumundaki haberler", "Web araması · kaynaklar her yorumun açıklamasında"),
        ],
        "maddeler": [
            "Bu hesabın bu kuruluşlarla bir bağı yoktur; veriler kaynak gösterilerek kullanılır.",
        ],
    },
    {
        "baslik": "Otomatik paylaşım",
        "maddeler": [
            "Paylaşımlar otomatik üretilir: hafta içi ~10:00 ve ~20:00 gram fiyatı; ayrıca "
            "rehber, özet ve bilgi paylaşımları, pazar ~11:00 yorum.",
            "Pazar yorumları fiyat ve kur verileri ile haftanın haberlerinden üst düzey yapay "
            "zekâ ile üretilir; yine de tahmindir, hata içerebilir ve uzman incelemesinden geçmez.",
            "Sesli videolarda seslendirme yapay zekâ ile üretilir.",
            "Hesap kendi tanıtımı için ücretli reklam verebilir (\"Sponsorlu\" görünür); iş birliği "
            "ve başkası adına reklam #reklam etiketiyle belirtilir. Fiyat verileri reklamdan etkilenmez.",
            "Hatalı bir değer görürseniz DM ile bildirebilirsiniz.",
        ],
    },
]

ACIKLAMA = f"""Yasal bilgilendirme | Son güncelleme: {GUNCELLEME}

1) Yatırım tavsiyesi değildir
Bu hesaptaki tüm paylaşımlar yalnızca bilgi amaçlıdır ve alım-satım önerisi içermez. Hiçbir paylaşım yatırım danışmanlığı değildir; yatırım danışmanlığı, SPK'dan yetkili kuruluşlarla imzalanan sözleşmeyle sunulur. Değerler mali durumunuza ve risk tercihlerinize uygun olmayabilir; yalnızca bunlara dayanarak karar vermeyin. Bu hesap DM'den tavsiye vermez, para ya da yatırım istemez; hesap adına yazanlara itibar etmeyin.

2) Fiyatlar nasıl hesaplanır
Gram gümüş = ons gümüş (USD) × dolar/TL ÷ 31,1035. Bu bir gösterge fiyattır; kuyumcu, banka ve borsa alış-satış fiyatlarından farklıdır, işçilik, makas ve vergiler dahil değildir. Dolar/TL, ECB euro referans kurlarından EUR çaprazıyla hesaplanan orta kurdur; TCMB'nin ve bankaların alış kurundan genelde biraz (binde birkaç) yüksektir, gram gümüş de aynı oranda farklı çıkar. ECB kuru her iş günü yaklaşık 17:00'de yenilenir: 10:00 paylaşımında önceki iş gününün, 20:00 özetinde o günün kuru kullanılır. Değişimler önceki iş gününe, haftalık özette önceki haftaya göredir. Veriler gecikmeli ya da hatalı olabilir.

3) Kaynaklar
Metal fiyatları: MetalCharts (metalcharts.org)
Dolar/TL: Avrupa Merkez Bankası (ECB) euro referans kurları, Frankfurter (frankfurter.dev) üzerinden
Müzik: Pixabay İçerik Lisansı; künye açıklamalarda.
Bu hesabın bu kuruluşlarla bir bağı yoktur.

4) Otomatik paylaşım
Paylaşımlar otomatik olarak üretilir: hafta içi yaklaşık 10:00 ve 20:00'de gram fiyatı; ayrıca rehber, özet ve bilgi paylaşımları, pazar 11:00'de yorum. Pazar yorumları fiyat ve kur verileri ile web aramasıyla derlenen haftanın haberlerinden üst düzey yapay zekâ ile üretilir (kaynaklar yorumun açıklamasında); yine de tahmin niteliğindedir, hata içerebilir ve yayından önce uzman incelemesinden geçmez. Sesli videolarda seslendirme de yapay zekâ ile üretilir. Hesap kendi tanıtımı için ücretli reklam verebilir (Instagram'da "Sponsorlu" görünür); iş birliği ve başkası adına reklam #reklam etiketiyle açıkça belirtilir. Fiyat verileri ve hesaplama yöntemi reklamdan etkilenmez. Hatalı bir değer görürseniz DM ile bildirebilirsiniz.

#gümüş #gramgümüş #gümüşfiyatları"""
