import cv2
import numpy as np
import os

# Create uploads directory if it doesn't exist
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Create a simple test image - a green leaf with some brown spots
test_image = np.ones((224, 224, 3), dtype=np.uint8)

# Green leaf background
test_image[:, :] = [34, 139, 34]  # Forest green in BGR

# Add some brown disease spots
cv2.circle(test_image, (60, 60), 20, (0, 70, 140), -1)  # Brown spot
cv2.circle(test_image, (150, 100), 15, (0, 80, 150), -1)  # Brown spot
cv2.circle(test_image, (180, 180), 18, (10, 75, 145), -1)  # Brown spot
cv2.circle(test_image, (100, 150), 12, (5, 85, 155), -1)  # Brown spot

# Add some texture
for _ in range(50):
    x = np.random.randint(0, 224)
    y = np.random.randint(0, 224)
    radius = np.random.randint(1, 5)
    color = (np.random.randint(20, 50), np.random.randint(120, 160), np.random.randint(20, 50))
    cv2.circle(test_image, (x, y), radius, color, -1)

# Save the test image
test_image_path = os.path.join(uploads_dir, "test_leaf.jpg")
cv2.imwrite(test_image_path, test_image)
print(f"Test image created: {test_image_path}")
