"""Gümüş rehberi: profili çeşitlendiren, fiyat verisi kullanmayan bilgi gönderileri (kaydırmalı).

Her bölüm kapak + 3 sayfa olarak paylaşılır. TAKVIM'deki günlerde hafta içi ~14:00'te
otomatik gider; elle göndermek için Actions → Run workflow → tür: bilgi, konu: 1-6.
Rakamlar örnek ya da sabit değerlerdir (güncel fiyat içermez), bu yüzden MetalCharts hakkı harcanmaz.
"""

SERI = "GÜMÜŞ REHBERİ"

# Hangi gün hangi bölüm gider (TR tarihi). Listede olmayan günlerde zamanlı çalışma bir şey paylaşmaz.
TAKVIM = {
    "2026-10-14": 1,
    "2026-10-15": 2,
    "2026-10-16": 3,
    "2026-10-19": 4,
    "2026-10-20": 5,
    "2026-10-21": 6,
}

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
        "soru": "Sizce külçe mi, gram hesabı mı daha pratik? Yorumlarda konuşalım.",
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


def aciklama(no):
    b = BOLUMLER[no - 1]
    toplam = len(BOLUMLER)
    parcalar = [f"{b['baslik']} | Gümüş rehberi {no}/{toplam}", b["alt"]]
    parcalar += [_sayfa_metni(s) for s in b["sayfalar"]]
    son = "Kaydedin, lazım olunca bakarsınız."
    if no < toplam:
        son += f" Sıradaki bölüm: {BOLUMLER[no]['baslik']}"
    parcalar += [son, b["soru"], "Bilgi amaçlıdır, yatırım tavsiyesi değildir.", b["hashtag"]]
    return "\n\n".join(parcalar)
