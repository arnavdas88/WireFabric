PYTHON_ENV="/usr/bin/env /home/codespace/.python/current/bin/python"

CWD="$PWD"

# Installs Cython for WireguardPy Compilation
$PYTHON_ENV -m pip install Cython --break-system-packages

# Downloads WireguardPy
cd /tmp/ && git clone https://github.com/arnavdas88/wireguard_py

# Installs WireguardPy
cd /tmp/wireguard_py && \
sed -i "s/trunk/v0.0.1-dev0/g" wireguard_py/__init__.py && \
$PYTHON_ENV setup.py sdist && \
$PYTHON_ENV setup.py build_ext --inplace && \
$PYTHON_ENV setup.py build && \
$PYTHON_ENV setup.py install && \
$PYTHON_ENV -m pip install -e . --break-system-packages

# Installs WireFabric
cd $CWD && $PYTHON_ENV -m pip install -e . --break-system-packages