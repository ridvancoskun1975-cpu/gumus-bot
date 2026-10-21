"""Gümüş rehberi: profili çeşitlendiren, fiyat verisi kullanmayan bilgi gönderileri (kaydırmalı).

Her bölüm kapak + 3 sayfa olarak paylaşılır, hafta içi ~14:00'te otomatik gider.
Takvim: 1-2. bölümler 13 Ekim 2026 akşamı elle paylaşıldı (ONCEDEN_YAYIMLANAN); 3-6. bölümler
14-19 Ekim'de her iş günü (BASLANGIC); sonrası haftada 1, DUZENLI_GUNLER'de (çarşamba; Rıdvan 19 Ekim 2026) sırayla:
önce #7–#8, sonra rehber arşivi Reels'i (ARSIV_SIRASI: #3–#5), sonra #9 ve sonrası. Yeni bölüm eklemek için BOLUMLER'in
sonuna ekle; takvime kendiliğinden girer. Bölümler bitince zamanlı çalışma bir şey paylaşmaz.
Elle göndermek için Actions → Run workflow → tür: bilgi, konu: <no>.
Rakamlar örnek ya da sabit değerlerdir (güncel fiyat içermez), bu yüzden MetalCharts hakkı harcanmaz.

Komut satırı: python bot/bilgi.py bugun  → bugünün bölüm numarasını yazar (yoksa boş)
              python bot/bilgi.py takvim → bütün takvimi yazar
              python bot/bilgi.py arsiv  → bugün rehber arşivi Reels'i yapılacak bölüm (yoksa boş; ARSIV_REELS)
              python bot/bilgi.py arsiv-takvim → rehber arşivi Reels'i günleri
"""
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

SERI = "GÜMÜŞ REHBERİ"
# Sitenin alan adı, paylaşımlarda yazıldığı biçimiyle (bot/sayfa.py → ALAN_ADI ile aynı; test_sayfa.py denetler).
# Rıdvan, 19 Ekim 2026 ("1 den başlayalım"): web sayfası tanıtımı, ek paylaşım açmadan var olan paylaşımlara site satırı.
# Biyografideki bağlantı her yerde "link bio'da" diye anılır (Rıdvan, 19 Ekim 2026: "daha sık kullanılan bir terim olmalı").
LINK_BIO = "link bio'da"
SITE = "gunlukgumus.com"
SITE_REHBER = f"Rehberin tamamı ve hesap makinesi sitemizde: {SITE}/rehber ({LINK_BIO})"
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# Takvim dışında elle paylaşılan bölümler: {bölüm no: TR tarihi}. 13 Ekim 2026 akşamı profil boş
# görünmesin diye 1-2. bölümler Run workflow ile paylaşıldı; zamanlı takvim 3. bölümden devam eder.
ONCEDEN_YAYIMLANAN = {
    1: "2026-10-13",
    2: "2026-10-13",
}
# İlk hafta her iş günü bir bölüm (TR tarihi). 20 ve 21 Ekim (#7, #8) Rıdvan'ın 19 Ekim 2026 kararıyla kaldırıldı
# ("rehber bölümlerini haftada 1'e düşürelim. ben de rahatça öne çıkarabilirim." — "evet"): #7 ve #8 haftalık sıraya girdi.
BASLANGIC = {
    "2026-10-14": 3,
    "2026-10-15": 4,
    "2026-10-16": 5,
    "2026-10-19": 6,
}
# Sonrasında haftada 1: çarşamba (Pazartesi = 0). Rıdvan, 19 Ekim 2026: takipçiyi bıktırmamak için paylaşım
# sayısı azaltıldı; salı ve perşembe (haftada 2) yerine haftada 1. Ayda 4 yeni bölüm gelen aylık paketle aynı hız.
DUZENLI_BASLANGIC = date(2026, 10, 26)
DUZENLI_GUNLER = {2}

