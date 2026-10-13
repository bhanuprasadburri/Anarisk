from app.services.detection.base import DetectionContext, SignalResult
from app.services.detection.behavior import BehaviorDetector
from app.services.detection.brand_logo import BrandLogoDetector
from app.services.detection.impersonation import ImpersonationDetector
from app.services.detection.url_risk import UrlRiskDetector

# Independent detection families (replaceable / extendable). Order is the display order.
DETECTORS = [BrandLogoDetector(), ImpersonationDetector(), UrlRiskDetector(), BehaviorDetector()]

__all__ = ["DETECTORS", "DetectionContext", "SignalResult"]
