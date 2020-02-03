FROM tensorflow/tensorflow:latest-py3

ARG USERNAME=paraglidable
RUN useradd -m $USERNAME
ENV HOME /home/$USERNAME

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get install -y --no-install-recommends net-tools libopenjp2-7-dev libpng-dev libpng16-16 vim sass wget qt5-default pdf2svg apache2 php libapache2-mod-php nodejs npm ibgeos-3.6.2 libgeos-dev unzip

# grib
RUN apt-get -y update && apt-get install -y --no-install-recommends libgrib-api-dev libgrib-api0
RUN apt-get -y update && apt-get install -y --no-install-recommends libeccodes-dev libeccodes0

# tex2svg
RUN npm install -y --no-install-recommends --global mathjax-node-cli

# Add sudo support
RUN apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME


USER $USERNAME

RUN sudo pip install glob3 tqdm colorama requests pandas matplotlib pillow numba pyproj jupyter
RUN sudo pip install pygrib
RUN sudo pip install https://github.com/matplotlib/basemap/archive/master.zip

