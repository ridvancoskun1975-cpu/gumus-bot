// Somurtan goril (sert düşüş günü): kollarını kavuşturup oturur, başının üstünde yağmur bulutu.
// Yalnızca duygu gösterir; "al", "fırsat", "tut" gibi bir çağrışım taşımaz.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa durağan görseldeki hâlinde kalır.
(function () {
  const svg = document.getElementById('goril-somurt');
  if (!svg) return;
  const $ = id => document.getElementById(id);
  const hepsi = $('gs-hepsi'), govde = $('gs-govde'), bas = $('gs-bas'), isik = $('gs-isik-el'),
        bulutGrup = $('gs-bulut-grup'), bulut = $('gs-bulut');
  const damlalar = Array.from(svg.querySelectorAll('.gs-d')).map(d => ({ el: d, f: +d.dataset.f || 0 }));

  const GIRIS = 1.35, GIRIS_SURE = 0.45, T0 = GIRIS + GIRIS_SURE;
  const BULUT = 1.95, BULUT_SURE = 0.5, YAGMUR = BULUT + 0.35;
  const UST = 70, BOY = 40;                          // damlalar bulutun altından başın üstüne düşer
  const kenet = x => Math.min(Math.max(x, 0), 1);
  const yum = x => { x = kenet(x); return x * x * (3 - 2 * x); };
  const geriTasma = x => { const c1 = 1.2, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

  const onceki = window.kare;
  window.kare = function (t) {
    if (typeof onceki === 'function') onceki(t);

    // 1) Giriş: yerine çöker gibi belirir
    const g = kenet((t - GIRIS) / GIRIS_SURE);
    const s = g === 0 ? 0.0001 : geriTasma(g);
    hepsi.setAttribute('transform', `translate(160 345) scale(${s}) translate(-160 -345)`);

    // 2) İç çeker, başını iki yana sallar
    const z = Math.max(t - T0, 0);
    govde.setAttribute('transform',
      `translate(160 336) scale(1 ${(1 + 0.022 * Math.sin(2 * Math.PI * z / 2.6)).toFixed(4)}) translate(-160 -336)`);
    bas.setAttribute('transform', `rotate(${(4 * Math.sin(2 * Math.PI * z / 2.4)).toFixed(2)} 160 196)`);
    isik.setAttribute('opacity', (0.8 + 0.2 * Math.sin(2 * Math.PI * t / 2.6)).toFixed(3));

    // 3) Bulut yukarıdan gelir, hafifçe salınır
    const b = yum((t - BULUT) / BULUT_SURE);
    bulutGrup.setAttribute('opacity', b.toFixed(3));
    bulutGrup.setAttribute('transform', `translate(${(4 * Math.sin(2 * Math.PI * t / 3)).toFixed(2)} ${(-60 * (1 - b) + 2 * Math.sin(2 * Math.PI * t / 2)).toFixed(2)})`);
    bulut.setAttribute('transform', `translate(160 45) scale(${(1 + 0.025 * Math.sin(2 * Math.PI * t / 1.7)).toFixed(4)}) translate(-160 -45)`);

    // 4) Yağmur
    damlalar.forEach(d => {
      if (t < YAGMUR) { d.el.setAttribute('opacity', 0); return; }
      const r = ((t - YAGMUR) * 1.6 + d.f) % 1;     // 0 bulutta, 1 başta
      d.el.setAttribute('y', (UST + BOY * r).toFixed(1));
      d.el.setAttribute('opacity', (r < 0.12 ? r / 0.12 : 1 - Math.pow(r, 4)).toFixed(3));
    });
  };
})();
