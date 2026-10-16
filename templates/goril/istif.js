// İstifçi goril (sakin gün): elindeki külçeyi yanındaki yığına koyar, yığın büyür.
// Bot her kare için window.kare(t) çağırır; çağrılmazsa durağan poz çizilir.
(function () {
  const svg = document.getElementById('goril-istif');
  if (!svg) return;
  const $ = id => document.getElementById(id);
  const hepsi = $('gi-hepsi'), govde = $('gi-govde'), bas = $('gi-bas'), gozbebek = $('gi-gozbebek'),
        kontur = $('gi-kol-kontur'), kol = $('gi-kol-ic'), el = $('gi-el'), tasinan = $('gi-tasinan'), tin = $('gi-tin');
  const yigin = Array.from($('gi-yigin').children);

  const GIRIS = 1.35, GIRIS_SURE = 0.45, T0 = GIRIS + GIRIS_SURE;
  const P = 2.0, ILK = 3, EN_COK = yigin.length;           // bir külçe 2 sn; 3 külçeden başlar
  const TUTUS = 30;                                        // el merkezinden külçenin altına
  const OMUZ = [170, 186], DINLEN = [230, 240], YIGIN_X = 266, TABAN = 334, KAT = 16;
  const kenet = x => Math.min(Math.max(x, 0), 1);
  const yum = x => { x = kenet(x); return x * x * (3 - 2 * x); };
  const ara = (a, b, u) => a + (b - a) * u;
  const geriTasma = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

  function poz(nb, p) {
    // nb: bu turda koymadan önceki külçe sayısı; p: tur içindeki yer (0–1)
    const koy = TABAN - KAT * nb - TUTUS, ustu = koy - 22;
    let x, y, tasiyor = true, olcek = 1, n = nb;
    if (p < 0.40) { const u = yum(p / 0.40); x = ara(DINLEN[0], YIGIN_X, u); y = ara(DINLEN[1], ustu, u) - 26 * Math.sin(Math.PI * u); }
    else if (p < 0.52) { const u = yum((p - 0.40) / 0.12); x = YIGIN_X; y = ara(ustu, koy, u); }
    else if (p < 0.62) { const u = yum((p - 0.52) / 0.10); x = YIGIN_X; y = ara(koy, koy - 14, u); tasiyor = false; n = nb + 1; }
    else if (p < 0.95) { const u = yum((p - 0.62) / 0.33); x = ara(YIGIN_X, DINLEN[0], u); y = ara(koy - 14, DINLEN[1], u) - 14 * Math.sin(Math.PI * u); tasiyor = false; n = nb + 1; }
    else { x = DINLEN[0]; y = DINLEN[1]; n = nb + 1; olcek = yum((p - 0.95) / 0.05); }
    const tinS = p >= 0.52 && p <= 0.80 ? (p - 0.52) / 0.28 : null;
    return { x, y, tasiyor, olcek, n, tinS, ustY: TABAN - KAT * (nb + 1) };
  }

  function ciz(t) {
    let d;
    if (t === null) d = poz(5, 0.46);                       // durağan görsel
    else if (t < T0) d = { x: DINLEN[0], y: DINLEN[1], tasiyor: true, olcek: 1, n: ILK, tinS: null };
    else {
      const k = Math.floor((t - T0) / P), p = (t - T0) / P - k;
      d = ILK + k >= EN_COK ? { x: DINLEN[0], y: DINLEN[1], tasiyor: true, olcek: 1, n: EN_COK, tinS: null }
                            : poz(ILK + k, p);
    }
    // giriş
    const g = t === null ? 1 : kenet((t - GIRIS) / GIRIS_SURE);
    const s = g === 0 ? 0.0001 : geriTasma(g);
    hepsi.setAttribute('transform', `translate(160 345) scale(${s}) translate(-160 -345)`);
    // yığın
    yigin.forEach((b, i) => b.setAttribute('visibility', i < d.n ? 'visible' : 'hidden'));
    // kol: omuzdan ele, dirsek dışa/yukarı
    const dx = d.x - OMUZ[0], dy = d.y - OMUZ[1], L = Math.hypot(dx, dy) || 1;
    const cx = (OMUZ[0] + d.x) / 2 + 26 * dy / L, cy = (OMUZ[1] + d.y) / 2 - 26 * dx / L;
    const yol = `M${OMUZ[0]} ${OMUZ[1]} Q${cx.toFixed(1)} ${cy.toFixed(1)} ${d.x.toFixed(1)} ${d.y.toFixed(1)}`;
    kontur.setAttribute('d', yol); kol.setAttribute('d', yol);
    el.setAttribute('transform', `translate(${d.x.toFixed(1)} ${d.y.toFixed(1)})`);
    tasinan.setAttribute('transform', `translate(${d.x.toFixed(1)} ${(d.y + TUTUS).toFixed(1)}) scale(${d.olcek})`);
    tasinan.setAttribute('visibility', d.tasiyor ? 'visible' : 'hidden');
    // "tın" parıltısı
    if (d.tinS !== null) {
      const o = Math.sin(Math.PI * d.tinS);
      tin.setAttribute('transform', `translate(${YIGIN_X + 30} ${d.ustY - 14}) scale(${0.3 + 0.9 * o}) rotate(${40 * d.tinS})`);
      tin.setAttribute('opacity', o.toFixed(3));
    } else tin.setAttribute('opacity', 0);
    // gözler eli izler, baş hafifçe sallanır, gövde nefes alır
    const gx = Math.max(-1, Math.min(3.2, 1 + 2.4 * (d.x - DINLEN[0]) / 40));
    const gy = Math.max(-2.6, Math.min(1.8, 1 + 2.2 * (d.y - DINLEN[1]) / 50));
    gozbebek.setAttribute('transform', `translate(${gx.toFixed(2)} ${gy.toFixed(2)})`);
    const tt = t === null ? 0 : t;
    bas.setAttribute('transform', `rotate(${(2 + 2.5 * Math.sin(2 * Math.PI * tt / P)).toFixed(2)} 160 178)`);
    govde.setAttribute('transform', `translate(160 334) scale(1 ${(1 + 0.012 * Math.sin(2 * Math.PI * tt / 2.2)).toFixed(4)}) translate(-160 -334)`);
  }

  ciz(null);
  const onceki = window.kare;
  window.kare = function (t) { if (typeof onceki === 'function') onceki(t); ciz(t); };
})();
