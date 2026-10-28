# Claude için kurallar (gumus-bot)

- **Galeri (Rıdvan, 17 Ekim 2026: "Bana gönderdiğin her görsel ve videoyu aynı anda proje galerisine ekle."):**
  Rıdvan'a gönderilen her görsel ve video (önizleme, önce/sonra, deneme çıktısı dahil) aynı turda proje galerisine
  de eklenir: https://claude.ai/artifact/CFKCZroCrWfYDG8b1BgDzm (proje-galerisi becerisi; veri `ogeler`
  koleksiyonunda). Oturumun dosyaları başka sohbetten erişilemez; eklenmeyen dosya kaybolur.
- **Web araştırması (Rıdvan, 20 Ekim 2026: "Bunu kural olarak kabul et. Bütün sohbetler böyle başlasın … bütün
  projeler"):** WebFetch yalnızca WebSearch sonuçlarında çıkan adreslerle; hafızadan ya da adresi elle değiştirerek URL
  üretilmez (her yeni site onay sorusu açıp işi yavaşlatıyor). Mümkünse arama sonuçlarının kendisinden doğrula; kaynak
  yeterince toplanınca yazmaya geç. Alt görevlere (yazar, denetçi) verilen her tarife bu kural yazılır.
- **Günlük sınır: günde en fazla 4** (14 Ekim 2026 21:23'ten beri; önce 3). **19 Ekim 2026'dan beri takipçinin gördüğü
  her şey sayılır: akış gönderisi, Reels ve hikâye ayrı ayrı** (Rıdvan: "takipçiler bizden gelecek, bizle ilgili
  görecekleri post, bildirim, reels, hikâye sayısından bahsediyorum"). Gün aşılacaksa önce hikâye kopyası düşer
  (akşam özeti hikâyesiz gider); hikâyesiz de aşacaksa yalnızca Rıdvan sohbette açıkça onay verirse gider.
  Paylaşım sayısını konuşurken ve yeni paylaşım/hikâye önerirken hep bu ölçüyle say.
  Ayrıntı: README → "Günlük sınır", kod `bot/sinir.py`.
  - Onay işaretini (`Run workflow → onay: true`) ya da `bot/sinir.py` → `GUN_SINIRI` istisnasını Rıdvan
    sohbette açıkça "onayla" / "gitsin" demeden **kullanma**. Bir paylaşımın onayı yalnızca o paylaşım içindir.
  - Paylaşım yapan bir çalıştırmayı elle başlatmadan önce bugünkü sayıyı söyle; o paylaşım akşamki zamanlı
    paylaşımları 5.'ye itecekse bunu da söyle.
- **Ortak çalışma: bu depoda aynı anda birden çok sohbet çalışır** (Rıdvan, 17 Ekim 2026 "Ekle"; o gün bir sohbet
  pazar Reels'ini sesli yaparken diğeri eski kopya üstünde aynı şablona önizleme hazırladı):
  1. İşe başlarken, Rıdvan'a önizleme göstermeden önce ve main'e almadan önce `git fetch origin main` ile son hâli çek;
     son baktığından beri gelen commit'leri (`git log`) oku. Başka bir sohbet aynı dosyalara ya da aynı paylaşım türüne
     dokunmuşsa devam etmeden Rıdvan'a söyle.
  2. Rıdvan'a gösterilen her önizleme o anki main'in (ya da onun üstüne kurulmuş dalın) üstüne kurulur; eski bir
     kopyadan önizleme gösterme.
  3. `CALISMA.md`: işe başlamadan önce oku. İşe başlarken konuyu, dokunacağın dosyaları ve dalı bir satır olarak ekle
     (commit + push); iş bitince ya da bırakılınca satırı sil. Aynı dosyalarda ya da aynı paylaşım türünde başka bir iş
     yazılıysa Rıdvan'a sor. Satır 24 saatten eskiyse Rıdvan'a "hâlâ sürüyor mu" diye sor, kendiliğinden silme.
- Bakım güncellemeleri (eylem ve kütüphane sürümleri) ayrı dalda yapılır. Deneme başarılıysa ve paylaşım çıktısı
  değişmiyorsa main'e alınır, sonra bildirilir. Paylaşım içeriğini ya da takvimi değiştiren her şey önce önizleme ve
  onay ister. (Rıdvan'ın 15 Ekim 2026 tarihli açık isteği; metni kendisi verdi.)
- Rıdvan genelde yalnızca telefondan, Claude üzerinden çalışır: GitHub ayarı, GitHub onay ekranı ya da başka
  bir arayüz gerektiren çözüm önerme.
- Taahhüt: hafta içi her gün 2 kez gram fiyatı (~10:00 Reels, ~20:00 özet); bu ikisi kaldırılmaz, başka içerikle
  değiştirilmez.
- Pazar yorumu 2 sayılır (kaydırmalı + Reels; hikâye 25 Ekim 2026'da kaldırıldı, Rıdvan: "Hikayeyi kaldıralım";
  `main.PAZAR_HIKAYE`; öne çıkan yerine pazar analizi profilde sabitlenir). Pazar Reels'i sesli (Rıdvan, 17 Ekim 2026: Gemini erkek
  sesi, analizin tamamı okunur; okumayı ona sormadan kısaltma). Ses **Orus** (`ses.YORUM_SES`; Rıdvan, 3 örnekten "Ses 2"); 24 sn müzikli sürüm
  yine üretilir; ses alınamazsa Reels 24 sn müzikli gider (yedek yol kaldırılmaz). Ses, üslup ya da okunan metin
  değişecekse önce önizleme ve onay.
- Pazar yorumunun orta vade geçmişini MetalCharts Starter verir (17 Ekim 2026); Ocak 2027'de iptal (11 Ocak
  hatırlatması), sonra kendi kayıtlarımız. Pazar yorumu önizlemesini Rıdvan'a gerçek veriyle üret (deneme, ornek
  işaretsiz): örnek veride orta vade boş görünür. (Yalnız kısa ve orta vade kuralı aşağıda.)
- Bütün seslendirmeler 1,5 kat hızlı (`ses.HIZ`) ve sesli Reels'te hareketli "Sesi açın" rozeti var (Rıdvan,
  17 Ekim 2026); hız ya da rozet değişecekse önce önizleme ve onay. Sesli rehber Reels'inde ayrıca ilk 2,5 sn ekran
  kararır ve rozet ortada büyük çıkar (Rıdvan, 19 Ekim 2026 "onaylıyorum uygula": üstteki rozet masaüstü akışında
  kırpılıyor, telefon akışında "Orijinal ses" satırının altında kalıyor; `bot/main.py` → `SES_ROZETI_ORTA_*`).
  Pazar Reels'inin rozeti yerinde kalır (Rıdvan: "pazarda sorun yok").
  Sesli rehber Reels'inde iki rozetle birlikte "Seslendirme: yapay zekâ" satırı da var (Rıdvan, 26 Ekim 2026 "Uygun";
  yasal inceleme 4: Meta yapay zekâ sesi etiketi, AB Yapay Zekâ Tüzüğü md. 50; `main.SES_NOTU`). Kaldırma; yalnız müzikle
  giden Reels'te çıkmaz.
