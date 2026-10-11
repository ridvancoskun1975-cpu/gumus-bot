# Gümüş Fiyat Botu

Hafta içi her gün Instagram'a otomatik paylaşım yapar:

| Saat (TR) | Paylaşım |
|---|---|
| ~10:00 | Reels (7 sn video) |
| ~17:00 | Reels (7 sn video) |
| ~20:00 | Feed postu (günün özeti) |

Her paylaşımda: **gram gümüş (₺)**, **altın/gümüş paritesi**, **dolar/TL** ve her birinin önceki gün kapanışına göre değişimi (ok ile).

Hafta sonu ons gümüş işlem görmediği için paylaşım yapılmaz. GitHub zamanlı işleri genelde 5-15 dakika gecikmeyle başlatır.

---

## Kurulum (bir kerelik)

### 1. Instagram hesabını profesyonel hesaba çevir
Instagram → Ayarlar → **Hesap türü ve araçlar** → **Profesyonel hesaba geç** → İşletme ya da İçerik Üretici.

### 2. Meta'dan erişim anahtarı (token) al
1. Bilgisayardan **developers.facebook.com** adresine Facebook hesabınla gir, **Uygulamalarım → Uygulama oluştur**.
2. Kullanım alanı olarak **Instagram API** ile içerik yönetimini seç (Instagram'da mesaj ve içerik yönetimi).
3. Uygulama panelinde **Instagram → API setup with Instagram login** bölümüne gir.
4. **Add account** ile kendi Instagram hesabını ekle ve izin ver.
5. Hesabın yanındaki **Generate token** ile anahtarı oluştur ve bir yere kopyala. (`instagram_business_basic` ve `instagram_business_content_publish` izinleri açık olmalı.)

> Meta menü adlarını zaman zaman değiştiriyor; adımlar birebir aynı görünmeyebilir.

### 3. GitHub ayarları
Bu depo **herkese açık (Public)** olmalı. Görseller ücretsiz GitHub Pages üzerinden Instagram'a verilir; gizli bilgiler (token) yine de güvende kalır.

1. **Settings → Pages → Source:** `GitHub Actions` seç.
2. **Settings → Secrets and variables → Actions → New repository secret:**
   - `IG_TOKEN` → 2. adımda aldığın anahtar
   - `GH_PAT` → token'ın otomatik yenilenmesi için (aşağıya bak)
3. (İsteğe bağlı) Aynı sayfada **Variables** sekmesi → `HESAP_ADI` → görsellerde yazacak kullanıcı adı. Boş bırakırsan bot hesabından otomatik alır.

**GH_PAT nasıl alınır:** GitHub → sağ üstte profil → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Repository access: sadece bu depo. Permissions → **Secrets: Read and write**. Süreyi en uzun seç, oluşan anahtarı `GH_PAT` olarak kaydet.

### 4. Dene
1. **Actions** sekmesi → **Gümüş paylaşımı** → **Run workflow**.
2. `tur`: reels, `deneme`: işaretli bırak → çalıştır.
3. İş bitince sayfanın altındaki **onizleme-reels** dosyasını indirip videoya bak.
4. Her şey doğruysa `deneme` işaretini kaldırıp tekrar çalıştır: bu sefer Instagram'a gerçekten paylaşır.

Bundan sonra bot kendi kendine çalışır.

---

## Notlar
- **Veri kaynağı:** Yahoo Finance (ons gümüş `SI=F`, ons altın `GC=F`, dolar/TL `TRY=X`). Bunlar vadeli işlem fiyatlarıdır, spot fiyata çok yakındır. Gram gümüş TL fiyatı `ons gümüş × dolar/TL ÷ 31,1035` ile hesaplanır; Kapalıçarşı ya da banka alış-satış fiyatlarından biraz farklı olabilir.
- **Müzik:** Otomatik paylaşımda Instagram'ın müzik kütüphanesi kullanılamaz. Telifsiz bir müziği `assets/muzik.mp3` adıyla eklersen videolara otomatik konur.
- **Saatleri değiştirmek:** `.github/workflows/paylas.yml` içindeki `cron` satırları. Saatler UTC'dir (TR saati − 3). Post saatini değiştirirsen aynı dosyadaki `"50 16 * * 1-5"` kontrolünü de güncelle.
- **Tasarım:** `templates/reels.html` ve `templates/post.html`.
- Yazı tipleri (Archivo, JetBrains Mono) SIL Open Font License ile dağıtılır, lisansları `assets/fonts` içinde.
