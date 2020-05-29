import os

MODEL_ROOT = os.environ.get('GRV2GRV_MODEL_ROOT')
MODELS = {name: {} for name in os.environ.get('GRV2GRV_MODEL_NAMES', '').split(',')}
