"""Training model v2: stimulus, fatigue, exposure, readiness and recommendations.

See docs/training-model.md for the model description and parameters.py for
every coefficient with its evidence level.
"""

from .service import TrainingAnalysis, TrainingModelService, analyse

__all__ = ["TrainingAnalysis", "TrainingModelService", "analyse"]
