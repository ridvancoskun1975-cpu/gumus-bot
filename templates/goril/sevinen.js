// Gümüş sırtlı goril maskotu: videoda hareket (bot her kare için window.kare(t) çağırır).
// Çağrılmazsa goril durağan görseldeki hâlinde kalır.
(function () {
  const svg = document.getElementById('goril-sevinen');
  if (!svg) return;
  const $ = id => document.getElementById(id);
  const hepsi = $('gr-hepsi'), govde = $('gr-govde'), kollar = $('gr-kollar'), ust = $('gr-ust'),
        bas = $('gr-bas'), golge = $('gr-golge'), isik = $('gr-isik'), parilti = $('gr-parilti'),
        cizgiSol = $('gr-cizgi-sol'), cizgiSag = $('gr-cizgi-sag');
  const konfeti = Array.from(svg.querySelectorAll('.gr-k')).map((k, i) => ({
    el: k, x: +k.dataset.x, y: +k.dataset.y, h: +k.dataset.h || 1, faz: (i * 0.37) % 1 }));
  const yildiz = Array.from(svg.querySelectorAll('.gr-p')).map(p => ({
    el: p, x: +p.dataset.x, y: +p.dataset.y, f: +p.dataset.f || 0 }));

  const GIRIS = 1.35, GIRIS_SURE = 0.45;   // fiyat sayımı bitince (hareket.js: 0,15–1,35 sn) goril fırlar
  const ZIPLAMA = 0.9;                     // bir zıplama, saniye
  const kenet = x => Math.min(Math.max(x, 0), 1);
  const geriTasma = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

  const onceki = window.kare;
  window.kare = function (t) {
    if (typeof onceki === 'function') onceki(t);

    // 1) Giriş: alttan yaylanarak büyür
    const g = kenet((t - GIRIS) / GIRIS_SURE);
    const s = g === 0 ? 0.0001 : geriTasma(g);
    hepsi.setAttribute('transform', `translate(160 345) scale(${s}) translate(-160 -345)`);

    // 2) Sevinç: zıplar, kolları külçeyle iner kalkar, başı sallanır
    const z = Math.max(t - (GIRIS + GIRIS_SURE), 0);
    const p = (z % ZIPLAMA) / ZIPLAMA;
    const yuk = z > 0 ? Math.sin(Math.PI * p) : 0;            // 0 yerde, 1 tepede
    const inis = z > 0 ? kenet(1 - yuk / 0.35) : 0;            // yere değerken basılma
    const sx = 1 + 0.045 * inis, sy = 1 - 0.055 * inis;
    govde.setAttribute('transform',
      `translate(0 ${-20 * yuk}) translate(160 334) scale(${sx} ${sy}) translate(-160 -334)`);
    const k = 1 + 0.09 * yuk;                                   // kollar omuzdan uzar
    kollar.setAttribute('transform', `translate(0 180) scale(1 ${k}) translate(0 -180)`);
    ust.setAttribute('transform', `translate(0 ${-(180 - 80) * (k - 1)})`);
    const egim = z > 0 ? 5 * Math.sin(2 * Math.PI * z / (ZIPLAMA * 2)) : 0;
    bas.setAttribute('transform', `rotate(${egim} 160 178)`);
    golge.setAttribute('transform', `translate(160 338) scale(${1 - 0.28 * yuk} 1) translate(-160 -338)`);
    golge.setAttribute('opacity', (0.45 - 0.2 * yuk).toFixed(3));

    // 3) Işık atar, külçe parlar, sallanma çizgileri yanıp söner
    isik.setAttribute('opacity', (0.75 + 0.25 * Math.sin(2 * Math.PI * t / 1.8)).toFixed(3));
    parilti.setAttribute('opacity', (0.35 + 0.65 * Math.abs(Math.sin(Math.PI * t / 1.3))).toFixed(3));
    const c = 0.5 + 0.5 * Math.sin(2 * Math.PI * z / (ZIPLAMA / 2));
    cizgiSol.setAttribute('opacity', z > 0 ? (0.25 + 0.75 * c).toFixed(3) : 0);
    cizgiSag.setAttribute('opacity', z > 0 ? (0.25 + 0.75 * (1 - c)).toFixed(3) : 0);

    // 4) Pırıltılar yanıp söner
    yildiz.forEach(y => {
      const o = Math.abs(Math.sin(Math.PI * (t / 1.1 + y.f)));
      y.el.setAttribute('transform', `translate(${y.x} ${y.y}) scale(${0.35 + 0.75 * o}) rotate(${45 * o}) translate(${-y.x} ${-y.y})`);
    });

    // 5) Konfeti yukarıdan yağar, dönerek
    konfeti.forEach(q => {
      const hiz = 70 * q.h;                                     // birim/sn
      const ust = q.x < 70 ? 60 : 0, H = 340 - ust;            // soldakiler manşetin hizasına girmesin
      const yeniY = ust + ((q.y - ust + hiz * t + q.faz * H) % H + H) % H;
      const dx = 6 * Math.sin(2 * Math.PI * (t * 0.8 + q.faz));
      q.el.setAttribute('transform',
        `translate(${dx} ${yeniY - q.y}) rotate(${(t * 220 * q.h + q.faz * 360) % 360} ${q.x} ${q.y})`);
    });
  };
})();