# Her sayfada isteğe bağlı alanlar: buyuk + buyuk_alt (büyük rakam), formul, tablo [(etiket, değer)],
# maddeler (görselde ayrı satırlar; kısa tut), kaynak (küçük not).
BOLUMLER = [
    {
        "baslik": "Ons nedir?",
        "alt": "Gümüş fiyatı neden onsla verilir, bir ons kaç gram eder?",
        "buyuk": "31,1035 g",
        "buyuk_alt": "1 troy ons",
        "hashtag": "#gümüş #gramgümüş #değerlimetaller #emtia #silver",
        "soru": "Gümüşü siz hangi birimle takip ediyorsunuz: ons mu, gram mı?",
        "sayfalar": [
            {
                "baslik": "Troy ons",
                "buyuk": "31,1035 g",
                "buyuk_alt": "1 troy ons",
                "maddeler": [
                    "Altın, gümüş ve platin gibi değerli metaller dünyada troy ons ile fiyatlanır.",
                    "Ekranlarda “ons gümüş” diye görülen fiyat, 1 troy ons saf gümüşün dolar fiyatıdır.",
                    "Adını, ortaçağın ünlü ticaret panayırlarının kurulduğu Fransız şehri Troyes'dan "
                    "aldığı düşünülür.",
                ],
            },
            {
                "baslik": "Mutfaktaki onsla karıştırmayın",
                "tablo": [
                    ("Troy ons (değerli metal)", "31,1035 g"),
                    ("Günlük ons (yiyecek, posta)", "28,3495 g"),
                    ("Troy ons daha ağır", "%9,7"),
                ],
                "maddeler": [
                    "Değerli metal fiyatlarında “ons” denince her zaman troy ons kastedilir.",
                ],
            },
            {
                "baslik": "Pratik dönüşümler",
                "tablo": [
                    ("1 troy ons", "31,1035 g"),
                    ("1 kilogram", "32,15 troy ons"),
                    ("100 gram", "3,215 troy ons"),
                    ("1 gram", "0,0322 troy ons"),
                ],
                "maddeler": [
                    "Ons fiyatı 31,1035'e bölününce 1 gramın dolar fiyatı bulunur; dolar/TL ile "
                    "çarpınca TL fiyatı çıkar.",
                ],
            },
        ],
    },
    {
        "baslik": "Gram gümüş nasıl hesaplanır?",
        "alt": "Tek satırlık formül ve adım adım bir örnek.",
        "buyuk": "÷ 31,1035",
        "buyuk_alt": "formülün sabit sayısı: bir onstaki gram",
        "hashtag": "#gümüş #gramgümüş #gümüşfiyatları #gümüşyatırımı #gumus",
        "soru": "Hesabı kendiniz yapmayı denediniz mi? Sonucu yorumlara yazın.",
        "sayfalar": [
            {
                "baslik": "Formül",
                "formul": "Gram gümüş = ons gümüş × dolar/TL ÷ 31,1035",
                "maddeler": [
                    "Ons gümüş dolar cinsindendir; dolar/TL ile çarpınca 1 onsun TL fiyatı bulunur.",
                    "Bunu bir onstaki gram sayısına (31,1035) bölünce 1 gram saf gümüşün TL fiyatı çıkar.",
                ],
            },
            {
                "baslik": "Örnek",
                "tablo": [
                    ("Ons gümüş", "50,00 $"),
                    ("Dolar/TL", "50,00 ₺"),
                    ("1 ons (50 × 50)", "2.500,00 ₺"),
                    ("1 gram (2.500 ÷ 31,1035)", "80,38 ₺"),
                ],
                "maddeler": [
                    "Rakamlar yalnızca örnektir, güncel fiyat değildir. Güncel değerler günlük "
                    "paylaşımlarımızda.",
                ],
            },
            {
                "baslik": "Fiyatı iki şey değiştirir",
                "maddeler": [
                    "Ons sabitken dolar/TL %1 artarsa gram gümüş de %1 artar.",
                    "Kur sabitken ons %1 düşerse gram gümüş de %1 düşer.",
                    "İkisi birlikte hareket edince etkiler birleşir: ons %2 düşer, kur %1 artarsa "
                    "gram gümüş yaklaşık %1 düşer.",
                ],
            },
        ],
    },
    {
        "baslik": "Külçede 999 ne demek?",
        "alt": "Saflık, milyem ve takıdaki 925 farkı.",
        "buyuk": "999",
        "buyuk_alt": "binde 999 saf gümüş",
        "hashtag": "#gümüş #külçegümüş #gümüşyatırımı #değerlimetaller #silver",
        "soru": "Gümüşü siz hangi biçimde tercih ediyorsunuz: külçe mi, takı mı? Yorumlarda konuşalım.",
        "sayfalar": [
            {
                "baslik": "Binde kaç saf?",
                "buyuk": "999",
                "buyuk_alt": "1000 birimin 999'u saf gümüş",
                "maddeler": [
                    "Gümüşün saflığı binde (milyem) olarak yazılır.",
                    "Yatırım amaçlı külçe gümüş genelde 999 ya da 999,9 saflıktadır.",
                    "Saflık, ağırlık ve üretici bilgisi genelde külçenin üzerinde damgalıdır.",
                ],
            },
            {
                "baslik": "Takıda 925",
                "tablo": [
                    ("999,9", "%99,99 gümüş · külçe"),
                    ("999", "%99,9 gümüş · külçe"),
                    ("925", "%92,5 gümüş · takı"),
                ],
                "maddeler": [
                    "Saf gümüş yumuşaktır; takıda sertlik için genelde bakırla alaşım yapılır. "
                    "925 ayara “sterling gümüş” de denir.",
                ],
            },
            {
                "baslik": "Başka ayarlar",
                "tablo": [
                    ("958", "%95,8 gümüş · Britannia"),
                    ("830", "%83 gümüş"),
                    ("800", "%80 gümüş · en düşük"),
                ],
                "maddeler": [
                    "Uluslararası damga sözleşmesinde gümüş için en düşük ayar 800'dür; "
                    "830, 925, 958 ve 999 gibi ayarlar da tanınır.",
                    "958 ayarı İngiltere'de Britannia ayarı olarak bilinir.",
                ],
                "kaynak": "Kaynak: Hallmarking Convention teknik kararları; İngiltere Hallmarking Act 1973",
            },
            {
                "baslik": "Külçede ne yazar?",
                "maddeler": [
                    "Uluslararası piyasadaki büyük külçelerde rafineri damgası, seri numarası, "
                    "saflık ve 2019'dan beri üretim ayı ile yılı bulunur.",
                    "Bu külçeler yaklaşık 1.000 ons (±%10) ağırlığında ve en az 999 saflıktadır.",
                ],
                "kaynak": "Kaynak: LBMA Good Delivery teknik şartları",
            },
            {
                "baslik": "Fiyata etkisi",
                "maddeler": [
                    "Paylaşımlarımızdaki gram fiyat saf gümüş içindir.",
                    "925 ayar 10 gramlık bir takıda yaklaşık 9,25 gram saf gümüş vardır.",
                    "Takının fiyatını çoğu zaman işçilik ve tasarım belirler; içindeki gümüşün "
                    "değeri fiyatın küçük bir kısmı olabilir.",
                ],
            },
        ],
    },
    {
        "baslik": "Altın/gümüş paritesi ne anlatır?",
        "alt": "Paylaşımlarımızdaki o oranın anlamı.",
        "buyuk": "Au ÷ Ag",
        "buyuk_alt": "1 ons altın kaç ons gümüş eder",
        "hashtag": "#gümüş #gümüşyatırımı #değerlimetaller #emtia #gumus",
        "soru": "Pariteyi takip ediyor musunuz? Yorumlara yazın.",
        "sayfalar": [
            {
                "baslik": "Tanım",
                "formul": "Parite = ons altın ÷ ons gümüş",
                "maddeler": [
                    "1 ons altının kaç ons gümüş ettiğini gösterir.",
                    "Örnek: altın 4.000 $, gümüş 50 $ ise parite 80'dir (örnek rakamlar).",
                    "Birimden bağımsızdır: dolar, TL, ons ya da gram fark etmez, oran aynı kalır.",
                ],
            },
            {
                "baslik": "Nasıl okunur?",
                "maddeler": [
                    "Parite yükselirse gümüş altına göre görece ucuzlamış, düşerse görece "
                    "pahalanmış demektir.",
                    "Pariteyi hangi metalin daha çok hareket ettiği belirler. İki metal birlikte "
                    "yükselirken de parite değişebilir.",
                    "Paylaşımlarımızdaki ok, paritenin önceki iş gününe göre yönünü gösterir.",
                ],
            },
            {
                "baslik": "Geçmişte parite",
                "tablo": [
                    ("1980 başı", "20'nin altı"),
                    ("Mart 2020", "120'nin üstü"),
                ],
                "maddeler": [
                    "Son 50 yılda çok geniş bir aralıkta dolaştı.",
                    "Tek başına al-sat sinyali değildir: yüksek parite daha da yükselebilir, "
                    "düşük parite daha da düşebilir.",
                ],
            },
        ],
    },
    {
        "baslik": "Gümüş fiyatını ne hareket ettirir?",
        "alt": "Ons tarafı ve kur tarafı.",
        "buyuk": "%50+",
        "buyuk_alt": "gümüş talebinin sanayiden gelen payı",
        "hashtag": "#gümüş #gümüşfiyatları #emtia #değerlimetaller #silver",
        "soru": "Sizce gümüşü en çok ne etkiliyor: sanayi mi, dolar mı, kur mu?",
        "sayfalar": [
            {
                "baslik": "Hem değerli hem sanayi metali",
                "buyuk": "%50+",
                "buyuk_alt": "talebin sanayiden gelen payı",
                "maddeler": [
                    "Gümüş talebinin yarıdan fazlası sanayiden gelir: elektronik, güneş paneli, otomotiv.",
                    "Piyasası altından küçüktür; fiyatı genelde altından daha oynak seyreder.",
                ],
                "kaynak": "Kaynak: The Silver Institute, World Silver Survey",
            },
            {
                "baslik": "Dolar ve faiz",
                "maddeler": [
                    "Ons gümüş dolarla fiyatlanır; dolar dünya genelinde güçlendiğinde ons fiyatı "
                    "çoğu zaman baskı altında kalır.",
                    "Faiz getirmeyen bir varlık olduğu için faiz beklentileri de fiyatı etkiler.",
                    "Çoğu zaman altınla aynı yönde hareket eder, ama her zaman değil.",
                ],
            },
            {
                "baslik": "Türkiye'de bir de kur var",
                "maddeler": [
                    "Gram gümüşün TL fiyatını iki şey belirler: ons fiyatı ve dolar/TL.",
                    "Ons yatay seyrederken dolar/TL yükselirse gram gümüş de yükselir.",
                    "Bu yüzden paylaşımlarımızda gram fiyat, parite ve dolar/TL ayrı ayrı gösterilir.",
                ],
            },
        ],
    },
    {
        "baslik": "Kuyumcudaki fiyat neden farklı?",
        "alt": "Gösterge fiyatla aradaki farkı açan makas, işçilik, vergi ve kur.",
        "buyuk": "4",
        "buyuk_alt": "farkı açan dört kalem",
        "hashtag": "#gümüş #gramgümüş #külçegümüş #gümüşfiyatları #gumus",
        "soru": "Sizin gördüğünüz fark ne kadardı? Yorumlarda paylaşın.",
        "sayfalar": [
            {
                "baslik": "Makas",
                "maddeler": [
                    "Gösterge fiyat tek bir orta değerdir; alış ya da satış fiyatı değildir.",
                    "Kuyumcu ve bankalar alırken daha düşük, satarken daha yüksek fiyat verir. "
                    "Aradaki farka makas denir.",
                    "Piyasa hareketliyken makas genelde açılır.",
                ],
            },
            {
                "baslik": "İşçilik ve vergi",
                "maddeler": [
                    "Takı ve hediyelik ürünlerde işçilik ücreti eklenir.",
                    "Vergiler fiyata yansıyabilir; ürüne ve satış şekline göre değişir.",
                    "Küçük külçelerde üretim maliyeti gram başına daha yüksektir.",
                ],
            },
            {
                "baslik": "Kur ve zaman",
                "maddeler": [
                    "Paylaşımlarımız ECB orta kurunu kullanır; bankaların döviz alış kurundan "
                    "genelde binde birkaç yüksektir.",
                    "Kuyumcu fiyatı anlık değişir; paylaşımlarımız günde iki kez güncellenir.",
                    "Gösterge fiyat fikir edinmek içindir; işlemden önce güncel alış-satış "
                    "fiyatını sorun.",
                ],
            },
        ],
    },
    {
        "baslik": "Gümüş nerede kullanılır?",
        "alt": "Takıdan güneş paneline: gümüşün iş başındaki hali.",
        "buyuk": "#1",
        "buyuk_alt": "elektriği ve ısıyı en iyi ileten metal",
        "hashtag": "#gümüş #değerlimetaller #emtia #gümüşyatırımı #silver",
        "soru": "Bu kullanım alanlarından hangisini biliyordunuz?",
        "sayfalar": [
            {
                "baslik": "Elektrik ve elektronik",
                "buyuk": "#1",
                "buyuk_alt": "elektrik ve ısı iletkenliğinde",
                "maddeler": [
                    "Gümüş, elektriği ve ısıyı bütün metallerden daha iyi iletir.",
                    "Anahtar, devre kartı ve bağlantı noktalarında kullanılır; telefonlarda ve "
                    "arabalarda az miktarda bulunur.",
                ],
            },
            {
                "baslik": "Güneş enerjisi",
                "maddeler": [
                    "Güneş panellerinde elektriği toplayan ince iletken çizgiler gümüşlü macunla basılır.",
                    "Güneş paneli kurulumları son yıllarda gümüşün en hızlı büyüyen kullanım "
                    "alanlarından biri oldu.",
                ],
                "kaynak": "Kaynak: The Silver Institute; ABD Jeoloji Araştırmaları Kurumu (USGS)",
            },
            {
                "baslik": "Sağlık, takı ve külçe",
                "maddeler": [
                    "Gümüş iyonları mikrop öldürücü olduğu için bazı yara örtülerinde ve tıbbi "
                    "malzemelerde kullanılır.",
                    "Takı, gümüş eşya, madeni para ve külçe talebin diğer büyük kısmını oluşturur.",
                    "Bir zamanlar en büyük kullanım alanlarından biri film fotoğrafçılığıydı.",
                ],
            },
        ],
    },
    {
        "baslik": "Gümüş nereden gelir?",
        "alt": "Madenler, yan ürünler ve geri dönüşüm.",
        "buyuk": "Meksika",
        "buyuk_alt": "dünyanın en büyük gümüş üreticisi",
        "hashtag": "#gümüş #değerlimetaller #emtia #külçegümüş #gumus",
        "soru": "Türkiye'deki gümüş madenlerini biliyor muydunuz?",
        "sayfalar": [
            {
                "baslik": "Çoğu yan ürün",
                "maddeler": [
                    "Gümüşün büyük kısmı kurşun-çinko, bakır ve altın madenlerinden yan ürün olarak çıkar.",
                    "Bu yüzden gümüş fiyatı yükselse bile üretim hemen artmayabilir; arzı başka "
                    "metallerin madenciliği de belirler.",
                ],
                "kaynak": "Kaynak: ABD Jeoloji Araştırmaları Kurumu (USGS)",
            },
            {
                "baslik": "Başlıca üreticiler",
                "tablo": [
                    ("1. Meksika", "6.300 ton"),
                    ("2. Peru", "3.600 ton"),
                    ("3. Çin", "3.400 ton"),
                ],
                "maddeler": [
                    "Bolivya, Şili, Polonya, Rusya, ABD ve Avustralya da büyük üreticiler arasında.",
                ],
                "kaynak": "2025 maden üretimi tahmini · USGS Mineral Commodity Summaries 2026",
            },
            {
                "baslik": "Geri dönüşüm ve Türkiye",
                "maddeler": [
                    "Dünya arzının yaklaşık beşte biri eski takı, gümüş eşya ve sanayi atıklarının "
                    "geri dönüşümünden gelir.",
                    "Türkiye'de gümüş denince akla gelen yerlerden biri Kütahya Gümüşköy'deki maden "
                    "işletmesidir.",
                ],
                "kaynak": "Kaynak: The Silver Institute (2024: 1.014 milyon ons arzın 194 milyonu geri dönüşüm)",
            },
        ],
    },
    {
        "baslik": "Gümüş fiyatı nerede belirlenir?",
        "alt": "Londra, New York, Şanghay ve hafta sonu boşluğu.",
        "buyuk": "24/5",
        "buyuk_alt": "hafta içi neredeyse kesintisiz işlem",
        "hashtag": "#gümüş #gümüşfiyatları #emtia #değerlimetaller #silver",
        "soru": "Gümüş fiyatını en çok nereden takip ediyorsunuz?",
        "sayfalar": [
            {
                "baslik": "Tek bir borsa yok",
                "maddeler": [
                    "Gümüş, dünya genelinde bankalar ve borsalar arasında hafta içi neredeyse 24 "
                    "saat alınıp satılır.",
                    "Ekranlarda görülen ons fiyatı bu işlemlerden oluşan anlık (spot) fiyattır.",
                ],
            },
            {
                "baslik": "Büyük merkezler",
                "tablo": [
                    ("Londra", "fiziki piyasa"),
                    ("New York", "vadeli işlemler"),
                    ("Şanghay", "Asya borsası"),
                ],
                "maddeler": [
                    "Londra'da her iş günü belirlenen LBMA gümüş fiyatı birçok sözleşmede referans alınır.",
                ],
            },
            {
                "baslik": "Hafta sonu",
                "maddeler": [
                    "Cumartesi ve pazar ana piyasalar kapalıdır; ekranlarda cuma kapanışı görünür.",
                    "Pazartesi açılışında fiyat, hafta sonu gelişmelerine göre cuma kapanışından "
                    "farklı başlayabilir.",
                    "Bu yüzden hafta sonu günlük fiyat paylaşımı yapmıyoruz.",
                ],
            },
        ],
    },
    {
        "baslik": "Gümüş neden kararır?",
        "alt": "Kararmanın nedeni ve saklama.",
        "buyuk": "kükürt",
        "buyuk_alt": "kararmanın asıl sebebi",
        "hashtag": "#gümüş #külçegümüş #gümüşyatırımı #değerlimetaller #gumus",
        "soru": "Gümüşlerinizi nasıl saklıyorsunuz?",
        "sayfalar": [
            {
                "baslik": "Paslanma değil",
                "maddeler": [
                    "Gümüş havadaki kükürtlü gazlarla tepkimeye girer; yüzeyde ince bir gümüş "
                    "sülfür tabakası oluşur.",
                    "Nem, lastik ve kauçuk, yumurta ve soğan gibi kükürtlü maddeler kararmayı hızlandırır.",
                ],
            },
            {
                "baslik": "Değeri değişir mi?",
                "maddeler": [
                    "Kararma yalnızca yüzeydedir; külçenin saflığı ve ağırlığı değişmez.",
                    "Koleksiyon paralarında sert parlatma çizik bırakıp koleksiyon değerini düşürebilir.",
                ],
            },
            {
                "baslik": "Saklama",
                "maddeler": [
                    "Kuru ve hava almayan bir kap, mümkünse orijinal ambalaj kararmayı yavaşlatır.",
                    "Kararma önleyici bez ve poşetler de yardımcı olur.",
                    "Takılarda yumuşak bir bezle silmek çoğu zaman yeterlidir.",
                ],
            },
        ],
    },
    {
        "baslik": "Külçe gümüş hangi boylarda olur?",
        "alt": "1 onstan 30 kiloya: boy, prim ve pratiklik.",
        "buyuk": "~31 kg",
        "buyuk_alt": "uluslararası piyasanın standart külçesi (yaklaşık 1.000 ons)",
        "hashtag": "#gümüş #külçegümüş #gramgümüş #gümüşyatırımı #silver",
        "soru": "Sizce en pratik boy hangisi?",
        "sayfalar": [
            {
                "baslik": "Yaygın boylar",
                "tablo": [
                    ("1 ons", "31,1 g"),
                    ("100 g", "3,2 ons"),
                    ("1 kg", "32,15 ons"),
                    ("1.000 ons", "yaklaşık 31 kg"),
                ],
                "maddeler": [
                    "Bireysel alımlarda genelde 1 ons ile 1 kg arası boylar görülür.",
                ],
            },
            {
                "baslik": "Büyük külçe",
                "maddeler": [
                    "Uluslararası piyasada el değiştiren standart külçe yaklaşık 1.000 ons (±%10; "
                    "yaklaşık 28–34 kg) ağırlığında ve en az 999 saflıktadır. 2025'ten önce "
                    "üretilenlerde aralık 750–1.100 ons.",
                    "Bu külçeler genelde bankalar, rafineriler ve fonlar arasında el değiştirir.",
                ],
                "kaynak": "Kaynak: LBMA Good Delivery kuralları",
            },
            {
                "baslik": "Küçük boy, yüksek prim",
                "maddeler": [
                    "Küçük külçelerde üretim ve ambalaj maliyeti gram başına daha yüksektir; gram "
                    "fiyatı büyük külçeden yüksek olur.",
                    "Büyük külçe gram başına daha ucuzdur ama bölünemez; satarken tamamı satılır.",
                ],
            },
        ],
    },
    {
        "baslik": "Aynı değerde altın ve gümüş",
        "alt": "Parite 80 iken gümüş ne kadar yer kaplar?",
        "buyuk": "147×",
        "buyuk_alt": "aynı değerdeki gümüşün hacmi, altına göre (parite 80 iken)",
        "hashtag": "#gümüş #değerlimetaller #gümüşyatırımı #emtia #gumus",
        "soru": "Bu farkı tahmin etmiş miydiniz?",
        "sayfalar": [
            {
                "baslik": "Ağırlık",
                "formul": "Parite 80 → 1 ons altın = 80 ons gümüş",
                "maddeler": [
                    "Aynı değer için gümüş, altından parite kadar kat ağırdır.",
                    "Örnek: parite 80 iken 100 gram altın değerindeki gümüş 8 kilogram eder.",
                ],
            },
            {
                "baslik": "Hacim",
                "tablo": [
                    ("Altın yoğunluğu", "19,3 g/cm³"),
                    ("Gümüş yoğunluğu", "10,5 g/cm³"),
                    ("Aynı değerde hacim", "~147 kat"),
                ],
                "maddeler": [
                    "Gümüş hem daha ucuz hem daha hafif bir metaldir; aynı değer çok daha büyük yer kaplar.",
                ],
            },
            {
                "baslik": "Pratikte ne demek?",
                "maddeler": [
                    "Taşıma ve saklama, gümüşte değere oranla daha fazla yer ister.",
                    "Öte yandan gümüş, küçük tutarlar için daha küçük birimlere bölünebilir.",
                    "Hangisinin uygun olduğu kişinin amacına göre değişir; bu bir tercih önerisi değildir.",
                ],
            },
        ],
    },
    {
        "baslik": "Akçeden kuruşa: gümüş para",
        "alt": "Osmanlı'dan bugüne paranın gümüşle hikâyesi.",
        "buyuk": "akçe",
        "buyuk_alt": "Osmanlı'nın gümüş sikkesi",
        "hashtag": "#gümüş #değerlimetaller #gramgümüş #külçegümüş #gumus",
        "soru": "Evinizde eski bir gümüş sikke var mı?",
        "sayfalar": [
            {
                "baslik": "Akçe",
                "maddeler": [
                    "Osmanlı'nın temel sikkesi akçe gümüştendi; ilk akçeler Orhan Gazi döneminde basıldı.",
                    "Adı “ak” (beyaz) kelimesinden gelir, gümüşün rengine işaret eder.",
                    "Devlet zaman zaman akçedeki gümüş oranını düşürdü; buna tağşiş denir.",
                ],
            },
            {
                "baslik": "Kuruş",
                "maddeler": [
                    "Kuruş, 17. yüzyılın sonunda basılmaya başlanan iri bir gümüş sikkeydi.",
                    "Zamanla kâğıt para ve ucuz metal alaşımları gümüşün yerini aldı.",
                ],
            },
            {
                "baslik": "Dünyada",
                "maddeler": [
                    "İngiliz sterlini adını “sterling” gümüşten alır; başlangıçta bir pound "
                    "ağırlığındaki gümüşe dayanıyordu.",
                    "Bugün dolaşımdaki paralarda gümüş neredeyse hiç kullanılmıyor.",
                ],
            },
        ],
    },
    {
        "baslik": "Gerçek gümüş nasıl anlaşılır?",
        "alt": "Basit ipuçları ve kesin yol.",
        "buyuk": "999 · 925",
        "buyuk_alt": "damga ilk ipucu, kesin kanıt değil",
        "hashtag": "#gümüş #külçegümüş #gramgümüş #gümüşyatırımı #silver",
        "soru": "Siz hiç sahte gümüşle karşılaştınız mı?",
        "sayfalar": [
            {
                "baslik": "Damga",
                "maddeler": [
                    "Gerçek gümüş ürünlerde genelde 925 ya da 999 gibi bir saflık damgası bulunur.",
                    "Damga tek başına kanıt değildir; sahte üründe de damga olabilir.",
                ],
            },
            {
                "baslik": "Basit ipuçları",
                "maddeler": [
                    "Gümüş mıknatısa yapışmaz; yapışıyorsa içinde demir ya da nikel vardır.",
                    "Gümüş ısıyı çok iyi iletir; üzerine konan buz başka metallere göre hızlı erir.",
                    "Bu yöntemler yalnızca fikir verir; bazı sahteler bu testleri de geçer.",
                ],
            },
            {
                "baslik": "Kesin yol",
                "maddeler": [
                    "Saflık, kuyumcuda ya da bir ayar laboratuvarında yapılan ölçümle kesinleşir.",
                    "Külçede tanınmış üretici, seri numarası ve fatura güven sağlar.",
                    "Fiyatı piyasanın çok altında olan ürünlere dikkat edin.",
                ],
            },
        ],
    },
    # #15 — rehber ön paketi parti 1 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüşün simgesi neden Ag?",
        "alt": "Latince adından Arjantin'e: gümüşün adları.",
        "buyuk": "Ag",
        "buyuk_alt": "Latince argentum'dan",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #gumus #silver",
        "soru": "Gümüşün başka dillerdeki adlarından hangisini biliyordunuz?",
        "sayfalar": [
            {
                "baslik": "Latince argentum",
                "maddeler": [
                    "Gümüşün kimyasal simgesi Ag. Bu simge, Latince adı argentum'dan gelir.",
                    "Argentum, “parlamak, beyaz” anlamında çok eski bir Hint-Avrupa köküne dayanır: gümüş, “parlayan, beyaz metal”dir.",
                    "Gümüşün atom numarası 47'dir; periyodik tabloda bakır ve altınla aynı sütundadır."
                ]
            },
            {
                "baslik": "Simgeler Latince adlardan",
                "tablo": [
                    [
                        "Ag",
                        "argentum · gümüş"
                    ],
                    [
                        "Au",
                        "aurum · altın"
                    ],
                    [
                        "Pb",
                        "plumbum · kurşun"
                    ],
                    [
                        "Fe",
                        "ferrum · demir"
                    ]
                ],
                "maddeler": [
                    "İsveçli kimyacı Berzelius, 1813'te başlayan bir makalesinde simgeleri Latince adların baş harflerinden yapmayı önerdi.",
                    "Baş harfi aynı olan elementlerden birine ikinci bir harf eklenir; bugünkü simgeler büyük ölçüde bu sistemden gelir."
                ],
                "kaynak": "Kaynak: Britannica; Berzelius, Annals of Philosophy (1813–1814)"
            },
            {
                "baslik": "Başka dillerde gümüş",
                "maddeler": [
                    "Arjantin'in adı Latince argentum'dan gelir; Río de la Plata da “gümüş nehri” demektir.",
                    "Fransızcada argent hem gümüş hem para demektir.",
                    "Türkçe gümüş ise Eski Türkçe kümüş kelimesinden gelir; Orhun yazıtlarında “altun kümüş” diye geçer."
                ],
                "kaynak": "Kaynak: Nişanyan Sözlük; TDK; Larousse"
            }
        ]
    },
    # #16 — rehber ön paketi parti 1 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüş neden değerli metal sayılır?",
        "alt": "Nadirlik, dayanıklılık ve altınla farkı.",
        "buyuk": "~0,075 g",
        "buyuk_alt": "bir ton yer kabuğundaki ortalama gümüş",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #emtia #silver",
        "soru": "Sizce gümüşü değerli yapan en önemli özellik hangisi?",
        "sayfalar": [
            {
                "baslik": "Değerli metal ne demek?",
                "maddeler": [
                    "Doğada bulunan, nadir ve ekonomik değeri yüksek metallere değerli (kıymetli) metal denir.",
                    "Genelde altın, gümüş ve platin grubu metaller sayılır; liste kaynağa göre biraz değişir.",
                    "Türk kambiyo mevzuatı altın, gümüş, platin ve paladyumu kıymetli maden sayar; dördünün de uluslararası para kodu var."
                ]
            },
            {
                "baslik": "Bir ton kayada ne kadar?",
                "tablo": [
                    [
                        "Gümüş",
                        "~0,075 g"
                    ],
                    [
                        "Altın",
                        "~0,004 g"
                    ],
                    [
                        "Platin",
                        "~0,005 g"
                    ]
                ],
                "maddeler": [
                    "Yer kabuğunun ortalaması. Gümüş altından kaynağa göre yaklaşık 20–40 kat bol; yine de nadir bir metaldir.",
                    "2025'te madenlerden yaklaşık 26.000 ton gümüş, 3.300 ton altın ve 170 ton platin çıkarıldı."
                ],
                "kaynak": "Kaynak: CRC el kitabı (yer kabuğu ortalaması; tahminler kaynağa göre değişir) · USGS 2026 (2025 tahmini)"
            },
            {
                "baslik": "Altından farkı: soy metal",
                "maddeler": [
                    "Altın ve platin havada kararmaz; nitrik asitte bile çözünmez, ama kral suyunda çözünür. Bunlara soy metal denir.",
                    "Gümüş havadaki kükürtle kararır ve nitrik asitte çözünür; ders kitaplarında “yarı soy” metal sayılır.",
                    "Yine de paslanmaz; kararma yalnızca yüzeydedir. Dayanıklı, bölünebilir ve taşınabilir olduğu için yüzyıllarca para oldu."
                ]
            }
        ]
    },
    # #17 — rehber ön paketi parti 1 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüş neden en parlak metaldir?",
        "alt": "Işığı en iyi yansıtan metal ve aynanın hikâyesi.",
        "buyuk": "%95–99",
        "buyuk_alt": "taze, temiz gümüşün yansıttığı görünür ışık",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #emtia #silver",
        "soru": "Evinizdeki aynanın arkasında hangi metal var, hiç merak ettiniz mi?",
        "sayfalar": [
            {
                "baslik": "Işığın neredeyse tamamı",
                "tablo": [
                    [
                        "Gümüş",
                        "%95–99"
                    ],
                    [
                        "Alüminyum",
                        "%90–92"
                    ],
                    [
                        "Altın",
                        "mavide ~%40, kırmızıda ~%97"
                    ]
                ],
                "maddeler": [
                    "Görünür ışıkta en yüksek yansıtma gümüştedir; tablo taze ve temiz yüzeyler içindir.",
                    "Nedeni serbest elektronlar; gümüşte ışığı soğuran geçişler morötesinde kaldığı için görünür ışık neredeyse tamamen geri döner."
                ],
                "kaynak": "Kaynak: ölçülmüş optik sabitler (Johnson ve Christy 1972; McPeak vd. 2015); Los Alamos Ulusal Laboratuvarı"
            },
            {
                "baslik": "Morötesi ve altının rengi",
                "maddeler": [
                    "Morötesinde, 320 nanometre civarında gümüşün yansıtması %10'un altına düşer; orada alüminyum öndedir.",
                    "Gümüş bütün renkleri hemen hemen eşit yansıttığı için beyaz görünür.",
                    "Altın mavi ışığın çoğunu soğurur, sarı ve kırmızıyı yansıtır; bu yüzden sarıdır."
                ]
            },
            {
                "baslik": "Aynadan teleskoba",
                "maddeler": [
                    "Camı gümüşle kaplama yöntemini Alman kimyacı Justus von Liebig 1835'te buldu; önceki aynalarda cıva-kalay karışımı vardı.",
                    "Gümüş kararır; teleskop aynalarında ve ısı yansıtan pencere camlarında gümüş, koruyucu katmanların arasında durur."
                ],
                "kaynak": "Kaynak: Britannica; Cerro Pachón gözlemevi duyurusu (2004); Efficient Windows Collaborative"
            }
        ]
    },
    # #18 — rehber ön paketi parti 1 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüş hangi birimlerle tartılır?",
        "alt": "Gram ve kilodan tola, tael, dirhem ve okkaya.",
        "buyuk": "gram · kg",
        "buyuk_alt": "Türkiye'de gram, Şanghay ve Hindistan'da kilogram",
        "hashtag": "#gümüş #gramgümüş #külçegümüş #değerlimetaller #gumus",
        "soru": "Büyüklerinizden okka ya da dirhem lafını hiç duydunuz mu?",
        "sayfalar": [
            {
                "baslik": "Gram ve kilogram",
                "maddeler": [
                    "Türkiye'de metre sistemi 1931 tarihli Ölçüler Kanunu ile zorunlu oldu; kanun 1 Ocak 1933'te uygulamaya girdi.",
                    "Şanghay ve Hindistan borsalarında gümüş kilogram başına fiyatlanır.",
                    "Londra'daki büyük külçenin ağırlığı ise troy onsla yazılır."
                ],
                "kaynak": "Kaynak: 1782 sayılı Ölçüler Kanunu (1931); 3516 sayılı Ölçüler ve Ayar Kanunu"
            },
            {
                "baslik": "Tola, tael, troy pound",
                "tablo": [
                    [
                        "1 tola (Güney Asya)",
                        "11,66 g"
                    ],
                    [
                        "1 tael (Hong Kong)",
                        "37,43 g"
                    ],
                    [
                        "1 troy pound (12 ons)",
                        "373,24 g"
                    ]
                ],
                "maddeler": [
                    "Tola tam olarak sekizde üç troy onstur. Pakistan'da gümüş fiyatı bugün de tola başına açıklanır.",
                    "Tablodaki tael, Hong Kong'da değerli metal için tanımlı taeldir; Çin'de günlük tael bugün 50 gramdır."
                ]
            },
            {
                "baslik": "Osmanlı'dan kalanlar",
                "tablo": [
                    [
                        "1 dirhem",
                        "~3,207 g"
                    ],
                    [
                        "1 miskal = 1,5 dirhem",
                        "~4,81 g"
                    ],
                    [
                        "1 okka = 400 dirhem",
                        "~1,282 kg"
                    ]
                ],
                "maddeler": [
                    "Miskal, altın ve gümüş gibi değerli maddeleri tartmak için kullanılırdı.",
                    "Değerler döneme ve yere göre değişir; tablodakiler en yaygın kabul gören değerlerdir."
                ],
                "kaynak": "Kaynak: TDK Güncel Türkçe Sözlük; TDV İslâm Ansiklopedisi"
            }
        ]
    },
    # #19 — rehber ön paketi parti 2 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Cevherden külçeye: gümüş nasıl üretilir?",
        "alt": "Madenden rafineriye gümüşün yolculuğu.",
        "buyuk": "4 adım",
        "buyuk_alt": "kayadan külçeye: çıkarma, zenginleştirme, ayrıştırma, döküm",
        "hashtag": "#gümüş #külçegümüş #değerlimetaller #emtia #silver",
        "soru": "Bir külçenin yolculuğunda en çok hangi adım ilginizi çekti?",
        "sayfalar": [
            {
                "baslik": "Madenden tesise",
                "maddeler": [
                    "Yüzeye yakın, büyük ama gümüşü az yataklar açık ocakta; derindeki zengin damarlar yer altında işletilir.",
                    "Kaya kırılır, çoğu zaman ince toz hâline gelene kadar öğütülür.",
                    "Flotasyonda toz suyla karıştırılıp hava verilir; istenen mineraller kabarcıklara tutunup köpükle yüzer. Bu ürüne konsantre denir."
                ]
            },
            {
                "baslik": "Gümüş nasıl ayrılır?",
                "tablo": [
                    [
                        "Kurşun cevheri",
                        "çinkoyla ayırma, kupelasyon"
                    ],
                    [
                        "Bakır cevheri",
                        "elektrolizde anot çamuru"
                    ],
                    [
                        "Altın-gümüş cevheri",
                        "siyanür liçi"
                    ]
                ],
                "maddeler": [
                    "Kurşun eritilince gümüş erimiş kurşunda kalır; katılan çinko gümüşü toplar ve yüzeyde kabuk olur.",
                    "Siyanürlü çözelti gümüşü öğütülmüş cevherden çözer; gümüş çinko tozuyla çöktürülür ya da aktif karbona tutturulur."
                ],
                "kaynak": "Kaynak: Britannica (Parkes ve siyanür yöntemleri, kupelasyon)"
            },
            {
                "baslik": "Çoğu yan ürün, sonu külçe",
                "tablo": [
                    [
                        "Kurşun-çinko madenleri",
                        "~%29"
                    ],
                    [
                        "Bakır madenleri",
                        "~%28"
                    ],
                    [
                        "Altın madenleri",
                        "~%16"
                    ],
                    [
                        "Gümüş madenleri",
                        "~%26"
                    ]
                ],
                "maddeler": [
                    "2025'te madenden çıkan gümüşün yaklaşık dörtte üçü başka metallerin madenlerinden yan ürün olarak geldi.",
                    "Ham gümüş rafineride genelde binde 999 ya da daha yüksek saflığa getirilir, sonra kalıba dökülüp külçe olur."
                ],
                "kaynak": "Kaynak: World Silver Survey 2026 (2025 maden üretimi)"
            }
        ]
    },
    # #20 — rehber ön paketi parti 2 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüş nasıl saflaştırılır?",
        "alt": "Ham gümüşten 999,9'a: rafinerinin işi.",
        "buyuk": "999,9",
        "buyuk_alt": "elektrolizle ulaşılan saflık (binde)",
        "hashtag": "#gümüş #külçegümüş #değerlimetaller #emtia #silver",
        "soru": "Eski gümüş eşyaların eritilip yeniden külçe olabildiğini biliyor muydunuz?",
        "sayfalar": [
            {
                "baslik": "Ham gümüş",
                "maddeler": [
                    "Rafineriye gelen gümüş saf değildir: madende dökülen doré külçeleri, bakır ve kurşun üretiminin yan ürünleri, hurda.",
                    "Doré yarı saf bir külçedir; çoğunlukla altın ve gümüşten oluşur.",
                    "Eski bir yöntem kupelasyondur: gümüşlü kurşun hava verilerek eritilir, kurşun oksitlenip ayrılır, gümüş kalır. Beş bin yılı aşkın süredir bilinir."
                ],
                "kaynak": "Kaynak: Britannica; LBMA; PLoS ONE (2015)"
            },
            {
                "baslik": "Elektrolizle saflaştırma",
                "maddeler": [
                    "Ham gümüş levhalar gümüş nitrat çözeltisine daldırılıp akım verilir; gümüş çözülür, karşı levhada saf kristaller hâlinde birikir.",
                    "Altın çözünmez, çamur olarak toplanır; bakır çözeltide kalır.",
                    "Bu yolla binde 999, hatta binde 999,9 ve üstü saflık elde edilir."
                ],
                "kaynak": "Kaynak: Metso; BullionStar; ABD patentleri (1992, 1997)"
            },
            {
                "baslik": "Geri kazanım ve onay",
                "maddeler": [
                    "Eski eşya, fotoğraf banyosu atıkları, elektronik hurda ve kullanılmış katalizörlerdeki gümüş de rafineride yeniden saflaştırılır.",
                    "2025'te eski takı ve gümüş eşya satışları geri dönüşümü artırdı; ama rafinerilerdeki darboğaz hacmi sınırladı.",
                    "Londra Külçe Piyasası Birliği'nin onaylı listesinde 2026'da 80'den fazla gümüş rafinerisi vardı."
                ],
                "kaynak": "Kaynak: The Silver Institute (15 Nisan 2026); LBMA Good Delivery listesi (Mayıs ve Ekim 2026)"
            }
        ]
    },
    # #21 — rehber ön paketi parti 2 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Külçe sikke nedir?",
        "alt": "Nominal değer, metal değeri ve külçeden farkı.",
        "buyuk": "1 ons",
        "buyuk_alt": "Silver Eagle, Maple Leaf ve Philharmoniker'deki gümüş",
        "hashtag": "#gümüş #külçegümüş #değerlimetaller #gumus #silver",
        "soru": "Bu sikkelerden hangisini daha önce gördünüz?",
        "sayfalar": [
            {
                "baslik": "Tanım",
                "maddeler": [
                    "Külçe sikke, değeri büyük ölçüde içindeki değerli metalden gelen, resmî darphanelerin bastığı sikkedir.",
                    "Üzerinde nominal değer yazar ve çıkaran ülkede yasal ödeme aracıdır; ama günlük alışverişte kullanılmaz.",
                    "Değerini içindeki gümüşün ağırlığı ve saflığı belirler. Basım adedi genelde önceden sınırlanmaz."
                ]
            },
            {
                "baslik": "Tanınmış örnekler",
                "tablo": [
                    [
                        "Silver Eagle (ABD)",
                        "1986"
                    ],
                    [
                        "Maple Leaf (Kanada)",
                        "1988"
                    ],
                    [
                        "Britannia (İngiltere)",
                        "1997"
                    ],
                    [
                        "Philharmoniker (Avusturya)",
                        "2008"
                    ]
                ],
                "maddeler": [
                    "Hepsi 1 ons gümüş içerir; yıl, ilk basım yılıdır. Saflık binde 999 (Maple Leaf'te 999,9; Britannia'da 2013'ten önce 958).",
                    "Nominal değerleri: 1 ABD doları, 5 Kanada doları, 2 sterlin, 1,50 avro. Avustralya'nın Kangaroo'su da tanınmış bir örnektir."
                ],
                "kaynak": "Kaynak: ABD Darphanesi, Kanada Kraliyet Darphanesi ve The Royal Mint ürün sayfaları; Wikipedia"
            },
            {
                "baslik": "Nominal değer ve farklar",
                "maddeler": [
                    "Nominal değer büyük ölçüde semboliktir. Örnek (güncel fiyat değil): ons 50 dolar iken Silver Eagle'daki gümüş ~50 dolar eder, üzerinde 1 dolar yazar.",
                    "Külçe (bar) ve özel üretim yuvarlak külçelerin genelde nominal değeri yoktur; yasal ödeme aracı da sayılmazlar.",
                    "Koleksiyon sikkesinin değerini ise metalin yanında nadirlik, kondisyon ve talep belirler."
                ]
            }
        ]
    },
    # #22 — rehber ön paketi parti 2 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Koleksiyon değeri ile metal değeri farkı nedir?",
        "alt": "Sikkedeki gümüşün değeri ve koleksiyoncunun biçtiği değer.",
        "buyuk": "1–70",
        "buyuk_alt": "sikkenin kondisyon puanı (Sheldon ölçeği)",
        "hashtag": "#gümüş #değerlimetaller #gramgümüş #gumus #silver",
        "soru": "Elinizdeki eski gümüş paranın yılına hiç baktınız mı?",
        "sayfalar": [
            {
                "baslik": "İki ayrı değer",
                "maddeler": [
                    "Metal değeri, sikkenin içindeki saf gümüşün değeridir; ağırlık, ayar ve gram fiyatıyla hesaplanır.",
                    "Koleksiyon (nümismatik) değeri, koleksiyoncuların gözündeki değerdir; metal değerinin kat kat üstüne çıkabilir.",
                    "Yaygın sikkelerde iki değer birbirine yakın olabilir; gümüşün pahalı olduğu dönemlerde bu sikkelerin birçoğu eritildi."
                ]
            },
            {
                "baslik": "Aynı gümüş, farklı yıl",
                "tablo": [
                    [
                        "1 lira 1937",
                        "1.624.000 adet"
                    ],
                    [
                        "1 lira 1938",
                        "8.282.000 adet"
                    ],
                    [
                        "1 lira 1939",
                        "376.000 adet"
                    ]
                ],
                "maddeler": [
                    "Üçünde de ~10 g saf gümüş var; metal değerleri aynı. Az basılan yıl ise genelde daha nadirdir.",
                    "Koleksiyon değerini nadirlik, kondisyon, talep ve tarihî önem birlikte belirler; eski olmak tek başına yetmez."
                ],
                "kaynak": "Kaynak: koleksiyon katalogları (basım adedi) · Amerikan Nümismatik Derneği · Perth Darphanesi"
            },
            {
                "baslik": "Kondisyon ve bakım",
                "maddeler": [
                    "Kondisyon, Sheldon ölçeğiyle 1'den 70'e puanlanabilir; 60 ve üstü aşınmamış sikke demektir.",
                    "PCGS ve NGC gibi derecelendirme kurumları sikkeyi ücret karşılığı inceler, puanlar ve mühürlü bir kutuya koyar.",
                    "Temizleme ve parlatma ince çizikler bırakır, koleksiyon değerini düşürür; eski sikke olduğu gibi saklanır."
                ],
                "kaynak": "Kaynak: ABD Darphanesi · Avustralya Kraliyet Darphanesi · PCGS · NGC"
            }
        ]
    },
    # #23 — rehber ön paketi parti 3 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüş tıpta neden kullanılır?",
        "alt": "Gümüş iyonu, tarihteki izleri ve resmî uyarılar.",
        "buyuk": "iyon",
        "buyuk_alt": "gümüşün mikroplara etki eden hâli",
        "hashtag": "#gümüş #değerlimetaller #emtia #gumus #silver",
        "soru": "Gümüşlü bir yara örtüsü ya da su filtresi hiç gördünüz mü?",
        "sayfalar": [
            {
                "baslik": "Gümüş iyonu",
                "maddeler": [
                    "Gümüş iyonu, bir elektronunu vermiş, artı yüklü gümüş atomudur. Görece düşük miktarlarda bile mikroplara etki eder.",
                    "Mikropların proteinlerindeki kükürtlü kısımlara sıkıca bağlanıp proteinleri bozar; hücre zarını bozar, DNA'ya da bağlanabilir.",
                    "Bugün bazı yara örtülerinde, kateter kaplamalarında ve su filtrelerinde gümüş bulunur. Dünya Sağlık Örgütü ise içme suyu için gümüşü önermez."
                ],
                "kaynak": "Kaynak: Antibiotics dergisi (2018); ABD CDC (2008); Dünya Sağlık Örgütü (2022)"
            },
            {
                "baslik": "Tarihte gümüş",
                "tablo": [
                    [
                        "Gümüş kaplarda su",
                        "Antik Çağ"
                    ],
                    [
                        "Yenidoğana göz damlası",
                        "1881"
                    ],
                    [
                        "Gümüşlü yanık kremi",
                        "1968"
                    ]
                ],
                "maddeler": [
                    "Herodotos, Pers kralının kaynatılmış suyunun seferlerde gümüş kaplarda taşındığını yazar; gümüşün neden seçildiğini yazmaz.",
                    "Alman hekim Credé'nin yönteminde yenidoğanın gözüne gümüş nitrat damlatılırdı. Antibiyotikler yaygınlaşınca gümüşün yeri daraldı."
                ],
                "kaynak": "Kaynak: Herodotos, Tarih; Dünya Sağlık Örgütü Bülteni (2001); Wounds UK (2018)"
            },
            {
                "baslik": "Sınırlar ve uyarılar",
                "maddeler": [
                    "Ağızdan alınan gümüş dokularda birikip deriyi gri-maviye boyayabilir. Arjiri denen bu renk değişikliği genellikle kalıcıdır.",
                    "ABD'de FDA, 1999'da reçetesiz kolloidal gümüş ürünlerinin güvenli ve etkili sayılmadığına karar verdi.",
                    "Bu bölüm tıbbi öneri değildir; sağlık ürünlerinin kullanımı için hekiminize danışın."
                ],
                "kaynak": "Kaynak: ABD FDA (1999); ABD NCCIH (2023); StatPearls"
            }
        ]
    },
    # #24 — rehber ön paketi parti 3 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Fotoğraf filmi gümüşle nasıl çalışır?",
        "alt": "Işığa duyarlı gümüş tuzlarından dagerotipe ve röntgene.",
        "buyuk": "1839",
        "buyuk_alt": "Daguerre'in gümüş kaplı levhasının duyurulduğu yıl",
        "hashtag": "#gümüş #değerlimetaller #emtia #gumus #silver",
        "soru": "Siz en son ne zaman filmli bir makineyle fotoğraf çektiniz?",
        "sayfalar": [
            {
                "baslik": "Işığa duyarlı gümüş tuzları",
                "maddeler": [
                    "Filmin ışığa duyarlı katmanında, jelatin içine dağılmış çok küçük gümüş halojenür kristalleri vardır.",
                    "Filmde çoğunlukla gümüş bromür, biraz da gümüş iyodür kullanılır; fotoğraf kâğıtlarında gümüş klorür de bulunur.",
                    "Işık çarpan kristalde birkaç gümüş atomluk, gözle görülmeyen bir iz kalır: gizli görüntü."
                ],
                "kaynak": "Kaynak: Britannica; George Eastman Müzesi; MFA CAMEO"
            },
            {
                "baslik": "Banyo ve sabitleme",
                "maddeler": [
                    "Banyo, gizli görüntüyü siyah metal gümüşe çevirir. Işığın çok düştüğü yer koyu çıkar; bu yüzden filmde ilk çıkan görüntü negatiftir.",
                    "Sabitleme, ışık almamış gümüş tuzlarını çözüp temizler; görüntü artık ışıkta bozulmaz.",
                    "Klasik siyah beyaz filmde görüntünün kendisi gümüştür. Renkli filmde gümüş ağartılıp çıkarılır; geriye boyalar kalır."
                ],
                "kaynak": "Kaynak: Britannica; Image Permanence Institute"
            },
            {
                "baslik": "Dagerotipten röntgene",
                "tablo": [
                    [
                        "Dagerotip",
                        "1839"
                    ],
                    [
                        "Jelatinli kuru plak",
                        "1870'ler"
                    ],
                    [
                        "Saydam rulo film",
                        "1889"
                    ]
                ],
                "maddeler": [
                    "Dagerotip, gümüş kaplı bakır bir levhaydı; negatifi olmadığı için her görüntü tek kopyaydı.",
                    "Röntgen filmleri de gümüş halojenürlüdür. Sabitleme çözeltisinde biriken gümüş toplanıp geri kazanılır."
                ],
                "kaynak": "Kaynak: Oxford Bilim Tarihi Müzesi; Image Permanence Institute; Science and Media Museum; Radiopaedia"
            }
        ]
    },
    # #25 — rehber ön paketi parti 3 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Güneş paneli ve elektrikli araç neden gümüş ister?",
        "alt": "Hücredeki ince çizgiler, araçtaki kontaklar ve bakıra geçiş.",
        "buyuk": "150–250",
        "buyuk_alt": "bir otomobildeki elektrik kontağı (tahmin); çoğu gümüşlü",
        "hashtag": "#gümüş #değerlimetaller #emtia #gumus #silver",
        "soru": "Güneş panelinin üstündeki ince çizgileri hiç fark ettiniz mi?",
        "sayfalar": [
            {
                "baslik": "Güneş hücresinde neden gümüş?",
                "maddeler": [
                    "Hücredeki ince gümüş çizgiler, ışıkla oluşan elektriği toplar. Gümüşlü macun hücreye basılır ve fırında pişirilir.",
                    "Gümüş elektriği en iyi ileten metaldir; bakırın direnci ~%6 fazladır. Hücreleri bağlayan şeritler de gümüşe lehimlenir.",
                    "Bakır ucuzdur, ama fırında oksitlenir ve silisyuma sızarak hücreye zarar verebilir. Bu yüzden gümüşün yerine kolayca geçemez."
                ],
                "kaynak": "Kaynak: NREL ve DuraMAT (2024); ISFH (2025); özdirenç tabloları (HyperPhysics)"
            },
            {
                "baslik": "Hücre türü ve bakıra geçiş",
                "tablo": [
                    [
                        "PERC",
                        "TOPCon'dan az"
                    ],
                    [
                        "TOPCon",
                        "~10 miligram"
                    ],
                    [
                        "Heterojonksiyon",
                        "~12 miligram"
                    ]
                ],
                "maddeler": [
                    "Bunlar 2025'te watt başına ortalama gümüştür. TOPCon ve heterojonksiyonda iki yüze de gümüş basılır.",
                    "Hücre başına gümüş 2007'de ~400 miligramdan 2016'da ~130 miligrama indi: daha ince çizgiler, daha az macun.",
                    "Gümüş kaplı bakır macun heterojonksiyonda yayılıyor; büyük üreticiler 2025 sonu ve 2026 başında bakırlı seri üretim planı açıkladı."
                ],
                "kaynak": "Kaynak: ITRPV 2026 (17. baskı); CRU / The Silver Institute (2018); pv magazine (Ocak 2026)"
            },
            {
                "baslik": "Elektrikli araçta gümüş",
                "maddeler": [
                    "2021 tahminine göre bir otomobilde 150–250 elektrik kontağı olabilir; çoğu gümüşlüdür: anahtar, röle, sigorta ve bağlantılar.",
                    "Elektrikli araçlarda batarya yönetim sistemi, şarj istasyonlarında da röle ve bağlantılar gümüş kullanır.",
                    "Aralık 2025 tahminine göre elektrikli araçların 2027'de araçlardaki gümüş talebinde içten yanmalı araçları geçmesi bekleniyor."
                ],
                "kaynak": "Kaynak: The Silver Institute (Ocak 2021; Aralık 2025, Oxford Economics)"
            }
        ]
    },
    # #26 — rehber ön paketi parti 3 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Gümüşhane adını nereden alır?",
        "alt": "Bir şehrin adındaki gümüş: madenler, darphane ve gerileme.",
        "buyuk": "gümüş yeri",
        "buyuk_alt": "adı, yakınındaki gümüş madenlerinden gelir",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #gumus #silver",
        "soru": "Adında gümüş geçen başka bir yer biliyor musunuz? Yorumlara yazın.",
        "sayfalar": [
            {
                "baslik": "Gümüş ve hâne",
                "maddeler": [
                    "Ad, gümüş ile Farsçadan gelen hâne kelimesinden oluşur. Hâne birleşik kelimelerde “bina, yer” anlamı taşır; ad kabaca “gümüş yeri” demektir.",
                    "Şehir adını yakınındaki gümüş madenlerinden alır. Buradaki cevher gümüşlü kurşundu.",
                    "Türk kaynaklarındaki eski adı Canca'dır. Yunanca kökenli Argyropolis adı da “gümüş şehri” anlamına gelir."
                ],
                "kaynak": "Kaynak: TDV İslâm Ansiklopedisi; TDK; Britannica"
            },
            {
                "baslik": "Osmanlı'da ocaklar ve darphane",
                "maddeler": [
                    "Osmanlı döneminde burada gümüş sikke basıldı. Evliya Çelebi, üzerinde “Canca” yazan akçeler gördüğünü yazar.",
                    "Evliya Çelebi 1647'de yörede bir kısmı kapalı, bir kısmı işleyen yetmiş kadar gümüş ocağı saydı.",
                    "1700'lerin ikinci yarısında Keban, Ergani ve Gümüşhane, Osmanlı darphanesine maden gümüşü veren başlıca ocaklardı."
                ],
                "kaynak": "Kaynak: TDV İslâm Ansiklopedisi; İstanbul Üniversitesi Tarih Dergisi (2022)"
            },
            {
                "baslik": "Madenler neden kapandı?",
                "tablo": [
                    [
                        "Üçüncü Mustafa dönemi",
                        "su baskını"
                    ],
                    [
                        "1829",
                        "savaş ve göç"
                    ],
                    [
                        "1800'lerin ortası",
                        "işletme durdu"
                    ],
                    [
                        "1883–1888",
                        "son deneme"
                    ]
                ],
                "maddeler": [
                    "Üçüncü Mustafa döneminde su dolan ocaklar çalıştırılamadı; ormanlar tükenince yakıt da azaldı. Son deneme, gelir masrafı karşılamayınca bitti.",
                    "Türkiye'de bugün gümüşün nereden çıktığı ise ayrı bir bölümün konusu."
                ],
                "kaynak": "Kaynak: TDV İslâm Ansiklopedisi; Britannica; MTA Dergisi"
            }
        ]
    },
    # #27 — rehber ön paketi parti 4 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Türkiye'de gümüş nereden çıkar?",
        "alt": "Gümüşköy, yan ürün gümüş ve resmî rakamlar.",
        "buyuk": "Gümüşköy",
        "buyuk_alt": "Kütahya'da; MTA'ya göre işletilen tek gümüş yatağı",
        "hashtag": "#gümüş #değerlimetaller #emtia #gumus #silver",
        "soru": "Yaşadığınız yörede bilinen bir maden var mı?",
        "sayfalar": [
            {
                "baslik": "Gümüşköy (Kütahya)",
                "maddeler": [
                    "Kütahya'nın ~20 kilometre kuzeybatısındaki yatak, MTA'nın 2021 raporuna göre Türkiye'de işletilen tek gümüş yatağıdır.",
                    "Cevher açık ocakta çıkarılır. Eski hesaplara göre ton başına ortalama ~170–180 gram gümüş içerir.",
                    "Tesis 1980'lerde yılda ~1 milyon ton cevherden ~120 ton gümüş üretecek biçimde tasarlandı."
                ],
                "kaynak": "Kaynak: MTA, Dünyada ve Türkiye'de Gümüş (2021); Etibank (1980'ler); Jeoloji Mühendisliği (1995)"
            },
            {
                "baslik": "Başka madenlerden",
                "tablo": [
                    [
                        "Niğde Bolkardağ",
                        "altınla"
                    ],
                    [
                        "Gümüşhane",
                        "çinko-kurşunla"
                    ],
                    [
                        "Balıkesir Balya",
                        "kurşun-çinkoyla"
                    ]
                ],
                "maddeler": [
                    "Türkiye'de gümüş çoğu zaman kurşun, çinko, bakır ve altınla birlikte bulunur; bu madenlerde yan ürün olarak kazanılabilir.",
                    "Gümüşhane'nin eski ocakları 1800'lerde kapandı; yörede ve Bolkardağ'da 2020'lerde yeni işletmeler çalışıyordu."
                ],
                "kaynak": "Kaynak: MTA (2021); MT Bilimsel (2024); KTÜ (Hazinemağara); EMX (2015, Balya)"
            },
            {
                "baslik": "Ne kadar çıkıyor?",
                "tablo": [
                    [
                        "2017",
                        "~150 ton"
                    ],
                    [
                        "2020",
                        "~100–120 ton"
                    ]
                ],
                "maddeler": [
                    "2017–2022 yıllarında Türkiye'nin payı, dünya maden üretiminin yüzde birinden azdı.",
                    "Kaynaklar bazı yıllarda çok ayrışır: 2016 için ABD Jeoloji Araştırmaları Kurumu ~377 ton, Silver Institute ~209 ton der.",
                    "İthalat madenden çıkan gümüşün çok üstündedir: Borsa İstanbul verilerine göre 2025'te ~860 ton gümüş ithal edildi."
                ],
                "kaynak": "Kaynak: USGS Minerals Yearbook; World Silver Survey 2022; MTA (MAPEG verisi); Borsa İstanbul"
            }
        ]
    },
    # #28 — rehber ön paketi parti 4 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Tarihin ünlü gümüş madenleri hangileri?",
        "alt": "Laurion'dan Potosí'ye: madenler, kentler ve ticaret yolları.",
        "buyuk": "1545",
        "buyuk_alt": "Potosí'deki Cerro Rico'da gümüşün bulunduğu yıl",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #gumus #silver",
        "soru": "Bu madenlerden hangisini daha önce duymuştunuz?",
        "sayfalar": [
            {
                "baslik": "Antik Çağ: Laurion ve İspanya",
                "maddeler": [
                    "Atina'nın Laurion madenlerinde milattan önce 483 civarında zengin bir damar bulundu. Themistokles, Atinalıları geliri gemilere harcamaya ikna etti.",
                    "Atina'nın baykuşlu gümüş sikkeleri Laurion gümüşünden basıldı. Madenlerde ağır işi binlerce köle yaptı.",
                    "Roma, gümüşünün büyük kısmını İspanya'dan aldı. Polybios'a göre Cartagena yakınındaki madenlerde on binlerce kişi çalışıyordu."
                ],
                "kaynak": "Kaynak: Herodotos; Yunanistan Kültür Bakanlığı; Livius.org; Strabon (Polybios'tan aktarma)"
            },
            {
                "baslik": "Orta Avrupa'dan Amerika'ya",
                "tablo": [
                    [
                        "Kutná Hora (Çekya)",
                        "1200'ler"
                    ],
                    [
                        "Potosí (Bolivya)",
                        "1545"
                    ],
                    [
                        "Zacatecas (Meksika)",
                        "1546"
                    ],
                    [
                        "Comstock (ABD)",
                        "1859"
                    ]
                ],
                "maddeler": [
                    "Yıllar, gümüşün bulunduğu ya da madenciliğin başladığı dönemi gösterir.",
                    "Çekya'daki Joachimsthal 1516'da kuruldu; 1534'te 18–20 bin nüfusla Bohemya'nın Prag'dan sonra en kalabalık kentiydi.",
                    "Potosí'nin nüfusu otuz yıl içinde 150 bini aştı; kent, Amerika kıtasının en büyük şehri oldu."
                ],
                "kaynak": "Kaynak: UNESCO; Britannica; Radio Prague International"
            },
            {
                "baslik": "Zorla çalıştırma ve Çin'e giden gümüş",
                "maddeler": [
                    "İspanyol yönetimi, İnka'dan kalma mita sistemini Potosí'de zorunlu maden işçiliğine çevirdi; her yıl 10 binden fazla yerli madene gönderildi.",
                    "Ağır koşullar ve cıvayla çalışma çok can aldı. Ölenlerin sayısı bilinmiyor; tahminler tarihçiler arasında tartışmalı.",
                    "1565'ten 1815'e kadar Manila kalyonları Meksika gümüşünü Asya'ya taşıdı. Çin'de vergiler gümüşle ödendiği için talep büyüktü."
                ],
                "kaynak": "Kaynak: UNESCO; Pennsylvania Üniversitesi; Britannica; World History Encyclopedia"
            }
        ]
    },
    # #29 — rehber ön paketi parti 4 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Para neden artık gümüş değil?",
        "alt": "İki madenli sistemden gümüşsüz bozuk paraya.",
        "buyuk": "1873",
        "buyuk_alt": "ABD'de standart gümüş dolar basımının durduğu yıl",
        "hashtag": "#gümüş #değerlimetaller #emtia #gumus #silver",
        "soru": "Cebinizdeki bozuk paranın hangi metalden yapıldığını hiç merak ettiniz mi?",
        "sayfalar": [
            {
                "baslik": "İki madenli sistem",
                "maddeler": [
                    "On dokuzuncu yüzyılda birçok ülkede para hem altına hem gümüşe dayanıyordu. Yasa, iki metal arasındaki oranı sabitliyordu.",
                    "Piyasadaki oran değişince metali daha değerli hâle gelen sikkeler saklanır ya da eritilir, ucuz olanlar dolaşır. Buna Gresham kanunu denir.",
                    "Gresham kanunu kısaca şöyle özetlenir: kötü para iyi parayı kovar."
                ],
                "kaynak": "Kaynak: Britannica (“Bimetallism”, “Gresham's law”)"
            },
            {
                "baslik": "1870'lerde altına geçiş",
                "tablo": [
                    [
                        "Almanya",
                        "1871–1873"
                    ],
                    [
                        "ABD",
                        "1873"
                    ],
                    [
                        "Latin Para Birliği",
                        "1874–1878"
                    ]
                ],
                "maddeler": [
                    "Almanya altına geçti, ABD standart gümüş dolar basımını durdurdu, Latin Para Birliği gümüş 5 franklık basımını önce sınırladı, sonra durdurdu.",
                    "Gümüşün değeri düştü: bir ons altın 1873'te ~16 ons gümüş ederken 1894'te ~33 ons gümüş ediyordu."
                ],
                "kaynak": "Kaynak: IMF (2023); ABD 1873 Madeni Para Yasası; ABD İstatistik Yıllığı (1903); BullionVault"
            },
            {
                "baslik": "Gümüşsüz bozuk paraya geçiş",
                "tablo": [
                    [
                        "İngiltere",
                        "1947"
                    ],
                    [
                        "ABD, 10 ve 25 sent",
                        "1965"
                    ],
                    [
                        "Kanada, İsviçre",
                        "1968"
                    ]
                ],
                "maddeler": [
                    "Çoğu yerde neden gümüşün pahalanıp kıtlaşmasıydı: paradaki gümüş, üzerinde yazan değere yaklaşınca ya da onu aşınca paralar saklandı, eritildi.",
                    "İngiltere'de asıl neden, savaşta ABD'den ödünç alınan gümüşün geri ödenmesiydi; yerine bakır-nikel geldi.",
                    "Çin 1935'te gümüş standardını bıraktı. Türkiye'de dolaşım için basılan son gümüş paralar 1947 ve 1948 tarihlidir."
                ],
                "kaynak": "Kaynak: Royal Mint Müzesi; Hansard (1946); ABD 1965 Madeni Para Yasası; Canadian Coin News; Swissmint; 1935 para reformu; Numista"
            }
        ]
    },
    # #30 — rehber ön paketi parti 4 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Merkez bankaları neden gümüş tutmaz?",
        "alt": "Rezervlerde altının yeri, gümüşün geçmişi ve bugünü.",
        "buyuk": "altın",
        "buyuk_alt": "IMF kurallarına göre rezerv sayılan tek değerli metal",
        "hashtag": "#gümüş #değerlimetaller #külçegümüş #emtia #silver",
        "soru": "Gümüş sertifikası diye bir kâğıt para olduğunu biliyor muydunuz? Yorumlara yazın.",
        "sayfalar": [
            {
                "baslik": "Rezervde altın var, gümüş yok",
                "tablo": [
                    [
                        "Saf altın külçe",
                        "rezerv sayılır"
                    ],
                    [
                        "Gümüş külçe",
                        "mal sayılır"
                    ]
                ],
                "maddeler": [
                    "Merkez bankası rezervi başlıca döviz, Uluslararası Para Fonu'ndaki haklar ve altından oluşur. Gümüş bu listede yoktur.",
                    "Mayıs 2026 tarihli listeye göre merkez bankaları ve resmî kurumların elinde 36.000 tonu aşkın altın var."
                ],
                "kaynak": "Kaynak: IMF (BPM6 ve rezerv rehberi); Dünya Altın Konseyi (IMF verisi, Mayıs 2026)"
            },
            {
                "baslik": "Eskiden büyük gümüş stokları vardı",
                "maddeler": [
                    "ABD 1934 yasasıyla parasal stoklarının değerce dörtte birini gümüş yapmayı hedefledi. 1960'ların başında Hazine'de 1,5 milyar onsu aşkın gümüş vardı.",
                    "Bu stok satış ve madenî para basımıyla eridi. Gümüş sertifikaları 24 Haziran 1968'den sonra gümüşe çevrilemedi.",
                    "Çin, 1935 ile 1937 arasında yapılan anlaşmalarla gümüşünün bir kısmını ABD Hazinesi'ne sattı."
                ],
                "kaynak": "Kaynak: ABD Kongresi (1934); ABD Hazinesi ve Darphanesi belgeleri (1968); New York Fed (1967); ABD Dışişleri arşivi; Paper Money (2021)"
            },
            {
                "baslik": "Neden gümüş değil?",
                "maddeler": [
                    "Gümüş piyasası altınınkinden çok küçüktür ve fiyatı daha oynaktır. Talebinin yarısından fazlası sanayiden gelir.",
                    "ABD Hazine Bakanı 1968'de, Hazine'de kalan gümüşün “hiçbir anlamda” parasal rezerv amacıyla tutulmadığını yazdı.",
                    "Bugün gümüş, merkez bankalarının rezervlerinde kayda değer bir yer tutmuyor."
                ],
                "kaynak": "Kaynak: IMF; ABD Hazinesi (Aralık 1968); World Silver Survey 2026; piyasa raporları (2025–2026)"
            }
        ]
    },
    # #31 — rehber ön paketi parti 5 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Ons fiyatı neden dolarla verilir?",
        "alt": "Sterlinden dolara: gümüş fiyatının ortak dili.",
        "buyuk": "dolar",
        "buyuk_alt": "uluslararası gümüş fiyatının para birimi",
        "hashtag": "#gümüş #gümüşfiyatları #emtia #değerlimetaller #silver",
        "soru": "Gümüşü siz hangi parayla takip ediyorsunuz: dolarla mı, lirayla mı?",
        "sayfalar": [
            {
                "baslik": "Önce sterlin vardı",
                "maddeler": [
                    "Londra'nın gümüş referans fiyatı 1897'de başladı. İlk yıllarında fiyat İngiliz parasıyla, ons başına peni olarak veriliyordu.",
                    "Londra altın fiyatı da 1919'da sterlinle başladı; 1 Nisan 1968'den beri dolarla belirleniyor.",
                    "Bugünkü LBMA gümüş fiyatı da ons başına dolarla belirlenir."
                ],
                "kaynak": "Kaynak: LBMA (Alchemist 75 ve 95); The Perth Mint; ICE Benchmark Administration"
            },
            {
                "baslik": "Bretton Woods'tan bugüne",
                "tablo": [
                    [
                        "Bretton Woods anlaşması",
                        "1944"
                    ],
                    [
                        "Doların altına çevrilmesi durdu",
                        "1971"
                    ],
                    [
                        "Sabit kurlar fiilen bitti",
                        "1973"
                    ]
                ],
                "maddeler": [
                    "1944'te kurulan düzende öteki paralar dolara, dolar da ons başına 35 dolardan altına bağlıydı.",
                    "Altınla bağı kopunca da dolar, dünya ticaretinin ve finansının başlıca parası olarak kaldı."
                ],
                "kaynak": "Kaynak: Federal Reserve History; ABD Dışişleri Bakanlığı Tarih Ofisi; ABD Kongre Bütçe Ofisi (2023)"
            },
            {
                "baslik": "Bugün ve kur",
                "tablo": [
                    [
                        "Döviz işlemlerinde dolar",
                        "%89 (2025)"
                    ],
                    [
                        "Döviz rezervlerinde dolar",
                        "~%57 (2026)"
                    ]
                ],
                "maddeler": [
                    "Petrol ve metaller gibi emtialar da uluslararası piyasada genelde dolarla fiyatlanır.",
                    "Dünya fiyatı dolarla verildiği için başka parayla alan, kendi parasının dolar karşısındaki hareketini de yaşar.",
                    "Aynı gün gümüş, bir parayla alan için pahalanırken başka bir parayla alan için ucuzlayabilir."
                ],
                "kaynak": "Kaynak: BIS (Nisan 2025); IMF (Haziran 2026 sonu); New York Fed (2010); ABD Kongre Bütçe Ofisi (2023)"
            }
        ]
    },
    # #32 — rehber ön paketi parti 5 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Spot fiyat ve vadeli fiyat ne demek?",
        "alt": "Hemen teslim, ileri tarihte teslim ve aradaki fark.",
        "buyuk": "2 iş günü",
        "buyuk_alt": "Londra'da spot işlemin teslim süresi",
        "hashtag": "#gümüş #gümüşfiyatları #emtia #değerlimetaller #silver",
        "soru": "Ekrandaki ons fiyatının spot mu vadeli mi olduğuna hiç dikkat ettiniz mi? Yorumlara yazın.",
        "sayfalar": [
            {
                "baslik": "Spot: hemen teslim",
                "maddeler": [
                    "Spot fiyat, gümüşün hemen teslimi için geçerli fiyattır.",
                    "Londra'da “hemen”, işlemden iki iş günü sonra demektir; para ve gümüş o gün el değiştirir.",
                    "Ekranlarda görülen ons gümüş çoğu zaman spot fiyattır. Paylaşımlarımızdaki ons fiyatı da spottur."
                ]
            },
            {
                "baslik": "Vadeli ve ileri tarihli",
                "tablo": [
                    [
                        "Vadeli",
                        "borsada"
                    ],
                    [
                        "İleri tarihli",
                        "taraflar arası"
                    ]
                ],
                "maddeler": [
                    "Vadeli sözleşmede miktar, kalite ve vade standarttır; ileri tarihli işlemde koşulları iki taraf belirler.",
                    "Vadeli sözleşmelerin çoğu teslimden önce kapatılır. Borsa İstanbul'daki ons gümüş vadelisinde gümüş teslim edilmez, fark nakit ödenir."
                ],
                "kaynak": "Kaynak: CME Group; ABD Emtia Vadeli İşlemler Komisyonu (CFTC); Borsa İstanbul (VİOP)"
            },
            {
                "baslik": "Fark neden olur?",
                "maddeler": [
                    "Gümüşü vadeye kadar tutmanın bir maliyeti var: paranın faizi, depolama ve sigorta. Buna taşıma maliyeti denir.",
                    "Bu yüzden vadeli fiyat genelde spotun üstündedir. Bazen tersi olur ve spot fiyat üste çıkar.",
                    "Vade yaklaştıkça vadeli fiyat spot fiyata yaklaşır."
                ],
                "kaynak": "Kaynak: LBMA; CME Group; Borsa İstanbul VİOP Terimler Sözlüğü"
            }
        ]
    },
    # #33 — rehber ön paketi parti 5 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Fiziki ve fiziki olmayan gümüş farkı nedir?",
        "alt": "Külçe, kasa hesabı, banka hesabı, fon ve sertifikada neye sahip olduğunuz.",
        "buyuk": "4 soru",
        "buyuk_alt": "sahiplik, yer, karşı taraf ve elinize alıp alamamak",
        "hashtag": "#gümüş #külçegümüş #değerlimetaller #emtia #silver",
        "soru": "Bu dört sorudan hangisini daha önce hiç düşünmemiştiniz?",
        "sayfalar": [
            {
                "baslik": "Elde ve kasada",
                "maddeler": [
                    "Külçe ya da sikke elinizdeyse gümüşün kendisine sahipsiniz; arada bir kurum yoktur, saklamak ve korumak size kalır.",
                    "Ayrılmış (tahsisli) kasa hesabında belirli külçeler sizin adınıza ayrılır; her külçenin numarası bir listede yazar.",
                    "Ayrılmamış hesapta belirli bir külçe yoktur; hesabın açıldığı kuruma karşı bir miktar gümüş alacağınız vardır."
                ],
                "kaynak": "Kaynak: LBMA, kıymetli maden hesapları rehberi"
            },
            {
                "baslik": "Banka hesabı ve fon",
                "maddeler": [
                    "Türkiye'de bankalar gümüş depo hesabı açabilir. Hesap, bakiyesi gümüş cinsinden izlenen bir mevduattır; karşı taraf bankadır.",
                    "Gümüş fonunda gümüşe değil, fonun bir payına sahipsiniz. Bazı fonlar kasada külçe, bazıları vadeli sözleşme ya da başka fon tutar.",
                    "Fonun ne tuttuğu ve gümüşü kimin sakladığı izahnamesinde yazar. Payı gümüşe çevirmek genelde yalnız yetkili kurumlara açıktır."
                ],
                "kaynak": "Kaynak: Hazine tebliği (Resmî Gazete, 29 Mayıs 2008); mevduat sigortası yönetmeliği; Borsa İstanbul; ABD CFTC"
            },
            {
                "baslik": "Karşı taraf kim?",
                "tablo": [
                    [
                        "Ayrılmamış hesap",
                        "kurum"
                    ],
                    [
                        "Banka hesabı",
                        "banka"
                    ],
                    [
                        "Vadeli sözleşme",
                        "takas kurumu"
                    ],
                    [
                        "Sertifika",
                        "ihraççı"
                    ]
                ],
                "maddeler": [
                    "Vadeli işlemde elinizde gümüş değil, bir sözleşme vardır; borsanın takas kurumu her iki tarafın karşısında durur, teminat yatırılır.",
                    "Sertifika çoğu zaman ihraççıya karşı bir alacak hakkıdır ve ödeme genelde nakittir. Ne verdiğini ihraç belgesi söyler."
                ],
                "kaynak": "Kaynak: CME Group; İngiltere FCA; Borsa İstanbul varant ve sertifika rehberi"
            }
        ]
    },
    # #34 — rehber ön paketi parti 5 (Rıdvan, 20 Ekim 2026; iki kontrol Claude'da)
    {
        "baslik": "Dünyadaki gümüş nerede duruyor?",
        "alt": "Londra kasaları, New York ve Şanghay depoları, fonlar ve evler.",
        "buyuk": "29 bin ton",
        "buyuk_alt": "Eylül 2026 sonunda Londra kasalarındaki gümüş (yaklaşık)",
        "hashtag": "#gümüş #külçegümüş #değerlimetaller #emtia #silver",
        "soru": "Bu üç merkezden hangisinin gümüş depolarını daha önce duymuştunuz: Londra mı, New York mu, Şanghay mı?",
        "sayfalar": [
            {
                "baslik": "Londra kasaları",
                "maddeler": [
                    "LBMA, Londra'daki kasalarda duran gümüşü her ay yayımlar. Rakam bir önceki ayın son gününe aittir ve tonla verilir.",
                    "Eylül 2026 sonunda ~29 bin ton, yani ~930 milyon ons gümüş vardı. Rakam her ay değişir.",
                    "Fonların Londra'da tuttuğu gümüş de bu rakamın içindedir. Son yıllarda Londra'daki gümüşün çoğu fonlara aitti."
                ],
                "kaynak": "Kaynak: LBMA kasa verisi (Eylül 2026); LBMA Alchemist; piyasa analizleri (2021–2026)"
            },
            {
                "baslik": "New York: iki tür stok",
                "tablo": [
                    [
                        "Teslime hazır",
                        "belgeli"
                    ],
                    [
                        "Şartlara uygun",
                        "belge yok"
                    ]
                ],
                "maddeler": [
                    "CME, COMEX depolarındaki gümüşü her iş günü onsla yayımlar.",
                    "Teslime hazır gümüşün teslim belgesi vardır; vadeli sözleşmede yalnız o teslim edilir. Öteki tür şartlara uyar ama belgesi yoktur.",
                    "Ekim 2026 ortasında toplam ~335 milyon ons vardı, ~100 milyonu teslime hazır. Ekim 2025'te toplam ~530 milyon onsla rekordaydı."
                ],
                "kaynak": "Kaynak: CME Group günlük depo raporu (Ekim 2026); COMEX teslim arzı analizi (2021); Reuters (Ekim 2025)"
            },
            {
                "baslik": "Şanghay, fonlar ve evler",
                "maddeler": [
                    "Şanghay Vadeli İşlem Borsası'nın depolarında Şubat 2026'da ~350 ton, Eylül ve Ekim 2026'da ~1.400 ton gümüş vardı.",
                    "Gümüş fonlarının dünyadaki külçeleri 2026 başında ~1,3 milyar ons, yani ~40 bin tondu. Londra'dakiler o şehrin rakamında zaten sayılır.",
                    "Evdeki, takıdaki ve eşyadaki gümüş tahminle bilinir. Yer üstü toplam tahminleri, neyin sayıldığına göre ~600 bin ile 1,7 milyon ton arası."
                ],
                "kaynak": "Kaynak: Şanghay Vadeli İşlem Borsası verisi; The Silver Institute (2025, 2026); CPM Group (2019)"
            }
        ]
    },
]


