// Özel gün gorili (eşik aşıldı / en az bir aylık en yüksek): külçe kürsüsünün tepesine iner,
// göğsünü yumruklar, sonra iki yumruğunu havaya kaldırır; arkada havai fişekler patlar.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa durağan zafer pozu çizilir.
(function () {
  const svg = document.getElementById('goril-ozel');
  if (!svg) return;
  const NS = 'http://www.w3.org/2000/svg';
  const $ = id => document.getElementById(id);
  const hepsi = $('go-hepsi'), isik = $('go-isik-el'), kursu = $('go-kursu'), kursuParilti = $('go-kursu-parilti'),
        goril = $('go-goril'), bas = $('go-bas'), kukre = $('go-agiz-kukre'), gulus = $('go-agiz-gulus'),
        darbe = [$('go-darbe-sol'), $('go-darbe-sag')], fisekKap = $('go-fisekler');
  const kollar = ['go-kol-sol', 'go-kol-sag'].map(id => {
    const g = $(id);
    return { dis: g.querySelector('.go-kol-dis'), ic: g.querySelector('.go-kol-ic'),
             isik: g.querySelector('.go-kol-isik'), yumruk: g.querySelector('.go-yumruk') };
  });

  const kenet = x => Math.min(Math.max(x, 0), 1);
  const yum = x => { x = kenet(x); return x * x * (3 - 2 * x); };
  const ara = (a, b, u) => a + (b - a) * u;
  const nokta = (a, b, u) => [ara(a[0], b[0], u), ara(a[1], b[1], u)];
  const geriTasma = x => { const c1 = 1.4, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

  // ---- kollar: sol kol koordinatları; sağ kol x → 320 − x aynası
  const OMUZ = [110, 178];
  const GERI = { c: [46, 224], f: [106, 200] };     // yumruk göğüsten uzakta
  const VUR = { c: [58, 240], f: [138, 208] };      // yumruk göğüste
  const YUKARI = { c: [58, 130], f: [100, 74] };    // zafer: yumruklar havada
  const MERKEZ = [160, 220];

  function kolCiz(k, sag, h, r) {
    const ayna = p => sag ? [320 - p[0], p[1]] : p;
    const vC = nokta(GERI.c, VUR.c, h), vF = nokta(GERI.f, VUR.f, h);
    const S = ayna(OMUZ), C = ayna(nokta(vC, YUKARI.c, r)), F = ayna(nokta(vF, YUKARI.f, r));
    const d = `M${S[0]} ${S[1]} Q${C[0].toFixed(1)} ${C[1].toFixed(1)} ${F[0].toFixed(1)} ${F[1].toFixed(1)}`;
    k.dis.setAttribute('d', d); k.ic.setAttribute('d', d);
    k.yumruk.setAttribute('transform', `translate(${F[0].toFixed(1)} ${F[1].toFixed(1)})`);
    // dış kenarda ince gümüş parıltı
    const p = [];
    for (let i = 0; i <= 6; i++) {
      const t = 0.18 + 0.44 * i / 6, a = 1 - t;
      const x = a * a * S[0] + 2 * a * t * C[0] + t * t * F[0], y = a * a * S[1] + 2 * a * t * C[1] + t * t * F[1];
      let tx = 2 * a * (C[0] - S[0]) + 2 * t * (F[0] - C[0]), ty = 2 * a * (C[1] - S[1]) + 2 * t * (F[1] - C[1]);
      const L = Math.hypot(tx, ty) || 1; let nx = -ty / L, ny = tx / L;
      if (nx * (x - MERKEZ[0]) + ny * (y - MERKEZ[1]) < 0) { nx = -nx; ny = -ny; }
      p.push(`${(x + 12 * nx).toFixed(1)} ${(y + 12 * ny).toFixed(1)}`);
    }
    k.isik.setAttribute('d', 'M' + p.join(' L'));
    return F;
  }

  // ---- havai fişekler
  const YERLER = [[72, -36, 50], [250, -52, 54], [160, -78, 46], [52, 26, 40], [272, 14, 42], [110, -70, 44], [214, -22, 48]];
  const RENK = ['#5BC98C', '#EDEFF2', '#C9D1DA'];
  const GIRIS = 1.35, INIS = 1.45, INIS_SURE = 0.35, T0 = 2.0, DONGU = 2.3;
  const zamanlar = [1.75];
  for (let k = 0; T0 + k * DONGU < 10.5; k++) { zamanlar.push(T0 + k * DONGU + 0.55, T0 + k * DONGU + 1.3); }
  const fisekler = zamanlar.map((z, i) => {
    const [x, y, R] = YERLER[i % YERLER.length];
    const g = document.createElementNS(NS, 'g');
    const iz = document.createElementNS(NS, 'line');
    iz.setAttribute('stroke', '#EDEFF2'); iz.setAttribute('stroke-width', '2.5'); iz.setAttribute('stroke-linecap', 'round');
    g.appendChild(iz);
    const parca = [];
    const n = 16, renk = RENK[i % RENK.length];
    const parla = document.createElementNS(NS, 'circle');
    parla.setAttribute('fill', '#FFFFFF');
    g.appendChild(parla);
    for (let j = 0; j < n; j++) {
      const c = document.createElementNS(NS, 'line');
      c.setAttribute('stroke', j % 4 === 3 ? '#FFFFFF' : renk);
      c.setAttribute('stroke-width', '4'); c.setAttribute('stroke-linecap', 'round');
      g.appendChild(c);
      parca.push({ el: c, a: 2 * Math.PI * j / n + 0.21 * i, s: 0.8 + 0.2 * ((j * 7) % 5) / 4 });
    }
    fisekKap.appendChild(g);
    return { z, x, y, R, iz, parca, parla };
  });

  function fisekCiz(f, e, izU) {
    // izU: yükselen iz (0–1) ya da null; e: patlama ilerlemesi (0–1) ya da null
    if (izU !== null) {
      const y0 = f.y + 90, yy = ara(y0, f.y, yum(izU));
      f.iz.setAttribute('x1', f.x); f.iz.setAttribute('x2', f.x);
      f.iz.setAttribute('y1', (yy + 16).toFixed(1)); f.iz.setAttribute('y2', yy.toFixed(1));
      f.iz.setAttribute('opacity', 0.8);
    } else f.iz.setAttribute('opacity', 0);
    if (e === null || e > 0.2) f.parla.setAttribute('opacity', 0);
    else { f.parla.setAttribute('cx', f.x); f.parla.setAttribute('cy', f.y);
           f.parla.setAttribute('r', (6 + 10 * e / 0.2).toFixed(1)); f.parla.setAttribute('opacity', (0.9 * (1 - e / 0.2)).toFixed(3)); }
    f.parca.forEach(p => {
      if (e === null) { p.el.setAttribute('opacity', 0); return; }
      const g = 1 - Math.pow(1 - e, 3);
      const r2 = f.R * p.s * g, r1 = r2 * (0.35 + 0.4 * e), dus = 16 * e * e;
      p.el.setAttribute('x1', (f.x + r1 * Math.cos(p.a)).toFixed(1));
      p.el.setAttribute('y1', (f.y + r1 * Math.sin(p.a) + dus).toFixed(1));
      p.el.setAttribute('x2', (f.x + r2 * Math.cos(p.a)).toFixed(1));
      p.el.setAttribute('y2', (f.y + r2 * Math.sin(p.a) + dus).toFixed(1));
      p.el.setAttribute('stroke-width', (4.2 - 2.4 * e).toFixed(2));
      p.el.setAttribute('opacity', (e < 0.45 ? 1 : 1 - (e - 0.45) / 0.55).toFixed(3));
    });
  }

  function ciz(t) {
    const duragan = t === null;
    // giriş: kürsü belirir, goril yukarıdan iner
    const kG = duragan ? 1 : kenet((t - GIRIS) / 0.28);
    hepsi.setAttribute('opacity', duragan || t >= GIRIS ? 1 : 0);
    isik.setAttribute('opacity', duragan ? 1 : (kenet((t - GIRIS) / 0.4) * (0.8 + 0.2 * Math.sin(2 * Math.PI * t / 1.8))).toFixed(3));
    kursu.setAttribute('transform', `translate(160 350) scale(${kG === 0 ? 0.0001 : geriTasma(kG)}) translate(-160 -350)`);

    let dy = 0, ezil = 0, h = [0, 0], r = 1, hop = 0, kukreme = 0, egim = 0;
    if (!duragan) {
      if (t < INIS) { dy = -400; }
      else if (t < INIS + INIS_SURE) { const u = (t - INIS) / INIS_SURE; dy = -260 * (1 - u * u); r = 1; }
      else if (t < T0) { ezil = Math.sin(Math.PI * kenet((t - INIS - INIS_SURE) / 0.2)); r = 1; }
      else {
        const p = (t - T0) % DONGU;
        if (p < 1.3) {                                        // göğüs yumruklama
          r = p < 0.15 ? 1 - yum(p / 0.15) : 0;
          kukreme = 1;
          [0, 0.15].forEach((ofs, i) => {
            const u = (((p - ofs) % 0.3) + 0.3) % 0.3 / 0.3;
            h[i] = p < ofs ? 0 : (u < 0.35 ? 1 - yum(u / 0.35) : (u > 0.6 ? yum((u - 0.6) / 0.4) : 0));
            const v = u / 0.28, vurdu = p >= ofs && u < 0.28 && p < 1.2;
            darbe[i].setAttribute('opacity', vurdu ? (1 - v).toFixed(3) : 0);
            darbe[i].setAttribute('r', (18 + 20 * v).toFixed(1));
            darbe[i].setAttribute('stroke-width', (5 - 4 * v).toFixed(2));
          });
          ezil = 0.25 * Math.max(h[0], h[1]) * (p < 1.15 ? 1 : 0);
          egim = -3 + 3 * Math.sin(2 * Math.PI * p / 0.3);
        } else {                                              // zafer: yumruklar havada, bir zıplama
          darbe.forEach(d => d.setAttribute('opacity', 0));
          r = p < 1.5 ? yum((p - 1.3) / 0.2) : (p < 2.1 ? 1 : 1 - yum((p - 2.1) / 0.2));
          if (p >= 1.5 && p < 2.1) hop = Math.sin(Math.PI * (p - 1.5) / 0.6);
          kukreme = p > 2.15 ? 1 : 0;
        }
      }
    } else { darbe.forEach(d => d.setAttribute('opacity', 0)); }
    const sx = 1 + 0.05 * ezil, sy = 1 - 0.06 * ezil;
    // inişten önce görünmez (yukarıda beklerken fiyatın sağındaki Ag rozetinin üstüne binmesin)
    goril.setAttribute('opacity', !duragan && t < INIS ? 0 : 1);
    goril.setAttribute('transform',
      `translate(0 ${(dy - 22 * hop).toFixed(2)}) translate(160 334) scale(${sx.toFixed(4)} ${sy.toFixed(4)}) translate(-160 -334)`);
    [kolCiz(kollar[0], false, h[0], r), kolCiz(kollar[1], true, h[1], r)].forEach((F, i) => {
      darbe[i].setAttribute('cx', F[0].toFixed(1)); darbe[i].setAttribute('cy', F[1].toFixed(1));
      if (r > 0.2) darbe[i].setAttribute('opacity', 0);
    });
    bas.setAttribute('transform', `rotate(${egim.toFixed(2)} 160 178)`);
    kukre.setAttribute('opacity', kukreme);
    gulus.setAttribute('opacity', 1 - kukreme);

    // kürsünün üst külçelerinde parıltı geçer
    const gp = duragan ? null : ((t - GIRIS) % DONGU) / 0.6;
    if (gp !== null && gp >= 0 && gp <= 1) {
      kursuParilti.setAttribute('transform', `translate(${(40 + 250 * gp).toFixed(1)} 306)`);
      kursuParilti.setAttribute('opacity', (0.6 * Math.sin(Math.PI * gp)).toFixed(3));
    } else kursuParilti.setAttribute('opacity', 0);

    // havai fişekler
    fisekler.forEach((f, i) => {
      if (duragan) { fisekCiz(f, i === 1 || i === 2 ? 0.4 : null, null); return; }
      const izU = t >= f.z - 0.3 && t < f.z ? (t - (f.z - 0.3)) / 0.3 : null;
      const e = t >= f.z && t < f.z + 0.95 ? (t - f.z) / 0.95 : null;
      fisekCiz(f, e, izU);
    });
  }

  ciz(null);
  const onceki = window.kare;
  window.kare = function (t) { if (typeof onceki === 'function') onceki(t); ciz(t); };
})();
