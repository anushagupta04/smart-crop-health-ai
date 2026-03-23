import cv2
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import os
import sys

from tensorflow.keras.models import load_model, Model  

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predict import predict_disease
from severity_detection import detect_severity

# Get the base directory (smart-crop-health)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "dataset", "train")
MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "best_model.h5")

IMAGE_PATH = os.path.join(BASE_DIR, "uploads", "test_leaf.jpg")

if not os.path.exists(MODEL_PATH):
    print(f"Warning: Model not found at {MODEL_PATH}")

IMG_SIZE = 224
LAST_CONV_LAYER = "Conv_1"

try:
    class_names = sorted(os.listdir(DATASET_PATH))
except FileNotFoundError:
    print(f"Dataset directory not found. Using hardcoded class names.")
    class_names = [
        "Pepper__bell___Bacterial_spot", "Pepper__bell___healthy",
        "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
        "Tomato_Bacterial_spot", "Tomato_Early_blight", "Tomato_Late_blight",
        "Tomato_Leaf_Mold", "Tomato_Septoria_leaf_spot", 
        "Tomato_Spider_mites_Two_spotted_spider_mite", "Tomato__Target_Spot",
        "Tomato__Tomato_YellowLeaf__Curl_Virus", "Tomato__Tomato_mosaic_virus", 
        "Tomato_healthy"
    ]
    class_names = sorted(class_names)

model = load_model(MODEL_PATH)
print("Model loaded successfully")

img = cv2.imread(IMAGE_PATH)

if img is None:
    raise ValueError(f"Image not found: {IMAGE_PATH}")

img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
img_array = np.expand_dims(img / 255.0, axis=0)

pred_class_index, confidence = predict_disease(IMAGE_PATH, class_names)

predicted_label = class_names[pred_class_index]

print("Predicted Disease:", predicted_label.replace("__"," ").replace("_"," "))
print(f"Confidence: {confidence:.2f}%")

grad_model = Model(
    inputs=model.input,
    outputs=[model.get_layer(LAST_CONV_LAYER).output, model.output]
)

with tf.GradientTape() as tape:

    conv_outputs, predictions = grad_model(img_array)

    loss = predictions[:, pred_class_index]

grads = tape.gradient(loss, conv_outputs)

pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

conv_outputs = conv_outputs[0]

heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
heatmap = tf.squeeze(heatmap)

heatmap = np.maximum(heatmap, 0)
heatmap_np = heatmap.numpy() if hasattr(heatmap, 'numpy') else np.array(heatmap)

# Normalize to 0-1
heatmap_norm = (heatmap_np - np.min(heatmap_np)) / (np.max(heatmap_np) - np.min(heatmap_np) + 1e-8)

# Resize heatmap to match image size
heatmap_resized = cv2.resize(heatmap_norm, (IMG_SIZE, IMG_SIZE))

# Create BINARY MASK for disease regions - only values above 70th percentile
threshold = np.percentile(heatmap_resized, 70)
disease_mask = (heatmap_resized > threshold).astype(np.uint8)

# Apply morphological operations to clean the mask
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
disease_mask = cv2.morphologyEx(disease_mask, cv2.MORPH_OPEN, kernel)
disease_mask = cv2.morphologyEx(disease_mask, cv2.MORPH_CLOSE, kernel)

# Dilate slightly to make disease areas more visible
disease_mask = cv2.dilate(disease_mask, kernel, iterations=1)

# Get the heatmap values only in disease regions
heatmap_disease = heatmap_resized * disease_mask

severity_level, severity_percent = detect_severity(heatmap_disease)

print("Severity Level:", severity_level)
print(f"Infected Area: {severity_percent:.2f}%")

# Convert mask to 3D for blending
heatmap_color_uint8 = np.uint8(255 * heatmap_disease)
heatmap_color = cv2.applyColorMap(heatmap_color_uint8, cv2.COLORMAP_HOT)

# Apply only to masked regions
overlay = img.copy().astype(float)
for c in range(3):
    overlay[:, :, c] = img[:, :, c].astype(float) * (1 - disease_mask) + heatmap_color[:, :, c] * disease_mask

overlay = np.uint8(overlay)

plt.figure(figsize=(12, 5))

plt.subplot(1,2,1)
plt.title("Original Leaf")
plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
plt.axis("off")

plt.subplot(1,2,2)
plt.title(
    f"GradCAM\nDisease: {predicted_label.replace('__',' ').replace('_',' ')}"
    f" | Confidence: {confidence:.2f}%"
    f"\nSeverity: {severity_level} ({severity_percent:.2f}%)"
)

plt.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
plt.axis("off")

plt.show()