"""TK-002: `make dev-up` / `make dev-down` for the local stack.

Brings up the fake API (+ Garage as the S3-compatible R2 stand-in) via
docker compose, waits until /healthz answers, then bootstraps a single-node
Garage layout, bucket, and dev key. No Cloudflare account, no GPU needed.
"""

import re
import subprocess
import sys
import time
import urllib.request

ROOT_COMPOSE = "infra/compose.local.yaml"
API_HEALTH = "http://localhost:8000/healthz"

S3_BUCKET = "beosabasi-dev"
S3_KEY_ID = "beosabasidevkey01"
S3_KEY_SECRET = "beosabasidevsecret000000000000000001"
S3_REGION = "garage"
S3_ENDPOINT = "http://localhost:3900"


def sh(*args, capture=False):
    print(f"+ {' '.join(args)}")
    if capture:
        out = subprocess.run(args, capture_output=True, text=True)
        return out.returncode, (out.stdout or "") + (out.stderr or "")
    return subprocess.run(args).returncode


def compose(*args, capture=False):
    return sh("docker", "compose", "-f", ROOT_COMPOSE, *args, capture=capture)


def garage(*args):
    """Run a garage admin command inside the s3 container."""
    return compose("exec", "-T", "s3", "/garage", "-c", "/etc/garage.toml",
                   *args, capture=True)


def wait_for_api(retries=30):
    for _ in range(retries):
        try:
            with urllib.request.urlopen(API_HEALTH, timeout=3) as resp:
                if resp.status == 200:
                    print("[dev-up] API sehat di http://localhost:8000")
                    return 0
        except Exception:
            time.sleep(2)
    print("[dev-up] API tidak menjawab /healthz. Lihat log kontainer api.")
    return 1


def wait_for_garage(retries=30):
    for _ in range(retries):
        code, out = garage("status")
        if code == 0 and "HEALTHY" in out:
            return out
        time.sleep(2)
    print("[dev-up] Garage tidak sehat. Lihat log kontainer s3.")
    return ""


def bootstrap_s3():
    status = wait_for_garage()
    if not status:
        return 1
    node_ids = re.findall(r"\b[0-9a-f]{16}\b", status)
    if not node_ids:
        print("[dev-up] ID node Garage tidak ditemukan di `garage status`.")
        return 1
    node_id = node_ids[0]
    code, show = garage("layout", "show")
    if code != 0 or "No nodes currently have a role" in show:
        garage("layout", "assign", "-z", "dc1", "-c", "10G", node_id)
        code, out = garage("layout", "apply", "--version", "1")
        if code != 0 and "already" not in out.lower() and "version" not in out.lower():
            print(f"[dev-up] layout apply gagal:\n{out}")
            return 1
    code, buckets = garage("bucket", "list")
    if code == 0 and S3_BUCKET not in buckets:
        code, out = garage("bucket", "create", S3_BUCKET)
        if code != 0:
            print(f"[dev-up] bucket create gagal:\n{out}")
            return 1
    code, keys = garage("key", "list")
    if code == 0 and S3_KEY_ID not in keys:
        code, out = garage("key", "import", "--yes", "-n", "beosabasi-dev",
                           S3_KEY_ID, S3_KEY_SECRET)
        if code != 0 and "exists" not in out.lower():
            print(f"[dev-up] key import gagal:\n{out}")
            return 1
    code, out = garage("bucket", "allow", "--read", "--write", "--owner",
                       S3_BUCKET, "--key", S3_KEY_ID)
    if code != 0:
        print(f"[dev-up] bucket allow gagal:\n{out}")
        return 1
    print("[dev-up] S3 lokal siap:")
    print(f"  endpoint={S3_ENDPOINT} region={S3_REGION} bucket={S3_BUCKET}")
    print(f"  key_id={S3_KEY_ID} (sekret dev hanya untuk laptop ini)")
    return 0


def main(argv):
    if "--down" in argv:
        return compose("down")
    if sh("docker", "info", "--format", "{{.ServerVersion}}") != 0:
        print("[dev-up] Docker tidak tersedia. Pasang Docker Desktop dulu.")
        return 1
    api_only = "--api-only" in argv
    services = ["api"] if api_only else []
    if compose("up", "-d", "--build", *services) != 0:
        return 1
    if wait_for_api() != 0:
        return 1
    if api_only:
        print("[dev-up] mode api-only: S3 dilewati.")
        return 0
    return bootstrap_s3()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
