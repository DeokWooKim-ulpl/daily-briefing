"""pipeline/.env 를 환경변수로 읽어들인다. (로컬 테스트용. GitHub Actions에서는 Secrets가 환경변수로 들어오므로 파일이 없어도 됨)

research.py / enrich.py / build_doc.py / run_all.py 가 모두 import 하므로 어느 스크립트를 단독 실행해도 .env 가 적용된다.
이미 설정된 환경변수는 덮어쓰지 않는다.
"""
from __future__ import annotations

import os
import pathlib

ENV_FILE = pathlib.Path(__file__).resolve().parent / ".env"


def load(path: pathlib.Path = ENV_FILE) -> int:
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
            n += 1
    return n


load()
