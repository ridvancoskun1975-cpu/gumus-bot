# PDF Gümüş Rehberi: uzun bölüm metinleri nasıl yazılır

Rıdvan, 19 Ekim 2026: "kısa olan bilgiler pdf te eksiksiz doyurucu olmalı." Instagram'daki her rehber bölümünün
(`bot/bilgi.py` → `BOLUMLER`) PDF'te uzun, eksiksiz bir hâli vardır: `rehber_pdf/bolum-NN.html` (NN iki haneli bölüm
numarası). Kitabı `bot/rehber_pdf.py` derler (`templates/rehber-pdf.html`). Örnek ve ölçü: `bolum-02.html` (Rıdvan'ın
"uygundur" dediği önizleme).

## Ne zaman yazılır

- Yeni bölümler: aylık rehber paketiyle birlikte (her ayın 25'i). Bölümün kısa hâli `BOLUMLER`'e girerken uzun hâli de
  bu klasöre girer; ikisi aynı iki kontrolden geçer (paket görevi).
- Baskı: yılda bir, 1 Ocak ("2027 baskısı"; Rıdvan, 19 Ekim 2026: "1 yıl"). Baskıya o tarihe kadar Instagram'da
  yayımlanmış bölümler girer; yayımlanmamış bölüm girmez (Reels'in önüne geçmesin).

## İçerik kuralları

1. Sade Türkçe; okuyucu gümüşe ilgi duyan, uzman olmayan yetişkin. Kısa cümleler, somut örnekler.
2. Uzunluk: yaklaşık 800–1100 kelime (A5'te 4–7 sayfa). Başlık Instagram'daki soruyla aynıdır (şablon yazar).
3. Instagram'daki kısa hâlle çelişme; onu genişlet: neden, nasıl, örnek, tablo, sık yapılan hata.
4. Her rakam ve iddia en az iki bağımsız, güvenilir kaynaktan doğrulanır (kaynağı gerçekten aç). `bot/ayrintili.py`'deki
   doğrulanmış rakamlarla (World Silver Survey, USGS) tutarlı ol; farklı bir yıl/rapor kullanıyorsan açıkça yaz.
5. Güncel fiyat yazılmaz. Örnek rakamlar "örnek" diye belirtilir. Geçmişe ait rakamlar tarihleriyle yazılır.
6. Yatırım tavsiyesi yok: "alın/satın/yükselecek/fırsat" gibi yönlendirme ve tahmin yok. Gerekirse "bilgi amaçlıdır".
7. Rıdvan'ın kararları: 925/800 ayar ve takı odaklı içerik yok (kısa bir değinme olabilir, Bölüm 3'teki kadar); zekât
   nisabı ve çeyrek altın yok; model ya da şirket adı (yapay zekâ sağlayıcıları) yok.
8. Vergi, mevzuat gibi değişebilen konularda oran ya da kural yazacaksan yalnızca resmî kaynaktan, tarihiyle; emin
   değilsen genel anlat ve "işlemden önce sorun" de.
9. Başka bölümlere "Bölüm N" diye gönderme yapılabilir (yalnız var olan bölümlere).

## Biçim (HTML parçası)

Dosya giriş paragrafıyla başlar; bölüm açılışını ve bölüm sonu notunu şablon yazar. Yalnız aşağıdaki yapı taşları
kullanılır (stilleri şablonda; yeni sınıf uydurma, satır içi stil kullanma):

| Yapı taşı | Ne için |
|---|---|
| `<p class="giris">` | Bölümün ilk paragrafı (biraz büyük yazı) |
| `<div class="formul-kutu">` + `.etiket`, `.formul`, `.not` | Kısa cevap, formül ya da tek büyük bilgi (koyu kutu) |
| `<h3><span class="num">1</span>Başlık</h3>` | Alt başlıklar, 1'den sırayla (4–8 tane) |
| `<p>`, `<b>` | Metin |
| `<div class="parca"><div class="rozet">…</div><p>…</p></div>` | Kısa etiketli açıklama satırları (`.rozet.koyu` vurgulu) |
| `<table class="tablo">` (`th`, `td.r` sağa yaslı, `tr.son` kalın son satır, `td.adim`) | Tablolar |
| `<table class="izgara">` | Satır × sütun hızlı bakış tablosu |
| `<p class="aciklama">`, `<span class="aciklama">` | Tablo altı ya da hücre içi küçük not |
| `<div class="birlikte">` | İçindekiler aynı sayfada kalsın (ör. başlık + tablo); satır içi stil yerine bu |
| `<div class="not-kutu">` | Önemli bir gözlem (sol çizgili kutu) |
| `<ol class="hatalar"><li><b>Başlık</b>Açıklama</li></ol>` | Sık yapılan hatalar |
| `<ul class="duz">` | Madde listesi |
| `<div class="deneme">` + `.etiket` "KENDİNİZ DENEYİN", `<p>`, `.cevap` | İsteğe bağlı alıştırma |
| `<div class="akilda">` + `.etiket` "AKILDA KALSIN", `<ul>` (3 madde) | Her bölümün sonunda zorunlu özet |
| `<p class="kaynaklar">Kaynak: …</p>` | Okuyucuya kaynak adları (yıl/rapor adıyla) |

Kaynakların adresleri ikinci kontrol için dosyanın sonunda yorum satırı olarak durur (PDF'te görünmez):

```html
<!-- KAYNAK: https://… — hangi bilgi için -->
```

## Kontrol

`python bot/rehber_pdf.py denetle` bütün parçaları denetler (izinli yapı taşları, akılda kalsın kutusu, kelime sayısı,
kaynak yorumları). `python bot/rehber_pdf.py uret --cikti <dosya.pdf> --tarih 2027-01-01 [--onizleme]` kitabı üretir.
