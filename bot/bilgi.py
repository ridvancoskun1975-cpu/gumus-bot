"""Gümüş rehberi: profili çeşitlendiren, fiyat verisi kullanmayan bilgi gönderileri (kaydırmalı).

Her bölüm kapak + 3 sayfa olarak paylaşılır, hafta içi ~14:00'te otomatik gider.
Takvim: ilk 6 bölüm 14-21 Ekim 2026'da her iş günü (BASLANGIC); sonrası DUZENLI_GUNLER'de
(salı, perşembe) sıradaki bölüm. Yeni bölüm eklemek için BOLUMLER'in sonuna ekle; takvime
kendiliğinden girer. Bölümler bitince zamanlı çalışma bir şey paylaşmaz.
Elle göndermek için Actions → Run workflow → tür: bilgi, konu: <no>.
Rakamlar örnek ya da sabit değerlerdir (güncel fiyat içermez), bu yüzden MetalCharts hakkı harcanmaz.

Komut satırı: python bot/bilgi.py bugun  → bugünün bölüm numarasını yazar (yoksa boş)
              python bot/bilgi.py takvim → bütün takvimi yazar
"""
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

SERI = "GÜMÜŞ REHBERİ"
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# İlk hafta her iş günü bir bölüm (TR tarihi)
BASLANGIC = {
    "2026-10-14": 1,
    "2026-10-15": 2,
    "2026-10-16": 3,
    "2026-10-19": 4,
    "2026-10-20": 5,
    "2026-10-21": 6,
}
# Sonrasında haftada 2 bölüm: salı ve perşembe (Pazartesi = 0). Haftada 1 için {1} yeter.
DUZENLI_BASLANGIC = date(2026, 10, 26)
DUZENLI_GUNLER = {1, 3}

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
                    "Cumartesi ve pazar küresel piyasa kapalıdır, ons fiyatı oluşmaz.",
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
                    "Uluslararası piyasada el değiştiren standart külçe 750–1.100 ons (yaklaşık "
                    "23–34 kg) ağırlığında ve en az 999 saflıktadır.",
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


def takvim():
    """{"YYYY-AA-GG": bölüm no} — ilk hafta BASLANGIC, sonrası DUZENLI_GUNLER'de sıradaki bölüm."""
    t = dict(BASLANGIC)
    no = max(BASLANGIC.values()) + 1
    gun = DUZENLI_BASLANGIC
    while no <= len(BOLUMLER):
        if gun.weekday() in DUZENLI_GUNLER:
            t[gun.isoformat()] = no
            no += 1
        gun += timedelta(days=1)
    return t


def bugunun_bolumu(gun=None):
    gun = gun or datetime.now(ZoneInfo("Europe/Istanbul")).date()
    return takvim().get(gun.isoformat())


def aciklama(no):
    b = BOLUMLER[no - 1]
    parcalar = [f"{b['baslik']} | Gümüş rehberi #{no}", b["alt"]]
    parcalar += [_sayfa_metni(s) for s in b["sayfalar"]]
    son = "Kaydedin, lazım olunca bakarsınız."
    if no < len(BOLUMLER):
        son += f" Sıradaki bölüm: {BOLUMLER[no]['baslik']}"
    parcalar += [son, b["soru"], "Bilgi amaçlıdır, yatırım tavsiyesi değildir.", b["hashtag"]]
    return "\n\n".join(parcalar)


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "bugun"
    if komut == "takvim":
        for g, n in takvim().items():
            print(g, GUNLER[date.fromisoformat(g).weekday()], n, BOLUMLER[n - 1]["baslik"])
    else:
        print(bugunun_bolumu() or "")
