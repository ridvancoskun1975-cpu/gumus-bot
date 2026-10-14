"""Bilgi sayfasındaki "Ayrıntılı rehber": Instagram rehber serisinden daha kapsamlı, kaynaklı başvuru bölümü.

12 Ekim 2026'daki ilk bilgi sayfası taslağından (arşivde) türetildi; 14 Ekim 2026'da bütün rakamlar
birincil kaynaklardan yeniden doğrulandı ve düzeltildi (Rıdvan: "a+b+c"). Tavsiye gibi okunabilecek
cümleler tarafsız bilgiye çevrildi (yatırım tavsiyesi değildir).

GÜNCELLİK: Rakamların çoğu yıllık raporlara dayanır. Yeni World Silver Survey her yıl Nisan'da,
USGS Mineral Commodity Summaries her yıl Ocak-Şubat'ta çıkar. SONRAKI_GOZDEN_GECIRME geçince bilgi
sayfası üretilirken iş akışında uyarı çıkar (bot/sayfa.py) ve sayfada "gözden geçirilecek" notu belirir;
rakamlar yeni raporlarla güncellenip tarihler ileri alınmalı.

Biçim: BOLUMLER = [{id, baslik, giris?, maddeler?, tablo?: {basliklar, satirlar, sayisal?}, not?, kaynaklar: [(ad, url)]}]
(sayisal: sütun başına sağa yaslı, kırılmayan sayı sütunu mu; yoksa 3+ sütunlu tablolarda ilk sütun hariç hepsi)
Metinler düz yazıdır (HTML değil); şablon kaçışlar.
"""
from datetime import date

GOZDEN_GECIRME = date(2026, 10, 14)            # rakamların son doğrulandığı gün
SONRAKI_GOZDEN_GECIRME = date(2027, 4, 30)     # World Silver Survey 2027'den sonra
KAYNAK_DONEMI = "World Silver Survey 2026 (Nisan 2026) ve USGS Mineral Commodity Summaries 2026 (Şubat 2026)"

WSS = ("The Silver Institute / Metals Focus, World Silver Survey 2026",
       "https://silverinstitute.org/wp-content/uploads/2026/04/World-Silver-Survey-2026.pdf")
WSS_BULTEN = ("The Silver Institute, basın bülteni (15 Nisan 2026)",
              "https://silverinstitute.org/elevated-lease-rates-regional-liquidity-tightness-and-robust-investor-interest-resulted-in-record-silver-prices-in-2025/")
USGS_MCS = ("USGS, Mineral Commodity Summaries 2026 – Silver",
            "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-silver.pdf")
USGS_BILGI = ("USGS, Silver Statistics and Information",
              "https://www.usgs.gov/centers/national-minerals-information-center/silver-statistics-and-information")

