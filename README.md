# 🌿 CropSense AI — Smart Crop Disease Monitoring & Decision Support System

An end-to-end AI-powered crop disease prediction, monitoring, and decision support system. Built with Multi-Task Learning, Multi-Modal inputs, Explainable AI, temporal disease tracking, and an intelligent AI assistant.

This project presents a production-grade, end-to-end intelligent system for crop disease detection, severity estimation, and adaptive decision support, designed to enable next-generation precision agriculture.

At its core, the system employs a multi-task deep learning framework built on a fine-tuned MobileNetV2 backbone, jointly optimizing for disease classification (categorical output) and severity prediction (continuous regression). This shared representation learning approach improves generalization while reducing computational overhead.

To enhance predictive robustness, the system integrates multi-modal data fusion, combining high-dimensional visual features extracted from plant leaf images with structured environmental signals such as weather patterns, soil conditions, and transactional crop metadata. This enables context-aware inference aligned with real-world agricultural variability.

A comprehensive Explainable AI (XAI) layer is incorporated to ensure model transparency and trust. Grad-CAM is used for spatial localization of disease patterns, while SHAP and LIME provide feature-level attribution, allowing both global and local interpretability of model decisions.

Beyond static predictions, the system introduces temporal disease intelligence by tracking severity progression across time-series data and applying regression-based forecasting models to predict future disease trajectories. This facilitates early intervention and proactive farm management.

An intelligent decision support engine translates model outputs into actionable insights, including:
- Risk stratification (Low → Critical)
- Dynamic health scoring (0–100 scale)
- Treatment recommendations
- Anomaly detection and alert generation

The system follows a modular, scalable architecture consisting of:
- A deep learning inference layer (Keras/TensorFlow)
- A RESTful backend service (Flask)
- A lightweight relational database (SQLite)
- An interactive frontend dashboard for visualization and monitoring

This work demonstrates a complete AI lifecycle pipeline — from multi-modal data ingestion and model training to explainability, temporal analytics, and deployment — closely reflecting real-world agri-tech platforms and decision intelligence systems.

---

## ✨ Key Innovation Highlights

| Feature | Description |
|---------|-------------|
| **Multi-Task Learning** | Disease classification + severity prediction from shared MobileNetV2 backbone |
| **Multi-Modal Learning** | Image + weather + soil data fusion for comprehensive analysis |
| **Bayesian Optimization** | Hyperparameter auto-tuning (learning rate, batch size, dropout) |
| **Explainable AI** | Grad-CAM heatmaps + SHAP feature contributions + LIME explanations |
| **Temporal Tracking** | Disease severity progression over time with trend analysis |
| **AI Decision Support** | Intelligent assistant with warnings, next steps, and risk analysis |
| **Database Integration** | SQLite for user data, crop data, prediction history, environmental data |
| **Alert System** | Automatic notifications for severity spikes and risky conditions |
| **Health Score** | 0–100 crop health scoring combining disease, severity, and confidence |
| **Future Prediction** | Linear regression-based severity forecasting with trend analysis |

---

## 🏗️ Architecture

### System Workflow
```
User Input → Multi-Modal Model → Multi-Task Prediction →
Store in Database → AI Assistant Analysis →
Recommendations + Alerts + Tracking
```

### Components
- **Frontend**: HTML5 + CSS3 + Vanilla JS with glassmorphism, Canvas charts, dashboard
- **Backend**: Python Flask with RESTful API, SQLite database
- **ML Core**: Keras MobileNetV2 fine-tuned on PlantVillage (15 classes)
- **XAI**: Grad-CAM gradient-based visualization
- **Database**: SQLite with tables for users, crops, predictions, environmental data, alerts

---

## 🛠️ Project Structure

```
smart-crop-health/
├── frontend/
│   ├── index.html          # Main dashboard + analyzer UI
│   ├── app.js              # Multi-modal logic, charts, API calls
│   └── styles.css          # Dark theme, glassmorphism, animations
│
├── backend/
│   └── app.py              # Flask API with DB, AI assistant, alerts
│
├── ml/
│   ├── train.py            # Model training pipeline
│   ├── evaluation.py       # Metrics & confusion matrix
│   ├── gradcam.py          # Grad-CAM standalone
│   ├── predict.py          # CLI predictor
│   ├── severity_detection.py
│   ├── recomendation.py
│   └── utils/
│       └── download_model.py
│
├── data/
│   ├── dataset/            # PlantVillage dataset (train/test)
│   └── cropsense.db        # SQLite database (auto-created)
│
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Setup Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
```bash
cd backend
python app.py
```

Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve frontend |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/classes` | List disease classes |
| `POST` | `/api/predict` | Multi-modal prediction (image + env data) |
| `GET` | `/api/history/<user_id>` | Prediction history |
| `GET` | `/api/progression/<user_id>` | Severity progression over time |
| `GET` | `/api/alerts/<user_id>` | User alerts & notifications |
| `POST` | `/api/alerts/<user_id>/read` | Mark alerts as read |
| `GET` | `/api/dashboard/<user_id>` | Dashboard overview data |
| `POST` | `/api/environmental` | Store environmental data |

---

## 🧪 Model Details

- **Architecture**: MobileNetV2 + Custom Dense Head (Multi-Task)
- **Input**: 224×224×3 images
- **Outputs**: Disease Classification (Softmax) + Severity (Regression)
- **Optimizer**: Adam (lr=0.0001)
- **Callbacks**: EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

### Supported Classes (15)
- **Pepper**: Healthy, Bacterial Spot
- **Potato**: Healthy, Early Blight, Late Blight
- **Tomato**: Healthy, Bacterial Spot, Early Blight, Late Blight, Leaf Mold, Septoria Leaf Spot, Spider Mites, Target Spot, Yellow Leaf Curl Virus, Mosaic Virus

---

## 📊 Evaluation Metrics

The system tracks:
- Accuracy, Precision, Recall, F1-score
- Confusion Matrix
- Loss curves
- Health Score (0–100)
- Risk Level (Low → Critical)

---

*Built for smart agriculture — powered by multi-task AI with decision support.*
