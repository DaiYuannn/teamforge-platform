"""
通用 Webhook 通知 Provider
支持向任意 Webhook URL 发送 JSON 格式的通知消息
可用于对接钉钉、飞书(自定义)、Slack 等
"""
import json
import logging

import requests
from django.utils import timezone

from .base import BaseNotificationProvider
from apps.integrations.models import IntegrationLog

logger = logging.getLogger('apps.integrations')


class WebhookProvider(BaseNotificationProvider):
    """通用 Webhook 通知 Provider"""

    def send(self, event_type: str, target: str, payload: dict) -> IntegrationLog:
        """
        发送 Webhook 消息
        :param event_type: 事件类型
        :param target: Webhook URL（或使用 config 中配置的 webhook_url）
        :param payload: 消息内容
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
                error_message='未配置 Webhook URL',
            )
            return log

        # 构造统一格式的消息体
        message = {
            'event_type': event_type,
            'title': payload.get('title', '团队管理通知'),
            'content': payload.get('content', ''),
            'timestamp': timezone.now().isoformat(),
            'source': 'team_management_system',
            'data': payload,
        }

        # 如果有自定义 headers
        headers = {'Content-Type': 'application/json'}
        custom_headers = self.config.config.get('headers', {})
        if custom_headers:
            headers.update(custom_headers)

        try:
            resp = requests.post(
                webhook_url,
                json=message,
                timeout=10,
                headers=headers,
            )

            if resp.status_code in [200, 201, 202, 204]:
                try:
                    result = resp.json()
                except Exception:
                    result = {'status_code': resp.status_code, 'text': resp.text[:500]}

                log = IntegrationLog.objects.create(
                    config=self.config,
                    provider=self.config.provider,
                    event_type=event_type,
                    target=target,
                    payload=payload,
                    status='success',
                    response_data=result,
                )
                logger.info('Webhook 消息发送成功: %s -> %s', event_type, webhook_url[:50])
            else:
                log = IntegrationLog.objects.create(
                    config=self.config,
                    provider=self.config.provider,
                    event_type=event_type,
                    target=target,
                    payload=payload,
                    status='failed',
                    error_message=f'HTTP {resp.status_code}: {resp.text[:200]}',
                )
                logger.warning('Webhook 消息发送失败: HTTP %s', resp.status_code)
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
            logger.exception('Webhook 消息发送异常: %s', e)

        return log

    def validate_config(self) -> bool:
        """校验 Webhook URL 是否有效"""
        webhook_url = self.config.config.get('webhook_url', '')
        if not webhook_url:
            return False
        return webhook_url.startswith('http://') or webhook_url.startswith('https://')