def _sayfa_metni(s):
    satirlar = [s["baslik"]]
    if s.get("buyuk"):
        satirlar.append(f"{s['buyuk']} = {s['buyuk_alt']}")
    if s.get("formul"):
        satirlar.append(s["formul"])
    satirlar += [f"{etiket}: {deger}" for etiket, deger in s.get("tablo", [])]
    satirlar += [f"• {m}" for m in s.get("maddeler", [])]
    if s.get("kaynak"):
        satirlar.append(s["kaynak"])
    return "\n".join(satirlar)


def _duzenli_gunler():
    gun = DUZENLI_BASLANGIC
    while True:
        if gun.weekday() in DUZENLI_GUNLER:
            yield gun
        gun += timedelta(days=1)


def _haftalik_sira():
    """{"YYYY-AA-GG": ("arsiv" | "yeni", bölüm no)} — DUZENLI_GUNLER'deki haftalık rehber sırası: önce ARSIVDEN_ONCE
    kadar yeni bölüm (#7, #8), sonra rehber arşivi Reels'i (ARSIV_SIRASI), sonra kalan yeni bölümler."""
    yeniler = [("yeni", n) for n in range(max(BASLANGIC.values()) + 1, len(BOLUMLER) + 1)]
    kuyruk = yeniler[:ARSIVDEN_ONCE] + [("arsiv", n) for n in ARSIV_SIRASI] + yeniler[ARSIVDEN_ONCE:]
    return {g.isoformat(): k for g, k in zip(_duzenli_gunler(), kuyruk)}


