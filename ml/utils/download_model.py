import os
import gdown

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "best_model.h5")
MODEL_URL = "https://drive.google.com/uc?export=download&id=1IEKhFUE3xHpXeHpU8OtSIjKFf3yzVu6k"

def download_model_if_not_exists():
    if not os.path.exists(MODEL_PATH):
        print("Downloading model...")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        gdown.download(MODEL_URL, MODEL_PATH, quiet=False)
        print("Model downloaded successfully!")
    else:
        print("Model already exists.")