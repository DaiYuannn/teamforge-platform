"""
企业微信机器人通知 Provider（预留实现）
"""
from .base import BaseNotificationProvider


class WecomProvider(BaseNotificationProvider):
    """企业微信通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict):
        # 预留：对接企业微信群机器人 Webhook 接口
        raise NotImplementedError

    def validate_config(self) -> bool:
        # 预留：校验企业微信 webhook_url 是否有效
        raise NotImplementedError
