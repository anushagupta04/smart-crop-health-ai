import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import keras_tuner as kt
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_DIR = os.path.join(BASE_DIR, "data", "dataset", "train")
TEST_DIR = os.path.join(BASE_DIR, "data", "dataset", "test")

# 1. Data Generators
train_gen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    zoom_range=0.2,
    horizontal_flip=True
)
test_gen = ImageDataGenerator(rescale=1./255)

train_data = train_gen.flow_from_directory(
    TRAIN_DIR, target_size=(224,224), batch_size=16, class_mode='categorical'
)
test_data = test_gen.flow_from_directory(
    TEST_DIR, target_size=(224,224), batch_size=16, class_mode='categorical'
)

NUM_CLASSES = train_data.num_classes

# 2. Hypermodel Builder for Bayesian Optimization
def build_model(hp):
    base_model = MobileNetV2(
        weights='imagenet',
        include_top=False,
        input_shape=(224,224,3)
    )
    
    # Freeze the base model
    base_model.trainable = False

    x = base_model.output
    x = layers.GlobalAveragePooling2D()(x)
    
    # Tune the number of units in the Dense layer
    hp_units = hp.Int('units', min_value=64, max_value=256, step=64)
    x = layers.Dense(units=hp_units, activation='relu')(x)
    
    # Tune the dropout rate (0.2, 0.3, 0.4, 0.5)
    hp_dropout = hp.Float('dropout', min_value=0.2, max_value=0.5, step=0.1)
    x = layers.Dropout(rate=hp_dropout)(x)
    
    output = layers.Dense(NUM_CLASSES, activation='softmax')(x)
    
    model = models.Model(inputs=base_model.input, outputs=output)
    
    # Tune the learning rate for the optimizer
    hp_learning_rate = hp.Choice('learning_rate', values=[1e-3, 5e-4, 1e-4])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=hp_learning_rate),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

# 3. Apply Bayesian Optimization (Gaussian Process)
tuner = kt.BayesianOptimization(
    build_model,
    objective='val_accuracy',
    max_trials=2,              # Reduced for faster demonstration
    num_initial_points=1,      # Random exploration steps before using Gaussian Process
    directory=os.path.join(BASE_DIR, "ml", "tuning"),
    project_name='cropsense_bayesian_tuning'
)

# 4. Search for the Best Hyperparameters
early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)

print("\n🚀 Starting Bayesian Optimization Phase...")
tuner.search(
    train_data,
    validation_data=test_data,
    epochs=1,
    callbacks=[early_stop]
)

# 5. Retrieve best model and summary
best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
print(f"\n✅ Bayesian Optimization Complete!")
print(f"Optimal Dense Units: {best_hps.get('units')}")
print(f"Optimal Dropout: {best_hps.get('dropout')}")
print(f"Optimal Learning Rate: {best_hps.get('learning_rate')}")

# Build the final optimized model
best_model = tuner.hypermodel.build(best_hps)

# Train the optimally tuned model normally
history = best_model.fit(
    train_data,
    validation_data=test_data,
    epochs=1,
    callbacks=[early_stop]
)

best_model.save(os.path.join(BASE_DIR, "ml", "models", "bayesian_optimized_model.h5"))
print("Saved optimized model as bayesian_optimized_model.h5")
