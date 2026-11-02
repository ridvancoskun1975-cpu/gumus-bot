"""Külçe sahnesinin kare kare çizimi (Mitsuba 3, iki geçiş + gürültü giderme).

A geçişi: külçeler + siyah mat zemin + stüdyo ortamı (zemin yansımaz, yalnız siyah zemin).
B geçişi: zemin düzlemine göre aynalanmış kameradan külçeler (zeminsiz); görüntü dikeyde çevrilince
          zemin yansıması olur. Yalnız külçelerin yansıması alınır, zemine doğru solar.
Sahneler bir kez yüklenir; her karede yalnız kamera ve ortamın dönüşü güncellenir.

Kullanım: python cizer.py <dikey|yatay> <başlangıç kare> <bitiş kare (hariç)> <klasör> [spp_a] [spp_b]
          python cizer.py <dikey|yatay> deneme <t> <çıktı.png>
"""
import math
import sys
import time
from pathlib import Path

import numpy as np
import mitsuba as mi

mi.set_variant("llvm_ad_rgb")
import pyoidn  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sahne as S  # noqa: E402

T = mi.ScalarTransform4f
FPS = 30
YANSIMA = 0.24          # zemin yansımasının gücü
POZLAMA = 1.0


OLCEK = 0.8              # %80 boyutta çizilir, yazarken tam boya büyütülür


def cikti_boyutu(bicim):
    return (1080, 1920) if bicim == "dikey" else (1920, 1080)


def boyut(bicim):
    g, y = cikti_boyutu(bicim)
    return (round(g * OLCEK), round(y * OLCEK))


def sahne_dict(bicim, spp, yansima_gecisi):
    gen, yuk = boyut(bicim)
    d = S.sahne(0.0, gen, yuk, spp, bicim)
    d["integrator"] = {"type": "aov", "aovs": "alb:albedo,nn:sh_normal,pos:position",
                       "yol": {"type": "path", "max_depth": 5}}
    if yansima_gecisi:
        del d["zemin"]
    else:
        d["zemin"]["bsdf"] = {"type": "diffuse", "reflectance": {"type": "rgb", "value": 0.0}}
    return d


def kamera_donusumu(t, bicim, ayna=False):
    poz, hedef, _ = S.kamera(t, bicim)
    if ayna:
        poz = [poz[0], -poz[1], poz[2]]
        hedef = [hedef[0], -hedef[1], hedef[2]]
    return T().look_at(origin=poz, target=hedef, up=[0, 1, 0])


def ayir(img):
    img = np.asarray(img, dtype=np.float32)
    # kanallar: renk(3) [alfa(1)] alb(3) nn(3) pos(3)
    o = 0 if img.shape[-1] == 12 else 1
    renk = img[..., 0:3]
    alb = img[..., 3 + o:6 + o]
    nn = img[..., 6 + o:9 + o]
    pos = img[..., 9 + o:12 + o]
    return renk, alb, nn, pos


def kulce_maskesi(nn, pos):
    """Külçe/plaka isabeti: normal tanımlı ve zeminin üstünde. Kenar piksellerinde kısmi (ortalama normal boyu)."""
    boy = np.clip(np.linalg.norm(nn, axis=-1, keepdims=True), 0, 1)
    ust = (pos[..., 1:2] > 0.0005).astype(np.float32)
    return boy * ust


def temizle(renk, alb, nn):
    return np.asarray(pyoidn.denoise(np.ascontiguousarray(renk), np.ascontiguousarray(np.clip(alb, 0, 1)),
                                     np.ascontiguousarray(np.clip(nn, -1, 1)), hdr=True, quality="high"),
                      dtype=np.float32)


class Cizici:
    def __init__(self, bicim, spp_a=32, spp_b=12):
        self.bicim, self.spp_a, self.spp_b = bicim, spp_a, spp_b
        self.A = mi.load_dict(sahne_dict(bicim, spp_a, False))
        self.B = mi.load_dict(sahne_dict(bicim, spp_b, True))
        self.pA, self.pB = mi.traverse(self.A), mi.traverse(self.B)

    def _guncelle(self, p, t, ayna):
        _, _, aci = S.kamera(t, self.bicim)
        p["sensor.to_world"] = kamera_donusumu(t, self.bicim, ayna)
        p["env.to_world"] = T().rotate([0, 1, 0], math.degrees(aci))
        p.update()

    def kare(self, t, seed=0):
        self._guncelle(self.pA, t, False)
        self._guncelle(self.pB, t, True)
        rA, _, nA, pA = ayir(mi.render(self.A, spp=self.spp_a, seed=seed))
        rB, _, nB, pB = ayir(mi.render(self.B, spp=self.spp_b, seed=seed + 7))
        mA, mB = kulce_maskesi(nA, pA), kulce_maskesi(nB, pB)
        aA, aB = np.repeat(mA * 0.93, 3, -1), np.repeat(mB * 0.93, 3, -1)
        A = temizle(rA, aA, nA)
        B = temizle(rB, aB, nB)
        # yansıma: görüntüyü dikeyde çevir; yalnız külçe isabetleri, zemine yakın kısım güçlü
        B, aB, pB = B[::-1], aB[::-1], pB[::-1]
        isabet = mB[::-1] ** 4                                          # kenar piksellerinde arka plan sızmasın
        sol = np.clip(1.0 - pB[..., 1:2] / 0.9, 0, 1) ** 2.2
        kaplama = mA                                                    # A'da külçe olan yer
        cikti = A + B * isabet * sol * YANSIMA * (1 - kaplama)
        cikti = cikti * POZLAMA
        cikti = cikti / (1.0 + 0.06 * cikti)                          # parlamalar yanmasın
        return cikti

    def yaz(self, t, yol, seed=0):
        from PIL import Image
        x = self.kare(t, seed)
        x = np.clip(x, 0, 1)
        srgb = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
        img = Image.fromarray((srgb * 255 + 0.5).astype(np.uint8))
        img = img.resize(cikti_boyutu(self.bicim), Image.LANCZOS)
        img.save(str(yol))


if __name__ == "__main__":
    bicim = sys.argv[1]
    if sys.argv[2] == "deneme":
        t0 = time.time()
        c = Cizici(bicim, *(int(a) for a in sys.argv[5:7]))
        t1 = time.time()
        c.yaz(float(sys.argv[3]), sys.argv[4])
        print(f"yükleme {t1 - t0:.1f} sn, kare {time.time() - t1:.1f} sn → {sys.argv[4]}")
    else:
        bas, son, klasor = int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
        klasor.mkdir(parents=True, exist_ok=True)
        c = Cizici(bicim, *(int(a) for a in sys.argv[5:7]))
        for i in range(bas, son):
            yol = klasor / f"{i:04d}.png"
            if yol.exists():
                continue
            t0 = time.time()
            gecici = klasor / f"{i:04d}.yaziliyor.png"
            c.yaz(i / FPS, gecici, seed=i * 13)
            gecici.rename(yol)
            print(f"kare {i} ({time.time() - t0:.1f} sn)", flush=True)
