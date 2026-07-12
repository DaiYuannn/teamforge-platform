"""
第三方集成 Provider 服务包
- base: 抽象基类
- wecom: 企业微信机器人
- webhook: 通用 Webhook
- email: 邮件通知
- bot_push: 群机器人统一推送服务
"""
from .wecom import WecomProvider
from .webhook import WebhookProvider
from .bot_push import BotPushService

__all__ = ['WecomProvider', 'WebhookProvider', 'BotPushService']
