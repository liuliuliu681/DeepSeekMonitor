import logging
import time

import requests

logger = logging.getLogger("deepseek-monitor")


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
                logger.info("余额查询成功")
                return {
                    "success": True,
                    "is_available": data.get("is_available", False),
                    "balance_infos": data.get("balance_infos", []),
                }
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            logger.warning("余额查询 %s (第 %d 次): %s", url, attempt + 1, last_error)
        except requests.exceptions.Timeout:
            last_error = "请求超时"
            logger.warning("余额查询超时 (第 %d 次, timeout=%ds)", attempt + 1, timeout)
        except requests.exceptions.ConnectionError:
            last_error = "网络连接失败"
            logger.warning("余额查询网络连接失败 (第 %d 次)", attempt + 1)
        except Exception as e:
            last_error = str(e)
            logger.error("余额查询异常 (第 %d 次): %s", attempt + 1, e)

        if attempt < 2:
            time.sleep(2**attempt)

    logger.error("余额查询最终失败: %s", last_error)
    return {"success": False, "error": last_error}
