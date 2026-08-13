"""
AnomalyDetector — MetricStore'daki geçmiş verilere bakarak mevcut değerin
anormal olup olmadığını saptar.

Yöntem seçimi (otomatik):
  - n < 8   → basit z-score (ortalama ± k·std)
  - n >= 8  → statsmodels Holt-Winters ExponentialSmoothing (trend + mevsimsel)

Her iki yöntem de aynı AnomalyResult arayüzünü döndürür.

Kurulum:
    pip install statsmodels
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

import statistics


@dataclass
class AnomalyResult:
    metric_name:  str
    current:      float | None
    is_anomaly:   bool
    score:        float          # ne kadar sapkın (z-score veya normalize hata)
    method:       str            # "zscore" | "holt_winters"
    lower_bound:  float | None = None
    upper_bound:  float | None = None
    message:      str = ""

    @property
    def status(self) -> str:
        return "ANOMALY" if self.is_anomaly else "OK"


    def to_check_dict(self) -> dict:
        """run_results tablosuna yazilabilecek dict dondurur."""
        lo = self.lower_bound
        hi = self.upper_bound
        expected_str = (
            f"{lo} - {hi}" if lo is not None and hi is not None else "-"
        )
        return {
            "name":     self.metric_name,
            "passed":   not self.is_anomaly,
            "value":    self.current,
            "expected": expected_str,
            "message":  f"[{self.method}] skor={self.score} {self.message}",
        }

# ── Yardımcı: geçmiş değerleri listele ───────────────────────────────────────

def _values(history: list[dict]) -> list[float]:
    return [h["value"] for h in history if h["value"] is not None]


# ── Yöntem 1: Z-score (az veri için) ─────────────────────────────────────────

def _zscore_detect(name: str, current: float, hist: list[float],
                   threshold: float) -> AnomalyResult:
    if len(hist) < 2:
        return AnomalyResult(name, current, False, 0.0, "zscore",
                             message="Yeterli geçmiş veri yok (< 2)")

    mean = statistics.mean(hist)
    std  = statistics.stdev(hist) or 1e-9   # sıfıra bölmeyi önle

    z     = abs(current - mean) / std
    lower = mean - threshold * std
    upper = mean + threshold * std

    return AnomalyResult(
        metric_name  = name,
        current      = current,
        is_anomaly   = z > threshold,
        score        = round(z, 4),
        method       = "zscore",
        lower_bound  = round(lower, 4),
        upper_bound  = round(upper, 4),
        message      = f"z={z:.2f}, eşik={threshold}",
    )



def _ewma_detect(name: str, current: float, hist: list[float],
                 threshold: float, alpha: float = 0.3) -> AnomalyResult:
    """
    EWMA (Exponentially Weighted Moving Average) anomali tespiti.
    5-13 veri noktası için idealdir — trend'e duyarlı, hafif.
    alpha: düzleştirme faktörü (0<alpha<1, küçük=uzun hafıza)
    """
    if len(hist) < 2:
        return AnomalyResult(name, current, False, 0.0, "ewma",
                             message="Yeterli geçmiş veri yok (< 2)")
    # EWMA hesapla
    ewma = hist[0]
    sq_errors = []
    for val in hist[1:]:
        ewma = alpha * val + (1 - alpha) * ewma
        sq_errors.append((val - ewma) ** 2)
    # EWMA std (eksponansiyel ağırlıklı)
    ewma_std = (sum(sq_errors) / len(sq_errors)) ** 0.5 or 1e-9
    forecast = ewma
    error = abs(current - forecast)
    norm_score = error / ewma_std
    lower = forecast - threshold * ewma_std
    upper = forecast + threshold * ewma_std
    return AnomalyResult(
        metric_name  = name,
        current      = current,
        is_anomaly   = norm_score > threshold,
        score        = round(norm_score, 4),
        method       = "ewma",
        lower_bound  = round(lower, 4),
        upper_bound  = round(upper, 4),
        message      = f"tahmin={forecast:.2f}, hata={error:.2f}, alpha={alpha}",
    )

# ── Yöntem 2: Holt-Winters (yeterli veri için) ───────────────────────────────

def _holt_winters_detect(name: str, current: float, hist: list[float],
                         threshold: float) -> AnomalyResult:
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        import numpy as np

        series = np.array(hist, dtype=float)

        # Mevsimsel dönem: 7 (haftalık) veya trend only
        seasonal_periods = 7 if len(series) >= 14 else None
        trend_type: Literal["add"] | None = "add"
        seasonal_type = "add" if seasonal_periods else None

        model = ExponentialSmoothing(
            series,
            trend=trend_type,
            seasonal=seasonal_type,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True, disp=False)

        # Bir adım ilerisi tahmin
        forecast = float(model.forecast(1)[0])
        residuals = model.resid
        std = float(np.std(residuals)) or 1e-9

        error      = abs(current - forecast)
        norm_score = error / std
        lower      = forecast - threshold * std
        upper      = forecast + threshold * std

        return AnomalyResult(
            metric_name  = name,
            current      = current,
            is_anomaly   = norm_score > threshold,
            score        = round(norm_score, 4),
            method       = "holt_winters",
            lower_bound  = round(lower, 4),
            upper_bound  = round(upper, 4),
            message      = f"tahmin={forecast:.2f}, hata={error:.2f}, eşik={threshold}",
        )

    except ImportError:
        # statsmodels yoksa z-score'a geri dön
        return _zscore_detect(name, current, hist, threshold)

    except Exception as exc:
        return AnomalyResult(name, current, False, 0.0, "holt_winters",
                             message=f"Model hatası, z-score'a geri dönüldü: {exc}")


# ── Ana sınıf ─────────────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    MetricStore geçmişini kullanarak mevcut değerin anormal olup olmadığını saptar.

    Args:
        store:     MetricStore nesnesi
        threshold: Kaç standart sapma üstü anormal sayılsın (varsayılan: 3.0)
        history_days: Kaç günlük geçmiş kullanılsın
    """

    def __init__(self, store, threshold: float = 3.0, history_days: int = 30):
        self.store        = store
        self.threshold    = threshold
        self.history_days = history_days

    def detect(self, metric_name: str, current_value: float) -> AnomalyResult:
        """Tek metrik için anomali tespiti yap."""
        history  = self.store.history(metric_name, days=self.history_days)
        hist_vals = _values(history)

        if current_value is None:
            return AnomalyResult(metric_name, None, False, 0.0, "none",
                                 message="Mevcut değer None")

        # Yöntem seçimi: veri miktarına göre otomatik
        # < 5  → zscore  (basit, az veri)
        # 5-13 → ewma    (trend duyarlı, orta veri)
        # >=14 → holt_winters (mevsimsel, çok veri)
        n = len(hist_vals)
        if n >= 14:
            return _holt_winters_detect(metric_name, current_value,
                                        hist_vals, self.threshold)
        elif n >= 5:
            return _ewma_detect(metric_name, current_value,
                                hist_vals, self.threshold)
        else:
            return _zscore_detect(metric_name, current_value,
                                  hist_vals, self.threshold)

    def detect_all(self, results) -> list[AnomalyResult]:
        """
        CheckResult / herhangi bir 'name + value' listesi için toplu tespit.
        Önce mevcut değerleri kaydeder, sonra her birini analiz eder.
        """
        self.store.record_results(results)
        return [
            self.detect(r.name, r.value)
            for r in results
            if r.value is not None
        ]
