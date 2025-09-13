# Linux
sudo apt-get install imagemagick
sudo apt-get install gifsicle

# - `-quality 70%`: 调整压缩质量（数值越低压缩率越高）。
# - **注意**：此命令会直接覆盖原文件，建议先备份！
mogrify -format jpg -path ./ -quality 70% *.jpg
mogrify -format jpeg -path ./ -quality 70% *.jpeg
mogrify -format png -path ./ -quality 70% *.png

# 压缩gif
for file in *.gif; do
    gifsicle -O3 --lossy=80 "$file" -o "${file}.tmp" && mv "${file}.tmp" "$file"
done
