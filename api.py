import time

import requests


def fetch_balance(api_key, base_url, endpoint, timeout=10):
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_error = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "is_available": data.get("is_available", False),
                    "balance_infos": data.get("balance_infos", []),
                }
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            last_error = "请求超时"
        except requests.exceptions.ConnectionError:
            last_error = "网络连接失败"
        except Exception as e:
            last_error = str(e)

        if attempt < 2:
            time.sleep(2**attempt)

    return {"success": False, "error": last_error}
