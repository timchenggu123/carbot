# Dockerfile

FROM ros:humble

RUN apt update && apt install -y \
    python3-opencv \
    ros-humble-cv-bridge \
    python3-pip \
    && pip install websockets

# (Optional) Install other ROS2 packages or tools here

WORKDIR /ros2_ws

COPY ros2_ws/src/ src/

# Build ROS2 workspace
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install"

# Source environment on shell start
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /ros2_ws/install/setup.bash" >> ~/.bashrc

# Set the ROS_DOMAIN_ID and RMW_IMPLEMENTATION environment variables
ENV ROS_DOMAIN_ID=42
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Default to interactive shell
CMD ["bash"]




