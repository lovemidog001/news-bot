import requests
import datetime
import os

# ===== 基本設定 =====
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")   # 從 workflow 傳入
OWNER = "YOUR_USERNAME"                    # 改成你的 GitHub 使用者名稱
REPO = "YOUR_REPO"                         # 改成你的 Repo 名稱
DAYS = int(os.getenv("DAYS", "7"))         # 預設刪除 7 天前，可在 cleanup.yml 設定

# ===== 計算截止日期 =====
cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=DAYS)

# ===== 取得所有 workflow runs =====
url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs"
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

runs = requests.get(url, headers=headers).json()

for run in runs.get("workflow_runs", []):
    run_id = run["id"]
    run_created = datetime.datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ")

    if run_created < cutoff_date:
        del_url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}"
        resp = requests.delete(del_url, headers=headers)
        if resp.status_code == 204:
            print(f"✅ Deleted run {run_id} from {run_created}")
        else:
            print(f"⚠️ Failed to delete run {run_id}: {resp.status_code}")
