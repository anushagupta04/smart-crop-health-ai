import os
import cv2
import numpy as np
import tensorflow as tf
import keras
from keras import Model
import base64
import json
import sqlite3
import uuid
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from werkzeug.utils import secure_filename


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="")
CORS(app)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "best_model.h5")
BAYESIAN_MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "bayesian_optimized_model.h5")

if os.path.exists(BAYESIAN_MODEL_PATH):
    print("Loading highly optimized Bayesian Tuned Model...")
    MODEL_PATH = BAYESIAN_MODEL_PATH

DATASET_PATH = os.path.join(BASE_DIR, "data", "dataset", "train")
DB_PATH = os.path.join(BASE_DIR, "data", "cropsense.db")
IMG_SIZE = 224
LAST_CONV_LAYER = "Conv_1"

from ml.utils.download_model import download_model_if_not_exists

try:
    download_model_if_not_exists()
except Exception as e:
    print("Failed to download model:", e)

print("Loading model...")
model = keras.saving.load_model(MODEL_PATH)

try:
    class_names = sorted(os.listdir(DATASET_PATH))
except FileNotFoundError:
    print("Dataset directory not found. Using hardcoded class names.")
    class_names = [
        "Pepper__bell___Bacterial_spot", "Pepper__bell___healthy",
        "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
        "Tomato_Bacterial_spot", "Tomato_Early_blight", "Tomato_Late_blight",
        "Tomato_Leaf_Mold", "Tomato_Septoria_leaf_spot", 
        "Tomato_Spider_mites_Two_spotted_spider_mite", "Tomato__Target_Spot",
        "Tomato__Tomato_YellowLeaf__Curl_Virus", "Tomato__Tomato_mosaic_virus", 
        "Tomato_healthy"
    ]
    # Ensure they are sorted just like os.listdir would if it existed
    class_names = sorted(class_names)

print(f"Model loaded. Classes ({len(class_names)}): {class_names}")

grad_model = Model(
    inputs=model.input,
    outputs=[model.get_layer(LAST_CONV_LAYER).output, model.output]
)


