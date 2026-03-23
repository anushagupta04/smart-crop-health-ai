import os
import shutil
import random

SOURCE_DIR = r"C:\Users\KIIT0001\Downloads\PlantVillage"

TRAIN_DIR = "dataset/train"
TEST_DIR = "dataset/test"

SPLIT_RATIO = 0.8  

if not os.path.exists(TRAIN_DIR):
    os.makedirs(TRAIN_DIR)

if not os.path.exists(TEST_DIR):
    os.makedirs(TEST_DIR)

for class_name in os.listdir(SOURCE_DIR):
    class_path = os.path.join(SOURCE_DIR, class_name)

    
    if not os.path.isdir(class_path):
        continue

    images = os.listdir(class_path)
    random.shuffle(images)

    split_index = int(len(images) * SPLIT_RATIO)

    train_images = images[:split_index]
    test_images = images[split_index:]

    train_class_dir = os.path.join(TRAIN_DIR, class_name)
    test_class_dir = os.path.join(TEST_DIR, class_name)

    if not os.path.exists(train_class_dir):
        os.makedirs(train_class_dir)

    if not os.path.exists(test_class_dir):
        os.makedirs(test_class_dir)

    for img in train_images:
        shutil.copy(
            os.path.join(class_path, img),
            os.path.join(train_class_dir, img)
        )

    for img in test_images:
        shutil.copy(
            os.path.join(class_path, img),
            os.path.join(test_class_dir, img)
        )

    print(f"✔ {class_name}: {len(train_images)} train, {len(test_images)} test")

print("\n Dataset split completed successfully!")
