# Site tanıtım (reklam) videosu — kaynaklar

2 Kasım 2026. Rıdvan: "3 boyutlu gümüş etrafında dönen kamera … sloganlar … takip edin"; metin "Gümüş sırtlı goril takipte. Ya siz?", açılış "Gümüş bugün kaç lira?" (Rıdvan "2"); ses Orus (Rıdvan "Ses 1"), hız 1,15, reklam spikeri üslubu; dikey 9:16.

- `kulce.html` — 1. sahne (0–5 sn): Three.js ile gümüş külçe piramidi, 13 Ekim 3B profil resmindeki gibi (döküm biçimi: üst geniş alt dar; canvas ile çizilen "SILVER 999.9 FINE" damgası ve çerçeve, kabartma + pürüz haritası; uzun kenar derinlikte, 3-2-1), soldan dolaşan kamera, stüdyo ışık çevresi (Rıdvan 2 Kasım 15:38: "Böyle bir külçe standardı yok").
- `sahne2.html` — 2. sahne (5–11 sn): program (~10:00 güncel fiyat, ~20:00 günün özeti, pazar üst düzey yapay zekâ analizi; kısa ve orta vade).
- `sahne3.html` — 3. sahne (11–16 sn): "Gümüş sırtlı goril takipte. Ya siz?", istifçi goril (templates/goril/istif.svg/js kopyası), Takip edin, @hesap, site, yasal satır + "Seslendirme: yapay zekâ".
- `render.mjs` — sahneyi 30 fps JPEG kare akışıyla ffmpeg'e çizer (`node render.mjs <html> <sn> <mp4> [fadein] [fadeout]`); `kare.mjs` tek kare.
- Ses: `python bot/ses.py ornek --sesler Orus --metin "a || b || c || d" --hiz 1.15 --uslup "<reklam üslubu>"` (ses-ornek.yml iş akışı; parçalar 0,8 / 5,3 / 11,2 / 13,9 sn'ye yerleştirildi).
- Müzik: gumus-kayit/muzik Motivate (NastelBom, Pixabay), 1:47'den 16 sn, %20 ses. Geçiş sesleri: Mixkit (whoosh-fast, transition-snap; Mixkit SFX Free License).
- Çalışma ortamı: Playwright Chromium (`--use-gl=angle --use-angle=swiftshader --allow-file-access-from-files`), `npm i three@0.170.0`, fontlar assets/fonts, goril templates/goril.
- Yatay (16:9) sürüm: `*-yatay.html` sahneleri, `W=1920 H=1080` ile render; ses izi dikey videodan kopyalanır (Rıdvan 2 Kasım 13:50: "Instagram reklamı ve Google reklamı olarak").

## 3. sürüm (2 Kasım 2026 akşamı): gerçek ışık hesabıyla külçeler
Rıdvan (16:00 "Ters", 16:04 "Ben kaliteli parlak net gümüş külçeler etrafında dönen kamera istiyorum."): Three.js
külçeleri hem ters (üst geniş) hem plastik görünüyordu. 1. sahne artık 13 Ekim 3B profil resmiyle aynı yöntemle,
Mitsuba 3 ile çiziliyor:
- `mts/sahne.py` — külçe modeli (8 kürenin dışbükey zarfı: taban geniş, üst yüz dar, yuvarlak kenar), "SILVER /
  999.9 FINE" oyma damga (kabartma + pürüz haritası), kamerayla dönen stüdyo ortamı (kameranın gördüğü bölge siyah),
  kamera yolu (dikey ve yatay).
- `mts/cizer.py` — kare kare çizim: A geçişi külçeler + siyah zemin; B geçişi aynalanmış kameradan zemin yansıması
  (yalnız külçeler, zemine doğru solar). Intel Open Image Denoise (pyoidn) ile gürültü giderme. Önemli: film süzgeci
  `box` olmalı (Gauss süzgeci gürültüyü komşu piksellere yayıyor, gürültü giderici çalışmıyor). %80 boyutta çizip
  büyütür; 24/8 örnek, ~14 sn/kare (2 çekirdek).
  `python cizer.py dikey 0 150 ../kareler/dikey 24 8` (yarıda kalırsa kaldığı yerden sürer).
- `katman-dikey.html`, `katman-yatay.html` — çizilen karelerin üstüne "Gümüş bugün kaç lira?" yazı katmanı;
  `node render.mjs katman-dikey.html 5 s1.mp4 0.4 0.25` ile 1. sahne videosu.
- Kurulum: `pip install mitsuba trimesh manifold3d pyoidn`.
