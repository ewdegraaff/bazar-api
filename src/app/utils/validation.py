import uuid

def is_valid_uuid(uuid_string: str) -> bool:
    try:
        val = uuid.UUID(uuid_string, version=4)
    except ValueError:
        return False
    return str(val) == uuid_string