- Instagram'a tarayıcıyla bakılmaz.
- **Paylaşım saati = hedef saat** (Rıdvan, 28 Ekim 2026: "takipçilere 20 00 yazdık … işleme önce başlamalıyız", "söze uymamız gerekiyor"): GitHub zamanlı işi 20–50 dk geç başlattığı için `paylas.yml` cron'ları hedeften ~45 dk öncedir (09:10, 13:10, 19:10; cumartesi 09:10, pazar 10:10 TR) ve bot hedefe kadar bekler (`bot/program.py` → `HEDEF_SAATLERI`, `bekle`; hedefler 09:55 / 13:55 / 19:55 / 09:55 / 10:55, paylaşım ~5 dk sonra). Cron'u geri 09:50/19:50'ye alma; saat değişecekse hedef ve cron birlikte, önizleme ve onayla (`python bot/program.py hedef-denetle`). Hedeften önceki 45 dk içinde elle çalıştırma başlatma (zamanlı çalışma kuyruğu tutar). Bekleme adımı hata verse de paylaşım gider; bu güvenlik kaldırılmaz.
- Sitede ve açıklamalarda model ya da şirket adı yazılmaz.
  (Bu dört kural: Rıdvan, 16 Ekim 2026 "CLAUDE.md'ye ekle".)
