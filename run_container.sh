sudo docker run -it --rm   --cap-add SYS_RAWIO   --cap-add SYS_ADMIN   --device /dev/i2c-1   --device /dev/spidev0.0  -v .:/src  -v /sys:/sys   -v /dev:/dev   -v /run/udev:/run/udev ros:humble
