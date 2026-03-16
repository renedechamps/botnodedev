import os
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate temporary RSA keys for testing immediately at import time
# ensuring they are available before any test module imports 'main'
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

os.environ["BOTNODE_JWT_PRIVATE_KEY"] = private_pem
os.environ["BOTNODE_JWT_PUBLIC_KEY"] = public_pem

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    pass
