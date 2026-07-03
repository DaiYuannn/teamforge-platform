"""
QQ 机器人通知 Provider（预留实现）
"""
from .base import BaseNotificationProvider


class QQBotProvider(BaseNotificationProvider):
    """QQ 机器人通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict):
        # 预留：对接 QQ 机器人开放接口
        raise NotImplementedError

    def validate_config(self) -> bool:
        # 预留：校验 app_id 与密钥是否齐全
        raise NotImplementedError
