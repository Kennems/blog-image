#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tinify
import argparse
import datetime
from pathlib import Path

# 支持的源文件扩展名（小写）
SUPPORTED_FORMATS = (".png", ".jpg", ".jpeg", ".webp", ".avif")

# MIME -> 扩展名 映射（用于 convert 后调整输出后缀）
MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/avif": "avif",
}

def human_size(num_bytes: int) -> str:
    """把字节数转成人类可读字符串"""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    for unit in ("KB", "MB", "GB", "TB"):
        num_bytes /= 1024.0
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.2f} {unit}"
    return f"{num_bytes:.2f} PB"

def ensure_dir(path: str):
    """确保目录存在"""
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

def parse_resize_arg(resize_str: str):
    """
    resize_str 示例: 'fit:300:200' 或 'cover:800:600'
    返回 dict 或 None
    """
    if not resize_str:
        return None
    try:
        method, w, h = resize_str.split(":")
        return {"method": method, "width": int(w), "height": int(h)}
    except Exception:
        raise ValueError("resize 参数格式错误，应为 METHOD:WIDTH:HEIGHT，例如 fit:300:200")

def parse_after_arg(after_str: str):
    """
    支持三类输入：
      - Unix 时间戳（整数或浮点字符串），例如 1630454400
      - 日期： YYYY-MM-DD
      - 日期时间： YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DDTHH:MM:SS
    返回 POSIX 时间戳（float）
    """
    if not after_str:
        return None
    # 1) 尝试当作数字时间戳
    try:
        return float(after_str)
    except Exception:
        pass

    # 2) 尝试常见日期/日期时间格式
    fmts = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
    for fmt in fmts:
        try:
            dt = datetime.datetime.strptime(after_str, fmt)
            # 对于 naive datetime，timestamp() 按本地时区计算
            return dt.timestamp()
        except Exception:
            continue

    # 3) 作为 ISO 8601 尝试（Python 3.7+ 支持部分）
    try:
        dt = datetime.datetime.fromisoformat(after_str)
        return dt.timestamp()
    except Exception:
        pass

    raise ValueError("无法解析 --after 参数，支持 Unix 时间戳 / YYYY-MM-DD / YYYY-MM-DD HH:MM:SS 格式")

def compress_image(input_path: str, output_path: str | None,
                   resize_options: dict | None, convert_type: str | None):
    """
    压缩单张图片：返回 (success_flag, message)
    """
    try:
        original_size = os.path.getsize(input_path)
    except OSError as e:
        return False, f"无法读取文件大小: {e}"

    try:
        src = tinify.from_file(input_path)

        if resize_options:
            src = src.resize(**resize_options)

        if convert_type:
            src = src.convert(type=convert_type)

        # 获取压缩后的字节流（包含 resize/convert 的效果）
        compressed_bytes = src.to_buffer()
        compressed_size = len(compressed_bytes)

        # 处理输出路径与扩展名
        if output_path:
            # 如果 convert_type 存在，确保输出后缀与 MIME 匹配
            if convert_type:
                ext = MIME_TO_EXT.get(convert_type, None)
                if ext:
                    output_path = os.path.splitext(output_path)[0] + "." + ext
        else:
            # 覆盖原图：如果转换类型，会更改后缀
            if convert_type:
                ext = MIME_TO_EXT.get(convert_type, None)
                if ext:
                    output_path = os.path.splitext(input_path)[0] + "." + ext
                else:
                    output_path = input_path
            else:
                output_path = input_path

        ensure_dir(output_path)

        # 写入文件
        with open(output_path, "wb") as f:
            f.write(compressed_bytes)

        # 获取当月压缩次数（API 返回当前已用次数）
        current_count = tinify.compression_count

        # 输出详情信息
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
        info = (
            f"✅ 压缩成功：{input_path} -> {output_path}\n"
            f"    本次为当月第 {current_count} 次压缩（序号）; 当月已使用 {current_count} 次。\n"
            f"    原始大小: {human_size(original_size)}；压缩后: {human_size(compressed_size)}；节省: {ratio:3.2f}%"
        )
        return True, info

    except tinify.AccountError as e:
        return False, f"❌ APIKey/账户问题: {e.message}"
    except tinify.ClientError as e:
        return False, f"❌ 客户端错误: {e.message}"
    except tinify.ServerError as e:
        return False, f"❌ 服务器错误: {e.message}"
    except tinify.ConnectionError as e:
        return False, f"❌ 网络连接错误: {e.message}"
    except Exception as e:
        return False, f"❌ 未知错误: {str(e)}"

