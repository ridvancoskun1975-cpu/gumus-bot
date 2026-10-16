// Gezinen goril (sakin gün ya da küçük düşüş): iki ayağı üstünde volta atar. Sağdan girip sola
// yürür, durup döner, sağa yürür, yine döner, ortada durup izleyiciye bakar. Fiyata değmez:
// sol sınır SOL_SINIR (sahne birimi), sağ sınır görselin kenarı.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa durağan yürüyüş pozu çizilir.
(function () {
  const svg = document.getElementById('goril-gezinen');
  if (!svg) return;
  const $ = id => document.getElementById(id);
  const yer = $('gz-yer'), ust = $('gz-ust'), bas = $('gz-bas'), gozbebek = $('gz-gozbebek'),
        gozler = $('gz-gozler'), kirpma = $('gz-kirpma'), golge = $('gz-golge'),
        bacakSol = $('gz-bacak-sol'), bacakSag = $('gz-bacak-sag'), kolSol = $('gz-kol-sol'), kolSag = $('gz-kol-sag');

  const kenet = x => Math.min(Math.max(x, 0), 1);
  const yum = x => { x = kenet(x); return x * x * (3 - 2 * x); };
  const SOL_SINIR = -10, SAG_SINIR = 100, ORTA = 30, ADIM = 120;  // ADIM: iki adımlık döngüde alınan yol

  // yürüyüş bölümleri: [başlangıç sn, bitiş sn, başlangıç x, bitiş x]
  const YOL = [
    [1.35, 3.5, 380, SOL_SINIR],      // sağdan girer, sola yürür
    [4.1, 6.0, SOL_SINIR, SAG_SINIR], // döner, sağa yürür
    [6.6, 8.2, SAG_SINIR, ORTA],      // döner, ortaya gelir
  ];
  const KIRP = [3.8, 8.8];

  function konum(t) {
    // x, o ana dek yürünen toplam yol, anlık hız (birim/sn) ve yön (-1 sol, +1 sağ, 0 duruyor)
    let x = YOL[0][2], top = 0, hiz = 0, yon = 0;
    for (const [t0, t1, x0, x1] of YOL) {
      if (t <= t0) break;
      const u = kenet((t - t0) / (t1 - t0)), d = Math.abs(x1 - x0);
      x = x0 + (x1 - x0) * yum(u);
      top += d * yum(u);
      if (t < t1) { hiz = d * 6 * u * (1 - u) / (t1 - t0); yon = Math.sign(x1 - x0); }
    }
    return { x, top, hiz, yon };
  }

  // bakış: yürürken gittiği yöne, dururken önce izleyiciye sonra yeni yöne; sonunda izleyiciye
  function bakisAl(t) {
    if (t < 3.5) return -1;
    if (t < 3.95) return -1 + yum((t - 3.5) / 0.25);          // izleyiciye
    if (t < 4.1) return yum((t - 3.95) / 0.15);               // sağa döner
    if (t < 6.0) return 1;
    if (t < 6.45) return 1 - yum((t - 6.0) / 0.25);           // izleyiciye
    if (t < 6.6) return -yum((t - 6.45) / 0.15);              // sola döner
    if (t < 8.2) return -1;
    return -1 + yum((t - 8.2) / 0.35);                        // izleyiciye
  }

  function ciz(t) {
    let x = ORTA, yol = ADIM * 0.25, kalk = 0.7, bakis = 0, yon = 0, nefes = 0, kirpik = 0, dur = 0;
    if (t !== null) {
      const k = konum(t);
      x = k.x; yol = k.top; yon = k.yon;
      kalk = kenet(k.hiz / 70);
      bakis = bakisAl(t);
      dur = 1 - kalk;
      nefes = Math.sin(2 * Math.PI * t / 2.6) * dur;
      KIRP.forEach(kp => { if (t >= kp && t < kp + 0.16) kirpik = 1; });
    }
    const s = 2 * Math.PI * yol / ADIM, sn = Math.sin(s);
    // ayaklar sırayla kalkar; beden basan ayağın üstüne yatar, gittiği yöne hafif eğilir
    bacakSol.setAttribute('transform', `translate(0 ${(-11 * kalk * Math.max(0, sn)).toFixed(2)})`);
    bacakSag.setAttribute('transform', `translate(0 ${(-11 * kalk * Math.max(0, -sn)).toFixed(2)})`);
    const yatma = 4.5 * kalk * sn + 2.5 * kalk * yon, zip = -4 * kalk * Math.abs(sn);
    ust.setAttribute('transform',
      `translate(0 ${zip.toFixed(2)}) rotate(${yatma.toFixed(2)} 160 300) translate(160 300) scale(1 ${(1 + 0.012 * nefes).toFixed(4)}) translate(-160 -300)`);
    // kollar adımlarla ters yönde sallanır
    kolSol.setAttribute('transform', `rotate(${(-10 * kalk * sn).toFixed(2)} 106 182)`);
    kolSag.setAttribute('transform', `rotate(${(-10 * kalk * sn).toFixed(2)} 214 182)`);
    // baş: beden yatarken dengede kalır, baktığı yana hafif döner
    bas.setAttribute('transform', `translate(0 ${(1.2 * nefes).toFixed(2)}) rotate(${(-0.6 * yatma + 4 * bakis).toFixed(2)} 160 176)`);
    gozbebek.setAttribute('transform', `translate(${(2.4 * bakis).toFixed(2)} 0)`);
    gozler.setAttribute('opacity', 1 - kirpik);
    kirpma.setAttribute('opacity', kirpik);
    golge.setAttribute('transform', `translate(160 338) scale(${(1 - 0.05 * kalk * Math.abs(sn)).toFixed(4)} 1) translate(-160 -338)`);
    yer.setAttribute('transform', `translate(${x.toFixed(1)} 0)`);
  }

  ciz(null);
  const onceki = window.kare;
  window.kare = function (t) { if (typeof onceki === 'function') onceki(t); ciz(t); };
})();
