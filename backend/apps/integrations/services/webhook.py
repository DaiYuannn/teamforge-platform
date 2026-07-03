"""
通用 Webhook 通知 Provider（预留实现）
"""
from .base import BaseNotificationProvider


class WebhookProvider(BaseNotificationProvider):
    """通用 Webhook 通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict):
        # 预留：向任意 Webhook 地址 POST JSON 数据
        raise NotImplementedError

    def validate_config(self) -> bool:
        # 预留：校验 webhook_url 是否有效
        raise NotImplementedError
