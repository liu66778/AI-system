"""
Git 自动提交模块
每次记录学习后自动 git commit + push
"""
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # AI-system/


def auto_commit(message=None):
    """git add + commit + push，返回 (success: bool, message: str)"""
    if not (BASE_DIR / ".git").exists():
        return False, "不是 git 仓库"

    try:
        if not message:
            message = f"📝 学习记录更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # git add
        result = subprocess.run(
            ["git", "add", "."],
            cwd=str(BASE_DIR),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, f"git add 失败：{result.stderr.strip()}"

        # git commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(BASE_DIR),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout + result.stderr:
                return True, "没有新内容"
            return False, f"git commit 失败：{result.stderr.strip()}"

        # git push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(BASE_DIR),
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"git push 失败：{result.stderr.strip()}"

        return True, "已推送到 GitHub ✅"

    except subprocess.TimeoutExpired:
        return False, "Git 操作超时"
    except FileNotFoundError:
        return False, "未安装 git"
    except Exception as e:
        return False, f"Git 出错：{e}"
