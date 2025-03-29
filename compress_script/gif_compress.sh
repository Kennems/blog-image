#!/bin/bash
# 设置错误日志文件
LOGFILE="error.log"
# 将标准错误输出重定向到日志文件
exec 2>>"$LOGFILE"

# 检查 gifsicle 是否已安装
if ! command -v gifsicle &> /dev/null; then
    echo "错误：gifsicle 未安装，请先安装该工具。" >&2
    exit 1
fi

# 开启 nullglob 以确保没有匹配时不会执行循环
shopt -s nullglob
files=(*.gif)
if [ ${#files[@]} -eq 0 ]; then
    echo "没有找到 GIF 文件。"
    exit 0
fi

# 定义压缩函数
compress_gif() {
    local file="$1"
    echo "正在处理文件：$file"
    local orig_size
    orig_size=$(stat -c %s "$file")
    echo "压缩前大小：$orig_size 字节"
    
    # 使用 gifsicle 进行压缩并输出到临时文件
    if gifsicle -O3 --lossy=80 --colors 256 "$file" -o "${file}.tmp"; then
        if mv "${file}.tmp" "$file"; then
            local new_size
            new_size=$(stat -c %s "$file")
            echo "压缩后大小：$new_size 字节"
            local saved=$((orig_size - new_size))
            local percent=0
            if [ $orig_size -gt 0 ]; then
                percent=$(( 100 * saved / orig_size ))
            fi
            echo "节省：$saved 字节，约 ${percent}%"
        else
            echo "移动临时文件失败：$file" >&2
            rm -f "${file}.tmp"
        fi
    else
        echo "压缩失败：$file" >&2
        rm -f "${file}.tmp"
    fi
    echo "-----------------------------"
}

# ===== 顺序处理所有 GIF 文件 =====
for file in "${files[@]}"; do
    compress_gif "$file"
done

# ===== 可选：并行处理方案 =====
# 如果文件较多，可启用并行处理以提高效率。
# 注意：并行处理时日志输出可能会混杂，如需精确日志记录可调整方案。
# export -f compress_gif
# printf "%s\n" "${files[@]}" | xargs -n 1 -P 4 -I {} bash -c 'compress_gif "$@"' _ {}
