import tensorflow as tf
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import json

from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras.preprocessing.image import ImageDataGenerator # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "best_model.h5")
TEST_DIR = os.path.join(BASE_DIR, "data", "dataset", "test")

IMG_SIZE = 224
BATCH_SIZE = 128

PRED_FILE = os.path.join(BASE_DIR, "data", "predictions.npy")
TRUE_FILE = os.path.join(BASE_DIR, "data", "true_labels.npy")

model = tf.keras.models.load_model(MODEL_PATH)

test_gen = ImageDataGenerator(rescale=1./255)

test_data = test_gen.flow_from_directory(
    TEST_DIR,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    shuffle=False
)

# Prediction caching mechanism

if os.path.exists(PRED_FILE) and os.path.exists(TRUE_FILE):

    print("⚡ Loading cached predictions (instant)...")

    y_pred = np.load(PRED_FILE)
    y_true = np.load(TRUE_FILE)

else:

    print("Running evaluation (this happens only once)...")

    predictions = model.predict(test_data)
    y_pred = np.argmax(predictions, axis=1)
    y_true = test_data.classes

    np.save(PRED_FILE, y_pred)
    np.save(TRUE_FILE, y_true)

    print("Predictions cached for future runs.")

report = classification_report(
    y_true,
    y_pred,
    target_names=list(test_data.class_indices.keys())
)

print("\nClassification Report:\n")
print(report)

# Confusion Matrix

cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(10,8))

sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=test_data.class_indices.keys(),
    yticklabels=test_data.class_indices.keys()
)

plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")

plt.show()

metrics = classification_report(
    y_true,
    y_pred,
    output_dict=True
)

metrics_file = os.path.join(BASE_DIR, "data", "metrics.json")
with open(metrics_file, "w") as f:
    json.dump(metrics, f)

print(f"\nMetrics saved to {metrics_file}")