def compress_folder(folder_path: str, output_folder: str | None,
                    resize_options: dict | None, convert_type: str | None,
                    since_ts: float | None = None, time_field: str = "mtime",
                    recursive: bool = True):
    """
    批量压缩目录下图片。若 output_folder 指定则在输出目录中保持相对目录结构。
    time_field: 'mtime' 或 'ctime'，默认为 'mtime'
    since_ts: 若指定，则只处理 modification/creation time >= since_ts 的文件
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        print("❌ 输入路径不是目录或不存在。")
        return

    try:
        start_count = tinify.compression_count
    except Exception:
        start_count = None

    print(f"开始压缩。脚本启动时当月已使用压缩次数: {start_count}")
    if since_ts:
        readable = datetime.datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d %H:%M:%S")
        print(f"只会压缩 {time_field} 在 {readable}（含） 之后的文件（时间基于本机时区）")

    total_files = 0
    skipped = 0
    success_count = 0
    fail_count = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if not file.lower().endswith(SUPPORTED_FORMATS):
                continue
            input_path = os.path.join(root, file)

            # 时间过滤
            if since_ts:
                try:
                    if time_field == "ctime":
                        file_ts = os.path.getctime(input_path)
                    else:
                        file_ts = os.path.getmtime(input_path)
                except Exception:
                    # 若无法读取时间，则跳过
                    skipped += 1
                    print(f"跳过（无法读取时间）: {input_path}")
                    continue

                if file_ts < since_ts:
                    skipped += 1
                    continue

            total_files += 1

            # 计算相对路径并在 output_folder 下保持结构
            if output_folder:
                rel = os.path.relpath(root, folder_path)
                out_dir = os.path.join(output_folder, rel)
                os.makedirs(out_dir, exist_ok=True)
                output_path = os.path.join(out_dir, file)
            else:
                output_path = None  # 覆盖原文件或根据 convert 更改扩展

            success, message = compress_image(input_path, output_path, resize_options, convert_type)
            if success:
                success_count += 1
                print(message)
            else:
                fail_count += 1
                print(message)

        if not recursive:
            break

    try:
        final_count = tinify.compression_count
    except Exception:
        final_count = None

    print("=== 处理完成 ===")
    print(f"总文件数(符合时间和格式)：{total_files}，成功：{success_count}，失败：{fail_count}，跳过（时间不满足或错误）：{skipped}")
    print(f"脚本结束时当月已使用压缩次数: {final_count}")

def main():
    parser = argparse.ArgumentParser(description="Tinify 批量压缩脚本（支持 resize / convert / 保留目录结构 / 时间过滤）")
    parser.add_argument("--input", "-i", required=True, help="输入文件夹或单个文件路径")
    parser.add_argument("--output", "-o", default=None, help="输出文件夹（可选），不填则覆盖原图或在同目录生成转换后文件")
    parser.add_argument("--resize", "-r", default=None,
                        help="可选 resize 参数，例如 fit:300:200 或 cover:800:600")
    parser.add_argument("--convert", "-c", default=None,
                        help='可选格式转换，使用 MIME 类型，例如 "image/webp" 或 "image/png"')
    parser.add_argument("--key", "-k", default=None, help="Tinify API Key，若不提供则读取环境变量 TINIFY_API_KEY")
    parser.add_argument("--no-recursive", action="store_true", help="仅处理当前目录，不递归子目录")
    parser.add_argument("--after", "-a", default=None,
                        help="只处理指定时间之后的文件。支持 Unix 时间戳，或 'YYYY-MM-DD' / 'YYYY-MM-DD HH:MM:SS' 格式")
    parser.add_argument("--time-field", choices=("mtime", "ctime"), default="mtime",
                        help="以哪个时间字段作为过滤基准（修改时间 mtime 或 创建时间 ctime），默认 mtime")
    args = parser.parse_args()

    api_key = args.key or os.environ.get("TINIFY_API_KEY")
    if not api_key:
        print("❌ 未提供 Tinify API Key。请通过 --key 或 环境变量 TINIFY_API_KEY 提供。")
        return
    tinify.key = api_key

    resize_options = parse_resize_arg(args.resize) if args.resize else None
    convert_type = args.convert
    since_ts = None
    if args.after:
        try:
            since_ts = parse_after_arg(args.after)
        except ValueError as e:
            print(f"❌ 解析 --after 参数失败: {e}")
            return

    input_path = args.input
    if os.path.isfile(input_path):
        # 单文件处理（针对单文件也支持时间过滤）
        if since_ts:
            try:
                file_ts = os.path.getmtime(input_path) if args.time_field == "mtime" else os.path.getctime(input_path)
                if file_ts < since_ts:
                    print(f"📎 单文件的 {args.time_field} 时间早于指定阈值，跳过：{input_path}")
                    return
            except Exception:
                print(f"❌ 无法读取文件时间，跳过：{input_path}")
                return

        output_path = args.output
        success, msg = compress_image(input_path, output_path, resize_options, convert_type)
        print(msg)
    else:
        # 目录处理
        compress_folder(input_path, args.output, resize_options, convert_type,
                        since_ts=since_ts, time_field=args.time_field, recursive=not args.no_recursive)

if __name__ == "__main__":
    main()
# 使用方法
# python tinify_batch.py -i ./pics -o ./out --after "2025-09-01"
# python tinify_batch.py -i ./pics -o ./out --after "2025-09-01 12:30:00"
# python tinify_batch.py -i ./pics --after 1693526400
# python tinify_batch.py -i ./pics -o ./out --after "2025-09-01" --time-field ctime
