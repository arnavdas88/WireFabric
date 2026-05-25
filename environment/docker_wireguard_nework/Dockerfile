FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install python3-dev python3-pip git -y
RUN apt-get install build-essential gcc make iproute2 iputils-ping iptables -y
RUN pip install Cython --break-system-packages
RUN pip install setuptools --break-system-packages
RUN apt-get install wireguard wireguard-tools -y

RUN git clone https://github.com/arnavdas88/wireguard_py

WORKDIR /wireguard_py
RUN sed -i "s/trunk/v0.0.1-dev0/g" wireguard_py/__init__.py
RUN python3 setup.py sdist
RUN python3 setup.py build_ext --inplace
RUN python3 setup.py build
RUN python3 setup.py install
RUN pip install -e . --break-system-packages

WORKDIR /config

ENTRYPOINT [ "python3", "sample.py" ]