BOLUMLER = [
    {
        "id": "metal",
        "baslik": "Gümüş nedir?",
        "giris": ("Gümüş, periyodik tablonun 47. elementidir; sembolü Ag, Latince argentum'dan gelir. "
                  "Metaller arasında elektriği ve ısıyı en iyi ileten, ışığı en iyi yansıtan metaldir. "
                  "Bu yüzden hem değerli maden hem de önemli bir sanayi hammaddesidir."),
        "tablo": {"basliklar": ["Özellik", "Değer"], "satirlar": [
            ["Atom numarası", "47"],
            ["Bağıl atom kütlesi", "107,868"],
            ["Yoğunluk", "10,5 g/cm³"],
            ["Erime noktası", "961,78 °C"],
            ["Kaynama noktası", "2.162 °C"],
            ["1 troy ons", "31,1035 g"],
        ]},
        "maddeler": [
            "Anadolu gümüşün çok eski bir yurdudur: MÖ 20.-19. yüzyıllarda Kültepe'de (Kaniş) Asurlu tüccarların "
            "borç ve ödeme kayıtlarında gümüş kullanıldı.",
            "İlk sikkeler Lidya'da, doğal altın-gümüş alaşımı olan elektrumdan basıldı. Kral Kroisos döneminde "
            "(MÖ 6. yüzyıl ortası) elektrum altın ve gümüşe ayrılarak ayrı altın ve gümüş sikkeler basılabildi.",
            "Osmanlı'nın temel parası akçe de gümüştü (Gümüş rehberi #13).",
        ],
        "kaynaklar": [
            ("Royal Society of Chemistry, Periodic Table – Silver", "https://periodic-table.rsc.org/element/47/silver"),
            USGS_BILGI,
            ("The Metropolitan Museum of Art, Kültepe gümüş borç belgesi", "https://www.metmuseum.org/art/collection/search/325857"),
            ("LBMA, Croesus Stater", "https://www.lbma.org.uk/wonders-of-gold/items/croesus-stater"),
        ],
    },
    {
        "id": "zirveler",
        "baslik": "Fiyat geçmişi: zirveler",
        "giris": ("Gümüş 1980'deki zirvesini 45 yıl aşamadı. 2025'te 50 $ sınırı kırıldı, fiyat Ocak 2026'da "
                  "yeni bir rekora çıktı ve ertesi gün sert düştü. Zirveler ölçüye göre farklı yazılır: "
                  "LBMA sabitleme (Londra'da günde bir kez belirlenen referans fiyat), COMEX vadeli kontrat "
                  "ve spot (anlık) fiyat."),
        "tablo": {"basliklar": ["Tarih", "Ölçü", "Dolar/ons"], "sayisal": [False, False, True], "satirlar": [
            ["18 Ocak 1980", "LBMA sabitleme (aynı gün COMEX vadeli gün içi 50,35 $)", "49,45 $"],
            ["28 Nisan 2011", "LBMA sabitleme (aynı gün COMEX gün içi 49,52 $)", "48,70 $"],
            ["17 Ekim 2025", "Spot gün içi; 50 $ ilk kez 9 Ekim'de aşıldı", "54,48 $"],
            ["29 Ocak 2026", "Spot gün içi rekor (kaynağa göre 121,58–121,67 $)", "≈121,6 $"],
            ["30 Ocak 2026", "Spot; bir günde ≈%28 düşüş", "83,99 $"],
        ]},
        "maddeler": [
            "1980 zirvesi (LBMA 49,45 $), ABD tüketici fiyatlarıyla Ağustos 2026 dolarına çevrilince yaklaşık 213 $ eder: "
            "nominal rekora rağmen gümüş, enflasyondan arındırılmış 1980 zirvesinin altında kaldı.",
            "Ocak 2026 rekoru ve ertesi günkü düşüş, gümüşün altına göre çok daha oynak seyredebildiğini gösterir.",
        ],
        "not": ("Enflasyon hesabı: ABD TÜFE-U (1982-84=100), Ocak 1980 = 77,8, Ağustos 2026 = 334,98; "
                "49,45 × 334,98 ÷ 77,8 ≈ 212,9. Güncel fiyat bu sayfanın üstünde."),
        "kaynaklar": [
            ("The Silver Institute, Silver News (Ekim 2025)", "https://silverinstitute.org/wp-content/uploads/2025/11/Silver-News-OCT2025.pdf"),
            ("BullionVault (Nisan 2011 LBMA sabitleme)", "https://www.bullionvault.com/gold-news/opinion-analysis/silver-investing-mania-5-years-day-04302016"),
            ("Numismatic News (Nisan 2011 COMEX)", "https://www.numismaticnews.net/archive/silver-slides-after-near-record-highs"),
            ("The Vault Report (Ocak 2026 rekoru, kaynaklara göre aralık)", "https://thevaultreport.com/research/silver-1980-record-46-year-round-trip"),
            ("QNA / The Peninsula (30 Ocak 2026 düşüşü)", "https://thepeninsulaqatar.com/article/31/01/2026/gold-prices-post-biggest-one-day-drop-in-four-decades"),
            ("FRED, ABD TÜFE-U (CPIAUCNS)", "https://fred.stlouisfed.org/series/CPIAUCNS"),
        ],
    },
    {
        "id": "arz",
        "baslik": "Arz: gümüş nereden geliyor?",
        "giris": ("Gümüşün iki kaynağı vardır: madenler ve geri dönüşüm. Çıkarılan gümüşün yaklaşık dörtte üçü "
                  "kurşun-çinko, bakır ve altın madenlerinin yan ürünüdür; bu yüzden fiyat yükselse bile "
                  "üretim hızla artmaz."),
        "tablo": {"basliklar": ["2025", "Milyon ons", "Ton"], "satirlar": [
            ["Dünya maden üretimi (+%3)", "846,6", "26.331"],
            ["Meksika (−%5; üst üste 3. düşüş)", "172,9", "5.378"],
            ["Peru (+%7)", "130,6", "4.063"],
            ["Çin (+%3)", "112,8", "3.509"],
            ["Geri dönüşüm (12 yılın en yükseği)", "197,6", "6.145"],
        ]},
        "maddeler": [
            "2025 maden üretiminin kaynağı: birincil gümüş madenleri %26, kurşun-çinko %29, bakır %28, altın %16.",
            "Maden üretiminin 2026'da yatay kalması (844,1 milyon ons) bekleniyor.",
            "USGS, aynı yıl için farklı bir yöntemle Meksika'ya 6.300 ton, dünyaya 26.000 ton diyor "
            "(Gümüş rehberi #8 bu rakamları kullanır). Dünya rezervi 610.000 ton; en büyüğü Peru'da (110.000 ton).",
        ],
        "kaynaklar": [WSS, WSS_BULTEN, USGS_MCS],
    },
    {
        "id": "talep",
        "baslik": "Talep: gümüş nereye gidiyor?",
        "giris": ("2025'te dünya gümüş talebi %2 azalarak 1.130,6 milyon onsa (yaklaşık 35.200 ton) indi; "
                  "2021'den beri en düşük seviye. Talebin yarısından fazlası sanayiden geliyor."),
        "tablo": {"basliklar": ["Talep kalemi (2025)", "Milyon ons", "Değişim"], "satirlar": [
            ["Sanayi", "657,4", "−%3"],
            ["  içinde güneş paneli", "186,6", "−%6"],
            ["Sikke ve külçe", "217,7", "+%14"],
            ["Mücevher", "189,3", "−%8"],
            ["Gümüş eşya", "42,1", "−%21"],
        ]},
        "maddeler": [
            "Güneş panelleri sanayide gümüşü en çok kullanan tek alan; üreticiler gümüşü azaltıp bakır gibi "
            "metallere yöneldiği için bu kalemin 2026'da %19 azalarak 151 milyon onsa inmesi bekleniyor.",
            "Diğer sanayi alanları: elektronik ve elektrik bağlantıları, otomotiv (özellikle elektrikli araçlar), "
            "lehim, sağlık ürünleri, ayna ve cam kaplama.",
            "Sikke ve külçe talebinin 2026'da %18 artarak 257,6 milyon onsa çıkması bekleniyor. Orta Doğu'da "
            "fiziksel gümüş yatırımı 2025'te üç kattan fazla artıp 11,4 milyon onsla rekor kırdı.",
        ],
        "kaynaklar": [WSS, WSS_BULTEN],
    },
    {
        "id": "acik",
        "baslik": "Arz açığı",
        "giris": ("2021'den beri her yıl dünyada üretilenden fazla gümüş kullanılıyor; 2025 beşinci açık yılı oldu. "
                  "Aradaki fark mevcut stoklardan karşılanıyor."),
        "tablo": {"basliklar": ["", "Milyon ons", "Ton"], "satirlar": [
            ["2025 açığı", "40,3", "1.252"],
            ["2026 beklenen açık (6. yıl)", "46,3", "1.439"],
            ["2021–2026 toplamı (2026 tahmini dahil)", "762,1", "23.705"],
        ]},
        "maddeler": [
            "Ekim 2025'te Londra'da serbest stoklar azalınca benzeri görülmemiş bir likidite sıkışması yaşandı.",
            "Çin, gümüş ihracatını iki yılda bir yenilenen bir devlet ticaret şirketi listesiyle sınırlıyor; "
            "2026–2027 listesinde 44 şirket var. World Silver Survey 2026, Çin'in ihracatı yasakladığı yönündeki "
            "haberleri hatalı buluyor.",
            "Açık, fiyatın yönü hakkında tek başına bir şey söylemez; fiyat yatırım talebine de bağlıdır.",
        ],
        "kaynaklar": [WSS, WSS_BULTEN,
                      ("Çin Ticaret Bakanlığı (MOFCOM), 12 Aralık 2025 bildirimi",
                       "https://www.mofcom.gov.cn/zwgk/zcfb/art/2025/art_c3f0ac23c9c247e88b945db9f5c1d388.html")],
    },
    {
        "id": "turkiye",
        "baslik": "Türkiye'de gümüş: ayar ve vergi",
        "giris": ("Ayar, bin birimlik alaşımın kaç biriminin saf gümüş olduğunu gösterir (milyem). "
                  "Damga ürünün üzerinde yazar."),
        "tablo": {"basliklar": ["Damga", "Anlamı"], "satirlar": [
            ["999 / 999,9", "Saf gümüş; külçe ve granül"],
            ["925", "Takının yaygın standardı (sterling); kalanı genelde bakır"],
            ["958", "İngiltere'de Britannia ayarı"],
            ["830 / 800", "Uluslararası damga sözleşmesinin tanıdığı düşük ayarlar; en düşüğü 800"],
        ]},
        "maddeler": [
            "Külçe gümüş teslimi KDV'den istisnadır (KDV Kanunu md. 17/4-g).",
            "Gümüş takı, eşya ve sikke gümüşte KDV, satış bedelinin tamamından değil, içindeki külçe gümüş bedeli "
            "düşüldükten sonra kalan tutar üzerinden hesaplanır (KDV Genel Uygulama Tebliği III/A-4.2.2); "
            "genel oran %20.",
            "Darphane ve Damga Matbaası'nın kendi teslimleri KDV'den istisnadır (md. 17/4-f).",
            "Bankadaki gümüş (kıymetli maden) hesabında fiziki teslimat olmadan yapılan alım, 17 Mart 2025'ten beri "
            "kambiyo işlemi sayılır; binde 2 BSMV (kambiyo vergisi) alınır.",
            "Gümüşe erişim yolları: kuyumcu ve rafineriden fiziki külçe veya granül (fatura ve damga ile), "
            "bankaların gümüş hesapları, gümüşe dayalı fonlar.",
        ],
        "not": "Vergi bilgisi genel bilgilendirmedir; kendi durumunuz için mali müşavire danışın.",
        "kaynaklar": [
            ("Hallmarking Convention, Teknik Kararlar (PMC/W 2/2001 Rev. 12)",
             "https://hallmarkingconvention.org/users_uploads/editor/source/pmc-w-02-2001-rev-12-technical-decisions.pdf"),
            ("İngiltere, The Hallmarking Act 1973 (Amendment) Regulations 1998",
             "https://www.legislation.gov.uk/uksi/1998/2978/made"),
            ("3065 sayılı KDV Kanunu (mevzuat.gov.tr)", "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3065.pdf"),
            ("KDV Genel Uygulama Tebliği (TÜRMOB konsolide metin)", "https://www.turmob.org.tr/arsiv/mbs/pratikBilgiler/kdv_genteb-2023.pdf"),
            ("7346 sayılı Cumhurbaşkanı Kararı, KDV %20 (Resmî Gazete)", "https://www.resmigazete.gov.tr/eskiler/2023/07/20230707-11.pdf"),
            ("9595 sayılı Karar, kıymetli maden hesapları (Resmî Gazete)", "https://www.resmigazete.gov.tr/eskiler/2025/03/20250315-14.pdf"),
            ("3031 sayılı Karar, kambiyo BSMV binde 2 (Resmî Gazete)", "https://www.resmigazete.gov.tr/eskiler/2020/09/20200930-17.pdf"),
        ],
    },
    {
        "id": "dikkat",
        "baslik": "Bilinmesi gerekenler",
        "maddeler": [
            "Oynaklık: Gümüş fiyatı altına göre çok daha sert inip çıkabilir; 30 Ocak 2026'da spot fiyat bir günde "
            "yaklaşık %28 düştü.",
            "Makas: Alış ile satış fiyatı arasında fark vardır; aynı gün alıp satan, bu fark kadar düşük tutar alır. "
            "Makas yerden yere değişir.",
            "İşçilik: Takı ve eşyada işçilik bedeli vardır; bozdururken genelde yalnızca içindeki saf gümüşün "
            "değeri üzerinden hesap yapılır.",
            "Kararma: Gümüş havadaki kükürtle tepkimeye girip kararır (gümüş sülfür); bu, içindeki gümüş miktarını "
            "değiştirmez (Gümüş rehberi #10).",
            "Hacim: Aynı değerdeki gümüş, altından çok daha fazla yer kaplar (Gümüş rehberi #12).",
        ],
        "kaynaklar": [("QNA / The Peninsula (30 Ocak 2026)",
                       "https://thepeninsulaqatar.com/article/31/01/2026/gold-prices-post-biggest-one-day-drop-in-four-decades")],
    },
    {
        "id": "sozluk",
        "baslik": "Sözlük",
        "tablo": {"basliklar": ["Terim", "Anlamı"], "satirlar": [
            ["Troy ons", "Değerli madenlerin ağırlık birimi: 31,1035 g (günlük ons 28,35 g)."],
            ["Spot fiyat", "Hemen teslim için geçerli anlık piyasa fiyatı."],
            ["LBMA", "Londra Külçe Piyasası Birliği; günlük referans gümüş fiyatı Londra'da belirlenir."],
            ["COMEX", "New York'taki metal vadeli işlem borsası."],
            ["Makas", "Alış ile satış fiyatı arasındaki fark."],
            ["Ayar / milyem", "Alaşımdaki saf gümüş oranı, binde olarak (925 = binde 925)."],
            ["Külçe ve granül", "Külçe kalıba dökülmüş blok; granül küçük taneler hâlinde saf gümüş."],
            ["Yan ürün", "Asıl amacı başka metal olan madenden çıkan ikincil metal."],
            ["Arz açığı", "Bir yılda toplam talebin toplam arzı aşan kısmı."],
            ["ETF / fon", "Borsada işlem gören, gümüşe dayalı yatırım fonu."],
        ]},
        "kaynaklar": [],
    },
]