def takvim():
    """{"YYYY-AA-GG": bölüm no} — yeni bölümlerin günleri: ilk hafta BASLANGIC, sonrası haftalık sırada."""
    t = dict(BASLANGIC)
    t.update({g: no for g, (tur, no) in _haftalik_sira().items() if tur == "yeni"})
    return t


def yayim_listesi():
    """[(tarih, bölüm no)] — elle paylaşılanlar + zamanlı takvim, tarihe ve numaraya göre sıralı."""
    liste = [(date.fromisoformat(g), no) for no, g in ONCEDEN_YAYIMLANAN.items()]
    liste += [(date.fromisoformat(g), no) for g, no in takvim().items()]
    return sorted(liste)


# Rehber arşivi Reels'i (Rıdvan, 17 Ekim 2026 00:44 "öneriyi uygula"): rehber günü sesli Reels'i #6 ile (19 Ekim)
# başladı; ondan önce yayımlanan #3–#5'in hiç Reels'i yoktu (onları taşıyacak cumartesi kısa Reels'i 16 Ekim'de
# kaldırıldı). Her biri bir kez, bölümün tamamını okuyan sesli Reels olarak gider: yalnız Reels, kaydırmalı ve
# hikâye videosu zaten paylaşıldı (main.kisa_hazirla). 19 Ekim 2026'da Rıdvan ayrı günleri (22, 26, 28 Ekim)
# kaldırdı: "rehber sırasına girsinler" — haftalık rehber gününde (çarşamba ~14:00), #7 ve #8'den sonra, #9'dan önce
# (ARSIVDEN_ONCE; 28 Ekim #7, 4 Kasım #8, 11/18/25 Kasım #3/#4/#5, 2 Aralık #9).
# #1–#2'nin 13 Ekim'de sessiz kısa Reels'i var, listede yok. Elle: Run workflow → tür: kisa, konu: <no>.
ARSIV_SIRASI = [3, 4, 5]
ARSIVDEN_ONCE = 2   # haftalık sırada arşiv Reels'lerinden önce gidecek yeni bölüm sayısı (#7, #8)