- Goril maskotu (README → "Goril maskotu", `bot/goril.py`): hafta içi sabah Reels'i (19 Ekim 2026'dan; Rıdvan 16 Ekim
  22:25 "sabaha şimdi koy"), akşam özeti, cumartesi haftalık özeti ve aylık özette (Rıdvan, 18 Ekim 2026: aylıkta %5'te
  sevinir; haftalık ve aylıkta dönemde eşik ilk kez aşılır ya da dönem 1 aylık en yüksekte kapanırsa kutlar). Pazar yorumuna hiçbir zaman goril
  eklenmez. Hâller, eşikler ya da açıklama satırı değişecekse önce önizleme ve Rıdvan'ın onayı. Gorilli üretim her
  hatada ve süre aşımında gorilsiz paylaşıma düşmeli; bu yedek yol kaldırılmaz. Goril bir yazıyla üst üste binerse
  paylaşım durmaz, goril kalır ve Rıdvan'a bildirilir (gece kontrolü; Rıdvan, 16 Ekim 2026 22:43).
  Sitede yalnız istifçi goril, tanıtım kartında ve 404 sayfasında; fiyattan bağımsız, yön göstermez (Rıdvan, 19 Ekim
  2026 "2 ama istifçi goril", "onaylıyorum uygula"). Fiyatın yanına ya da güne göre değişen hâl koyma; kapatma `bot/sayfa.py` → `SITE_GORIL`.
- Rehber hikâyesi kareler tek tek değil, tek müzikli video olarak gider (kapak 3 sn, kare 6 sn), rehber gönderisiyle
  aynı çalıştırmada (`bot/main.py` → `REHBER_HIKAYE_OTOMATIK = True`); hikâye kalabalık olmamalı.
