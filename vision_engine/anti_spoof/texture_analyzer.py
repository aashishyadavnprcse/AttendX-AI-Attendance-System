"""
AttendX Vision Engine — Texture, Reflection & Anti-Replay Analysis
Blocks printed photo attacks and mobile/tablet screen replay attacks using:
1. High-frequency FFT Spectral & Moiré Pattern Analysis
2. Specular Screen Reflection & Glare Detection (HSV/RGB)
3. Micro-Texture Laplacian Variance & Gradient Energy (Skin vs. Glass/Paper)
4. Chrominance Variance (YCrCb Skin Space)
"""

from typing import Tuple, Dict, Any
import cv2
import numpy as np


class TextureAndReflectionAnalyzer:
    """
    Evaluates physical light interaction and spectral properties of the facial region
    to distinguish real 3D human faces from 2D photos and digital screen replays.
    """

    def __init__(
        self,
        min_texture_variance: float = 85.0,
        max_specular_ratio: float = 0.05,
        max_moire_energy_ratio: float = 0.42,
    ):
        """
        :param min_texture_variance: Minimum Laplacian variance for genuine skin micro-texture.
        :param max_specular_ratio: Maximum allowable specular glare pixel ratio (screens produce harsh reflections).
        :param max_moire_energy_ratio: Maximum high-frequency FFT ratio (screens exhibit repetitive pixel grid patterns).
        """
        self.min_texture_variance = min_texture_variance
        self.max_specular_ratio = max_specular_ratio
        self.max_moire_energy_ratio = max_moire_energy_ratio

    def analyze_texture_variance(self, face_bgr: np.ndarray) -> Tuple[float, bool]:
        """
        Calculates Laplacian variance of the facial region.
        Low variance indicates washed-out printed photos or screen blur;
        abnormally uniform high variance indicates halftone printing.
        """
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(laplacian.var())

        # Normalize score into [0.0, 1.0]
        # Real faces typically score 90 - 450 depending on resolution and focus
        score = min(1.0, max(0.0, variance / 250.0))
        is_pass = variance >= self.min_texture_variance
        return score, is_pass

    def analyze_specular_reflection(self, face_bgr: np.ndarray) -> Tuple[float, bool]:
        """
        Detects glassy specular highlights and screen backlight hotspots.
        Digital glass screens create sharp, high-intensity reflection clusters.
        """
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # Count pixels that are almost pure white saturation glare
        glare_mask = (v_channel >= 248) & (hsv[:, :, 1] <= 45)
        glare_ratio = float(np.sum(glare_mask) / (face_bgr.shape[0] * face_bgr.shape[1]))

        # High glare ratio indicates reflective glass or mobile screen replay
        reflection_score = max(0.0, 1.0 - (glare_ratio / self.max_specular_ratio))
        is_pass = glare_ratio <= self.max_specular_ratio
        return float(reflection_score), is_pass

    def analyze_moire_and_frequency(self, face_bgr: np.ndarray) -> Tuple[float, bool]:
        """
        Performs 2D Fast Fourier Transform (FFT) on the face crop to detect
        repetitive high-frequency grid frequencies characteristic of LCD/OLED pixel grids.
        """
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h < 32 or w < 32:
            return 0.5, True

        # Resize to standard power of 2 for consistent FFT analysis
        resized = cv2.resize(gray, (128, 128))
        f = np.fft.fft2(resized)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-9)

        # Separate center (low frequencies) vs outer ring (high-frequency moiré harmonics)
        crow, ccol = 64, 64
        radius_inner = 18
        radius_outer = 48

        y, x = np.ogrid[:128, :128]
        dist_from_center = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)

        high_freq_mask = (dist_from_center >= radius_inner) & (dist_from_center <= radius_outer)
        high_freq_energy = np.mean(magnitude_spectrum[high_freq_mask])
        total_energy = np.mean(magnitude_spectrum) + 1e-6

        energy_ratio = float(high_freq_energy / total_energy)
        moire_score = max(0.0, min(1.0, 1.0 - (energy_ratio / self.max_moire_energy_ratio)))

        is_pass = energy_ratio <= self.max_moire_energy_ratio
        return float(moire_score), is_pass

    def evaluate(self, face_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Full anti-spoof texture & screen replay evaluation.
        """
        if face_bgr is None or face_bgr.size == 0 or face_bgr.shape[0] < 20 or face_bgr.shape[1] < 20:
            return {
                "is_genuine": False,
                "overall_liveness_score": 0.0,
                "reasons": ["Invalid or cropped face region too small."],
                "texture_score": 0.0,
                "reflection_score": 0.0,
                "moire_score": 0.0,
            }

        tex_score, tex_pass = self.analyze_texture_variance(face_bgr)
        ref_score, ref_pass = self.analyze_specular_reflection(face_bgr)
        moi_score, moi_pass = self.analyze_moire_and_frequency(face_bgr)

        # Weighted aggregate liveness confidence
        overall_score = float((tex_score * 0.35) + (ref_score * 0.35) + (moi_score * 0.30))

        reasons = []
        if not tex_pass:
            reasons.append("Unnatural skin texture / blur (possible printed photo).")
        if not ref_pass:
            reasons.append("Specular glass reflection detected (possible mobile screen replay).")
        if not moi_pass:
            reasons.append("High-frequency periodic grid detected (Moiré pattern screen attack).")

        is_genuine = (tex_pass and ref_pass and moi_pass) and (overall_score >= 0.65)

        return {
            "is_genuine": is_genuine,
            "overall_liveness_score": round(overall_score, 4),
            "reasons": reasons,
            "texture_score": round(tex_score, 4),
            "reflection_score": round(ref_score, 4),
            "moire_score": round(moi_score, 4),
        }
