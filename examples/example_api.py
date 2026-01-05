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

if __name__ == "__main__":
    test_create_interface()
    test_verify_interface()
    test_delete_interface()
