import time, os, uuid
from typing import Dict, Optional
from pydantic import BaseModel
from jose import jwt, JWTError
from eth_utils import to_checksum_address
from db import ( get_categories_collection )

SECRET   = os.getenv("SECRET_KEY", "dev-secret-must-be-32-chars-or-more")
ORIGINS  = eval(os.getenv("ORIGINS", '["http://localhost:5173"]'))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_TTL = float(os.getenv("TOKEN_TTL", 86400))
NONCE_TTL = float(os.getenv("NONCE_TTL", 300))

nonces: Dict[str, float] = {} 

# ---------- models ----------
class NonceResp(BaseModel):
    nonce: str

class VerifyReq(BaseModel):
    message: str
    signature: str

class VerifyResp(BaseModel):
    token: str
    role: str

class SessionResp(BaseModel):
    address: str
    chainId: int

# ---------- helpers ----------

def _now() -> float:
    return time.time()


def _clean_nonces():
    now = _now()
    for n, exp in list(nonces.items()):
        if exp < now:
            nonces.pop(n, None)

def _new_nonce() -> str:
    _clean_nonces()
    nonce = uuid.uuid4().hex
    nonces[nonce] = _now() + NONCE_TTL
    return nonce


def _role(address: str) -> str:
    """
    Return 'evaluator' if the address is listed in ANY category's evaluators array.
    """
    if not address:
        return "user"
    address = to_checksum_address(address)          # normalise case
    # scan all categories for the address
    categories_collection = get_categories_collection()
    exists = categories_collection.find_one(
        {"evaluators": address},     # at least one category contains the address
    )
    return "evaluator" if exists else "user"


def _create_token(address: str, role: str) -> str:
    return jwt.encode(
        {"sub": address, "role": role, "exp": int(_now()) + TOKEN_TTL},
        SECRET,
        algorithm=ALGORITHM,
    )


def _verify_token(token: Optional[str]) -> Optional[Dict]:
    if not token:
        return None
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None