- Takvimi azaltma kararı (Rıdvan, 19 Ekim 2026: "takipçileri bıktırmamak ve kaçırmamak için … paylaşım sayısını
  biraz azaltmamız gerekiyor"; pazar dışındaki önerileri onayladı): çarşamba/cuma kartları kaldırıldı (kod duruyor),
  rehber haftada 1 çarşamba, arşiv Reels'i haftalık sıraya girdi, pazar kaydırmalı + Reels olduğu gibi kaldı.
  Yeni bir rutin paylaşım ya da hikâye eklemeyi önermeden önce olağan haftanın gün gün sayısını (README → "Günlük
  sınır") göster; hiçbir gün 4'ü aşmamalı.
- Rehber günü (14–19 Ekim 2026 her iş günü; sonra haftada 1, çarşamba ~14:00 — 20–21 Ekim Rıdvan'ın 19 Ekim kararıyla kalktı, #7 28 Ekim, #8 4 Kasım) akışa kaydırmalı gönderinin yerine bölümün tamamını kare kare okuyan (Rıdvan, 17 Ekim 2026: "Tabii ki tamamının okunması gerekiyor"; okumayı ona sormadan kısaltma) kadın sesli Reels gider,
  hikâyeye müzikli rehber videosu; cumartesi kısa Reels'i kaldırıldı (Rıdvan, 16 Ekim 2026 23:4x: "Kaydırmalı rehber
  kimse bakmaz"; `bot/main.py` → `REHBER_REELS`). Ses **Sulafat** (Rıdvan, 16 Ekim 2026, 3 önizlemeden seçti; README →
  "Rehber Reels seslendirmesi", `bot/ses.py`). Rehber hikâye videoları sesli değil, müzikli kalır. Reels üretilemezse
  o gün kaydırmalı gider; bu yedek yol kaldırılmaz. Ses, üslup ya da okunan metin değişecekse önce önizleme ve onay. Seslendirmenin her hatası Reels'i
  yalnızca müzikle paylaşmaya düşmeli; bu yedek yol kaldırılmaz. Gemini 17 Ekim 2026'dan beri ücretli katmanda (Rıdvan, ön
  ödemeli kredi + otomatik yenileme; günlük 10 okuma sınırı yok). Denemeler yine yalnızca yedek modelle (Rıdvan,
  16 Ekim 2026). Kredi biterse ses 402 verir, Reels müzikle gider; gece kontrolü bildirir. Yeni rehber bölümü eklenince `ses.OKUMA`'ya satır ekle.
- **PDF Gümüş Rehberi** (Rıdvan, 19 Ekim 2026: "kısa olan bilgiler pdf te eksiksiz doyurucu olmalı"; "uygundur
  başlayalım. bunu site tanıtımına da ekleyelim. beklenti olsun."; aralık: "1 yıl"): `bot/rehber_pdf.py`, şablon
  `templates/rehber-pdf.html`, bölüm metinleri `rehber_pdf/bolum-NN.html` (kurallar `rehber_pdf/YAZIM.md`; her rakam iki
  kaynaktan, fiyat ve yatırım tavsiyesi yok). Baskı yılda bir, 1 Ocak ("2027 baskısı"); baskıya yalnız o güne kadar
  Instagram'da yayımlanmış bölümler girer. Yeni bölümün uzun hâli aylık rehber paketiyle birlikte yazılır ve aynı iki
  kontrolden geçer; yeni yılın baskısı 25 Aralık'ta pakete ek önizleme olarak gider, aynı 7 gün kuralı. Onaylanan PDF `rehber_pdf/yayin/` altına konur ve `BASKILAR`'a eklenir; site baskı günü kendiliğinden
  yayınlar (gunlukgumus.com/rehber.pdf; `sayfa.yml` o gece çalışır). Baskı yokken sitede "Yakında · 1 Ocak 2027" kartı
  (`ILK_BASKI`). Dil (Rıdvan, 22:21; "Ücretsiz PDF rehber" fazla basitti): sitede "Gümüşte uzmanlaşmanın kısa yolu ·
  ücretsiz PDF kitap", Reels'te "Gümüş uzmanlık kitabı · ücretsiz PDF, 1 Ocak 2027'den itibaren", kapakta "Gümüş uzmanlık
  kitabı" ve "Gümüşü bir uzman gibi okuyun"; "uzman olursunuz" gibi söz verilmez. PDF Creative Commons BY-NC-ND 4.0 lisanslıdır (Rıdvan, 28 Ekim 2026 "C evet"): kaynak gösterilerek, değiştirmeden ve
  ticari olmayan amaçla paylaşılabilir; sayfalarda model ya da şirket adı yok. Kitap yalnız sitede (rehber sayfası, ana sayfa)
  ve site tanıtım Reels'inde tanıtılır: rehber Reels'inin site kartı ve okuması, sitenin tanıtım kartı ve özet/rehber
  açıklamalarındaki site satırı için Rıdvan 19 Ekim 2026'da "gerek yok" dedi ("her yere kitap yazmak bana biraz garip
  geldi"; 22:44 "karar değiştirdim"); ekleme, Aralık geri sayımı da önerme.
  - **Kitabın tanıtım dili kapsamla birlikte büyür** (Rıdvan, 21 Ekim 2026: "Şimdilik en kapsamlı demeyelim. Ama kapsam
    genişlettikçe kitabın kalitesine uygun bir şeyler seçmeliyiz."): "en kapsamlı", "tek", "en iyi" gibi kanıtlanamayan
    üstünlük iddiası yazılmaz. Tanıtım doğrulanabilir özelliklere dayanır: bölüm sayısı, her rakamın iki bağımsız
    kaynaktan doğrulanması, kaynakların kitapta yazılı olması, ücretsiz ve her yıl büyümesi. Her yeni baskının
    önizlemesiyle (25 Aralık) birlikte o baskıya uygun 2–3 tanıtım metni önerisi sunulur; site ve tanıtım Reels'i
    metni yalnız önizleme ve Rıdvan'ın onayıyla değişir.
  - **Kitabın tek takip yeri `rehber_pdf/DURUM.md`** (Rıdvan, 20 Ekim 2026): her bölüm ve ek için Instagram tarihi,
    uzun metin durumu (yok / yazılıyor · dal / önizlemede · dal / onaylandı), kontrol (kaynak · denetle) ve baskı yılı.
    Kitaba dokunan her iş (sohbetler, aylık rehber paketi, 25 Aralık baskı önizlemesi) işe başlamadan DURUM.md'yi okur
    ve durum her değiştiğinde günceller: başlarken main'de `yazılıyor · <dal>`, önizleme gidince `önizlemede`, onayla
    main'e alınırken `onaylandı`. `python bot/rehber_pdf.py denetle` dosyayı gerçek durumla karşılaştırır; hata
    verirken önizleme gösterme, main'e alma. GitHub'da `rehber-durum.yml` aynı denetimi bu dosyalara dokunan her itmede
    çalıştırır (Rıdvan, 20 Ekim 2026: "durum raporu ile github uyumlu olmalı"); kırmızıysa düzelt.
- Rehber arşivi Reels'i (Rıdvan, 17 Ekim 2026 "öneriyi uygula"): sesli rehber Reels'inden önce yayımlanan #3–#5 birer
  kez, aynı tam okumalı sesli Reels olarak gider; 19 Ekim 2026'dan beri haftalık rehber sırasında, çarşamba (Rıdvan:
  "rehber sırasına girsinler"; `bot/bilgi.py` → `ARSIV_SIRASI`: 11, 18 ve 25 Kasım, #7–#8'den sonra; tür `kisa`). Yalnız Reels: kaydırmalı ve hikâye tekrar gitmez; Reels üretilemezse o gün paylaşım
  yok. Tarih ya da bölüm değişecekse önce Rıdvan'a sor.
- "Rehber" öne çıkanının standardı (Rıdvan, 14 Ekim 2026): her bölüm tek video; öne çıkandaki sıra önemli değil,
  eksik olmaması önemli. Öne çıkana eklemeyi ve pazar analizini sabitlemeyi Rıdvan kendisi yapar; bunlar için hatırlatma
  görevi yok (Rıdvan, 25 Ekim 2026: "sabitleme görevini hatırlatmana gerek yok … Hatırlatmaları kaldır."; çarşamba ve pazar
  hatırlatmaları silindi). Yeniden kurma. Tek tek kare olarak giden eski #1–#2 yerine videoları 18 Ekim'de paylaşılır, eski
  kareleri Rıdvan siler. Rehber hikâyesini elle kareler hâlinde paylaşma.
- Claude API kredisi (pazar yorumu): bakiye Anthropic'ten okunamıyor, özel gumus-kayit deposundaki `api-bakiye.md`
  tahmin eder (bot/bakiye.py): yüklenen (Anthropic makbuz maillerinden, "credit purchase" satırı, KDV hariç) −
  harcanan (bot her yorumda kaydeder). Rıdvan kredi yüklemesini takip etmek istemiyor: makbuzları Claude'un
  "Claude API kredisi: Gmail makbuzları" zamanlanmış görevi işler (`python bot/bakiye.py yukleme --usd <kredi>
  --tarih <ISO> --kaynak "makbuz #<no>" --yerel <gumus-kayit klonu>/api-bakiye.md`, commit + push; aynı makbuz iki
  kez işlenmez). Rıdvan Billing'deki bakiyeyi kendisi söylerse `okuma` ile işle. Tutarları herkese açık yerlere
  (bu depo, iş akışı günlükleri, girdiler) yazma. Billing: https://platform.claude.com/settings/billing
- Dal temizliği otomatik (Rıdvan, 17 Ekim 2026: "Otomatiğe al"): `.github/workflows/dal-temizle.yml` her gece 03:17 TR'de
  içeriği tamamen main'de olan ve 24 saatten eski dalları siler; main'e alınmamış işi olan dala dokunmaz. Rıdvan'a
  dal silmesini söyleme. Onay bekleyen önizlemeyi main'e almadan ayrı dalda tutmak bu yüzden güvenli.
- Pazar yorumu **yalnız kısa ve orta vade, kalıcı** (Rıdvan, 17 Ekim 2026: "Kısa, orta, uzun yerine sadece kısa ve
  orta kalacak", "geleceği de etkilemeli"). Uzun vade hiçbir tarihte, veri birikse de geri gelmez; sesli okuma,
  müzikli video, Reels, kaydırmalı gönderi, cumartesi hatırlatması, bilgi sayfası hep kısa ve orta. Uzun vadeyi geri
  getiren tarih ya da koşul ekleme; yalnızca Rıdvan açıkça isterse. (Uzun vade için kurulan tek hatırlatma
  20 Ekim 2026 kota tasarrufuyla kapatıldı; yerine başka hatırlatma kurma.)
