Model artifacts are generated locally by:

    python scripts/train_models.py

The generated `predictive_models.joblib` contains two fitted regressors per farm,
forecast horizon and feature set. It is ignored by Git because it can be recreated
from the versioned dataset.
