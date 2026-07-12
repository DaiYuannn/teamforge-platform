"""
动态流业务服务
提供 log_activity 函数，用于在各类业务操作中记录动态。
"""
from .activity_models import Activity


def log_activity(
    activity_type,
    actor=None,
    project=None,
    target_type='',
    target_id=None,
    description='',
    metadata=None,
):
    """
    记录一条动态

    :param activity_type: 动态类型（Activity.Type 枚举值）
    :param actor: 操作人（User 实例或 None）
    :param project: 关联项目（Project 实例或 None）
    :param target_type: 目标类型（如 'project' / 'task' / 'file'）
    :param target_id: 目标对象 ID
    :param description: 动态描述文本
    :param metadata: 附加元数据（dict）
    :return: 创建的 Activity 实例
    """
    return Activity.objects.create(
        activity_type=activity_type,
        actor=actor,
        project=project,
        target_type=target_type,
        target_id=target_id,
        description=description,
        metadata=metadata or {},
    )
