# Sample Python file fixture for testing
# 文档缺陷标注：PLAN.md Task 4 需要此文件，应该在 Task 3 中一并说明需要创建此目录

"""
Sample Python file for testing review context loading.
Contains various code patterns for rule analysis.
"""

import time
import requests


async def endpoint(user, fetch_remote):
    """Sample async function with potential issues."""
    time.sleep(1)  # Blocking I/O in async function
    profile = user.profile  # Potential None access
    return fetch_remote()  # Missing await


def resource_leak():
    """Sample function with resource leak."""
    conn = connect()  # Resource not closed
    return conn.query()


def none_access(data):
    """Sample function with None access risk."""
    result = data.get("user")
    return result.profile.name  # result could be None