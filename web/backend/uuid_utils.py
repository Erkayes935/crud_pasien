# Utilitas UUID untuk backend
import uuid

def generate_uuid() -> str:
	"""Generate UUID4 string."""
	return str(uuid.uuid4())

def is_valid_uuid(val: str) -> bool:
	"""Cek apakah string adalah UUID valid."""
	try:
		uuid.UUID(val)
		return True
	except Exception:
		return False
