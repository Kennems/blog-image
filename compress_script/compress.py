from PIL import Image
import os

input_folder = "你的图片文件夹路径"
quality = 70  # 压缩质量（1-100）

for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filepath = os.path.join(input_folder, filename)
        img = Image.open(filepath)
        img.save(filepath, optimize=True, quality=quality)