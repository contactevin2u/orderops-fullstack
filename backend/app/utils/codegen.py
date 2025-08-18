from datetime import datetime

def generate_order_code(numeric_id: int) -> str:
    # KP + YYMM + 6-digit id
    yymm = datetime.now().strftime("%y%m")
    return f"KP{yymm}{numeric_id:06d}"