# ═══════════════════════════════════════════════════════
# DATABASE SETUP
# ═══════════════════════════════════════════════════════

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT 'Farmer',
            location TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crops (
            crop_id TEXT PRIMARY KEY,
            user_id TEXT,
            crop_type TEXT NOT NULL,
            growth_stage TEXT DEFAULT 'vegetative',
            planting_date TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id TEXT PRIMARY KEY,
            user_id TEXT,
            crop_id TEXT,
            disease_class TEXT NOT NULL,
            disease_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            severity_level TEXT,
            severity_percent REAL,
            health_score INTEGER DEFAULT 100,
            is_healthy INTEGER DEFAULT 0,
            temperature REAL,
            humidity REAL,
            rainfall REAL,
            soil_moisture REAL,
            soil_ph REAL,
            soil_nutrients TEXT,
            crop_type TEXT,
            growth_stage TEXT,
            ai_recommendation TEXT,
            risk_level TEXT DEFAULT 'low',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (crop_id) REFERENCES crops(crop_id)
        );

        CREATE TABLE IF NOT EXISTS environmental_data (
            env_id TEXT PRIMARY KEY,
            user_id TEXT,
            temperature REAL,
            humidity REAL,
            rainfall REAL,
            soil_moisture REAL,
            soil_ph REAL,
            soil_nutrients TEXT,
            wind_speed REAL,
            recorded_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            user_id TEXT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS Plants (
            plant_id TEXT PRIMARY KEY,
            crop_type TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Observations (
            id TEXT PRIMARY KEY,
            plant_id TEXT,
            image_path TEXT,
            predicted_disease TEXT,
            severity_percentage REAL,
            confidence_score REAL,
            timestamp TEXT DEFAULT (datetime('now')),
            embedding TEXT,
            FOREIGN KEY (plant_id) REFERENCES Plants(plant_id)
        );
    """)
    
    # Try to add embedding column if it doesn't exist (for existing databases)
    try:
        db.execute("ALTER TABLE Observations ADD COLUMN embedding TEXT")
    except sqlite3.OperationalError:
        pass

    # Ensure default user exists
    cursor = db.execute("SELECT user_id FROM users WHERE user_id = 'default'")
    if cursor.fetchone() is None:
        db.execute("INSERT INTO users (user_id, name, location) VALUES ('default', 'Farmer', 'Not Set')")
    db.commit()
    db.close()


init_db()


# ═══════════════════════════════════════════════════════
# RECOMMENDATIONS DATABASE
# ═══════════════════════════════════════════════════════

RECOMMENDATIONS = {
    "Pepper__bell___Bacterial_spot": {
        "description": "Bacterial spot caused by Xanthomonas bacteria, appearing as dark, water-soaked lesions on leaves and fruit.",
        "immediate_actions": [
            "Remove and destroy infected plant material immediately",
            "Avoid overhead irrigation to reduce leaf wetness",
            "Apply copper-based bactericides (e.g., Kocide 3000)"
        ],
        "treatments": [
            "Copper hydroxide spray (2-3 applications, 7-10 day intervals)",
            "Mancozeb + copper mixture for enhanced protection",
            "Acibenzolar-S-methyl (Actigard) as a plant activator"
        ],
        "prevention": [
            "Use certified disease-free seeds",
            "Practice crop rotation (3-4 year cycle)",
            "Maintain proper plant spacing for air circulation",
            "Plant resistant varieties (e.g., Aristotle, Revolution)"
        ],
        "fertilizer": "Reduce nitrogen; apply balanced NPK (10-10-10). Add calcium to strengthen cell walls.",
        "urgency": "high",
        "recovery_days": 14,
        "risk_factors": {"humidity_threshold": 80, "temp_min": 25, "temp_max": 35}
    },
    "Pepper__bell___healthy": {
        "description": "Your pepper plant is in excellent health! No disease detected.",
        "immediate_actions": ["Continue your current care routine", "Monitor regularly for early signs of stress", "Maintain consistent watering schedule"],
        "treatments": ["No treatment needed at this time"],
        "prevention": ["Keep soil moisture consistent", "Apply organic mulch to retain moisture", "Scout for pests weekly", "Maintain adequate phosphorus for root health"],
        "fertilizer": "Apply balanced fertilizer (5-10-10) to support fruiting. Avoid excess nitrogen.",
        "urgency": "none",
        "recovery_days": 0,
        "risk_factors": {"humidity_threshold": 90, "temp_min": 10, "temp_max": 40}
    },
    "Potato___Early_blight": {
        "description": "Early blight caused by Alternaria solani fungus - dark concentric-ring lesions on older leaves.",
        "immediate_actions": ["Remove lower infected leaves immediately", "Apply chlorothalonil or mancozeb fungicide", "Improve air circulation around plants"],
        "treatments": ["Chlorothalonil (Daconil) - apply every 7-10 days", "Mancozeb 75 WP at 2kg/acre", "Azoxystrobin (Quadris) for systemic control", "Copper oxychloride 50 WP as an alternative"],
        "prevention": ["Use certified disease-free seed potatoes", "Rotate crops (3-year cycle)", "Hill soil around plants to prevent splash spread", "Use drip irrigation"],
        "fertilizer": "Ensure adequate potassium (K) - use 60-80 kg K2O/ha. Avoid excess nitrogen.",
        "urgency": "medium",
        "recovery_days": 10,
        "risk_factors": {"humidity_threshold": 70, "temp_min": 20, "temp_max": 30}
    },
    "Potato___Late_blight": {
        "description": "Late blight (Phytophthora infestans) - the most devastating potato disease. Water-soaked lesions with white mold.",
        "immediate_actions": ["URGENT: Remove and destroy ALL infected tissue immediately", "Apply systemic fungicide within 24 hours", "Alert neighboring farms", "Stop overhead irrigation immediately"],
        "treatments": ["Metalaxyl + mancozeb (Ridomil Gold)", "Dimethomorph (Forum 50 WG) for resistant strains", "Cymoxanil + mancozeb (Curzate M8)", "Phosphonates (Fosphite) for curative action"],
        "prevention": ["Plant resistant varieties (Sarpo Mira, Defender)", "Apply preventative fungicides from early season", "Destroy volunteer potato plants", "Harvest tubers quickly in favorable weather"],
        "fertilizer": "Focus on phosphorus and potassium to enhance resistance.",
        "urgency": "critical",
        "recovery_days": 21,
        "risk_factors": {"humidity_threshold": 60, "temp_min": 15, "temp_max": 25}
    },
    "Potato___healthy": {
        "description": "Your potato crop is healthy! No disease detected. Great job!",
        "immediate_actions": ["Continue scouting every 5-7 days", "Maintain preventative spray program", "Monitor soil moisture levels"],
        "treatments": ["No treatment needed"],
        "prevention": ["Apply preventative copper-based sprays before wet season", "Ensure good drainage in the field", "Hill up plants at 15-20cm growth stage"],
        "fertilizer": "Apply NPK 12-32-16 at planting. Top-dress with urea at hilling stage.",
        "urgency": "none",
        "recovery_days": 0,
        "risk_factors": {"humidity_threshold": 85, "temp_min": 5, "temp_max": 35}
    },
    "Tomato_Bacterial_spot": {
        "description": "Bacterial spot (Xanthomonas) - dark spots with yellow halos on leaves and fruit.",
        "immediate_actions": ["Remove and bag infected leaves for disposal", "Apply copper bactericide immediately", "Disinfect gardening tools with 10% bleach"],
        "treatments": ["Copper hydroxide (Kocide 3000) - 7-day intervals", "Copper sulfate pentahydrate (0.25%)", "Streptomycin sulfate (if legal)", "Bacillus subtilis (Serenade) - biological"],
        "prevention": ["Plant resistant varieties (FL 47, Quincy)", "Use certified disease-free transplants", "Avoid working when plants are wet", "Practice 2-3 year rotation"],
        "fertilizer": "Balanced NPK with emphasis on calcium (Ca) and boron (B).",
        "urgency": "high",
        "recovery_days": 14,
        "risk_factors": {"humidity_threshold": 75, "temp_min": 24, "temp_max": 34}
    },
    "Tomato_Early_blight": {
        "description": "Early blight (Alternaria solani) - bulls-eye concentric ring patterns on lower leaves.",
        "immediate_actions": ["Remove affected lower leaves", "Apply protective fungicide", "Stake plants to improve airflow"],
        "treatments": ["Chlorothalonil - every 7 days in wet weather", "Mancozeb 75 WP (2 kg/acre)", "Boscalid + pyraclostrobin (Pristine)", "Neem oil (organic) - every 5-7 days"],
        "prevention": ["Mulch around base to minimize soil splash", "Water at the base; avoid wetting foliage", "Ensure balanced plant nutrition", "Remove crop debris at end of season"],
        "fertilizer": "Adequate K and Ca nutrition. Use compost to improve soil organic matter.",
        "urgency": "medium",
        "recovery_days": 10,
        "risk_factors": {"humidity_threshold": 70, "temp_min": 22, "temp_max": 32}
    },
    "Tomato_Late_blight": {
        "description": "Late blight (Phytophthora infestans) - greasy water-soaked patches, white mold in humid conditions.",
        "immediate_actions": ["URGENT: Act within 24 hours", "Remove and destroy all infected plants", "Apply systemic fungicide immediately", "Notify local agricultural office"],
        "treatments": ["Metalaxyl + Mancozeb (Ridomil MZ)", "Propamocarb (Previcur Energy)", "Amisulbrom (Leimay) for resistant strains", "Mandipropamid (Revus)"],
        "prevention": ["Grow resistant varieties (Mountain Magic, Defiant)", "Don't compost infected material - burn it", "Monitor using local forecasting tools", "Avoid late-season planting in cool, wet periods"],
        "fertilizer": "Increase calcium and potassium; reduce excessive nitrogen. Consider seaweed extracts.",
        "urgency": "critical",
        "recovery_days": 21,
        "risk_factors": {"humidity_threshold": 60, "temp_min": 12, "temp_max": 22}
    },
    "Tomato_Leaf_Mold": {
        "description": "Leaf mold (Passalora fulva) - yellow patches on upper surface with olive-green mold on undersides.",
        "immediate_actions": ["Increase ventilation in greenhouse", "Reduce humidity below 85%", "Remove severely infected leaves"],
        "treatments": ["Chlorothalonil or copper-based fungicides", "Difenoconazole (Score 250 EC)", "Azoxystrobin (Amistar)", "Sulfur dust (organic)"],
        "prevention": ["Grow resistant varieties", "Ensure 30-inch plant spacing", "Avoid high humidity for extended periods", "Use drip irrigation"],
        "fertilizer": "Balanced nutrition with emphasis on potassium. Avoid excessive fertilization.",
        "urgency": "medium",
        "recovery_days": 12,
        "risk_factors": {"humidity_threshold": 85, "temp_min": 20, "temp_max": 30}
    },
    "Tomato_Septoria_leaf_spot": {
        "description": "Septoria leaf spot - small circular spots with white/grey centers and dark borders.",
        "immediate_actions": ["Remove infected lower leaves (up to 1/3 of plant)", "Apply protective fungicide spray", "Sanitize all garden tools"],
        "treatments": ["Chlorothalonil (Bravo 720)", "Mancozeb or copper hydroxide", "Boscalid + trifloxystrobin (Flint Plus)", "Bacillus amyloliquefaciens (organic)"],
        "prevention": ["Stake and prune for good air movement", "Never till infected leaves into soil", "Apply organic mulch", "Rotate with non-solanaceous crops for 2+ years"],
        "fertilizer": "Well-balanced fertilizer. Ensure adequate calcium and magnesium.",
        "urgency": "medium",
        "recovery_days": 10,
        "risk_factors": {"humidity_threshold": 75, "temp_min": 20, "temp_max": 28}
    },
    "Tomato_Spider_mites_Two_spotted_spider_mite": {
        "description": "Two-spotted spider mites - tiny pests causing stippling, bronzing, and webbing.",
        "immediate_actions": ["Spray with strong jet of water to dislodge mites", "Apply miticide or neem oil immediately", "Increase ambient humidity"],
        "treatments": ["Abamectin (Agrimek)", "Bifenazate (Floramite)", "Spiromesifen (Oberon 2SC)", "Neem oil + insecticidal soap (organic)", "Predatory mites (biological)"],
        "prevention": ["Monitor leaf undersides weekly in hot, dry conditions", "Avoid broad-spectrum insecticides", "Maintain adequate plant moisture", "Remove weeds that harbour mites"],
        "fertilizer": "Avoid excess nitrogen. Ensure adequate silicon (Si).",
        "urgency": "high",
        "recovery_days": 7,
        "risk_factors": {"humidity_threshold": 40, "temp_min": 28, "temp_max": 40}
    },
    "Tomato__Target_Spot": {
        "description": "Target spot (Corynespora cassiicola) - concentric ring lesions on leaves, stems and fruit.",
        "immediate_actions": ["Remove severely affected leaves", "Apply fungicide spray program", "Improve air circulation"],
        "treatments": ["Tebuconazole (Folicur) + chlorothalonil", "Boscalid + pyraclostrobin (Pristine)", "Azoxystrobin + difenoconazole (Amistar Top)", "Propiconazole (Tilt)"],
        "prevention": ["Use resistant or tolerant varieties", "Avoid dense planting", "Stake plants for better airflow", "Practice crop rotation"],
        "fertilizer": "Ensure balanced NPK. Good potassium levels improve disease tolerance.",
        "urgency": "medium",
        "recovery_days": 12,
        "risk_factors": {"humidity_threshold": 80, "temp_min": 25, "temp_max": 35}
    },
    "Tomato__Tomato_YellowLeaf__Curl_Virus": {
        "description": "TYLCV - transmitted by whiteflies. Leaves curl upward, turn yellow; plants stunted.",
        "immediate_actions": ["URGENT: Remove and destroy infected plants", "Apply insecticide for whitefly control immediately", "Use yellow sticky traps"],
        "treatments": ["No cure - management focuses on vector control", "Imidacloprid (Admire) for whitefly control", "Spirotetramat (Movento)", "Pyriproxyfen (Knack)", "Reflective mulches to deter whiteflies"],
        "prevention": ["Plant TYLCV-resistant varieties", "Use insect-proof nets (50-mesh)", "Remove and destroy all crop debris", "Plant away from infested fields"],
        "fertilizer": "Well-balanced nutrition. Adequate silicon can reduce insect feeding.",
        "urgency": "critical",
        "recovery_days": 30,
        "risk_factors": {"humidity_threshold": 60, "temp_min": 25, "temp_max": 38}
    },
    "Tomato__Tomato_mosaic_virus": {
        "description": "Tomato mosaic virus (ToMV) - mosaic patterns of light/dark green, leaf distortion.",
        "immediate_actions": ["Remove and bag infected plants immediately", "Disinfect all tools with 10% bleach", "Wash hands thoroughly", "Restrict movement between rows"],
        "treatments": ["No chemical cure - prevention and removal are key", "Spray milk solution (1:10) - may inactivate virus", "Skim milk powder (100g/L) as protective spray"],
        "prevention": ["Use TMV-resistant varieties", "Start with certified virus-free seeds", "Control aphids and thrips", "Don't use tobacco near tomato plants"],
        "fertilizer": "Ensure stress-free nutrition with balanced fertilizer.",
        "urgency": "critical",
        "recovery_days": 30,
        "risk_factors": {"humidity_threshold": 70, "temp_min": 20, "temp_max": 35}
    },
    "Tomato_healthy": {
        "description": "Your tomato plant is perfectly healthy! Keep up the excellent work.",
        "immediate_actions": ["Continue current care routine", "Scout for pests and disease weekly", "Ensure consistent watering"],
        "treatments": ["No treatment needed"],
        "prevention": ["Apply preventative copper or neem oil monthly", "Train vines and remove suckers", "Deep water 2-3 times per week", "Mulch to maintain soil moisture"],
        "fertilizer": "Switch to high-potassium fertilizer (5-10-15) once flowering begins.",
        "urgency": "none",
        "recovery_days": 0,
        "risk_factors": {"humidity_threshold": 90, "temp_min": 5, "temp_max": 40}
    }
}


# ═══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE))
    return img_resized, np.expand_dims(img_resized / 255.0, axis=0)


def generate_gradcam(img_array, pred_class_index):
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        loss = predictions[:, pred_class_index]
    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_out = conv_outputs[0]
    heatmap = conv_out @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap).numpy()
    heatmap = np.maximum(heatmap, 0)
    if np.max(heatmap) > 0:
        heatmap /= np.max(heatmap)
    return heatmap


def detect_severity(heatmap):
    heatmap_uint8 = np.uint8(255 * heatmap)
    _, thresh = cv2.threshold(heatmap_uint8, 150, 255, cv2.THRESH_BINARY)
    infected_pixels = np.sum(thresh == 255)
    total_pixels = thresh.size
    severity_ratio = infected_pixels / total_pixels
    severity_percent = severity_ratio * 100

    if severity_percent < 20:
        severity_level = "Mild"
        severity_color = "#22c55e"
    elif severity_percent < 50:
        severity_level = "Moderate"
        severity_color = "#f59e0b"
    else:
        severity_level = "Severe"
        severity_color = "#ef4444"

    return severity_level, severity_percent, severity_color


def overlay_gradcam(img_rgb, heatmap):
    """Overlay Grad-CAM heatmap on the image."""
    # Normalize heatmap to 0-1 range
    heatmap_min = np.min(heatmap)
    heatmap_max = np.max(heatmap)
    if heatmap_max > heatmap_min:
        heatmap_norm = (heatmap - heatmap_min) / (heatmap_max - heatmap_min)
    else:
        heatmap_norm = heatmap
    
    # Resize to match image size
    heatmap_resized = cv2.resize(heatmap_norm, (IMG_SIZE, IMG_SIZE))
    
    # Apply colormap (JET shows heat clearly: blue->green->red)
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)
    
    # Simple weighted blend
    overlay = cv2.addWeighted(img_rgb, 0.7, heatmap_rgb, 0.3, 0)
    return overlay


def image_to_base64(img_array):
    _, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buffer).decode("utf-8")


def format_class_name(cls):
    return cls.replace("__", " - ").replace("_", " ")


def compute_health_score(is_healthy, severity_percent, confidence):
    """Compute a 0-100 crop health score."""
    if is_healthy:
        return min(100, int(70 + confidence * 0.3))
    # Inverse of severity, weighted by confidence
    base_score = max(0, 100 - severity_percent * 1.5)
    confidence_weight = confidence / 100
    return max(0, min(100, int(base_score * confidence_weight)))


def compute_risk_level(severity_percent, env_data, rec):
    """Compute risk level based on severity and environmental conditions."""
    risk_score = 0

    # Severity contribution
    if severity_percent > 50:
        risk_score += 40
    elif severity_percent > 20:
        risk_score += 20
    else:
        risk_score += 5

    risk_factors = rec.get("risk_factors", {})

    # Environmental risk
    if env_data:
        humidity = env_data.get("humidity")
        temperature = env_data.get("temperature")

        if humidity and risk_factors.get("humidity_threshold"):
            if humidity >= risk_factors["humidity_threshold"]:
                risk_score += 25
            elif humidity >= risk_factors["humidity_threshold"] - 10:
                risk_score += 10

        if temperature and risk_factors.get("temp_min") and risk_factors.get("temp_max"):
            if risk_factors["temp_min"] <= temperature <= risk_factors["temp_max"]:
                risk_score += 20  # In the disease-favorable temp range
            elif abs(temperature - risk_factors["temp_min"]) <= 5 or abs(temperature - risk_factors["temp_max"]) <= 5:
                risk_score += 10

        if env_data.get("rainfall") and env_data["rainfall"] > 10:
            risk_score += 15

    if risk_score >= 60:
        return "critical"
    elif risk_score >= 40:
        return "high"
    elif risk_score >= 20:
        return "moderate"
    return "low"


def generate_ai_recommendation(prediction, severity, env_data, history, rec):
    """Generate AI-powered intelligent recommendation considering all factors."""
    messages = []
    warnings = []
    next_steps = []

    disease_label = prediction["label"]
    is_healthy = prediction["is_healthy"]
    sev_level = severity["level"]
    sev_pct = severity["percentage"]

    # Basic assessment
    if is_healthy:
        messages.append(f"Your {disease_label.split(' - ')[0] if ' - ' in disease_label else disease_label.split(' ')[0]} plant appears healthy with {prediction['confidence']:.1f}% confidence.")
    else:
        messages.append(f"Disease detected: {disease_label} with {prediction['confidence']:.1f}% confidence and {sev_level} severity ({sev_pct:.1f}% infection area).")

    # Environmental analysis
    if env_data:
        temp = env_data.get("temperature")
        humidity = env_data.get("humidity")
        rainfall = env_data.get("rainfall")
        soil_moisture = env_data.get("soil_moisture")
        soil_ph = env_data.get("soil_ph")

        risk_factors = rec.get("risk_factors", {})

        if humidity and humidity > 80:
            warnings.append(f"High humidity ({humidity}%) creates favorable conditions for fungal diseases. Consider improving ventilation.")
        if temp and temp > 35:
            warnings.append(f"High temperature ({temp}°C) may stress plants. Ensure adequate watering and shade if possible.")
        if temp and temp < 10:
            warnings.append(f"Low temperature ({temp}°C) may slow plant growth and recovery. Consider protective covers.")
        if rainfall and rainfall > 20:
            warnings.append(f"Heavy rainfall ({rainfall}mm) increases disease spread risk. Avoid working with wet plants.")
        if soil_moisture and soil_moisture > 80:
            warnings.append(f"Soil moisture is very high ({soil_moisture}%). Ensure proper drainage to avoid root problems.")
        if soil_ph:
            if soil_ph < 5.5:
                warnings.append(f"Soil pH is low ({soil_ph}). Consider liming to raise pH for optimal nutrient uptake.")
            elif soil_ph > 7.5:
                warnings.append(f"Soil pH is high ({soil_ph}). Consider adding sulfur to lower pH.")

        if not is_healthy and humidity and risk_factors.get("humidity_threshold"):
            if humidity >= risk_factors["humidity_threshold"]:
                warnings.append(f"Current humidity ({humidity}%) exceeds the disease risk threshold ({risk_factors['humidity_threshold']}%). Immediate treatment is recommended.")

    # Temporal progression analysis
    if history and len(history) >= 2:
        severities = [h["severity_percent"] for h in history]
        if len(severities) >= 2:
            trend = severities[-1] - severities[-2]
            if trend > 10:
                warnings.append(f"⚠️ Disease severity is INCREASING rapidly (+{trend:.1f}% since last check). Escalate treatment immediately.")
                next_steps.append("Apply systemic fungicide within 24 hours and monitor daily.")
            elif trend > 0:
                warnings.append(f"Disease severity is slowly increasing (+{trend:.1f}%). Current treatment may be insufficient.")
                next_steps.append("Review and potentially upgrade your treatment plan.")
            elif trend < -5:
                messages.append(f"Good news: severity is decreasing ({trend:.1f}%). Treatment appears to be working.")
            else:
                messages.append("Severity is stable since last check. Continue monitoring.")

    # Recovery time
    recovery_days = rec.get("recovery_days", 0)
    if not is_healthy and recovery_days > 0:
        next_steps.append(f"Estimated recovery time with proper treatment: {recovery_days} days.")

    # Next steps based on urgency
    urgency = rec.get("urgency", "medium")
    if urgency == "critical":
        next_steps.insert(0, "🚨 CRITICAL: Immediate action required within 24 hours to prevent crop loss.")
    elif urgency == "high":
        next_steps.insert(0, "⚠️ HIGH PRIORITY: Begin treatment within 48 hours for best results.")
    elif not is_healthy:
        next_steps.append("Schedule treatment within the week for best recovery outcomes.")

    if is_healthy:
        next_steps.append("Continue regular scouting every 5-7 days to catch any issues early.")

    return {
        "messages": messages,
        "warnings": warnings,
        "next_steps": next_steps,
        "recovery_days": recovery_days
    }


def generate_alerts(user_id, prediction, severity, env_data, history, risk_level):
    """Generate alerts based on conditions."""
    db = get_db()
    alerts_generated = []

    # Rapid severity increase alert
    if history and len(history) >= 2:
        recent_severity = [h["severity_percent"] for h in history[-3:]]
        if len(recent_severity) >= 2 and recent_severity[-1] - recent_severity[0] > 15:
            alert = {
                "alert_id": str(uuid.uuid4()),
                "user_id": user_id,
                "alert_type": "severity_spike",
                "severity": "critical",
                "title": "Rapid Disease Progression",
                "message": f"Disease severity has increased by {recent_severity[-1] - recent_severity[0]:.1f}% in recent analyses. Immediate action required."
            }
            db.execute("INSERT INTO alerts (alert_id, user_id, alert_type, severity, title, message) VALUES (?, ?, ?, ?, ?, ?)",
                       (alert["alert_id"], alert["user_id"], alert["alert_type"], alert["severity"], alert["title"], alert["message"]))
            alerts_generated.append(alert)

    # Environmental risk alert
    if env_data:
        humidity = env_data.get("humidity", 0)
        temperature = env_data.get("temperature", 25)
        if humidity > 85 and temperature > 25:
            alert = {
                "alert_id": str(uuid.uuid4()),
                "user_id": user_id,
                "alert_type": "environmental_risk",
                "severity": "high",
                "title": "High Disease Risk Weather",
                "message": f"Current conditions (humidity: {humidity}%, temperature: {temperature}°C) are highly favorable for fungal diseases. Apply preventative treatments."
            }
            db.execute("INSERT INTO alerts (alert_id, user_id, alert_type, severity, title, message) VALUES (?, ?, ?, ?, ?, ?)",
                       (alert["alert_id"], alert["user_id"], alert["alert_type"], alert["severity"], alert["title"], alert["message"]))
            alerts_generated.append(alert)

    # Critical risk level alert
    if risk_level == "critical" and not prediction.get("is_healthy"):
        alert = {
            "alert_id": str(uuid.uuid4()),
            "user_id": user_id,
            "alert_type": "critical_risk",
            "severity": "critical",
            "title": "Critical Crop Risk Detected",
            "message": f"{prediction['label']}: Combined analysis of disease severity, environmental conditions, and progression indicates critical risk. Seek expert advice immediately."
        }
        db.execute("INSERT INTO alerts (alert_id, user_id, alert_type, severity, title, message) VALUES (?, ?, ?, ?, ?, ?)",
                   (alert["alert_id"], alert["user_id"], alert["alert_type"], alert["severity"], alert["title"], alert["message"]))
        alerts_generated.append(alert)

    db.commit()
    return alerts_generated


def predict_future_severity(history, days_ahead=7):
    """Predict future disease severity based on historical data."""
    if not history or len(history) < 2:
        return None

    severities = [h["severity_percent"] for h in history]
    n = len(severities)

    # Simple linear regression
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(severities) / n

    numerator = sum((x[i] - x_mean) * (severities[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return {"predicted_severity": severities[-1], "trend": "stable", "days_ahead": days_ahead}

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Predict future
    future_x = n + days_ahead
    predicted = max(0, min(100, slope * future_x + intercept))

    if slope > 2:
        trend = "rapidly_increasing"
    elif slope > 0.5:
        trend = "increasing"
    elif slope < -2:
        trend = "rapidly_decreasing"
    elif slope < -0.5:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "predicted_severity": round(predicted, 1),
        "trend": trend,
        "slope": round(slope, 3),
        "days_ahead": days_ahead,
        "confidence": max(20, min(95, int(80 - abs(slope) * 5)))
    }


# ═══════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/classes", methods=["GET"])
def get_classes():
    formatted = [{"id": name, "label": format_class_name(name)} for name in class_names]
    return jsonify({"classes": formatted, "total": len(class_names)})


@app.route("/api/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use JPG, PNG or WEBP"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Parse multi-modal data
    user_id = request.form.get("user_id", "default")
    crop_type = request.form.get("crop_type", "")
    growth_stage = request.form.get("growth_stage", "vegetative")
    crop_id = request.form.get("crop_id", "")
    plant_id = request.form.get("plant_id", "").strip()

    env_data = {}
    for field in ["temperature", "humidity", "rainfall", "soil_moisture", "soil_ph"]:
        val = request.form.get(field)
        if val:
            try:
                env_data[field] = float(val)
            except ValueError:
                pass
    soil_nutrients = request.form.get("soil_nutrients", "")

    try:
        img_rgb, img_array = preprocess_image(filepath)

        # Predict
        predictions = model.predict(img_array, verbose=0)
        preds = predictions[0]
        pred_class_index = int(np.argmax(preds))
        confidence = float(preds[pred_class_index] * 100)
        predicted_class = class_names[pred_class_index]
        is_healthy = "healthy" in predicted_class.lower()

        # Top-5 predictions
        top5_indices = np.argsort(preds)[::-1][:5]
        top5 = [
            {"class": format_class_name(class_names[i]), "confidence": float(preds[i] * 100)}
            for i in top5_indices
        ]

        predicted_label = format_class_name(predicted_class)

        # Grad-CAM
        heatmap = generate_gradcam(img_array, pred_class_index)

        # Severity
        severity_level, severity_percent, severity_color = detect_severity(heatmap)

        # Overlay
        overlay_img = overlay_gradcam(img_rgb, heatmap)

        # Encode images
        original_b64 = image_to_base64(img_rgb)
        overlay_b64 = image_to_base64(overlay_img)

        # Get recommendation
        rec = RECOMMENDATIONS.get(predicted_class, {
            "description": f"Analysis complete for {predicted_label}.",
            "immediate_actions": ["Consult a local agronomist"],
            "treatments": ["Refer to regional guidelines"],
            "prevention": ["Practice good agronomic hygiene"],
            "fertilizer": "Follow standard balanced fertilization program.",
            "urgency": "medium",
            "recovery_days": 14,
            "risk_factors": {}
        })

        is_healthy = "healthy" in predicted_class.lower()

        # Compute health score
        health_score = compute_health_score(is_healthy, severity_percent, confidence)

        # Compute risk level
        risk_level = compute_risk_level(severity_percent, env_data, rec)

        # Get predicted embedding for image similarity
        conv_out_for_emb, _ = grad_model(img_array)
        embedding_tensor = tf.reduce_mean(conv_out_for_emb[0], axis=(0, 1)).numpy()
        norm = np.linalg.norm(embedding_tensor)
        if norm > 0:
            embedding_tensor = embedding_tensor / norm
        embedding_json = json.dumps(embedding_tensor.tolist())

        db = get_db()

        # Image Similarity Check to Auto-Assign plant_id
        if not plant_id:
            rows = db.execute("SELECT plant_id, embedding FROM Observations WHERE embedding IS NOT NULL ORDER BY timestamp DESC LIMIT 200").fetchall()
            max_sim = -1
            best_plant = None
            for row in rows:
                if row["embedding"]:
                    try:
                        db_emb = np.array(json.loads(row["embedding"]))
                        sim = np.dot(embedding_tensor, db_emb)
                        if sim > max_sim:
                            max_sim = sim
                            best_plant = row["plant_id"]
                    except:
                        pass
            
            # Threshold for considering it the same plant
            if max_sim > 0.92 and best_plant:
                plant_id = best_plant
            else:
                plant_id = f"PLANT-{str(uuid.uuid4())[:8].upper()}"

        # Ensure Plant exists
        db.execute("INSERT OR IGNORE INTO Plants (plant_id, crop_type) VALUES (?, ?)", (plant_id, crop_type))
        db.commit()
        
        # Insert observation into the new schema
        obs_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO Observations (id, plant_id, image_path, predicted_disease, severity_percentage, confidence_score, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (obs_id, plant_id, filepath, predicted_label, severity_percent, confidence, embedding_json))
        db.commit()

        # Retrieve Plant History
        history_query = "SELECT severity_percentage as severity_percent, timestamp as created_at FROM Observations WHERE plant_id = ? ORDER BY timestamp ASC LIMIT 50"
        history_rows = db.execute(history_query, [plant_id]).fetchall()
        history = [{"severity_percent": row["severity_percent"] or 0, "created_at": row["created_at"]} for row in history_rows]

        # AI Recommendation
        prediction_data = {"label": predicted_label, "is_healthy": is_healthy, "confidence": confidence}
        severity_data = {"level": severity_level, "percentage": severity_percent}
        ai_rec = generate_ai_recommendation(prediction_data, severity_data, env_data, history, rec)

        # Future prediction
        future_pred = predict_future_severity(history)

        # Store prediction in older DB (backward compatibility)
        prediction_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO predictions (prediction_id, user_id, crop_id, disease_class, disease_label,
                confidence, severity_level, severity_percent, health_score, is_healthy,
                temperature, humidity, rainfall, soil_moisture, soil_ph, soil_nutrients,
                crop_type, growth_stage, ai_recommendation, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id, user_id, crop_id or None, predicted_class, predicted_label,
            confidence, severity_level, severity_percent, health_score, int(is_healthy),
            env_data.get("temperature"), env_data.get("humidity"), env_data.get("rainfall"),
            env_data.get("soil_moisture"), env_data.get("soil_ph"), soil_nutrients,
            crop_type, growth_stage, json.dumps(ai_rec), risk_level
        ))
        db.commit()

        # Generate alerts
        alerts = generate_alerts(user_id, prediction_data, severity_data, env_data, history, risk_level)

        result = {
            "success": True,
            "prediction_id": prediction_id,
            "plant_id": plant_id,
            "prediction": {
                "class": predicted_class,
                "label": predicted_label,
                "confidence": round(confidence, 2),
                "is_healthy": is_healthy,
                "top5": top5
            },
            "severity": {
                "level": severity_level,
                "percentage": round(severity_percent, 2),
                "color": severity_color
            },
            "health_score": health_score,
            "risk_level": risk_level,
            "images": {
                "original": original_b64,
                "gradcam": overlay_b64
            },
            "recommendation": rec,
            "ai_assistant": ai_rec,
            "future_prediction": future_pred,
            "alerts": alerts,
            "historical_progression": history,
            "environmental_data": env_data if env_data else None
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # Don't delete the filepath right away if we're storing it in Observations as requested
        # We can either keep it or use base64 in the future.
        pass


@app.route("/api/plant_history/<plant_id>", methods=["GET"])
def api_plant_history(plant_id):
    db = get_db()
    rows = db.execute("SELECT id, image_path, predicted_disease, severity_percentage, confidence_score, timestamp FROM Observations WHERE plant_id = ? ORDER BY timestamp DESC", (plant_id,)).fetchall()
    observations = [dict(row) for row in rows]
    return jsonify({
        "plant_id": plant_id,
        "observations": observations
    })


@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    import re
    data = request.json
    plant_id = data.get("plant_id")
    query = data.get("query", "").lower()
    
    # Extract alternative plant ID from query if user specifies one (e.g., "PLANT-123")
    match = re.search(r'(plant-[a-z0-9\-]+)', query)
    if match:
        plant_id = match.group(1).upper()
    
    # Basic greeting handling without needing a plant_id
    if query.strip() in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "hi ai", "hello ai"] or query.startswith("hi ") or query.startswith("hello "):
        return jsonify({"plant_id": plant_id, "response": "Hello! I am your Crop AI assistant. You can ask me how your plant is doing, ask if the disease trend is getting worse, or ask for treatment suggestions! What can I help you with?"})
        
    if not plant_id:
        return jsonify({"error": "plant_id is required. You can mention a Plant ID like PLANT-123 in your message!"}), 400
        
    db = get_db()
    rows = db.execute("SELECT predicted_disease, severity_percentage, timestamp FROM Observations WHERE plant_id = ? ORDER BY timestamp ASC", (plant_id,)).fetchall()
    
    if not rows:
        return jsonify({"response": f"I couldn't find any records for Plant ID {plant_id}. Are you sure the ID is correct?"})
    
    latest = rows[-1]
    sev_pct = round(latest['severity_percentage'], 1)
    
    if any(k in query for k in ["how", "doing", "status", "health"]):
        if sev_pct < 5:
            resp = f"Your plant {plant_id} is doing great! It was recently diagnosed as {latest['predicted_disease']} with a very low severity of {sev_pct}%."
        else:
            resp = f"Your plant {plant_id} is currently suffering from {latest['predicted_disease']} with a severity of {sev_pct}%."
    elif any(k in query for k in ["worse", "trend", "better", "improving", "progress"]):
        if len(rows) < 2:
            resp = f"I only have one record for {plant_id} so far, so I can't determine if it's getting worse. Please check back after your next scan!"
        else:
            prev = round(rows[-2]["severity_percentage"], 1)
            curr = sev_pct
            if curr > prev + 5:
                resp = f"Yes, the disease for {plant_id} seems to be getting worse. Severity increased from {prev}% to {curr}%."
            elif curr < prev - 5:
                resp = f"Good news! The disease for {plant_id} is improving. Severity decreased from {prev}% to {curr}%."
            else:
                resp = f"The condition for {plant_id} is relatively stable. Severity went from {prev}% to {curr}%."
    elif any(k in query for k in ["do next", "treatment", "help", "suggestion", "advice", "recommendation", "what to do"]):
        if "healthy" in latest["predicted_disease"].lower():
            resp = "Just keep up the good work! No specific treatments are needed right now."
        else:
            resp = f"For {latest['predicted_disease']} on {plant_id}, you should consider immediate actions like removing affected leaves, improving airflow, and applying the recommended fungicides."
    else:
        resp = f"I'm a simple AI currently focused on specific queries. Try asking me for 'suggestions', 'treatments', about its 'trend' or 'how is it doing'! (Latest scan for {plant_id}: {latest['predicted_disease']} at {sev_pct}%)"
        
    return jsonify({"plant_id": plant_id, "response": resp})


@app.route("/api/history/<user_id>", methods=["GET"])
def get_history(user_id):
    """Get prediction history for a user."""
    db = get_db()
    limit = request.args.get("limit", 20, type=int)
    rows = db.execute("""
        SELECT prediction_id, disease_class, disease_label, confidence,
               severity_level, severity_percent, health_score, is_healthy,
               risk_level, crop_type, growth_stage, created_at
        FROM predictions WHERE user_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()

    history = [{
        "prediction_id": row["prediction_id"],
        "disease_class": row["disease_class"],
        "disease_label": row["disease_label"],
        "confidence": row["confidence"],
        "severity_level": row["severity_level"],
        "severity_percent": row["severity_percent"],
        "health_score": row["health_score"],
        "is_healthy": bool(row["is_healthy"]),
        "risk_level": row["risk_level"],
        "crop_type": row["crop_type"],
        "growth_stage": row["growth_stage"],
        "created_at": row["created_at"]
    } for row in rows]

    return jsonify({"user_id": user_id, "history": history, "total": len(history)})


@app.route("/api/progression/<user_id>", methods=["GET"])
def get_progression(user_id):
    """Get disease severity progression over time."""
    db = get_db()
    crop_id = request.args.get("crop_id", "")

    query = """
        SELECT severity_percent, health_score, risk_level, disease_label,
               created_at, temperature, humidity
        FROM predictions WHERE user_id = ?
    """
    params = [user_id]
    if crop_id:
        query += " AND crop_id = ?"
        params.append(crop_id)
    query += " ORDER BY created_at ASC LIMIT 100"

    rows = db.execute(query, params).fetchall()
    data_points = [{
        "severity_percent": row["severity_percent"],
        "health_score": row["health_score"],
        "risk_level": row["risk_level"],
        "disease_label": row["disease_label"],
        "timestamp": row["created_at"],
        "temperature": row["temperature"],
        "humidity": row["humidity"]
    } for row in rows]

    # Calculate future prediction
    history = [{"severity_percent": row["severity_percent"] or 0} for row in rows]
    future = predict_future_severity(history)

    return jsonify({
        "user_id": user_id,
        "data_points": data_points,
        "future_prediction": future,
        "total": len(data_points)
    })


@app.route("/api/alerts/<user_id>", methods=["GET"])
def get_alerts(user_id):
    """Get alerts for a user."""
    db = get_db()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    query = "SELECT * FROM alerts WHERE user_id = ?"
    params = [user_id]
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY created_at DESC LIMIT 50"
    rows = db.execute(query, params).fetchall()
    alerts = [{
        "alert_id": row["alert_id"],
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "title": row["title"],
        "message": row["message"],
        "is_read": bool(row["is_read"]),
        "created_at": row["created_at"]
    } for row in rows]
    return jsonify({"user_id": user_id, "alerts": alerts, "unread_count": sum(1 for a in alerts if not a["is_read"])})


@app.route("/api/alerts/<user_id>/read", methods=["POST"])
def mark_alerts_read(user_id):
    """Mark alerts as read."""
    db = get_db()
    alert_ids = request.json.get("alert_ids", [])
    if alert_ids:
        placeholders = ",".join("?" * len(alert_ids))
        db.execute(f"UPDATE alerts SET is_read = 1 WHERE alert_id IN ({placeholders}) AND user_id = ?",
                   alert_ids + [user_id])
    else:
        db.execute("UPDATE alerts SET is_read = 1 WHERE user_id = ?", (user_id,))
    db.commit()
    return jsonify({"success": True})


@app.route("/api/dashboard/<user_id>", methods=["GET"])
def get_dashboard(user_id):
    """Get comprehensive dashboard data."""
    db = get_db()

    # Recent predictions
    predictions = db.execute("""
        SELECT prediction_id, disease_label, confidence, severity_level,
               severity_percent, health_score, is_healthy, risk_level,
               crop_type, created_at
        FROM predictions WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,)).fetchall()

    # Stats
    total_analyses = db.execute("SELECT COUNT(*) as cnt FROM predictions WHERE user_id = ?", (user_id,)).fetchone()["cnt"]
    diseases_found = db.execute("SELECT COUNT(*) as cnt FROM predictions WHERE user_id = ? AND is_healthy = 0", (user_id,)).fetchone()["cnt"]
    avg_health = db.execute("SELECT AVG(health_score) as avg_score FROM predictions WHERE user_id = ?", (user_id,)).fetchone()["avg_score"]

    # Severity progression (last 20 entries)
    progression = db.execute("""
        SELECT severity_percent, health_score, created_at, disease_label
        FROM predictions WHERE user_id = ?
        ORDER BY created_at ASC LIMIT 20
    """, (user_id,)).fetchall()

    # Unread alerts
    unread_alerts = db.execute("""
        SELECT alert_id, alert_type, severity, title, message, created_at
        FROM alerts WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,)).fetchall()

    # Disease distribution
    disease_dist = db.execute("""
        SELECT predicted_disease as disease_label, 
               COUNT(*) as cnt, 
               GROUP_CONCAT(plant_id, ', ') as plant_ids
        FROM (
            SELECT plant_id, predicted_disease 
            FROM Observations 
            GROUP BY plant_id 
            HAVING timestamp = MAX(timestamp)
        )
        WHERE predicted_disease NOT LIKE '%healthy%'
        GROUP BY predicted_disease 
        ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    return jsonify({
        "user_id": user_id,
        "stats": {
            "total_analyses": total_analyses,
            "diseases_found": diseases_found,
            "healthy_count": total_analyses - diseases_found,
            "avg_health_score": round(avg_health, 1) if avg_health else 100
        },
        "recent_predictions": [{
            "prediction_id": r["prediction_id"],
            "disease_label": r["disease_label"],
            "confidence": r["confidence"],
            "severity_level": r["severity_level"],
            "severity_percent": r["severity_percent"],
            "health_score": r["health_score"],
            "is_healthy": bool(r["is_healthy"]),
            "risk_level": r["risk_level"],
            "crop_type": r["crop_type"],
            "created_at": r["created_at"]
        } for r in predictions],
        "progression": [{
            "severity_percent": p["severity_percent"],
            "health_score": p["health_score"],
            "timestamp": p["created_at"],
            "disease_label": p["disease_label"]
        } for p in progression],
        "unread_alerts": [{
            "alert_id": a["alert_id"],
            "alert_type": a["alert_type"],
            "severity": a["severity"],
            "title": a["title"],
            "message": a["message"],
            "created_at": a["created_at"]
        } for a in unread_alerts],
        "disease_distribution": [{
            "disease": d["disease_label"],
            "count": d["cnt"],
            "plant_ids": d["plant_ids"]
        } for d in disease_dist]
    })


@app.route("/api/environmental", methods=["POST"])
def store_environmental():
    """Store environmental data."""
    data = request.json
    user_id = data.get("user_id", "default")
    db = get_db()
    env_id = str(uuid.uuid4())
    db.execute("""
        INSERT INTO environmental_data (env_id, user_id, temperature, humidity, rainfall,
            soil_moisture, soil_ph, soil_nutrients, wind_speed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        env_id, user_id, data.get("temperature"), data.get("humidity"), data.get("rainfall"),
        data.get("soil_moisture"), data.get("soil_ph"), data.get("soil_nutrients"),
        data.get("wind_speed")
    ))
    db.commit()
    return jsonify({"success": True, "env_id": env_id})


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "model": "MobileNetV2 (Multi-Task Learning)",
        "classes": len(class_names),
        "version": "2.0.0",
        "features": [
            "Disease Classification",
            "Severity Prediction",
            "Multi-Modal Learning",
            "Grad-CAM Explainability",
            "Temporal Tracking",
            "AI Decision Support",
            "Risk Analysis",
            "Alert System"
        ]
    })


