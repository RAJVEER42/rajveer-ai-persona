"""Deploy the backend to a HuggingFace Docker Space.

Usage:
    HF_WRITE_TOKEN=hf_xxx python deploy_hf.py [space_name]

Creates (or updates) the Space, uploads the backend, and sets the runtime
HF_TOKEN secret (inference) — plus CALCOM_* if present in the local .env.
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

from huggingface_hub import HfApi, add_space_secret, create_repo, upload_folder

HERE = Path(__file__).resolve().parent


def _env(key: str) -> str:
    env = (HERE / ".env").read_text() if (HERE / ".env").exists() else ""
    m = re.search(rf'^{key}=(\S+)', env, re.M)
    return m.group(1) if m else os.getenv(key, "")


def main() -> None:
    write_token = (os.getenv("HF_WRITE_TOKEN") or os.getenv("HF_TOKEN_WRITE")
                   or _env("HF_WRITE_TOKEN"))
    if not write_token:
        sys.exit("Set HF_WRITE_TOKEN in env or backend/.env (needs WRITE permission).")

    api = HfApi(token=write_token)
    user = api.whoami()["name"]
    space_name = sys.argv[1] if len(sys.argv) > 1 else "rajveer-ai-representative"
    repo_id = f"{user}/{space_name}"
    print(f"Target Space: {repo_id}")

    create_repo(repo_id, repo_type="space", space_sdk="docker",
                token=write_token, exist_ok=True)

    # README.md must carry the HF Space metadata header.
    (HERE / "README.md").write_text((HERE / "space_readme.md").read_text())

    upload_folder(
        repo_id=repo_id, repo_type="space", folder_path=str(HERE),
        token=write_token,
        ignore_patterns=[".env", ".venv/*", "**/__pycache__/*", "*.pyc",
                         "space_readme.md", "deploy_hf.py", "test_*.py",
                         "app/data/index/*"],  # index is rebuilt at image build
    )

    # runtime secrets
    runtime_token = _env("HF_TOKEN") or write_token
    add_space_secret(repo_id, "HF_TOKEN", runtime_token, token=write_token)
    for k in ("CALCOM_API_KEY", "CALCOM_EVENT_TYPE_ID", "LLM_MODEL"):
        v = _env(k)
        if v:
            add_space_secret(repo_id, k, v, token=write_token)

    print(f"\nDeployed. Building at: https://huggingface.co/spaces/{repo_id}")
    print(f"Live URL (after build): https://{user.lower()}-{space_name}.hf.space")


if __name__ == "__main__":
    main()
