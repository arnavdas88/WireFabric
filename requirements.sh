sudo apt install python3-dev -y

git clone https://github.com/arnavdas88/wireguard_py
cd wireguard_py
/usr/bin/env /home/gitpod/.pyenv/shims/python -m pip install Cython
sed -i "s/trunk/v0.0.1-dev0/g" wireguard_py/__init__.py
/usr/bin/env /home/gitpod/.pyenv/shims/python setup.py sdist
/usr/bin/env /home/gitpod/.pyenv/shims/python setup.py build_ext --inplace
/usr/bin/env /home/gitpod/.pyenv/shims/python setup.py build
/usr/bin/env /home/gitpod/.pyenv/shims/python setup.py install
/usr/bin/env /home/gitpod/.pyenv/shims/python -m pip install -e .