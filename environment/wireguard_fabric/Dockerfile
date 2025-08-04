FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install python3-dev python3-pip git -y
RUN apt-get install build-essential gcc make iproute2 iputils-ping -y
RUN pip install Cython --break-system-packages

# WireguardPy
RUN git clone https://github.com/arnavdas88/wireguard_py

WORKDIR /wireguard_py
RUN sed -i "s/trunk/v0.0.1-dev0/g" wireguard_py/__init__.py
RUN python3 setup.py sdist
RUN python3 setup.py build_ext --inplace
RUN python3 setup.py build
RUN python3 setup.py install
RUN pip install -e . --break-system-packages

# WireguardFabric
# COPY /workspace/WireGenie/* /wireguard_fabric/
# /workspace/WireGenie/environment/wireguard_fabric
COPY ./ /fabric
WORKDIR /fabric
RUN pip install -e . --break-system-packages

# ENTRYPOINT [ "python3", "-m", "fastapi", "run", "--host", "0.0.0.0", "--port", "8000", "src/wire_fabric/daemon/server.py" ]
# ENTRYPOINT [ "python3", "-m", "wire_fabric", "management-server", "--name", "venus", "--port", "8001", "--network", "10.0.0.0/24", "--public-ip", "127.0.0.1"]
