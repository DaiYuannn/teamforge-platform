"""
飞书机器人通知 Provider（预留实现）
"""
from .base import BaseNotificationProvider


class FeishuProvider(BaseNotificationProvider):
    """飞书通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict):
        # 预留：对接飞书自定义机器人 Webhook 接口
        raise NotImplementedError

    def validate_config(self) -> bool:
        # 预留：校验飞书 webhook_url 与签名密钥是否齐全
        raise NotImplementedError
