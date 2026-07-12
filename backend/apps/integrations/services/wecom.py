"""
企业微信机器人通知 Provider
通过企业微信群机器人 Webhook 接口推送消息
"""
import json
import logging

import requests
from django.utils import timezone

from .base import BaseNotificationProvider
from apps.integrations.models import IntegrationLog

logger = logging.getLogger('apps.integrations')


class WecomProvider(BaseNotificationProvider):
    """企业微信通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict) -> IntegrationLog:
        """
        发送企业微信机器人消息
        :param event_type: 事件类型
        :param target: 企业微信机器人 Webhook URL（或 config 中配置的 webhook_url）
        :param payload: 消息内容，支持以下字段：
            - text: 纯文本消息
            - markdown: Markdown 格式消息
            - title: 消息标题
            - content: 消息正文
        :return: IntegrationLog 实例
        """
        webhook_url = target or self.config.config.get('webhook_url', '')
        if not webhook_url:
            log = IntegrationLog.objects.create(
                config=self.config,
                provider=self.config.provider,
                event_type=event_type,
                target=target,
                payload=payload,
                status='failed',
                error_message='未配置企业微信机器人 Webhook URL',
            )
            return log

        # 构造企业微信消息体
        if payload.get('markdown'):
            # Markdown 消息
            message = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': payload['markdown'],
                }
            }
        elif payload.get('text'):
            # 纯文本消息
            message = {
                'msgtype': 'text',
                'text': {
                    'content': payload['text'],
                }
            }
        else:
            # 默认构造 Markdown 消息
            title = payload.get('title', '团队管理通知')
            content = payload.get('content', '')
            message = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': f'### {title}\n> {content}\n> {timezone.now().strftime("%Y-%m-%d %H:%M")}',
                }
            }

        try:
            resp = requests.post(
                webhook_url,
                json=message,
                timeout=10,
                headers={'Content-Type': 'application/json'},
            )
            result = resp.json()

            if resp.status_code == 200 and result.get('errcode') == 0:
                log = IntegrationLog.objects.create(
                    config=self.config,
                    provider=self.config.provider,
                    event_type=event_type,
                    target=target,
                    payload=payload,
                    status='success',
                    response_data=result,
                )
                logger.info('企业微信消息发送成功: %s', event_type)
            else:
                log = IntegrationLog.objects.create(
                    config=self.config,
                    provider=self.config.provider,
                    event_type=event_type,
                    target=target,
                    payload=payload,
                    status='failed',
                    error_message=f'企业微信返回错误: {result}',
                    response_data=result,
                )
                logger.warning('企业微信消息发送失败: %s', result)
        except Exception as e:
            log = IntegrationLog.objects.create(
                config=self.config,
                provider=self.config.provider,
                event_type=event_type,
                target=target,
                payload=payload,
                status='failed',
                error_message=str(e),
            )
            logger.exception('企业微信消息发送异常: %s', e)

        return log

    def validate_config(self) -> bool:
        """校验企业微信 Webhook URL 是否有效"""
        webhook_url = self.config.config.get('webhook_url', '')
        if not webhook_url:
            return False
        return webhook_url.startswith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send')
