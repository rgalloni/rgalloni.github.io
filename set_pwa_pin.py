import argparse
import base64
import hashlib
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Set fixed 6-digit PIN hash for PWA")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pin", help="6-digit PIN")
    source.add_argument("--pin-env", help="Environment variable name containing the 6-digit PIN")
    parser.add_argument("--iterations", type=int, default=250000, help="PBKDF2 iterations")
    args = parser.parse_args()

    if args.pin_env:
        raw = os.environ.get(args.pin_env, "")
    else:
        raw = args.pin or ""

    pin = raw.strip()
    if not (len(pin) == 6 and pin.isdigit()):
        raise SystemExit("PIN must be exactly 6 digits")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, args.iterations, dklen=32)

    payload = {
        "algorithm": "PBKDF2-SHA256",
        "iterations": args.iterations,
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(digest).decode("ascii"),
    }

    root = Path(__file__).resolve().parents[1]
    out = root / "itinerary" / "data" / "security" / "auth.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
