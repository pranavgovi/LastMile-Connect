"""Hash and verify passwords with bcrypt (no passlib)."""
import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plain password for storing in DB. Bcrypt limit is 72 bytes."""
    pw_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Check plain password against stored hash."""
    pw_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed.encode("ascii"))
