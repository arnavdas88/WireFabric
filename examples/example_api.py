import httpx

BASE_URL = "http://127.0.0.1:8000"
AUTH = ("admin", "adminpass")

def test_create_interface():
    payload = {
        "name": "wf_0",
        "ip": "10.10.0.1",
        "cidr": "10.10.0.0/24",
        "listen_port": 51820,
    }

    with httpx.Client(auth=AUTH) as client:
        r = client.post(f"{BASE_URL}/interfaces", json=payload)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body is not None


def test_verify_interface():
    name = "wf_0"

    with httpx.Client(auth=AUTH) as client:
        r = client.get(f"{BASE_URL}/interfaces/{name}")

    assert r.status_code == 200, r.text
    iface = r.json()

    assert iface["name"] == name
    assert iface["status"] is True
    assert iface["ip"] == "10.10.0.1"
    assert iface["cidr"] == "10.10.0.0/24"
    assert iface["public_key"] is not None


def test_delete_interface():
    name = "wf_0"

    with httpx.Client(auth=AUTH) as client:
        r = client.delete(
            f"{BASE_URL}/interfaces/{name}",
            params={"delete": True},
        )

    assert r.status_code == 200, r.text

    # Verify deletion
    with httpx.Client(auth=AUTH) as client:
        r = client.get(f"{BASE_URL}/interfaces/{name}")

    assert r.status_code == 404


def test_create_route():
    '''
    EXPERIMENTAL
    '''
    payload = {
        "src": None,
        "dst": "10.20.0.0/16",
        "gateway": "10.10.0.1",
        "interface": "wf_0",
        "proto": "static",
        "scope": "universe",
    }

    # Create route
    with httpx.Client(auth=AUTH) as client:
        r = client.post(
            f"{BASE_URL}/routes",
            json=payload,
        )

    assert r.status_code == 200, r.text
    route = r.json()

    assert route["dst"] == "10.20.0.0/16"
    assert route["gateway"] == "10.10.0.1"
    assert route["interface"] == "wf_0"
    assert route["proto"] == "static"
    assert route["scope"] == "universe"
    assert route["is_link"] is False

    # Verify route exists
    with httpx.Client(auth=AUTH) as client:
        r = client.get(f"{BASE_URL}/routes")

    assert r.status_code == 200, r.text
    routes = r.json()

    assert any(
        r["dst"] == "10.20.0.0/16"
        and r["gateway"] == "10.10.0.1"
        and r["interface"] == "wf_0"
        for r in routes
    ), "Route not found in route table"

if __name__ == "__main__":
    test_create_interface()
    test_verify_interface()
    test_create_route()
    test_delete_interface()
