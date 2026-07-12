"""
群机器人推送服务
统一管理企业微信/Webhook/邮件多渠道消息推送
支持按事件类型自动选择推送渠道
"""
import logging

from django.conf import settings

from apps.integrations.models import IntegrationConfig
from .wecom import WecomProvider
from .webhook import WebhookProvider

logger = logging.getLogger('apps.integrations')


class BotPushService:
    """
    群机器人推送服务
    根据事件类型和配置，自动选择渠道推送消息
    """

    # Provider 类映射
    PROVIDER_CLASSES = {
        'wecom': WecomProvider,
        'webhook': WebhookProvider,
    }

    @classmethod
    def get_provider(cls, config: IntegrationConfig):
        """获取 Provider 实例"""
        provider_class = cls.PROVIDER_CLASSES.get(config.provider)
        if not provider_class:
            logger.warning('未知的 Provider 类型: %s', config.provider)
            return None
        return provider_class(config)

    @classmethod
    def push_to_all_active(cls, event_type: str, title: str, content: str,
                           markdown: str = None, text: str = None) -> dict:
        """
        向所有已启用的集成配置推送消息
        :param event_type: 事件类型
        :param title: 消息标题
        :param content: 消息正文
        :param markdown: Markdown 格式消息（可选）
        :param text: 纯文本消息（可选）
        :return: {'total': N, 'success': N, 'failed': N}
        """
        payload = {
            'title': title,
            'content': content,
        }
        if markdown:
            payload['markdown'] = markdown
        if text:
            payload['text'] = text

        configs = IntegrationConfig.objects.filter(is_active=True)
        total = configs.count()
        success = 0
        failed = 0

        for config in configs:
            provider = cls.get_provider(config)
            if not provider:
                failed += 1
                continue

            try:
                # 使用配置中的 webhook_url 作为 target
                target = config.config.get('webhook_url', '')
                log = provider.send(event_type, target, payload)
                if log.status == 'success':
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.exception('推送消息到 %s 失败: %s', config.provider, e)
                failed += 1

        logger.info('群机器人推送完成: 事件=%s, 总计=%d, 成功=%d, 失败=%d',
                     event_type, total, success, failed)
        return {'total': total, 'success': success, 'failed': failed}

    @classmethod
    def push_task_reminder(cls, task_title: str, assignee_name: str,
                           project_name: str, deadline: str) -> dict:
        """推送任务延期提醒"""
        title = f'任务延期提醒: {task_title}'
        content = f'任务「{task_title}」已逾期\n负责人: {assignee_name}\n项目: {project_name}\n截止: {deadline}'
        markdown = f'### 任务延期提醒\n> **任务**: {task_title}\n> **负责人**: {assignee_name}\n> **项目**: {project_name}\n> **截止时间**: {deadline}\n> 请尽快处理'
        return cls.push_to_all_active('task_overdue', title, content, markdown=markdown)

    @classmethod
    def push_contribution_reminder(cls, project_name: str, count: int) -> dict:
        """推送贡献待审核提醒"""
        title = f'贡献记录待审核: {project_name}'
        content = f'项目「{project_name}」有 {count} 条贡献记录待审核'
        markdown = f'### 贡献记录待审核\n> **项目**: {project_name}\n> **待审核数**: {count} 条\n> 请尽快登录系统审核'
        return cls.push_to_all_active('contribution_pending', title, content, markdown=markdown)

    @classmethod
    def push_competition_reminder(cls, comp_name: str, level: str,
                                  date_type: str, date_val: str) -> dict:
        """推送比赛关键节点提醒"""
        title = f'比赛节点提醒: {comp_name}'
        content = f'比赛「{comp_name}」({level}) {date_type}: {date_val}'
        markdown = f'### 比赛节点提醒\n> **比赛**: {comp_name}\n> **级别**: {level}\n> **{date_type}**: {date_val}'
        return cls.push_to_all_active('competition_milestone', title, content, markdown=markdown)

    @classmethod
    def push_sensitive_request(cls, applicant: str, data_title: str) -> dict:
        """推送敏感资料审批提醒"""
        title = '敏感资料审批提醒'
        content = f'{applicant} 申请访问「{data_title}」，请尽快审批'
        markdown = f'### 敏感资料审批提醒\n> **申请人**: {applicant}\n> **申请内容**: {data_title}\n> 请尽快登录系统审批'
        return cls.push_to_all_active('sensitive_request', title, content, markdown=markdown)

    @classmethod
    def push_custom_message(cls, title: str, content: str,
                            markdown: str = None) -> dict:
        """推送自定义消息"""
        return cls.push_to_all_active('custom', title, content, markdown=markdown)
