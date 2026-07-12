"""
第三方通知 Provider 抽象基类
具体渠道（企业微信/Webhook/邮件）需继承本类并实现相关方法
"""
from apps.integrations.models import IntegrationConfig, IntegrationLog


class BaseNotificationProvider:
    """第三方通知 Provider 抽象基类"""

    def __init__(self, config: IntegrationConfig):
        """
        :param config: 集成配置实例
        """
        self.config = config

    def send(self, event_type: str, target: str, payload: dict) -> IntegrationLog:
        """
        发送通知，子类需实现具体逻辑
        :param event_type: 事件类型
        :param target: 发送对象
        :param payload: 发送内容
        :return: IntegrationLog 实例
        """
        raise NotImplementedError

    def validate_config(self) -> bool:
        """
        验证配置是否有效，子类需实现具体校验逻辑
        :return: 配置是否有效
        """
        raise NotImplementedError