def arsiv_takvim():
    """{"YYYY-AA-GG": bölüm no} — rehber arşivi Reels'i günleri (haftalık rehber sırasından)."""
    return {g: no for g, (tur, no) in sorted(_haftalik_sira().items()) if tur == "arsiv"}


def bugunun_arsiv_bolumu(gun=None):
    gun = gun or datetime.now(ZoneInfo("Europe/Istanbul")).date()
    return arsiv_takvim().get(gun.isoformat())


def bugunun_bolumu(gun=None):
    gun = gun or datetime.now(ZoneInfo("Europe/Istanbul")).date()
    return takvim().get(gun.isoformat())


def aciklama(no, reels=False, ek=(), muzik=None):
    """Rehber gönderisinin açıklaması. reels=True: sesli Reels (main.REHBER_REELS): ilk satırda kısa cevap,
    bölümün tamamı yine açıklamada; ek (seslendirme notu) uyarıdan önce, müzik künyesi sonda."""
    b = BOLUMLER[no - 1]
    if reels:
        parcalar = [f"{b['baslik']} Kısa cevap: {b['buyuk']}, {b['buyuk_alt']} | Gümüş rehberi #{no}", b["alt"]]
    else:
        parcalar = [f"{b['baslik']} | Gümüş rehberi #{no}", b["alt"]]
    parcalar += [_sayfa_metni(s) for s in b["sayfalar"]]
    son = ("Bölümün tamamı yukarıda ve profildeki Rehber öne çıkanında; kaydedin, lazım olunca bakarsınız."
           if reels else "Kaydedin, lazım olunca bakarsınız.")
    if no < len(BOLUMLER):
        son += f" Sıradaki bölüm: {BOLUMLER[no]['baslik']}"
    parcalar += [son, SITE_REHBER, b["soru"], *ek, "Bilgi amaçlıdır, yatırım tavsiyesi değildir."]
    if muzik:
        parcalar.append(f"Müzik: {muzik}")
    parcalar.append(b["hashtag"])
    return "\n\n".join(parcalar)


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "bugun"
    if komut == "takvim":
        zamanli = takvim()
        for g, n in yayim_listesi():
            elle = "" if zamanli.get(g.isoformat()) == n else "  (elle)"
            print(g, GUNLER[g.weekday()], n, BOLUMLER[n - 1]["baslik"] + elle)
    elif komut == "arsiv-takvim":
        for g, n in arsiv_takvim().items():
            print(g, GUNLER[date.fromisoformat(g).weekday()], n, BOLUMLER[n - 1]["baslik"])
    elif komut == "arsiv":
        print(bugunun_arsiv_bolumu() or "")
    else:
        print(bugunun_bolumu() or "")
