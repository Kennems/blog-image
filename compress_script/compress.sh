# Linux
sudo apt-get install imagemagick

# - `-quality 70%`: 调整压缩质量（数值越低压缩率越高）。
# - **注意**：此命令会直接覆盖原文件，建议先备份！
mogrify -format jpg -path 原文件夹路径 -quality 70% *.jpg