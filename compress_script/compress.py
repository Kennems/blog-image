from PIL import Image
import os
import logging
import shutil


# 配置日志，输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "./compress_script/compress_errors.log", mode="w", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)


def format_size(size_bytes):
    """将字节数转换为合适的单位显示"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f}TB"


def compress_image(filepath, quality=70):
    try:
        img = Image.open(filepath)
    except Exception as e:
        logging.error(f"无法打开 {filepath}，错误：{e}")
        return

    # 跳过 GIF 文件
    if img.format.upper() == "GIF":
        logging.info(f"跳过 GIF 文件：{filepath}")
        return

    temp_filepath = filepath + ".tmp"
    try:
        if img.format.upper() in ("JPEG", "JPG"):
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(
                temp_filepath, "JPEG", quality=quality, optimize=True, progressive=True
            )
        elif img.format.upper() == "PNG":
            if "A" in img.getbands():
                img.save(temp_filepath, "PNG", optimize=True, compress_level=9)
            else:
                img = img.convert("RGB")
                img = img.quantize(method=Image.MEDIANCUT)
                img.save(temp_filepath, "PNG", optimize=True, compress_level=9)
        else:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(temp_filepath, optimize=True, quality=quality)

        # 比较文件大小，如果压缩后文件更大则不替换
        original_size = os.path.getsize(filepath)
        new_size = os.path.getsize(temp_filepath)
        if new_size < original_size:
            shutil.move(temp_filepath, filepath)
            logging.info(f"{filepath} 压缩成功，新大小：{format_size(new_size)}")
        else:
            os.remove(temp_filepath)
            logging.info(f"{filepath} 压缩后反而更大，保留原文件。")
    except Exception as e:
        logging.error(f"处理 {filepath} 时出现错误：{e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)


def main():
    input_folder = "./"  # 启动脚本所在目录
    quality = 70  # 压缩质量（1-100）

    logging.info(f"当前工作目录：{os.getcwd()}")
    try:
        files = os.listdir(input_folder)
        logging.info(f"目标文件夹中的文件：{files}")
    except Exception as e:
        logging.error(f"无法列出目录 {input_folder} 中的文件，错误：{e}")
        return

    for filename in files:
        # 仅处理png、jpg、jpeg类型的文件，跳过gif
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            filepath = os.path.join(input_folder, filename)
            try:
                original_size = os.path.getsize(filepath)
            except Exception as e:
                logging.error(f"获取 {filepath} 大小时出错：{e}")
                continue
            logging.info(f"正在处理 {filename}，原始大小：{format_size(original_size)}")

            compress_image(filepath, quality=quality)

            try:
                new_size = os.path.getsize(filepath)
                logging.info(
                    f"{filename} 处理完成，压缩后大小：{format_size(new_size)}\n"
                )
            except Exception as e:
                logging.error(f"获取 {filepath} 压缩后大小时出错：{e}")


if __name__ == "__main__":
    main()
