import os
import cv2
import numpy as np
from tensorflow.keras.models import load_model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "best_model.h5")
IMG_SIZE = 224

model = load_model(MODEL_PATH)

# Hardcoded class names in case dataset directory doesn't exist
DEFAULT_CLASS_NAMES = [
    "Pepper__bell___Bacterial_spot", "Pepper__bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Tomato_Bacterial_spot", "Tomato_Early_blight", "Tomato_Late_blight",
    "Tomato_Leaf_Mold", "Tomato_Septoria_leaf_spot", 
    "Tomato_Spider_mites_Two_spotted_spider_mite", "Tomato__Target_Spot",
    "Tomato__Tomato_YellowLeaf__Curl_Virus", "Tomato__Tomato_mosaic_virus", 
    "Tomato_healthy"
]

def predict_disease(image_path, class_names=None):
    if class_names is None:
        class_names = DEFAULT_CLASS_NAMES

    img = cv2.imread(image_path)

    if img is None:
        raise ValueError("Image not found")

    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    img_array = np.expand_dims(img / 255.0, axis=0)

    predictions = model.predict(img_array)

    pred_class = np.argmax(predictions[0])
    confidence = predictions[0][pred_class] * 100

    return pred_class, confidence

if __name__ == "__main__":
    dataset_path = os.path.join(BASE_DIR, "data", "dataset", "train")
    if os.path.exists(dataset_path):
        class_names = sorted(os.listdir(dataset_path))
    else:
        class_names = DEFAULT_CLASS_NAMES

    IMAGE_PATH = r"C:\Users\KIIT0001\Documents\smart-crop-health\dataset\test\Pepper__bell___Bacterial_spot\0a4c007d-41ab-4659-99cb-8a4ae4d07a55___NREC_B.Spot 1954.JPG"

    pred_class, confidence = predict_disease(IMAGE_PATH, class_names)

    disease = class_names[pred_class].replace("__"," ").replace("_"," ")

    print("Disease:", disease)
    print(f"Confidence: {confidence:.2f}%")