// Video için hareket (reels, günlük özet ve haftalık özet şablonları bunu içerir).
// Bot her kare için window.kare(t) çağırır (t saniye). Çağrılmazsa sayfa son hâlinde kalır;
// PNG ve kapak bu son hâlden alınır. Gösterilen her sayı gerçek veridir: fiyat önceki
// değerden (önceki iş günü ya da önceki hafta) bugünkü değere sayar.
(function () {
  const fiyat = document.getElementById('fiyat');
  if (!fiyat) return;
  const hedef = parseFloat(fiyat.dataset.hedef), once = parseFloat(fiyat.dataset.once);
  if (!isFinite(hedef) || !isFinite(once)) return;   // veri yoksa hareket yok, durağan video
  const deg = document.getElementById('fiyat-deg');
  const nokta = document.getElementById('nokta');
  const manset = document.getElementById('manset');
  const isik = document.querySelector('.isik');
  const satirlar = Array.from(document.querySelectorAll('.satir'));
  const cizgi = document.getElementById('grafik-cizgi');
  const uzunluk = cizgi ? cizgi.getTotalLength() : 0;
  const grafikNoktalar = Array.from(document.querySelectorAll('.grafik-nokta'));
  const bicim = x => x.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const yumusak = p => 1 - Math.pow(1 - Math.min(Math.max(p, 0), 1), 3);
  const ara = (t, a, b) => yumusak((t - a) / (b - a));

  window.kare = function (t) {
    // 1) Fiyat önceki değerden bugüne sayar
    fiyat.textContent = bicim(once + (hedef - once) * ara(t, 0.15, 1.35));
    // 2) Değişim rozeti sayım bitince belirir
    if (deg) {
      const d = ara(t, 1.25, 1.6);
      deg.style.opacity = d;
      deg.style.transform = `scale(${0.6 + 0.4 * d})`;
    }
    // 3) Parite ve dolar sırayla kayarak gelir
    satirlar.forEach((s, i) => {
      const q = ara(t, 0.35 + 0.2 * i, 0.9 + 0.2 * i);
      s.style.opacity = q;
      s.style.transform = `translateY(${(1 - q) * 48}px)`;
    });
    // 4) Haftalık grafik soldan sağa çizilir, günler çizgi ulaştıkça belirir
    if (cizgi) {
      const c = Math.min(Math.max((t - 0.5) / 1.8, 0), 1);
      cizgi.style.strokeDasharray = uzunluk;
      cizgi.style.strokeDashoffset = uzunluk * (1 - c);
      grafikNoktalar.forEach(n => {
        const o = parseFloat(n.dataset.oran) || 0;
        n.style.opacity = Math.min(Math.max((c - o) / 0.08 + 1, 0), 1);
      });
    }
    // 5a) Büyük hareket manşeti ilk kareden görünür, dikkat çekmek için hafifçe atar
    if (manset) manset.style.transform = `scale(${1 + 0.035 * (0.5 - 0.5 * Math.cos(2 * Math.PI * t / 1.2))})`;
    // 5) Başlıktaki nokta canlı yayın gibi atar
    if (nokta) nokta.style.opacity = 0.35 + 0.65 * (0.5 + 0.5 * Math.cos(2 * Math.PI * t / 1.2));
    // 6) Gümüş parıltısı ekranı iki kez çapraz geçer
    if (isik) {
      const gecis = a => { const r = (t - a) / 1.3; return r >= 0 && r <= 1 ? r : null; };
      const r = gecis(2.4) ?? gecis(5.2);
      isik.style.transform = r === null ? 'translateX(-140%)' : `translateX(${-140 + 280 * r}%)`;
    }
  };
})();