@app.route("/api/suitability", methods=["POST"])
def check_suitability():
    """Predicts farming suitability purely based on environmental conditions."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        crop = data.get("crop_type", "unknown").lower()
        if crop not in ["tomato", "potato", "pepper"]:
            crop = "tomato" # fallback
            
        temp = float(data.get("temperature", 25))
        humidity = float(data.get("humidity", 60))
        rainfall = float(data.get("rainfall", 0))
        soil_moisture = float(data.get("soil_moisture", 50))
        soil_ph = float(data.get("soil_ph", 6.5))
        stage = data.get("growth_stage", "vegetative").lower()

        # Rule engine for crops
        ideal_conditions = {
            "tomato": {"temp": [21, 27], "humidity": [60, 80], "ph": [6.0, 6.8], "moisture": [60, 80]},
            "potato": {"temp": [15, 20], "humidity": [70, 85], "ph": [5.0, 6.0], "moisture": [70, 85]},
            "pepper": {"temp": [21, 29], "humidity": [50, 70], "ph": [6.0, 6.8], "moisture": [50, 70]}
        }

        crop_cond = ideal_conditions.get(crop)
        
        issues = []
        changes = []
        
        # Temp check
        if temp < crop_cond["temp"][0]:
            issues.append(f"Temperature ({temp}°C) is too low.")
            changes.append("Use greenhouse heating, clear plastic mulch, or row covers to trap heat.")
        elif temp > crop_cond["temp"][1]:
            issues.append(f"Temperature ({temp}°C) is too high.")
            changes.append("Install shade nets, increase irrigation frequency, and ensure good ventilation.")

        # Humidity check
        if humidity < crop_cond["humidity"][0]:
            issues.append(f"Humidity ({humidity}%) is too low.")
            changes.append("Use overhead sprinklers lightly or misting systems to raise local humidity.")
        elif humidity > crop_cond["humidity"][1]:
            issues.append(f"Humidity ({humidity}%) is too high (increases fungal risk).")
            changes.append("Improve air circulation by pruning lower leaves and increasing plant spacing.")

        # Soil pH Check
        if soil_ph < crop_cond["ph"][0]:
            issues.append(f"Soil pH ({soil_ph}) is too acidic.")
            changes.append(f"Add agricultural lime (calcium carbonate) to raise pH closer to {crop_cond['ph'][0]}.")
        elif soil_ph > crop_cond["ph"][1]:
            issues.append(f"Soil pH ({soil_ph}) is too alkaline.")
            changes.append(f"Incorporate elemental sulfur or peat moss to lower pH towards {crop_cond['ph'][1]}.")

        # Moisture Check
        if soil_moisture < crop_cond["moisture"][0]:
            issues.append(f"Soil moisture ({soil_moisture}%) is deficient.")
            changes.append("Implement drip irrigation and apply organic mulch to retain soil water.")
        elif soil_moisture > crop_cond["moisture"][1]:
            issues.append(f"Soil moisture ({soil_moisture}%) is excessive.")
            changes.append("Improve soil drainage by adding organic matter or creating raised beds to prevent root rot.")

        is_suitable = len(issues) <= 1

        if is_suitable:
            condition_analysis = f"Current conditions are highly favorable for farming {crop.capitalize()}. Minor adjustments will maximize your yield."
        elif len(issues) <= 3:
            condition_analysis = f"Conditions are moderately suitable for {crop.capitalize()}, but require active management to prevent stress."
        else:
            condition_analysis = f"Current environment is NOT ideal for {crop.capitalize()}. Significant interventions required before planting."

        if stage == "seedling":
            farming_time = "Establishment Phase - Focus on root development and protecting from extreme temperatures."
            harvest_time = "70-90 days away depending on variety."
            if not is_suitable: changes.append("Delay transplanting outdoors until conditions stabilize.")
        elif stage == "vegetative":
            farming_time = "Active Growth Phase - High nutrient and consistent water demand."
            harvest_time = "40-60 days away. Prepare trellising if applicable."
        elif stage == "flowering":
            farming_time = "Critical Phase - Avoid moisture stress to prevent blossom drop."
            harvest_time = "20-30 days away."
        elif stage == "fruiting":
            farming_time = "Maturation Phase - Maintain potassium levels."
            harvest_time = "Harvest incoming within 5-15 days."
        else: # maturity
            farming_time = "Harvest Phase."
            harvest_time = "Ready to pluck immediately. Harvest in the morning when plants are well hydrated."

        if not changes:
            changes.append("Continue current exceptional maintenance routine. No immediate changes required.")

        return jsonify({
            "is_suitable": is_suitable,
            "crop": crop.capitalize(),
            "condition_analysis": condition_analysis,
            "farming_time": farming_time,
            "harvest_time": harvest_time,
            "issues": issues,
            "changes_needed": changes
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  CropSense AI - Smart Monitoring & Decision Support")
    print(f"  Classes: {len(class_names)}")
    print("  Features: Multi-Modal | Temporal Tracking | AI Assistant")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
