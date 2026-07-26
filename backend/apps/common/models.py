"""
common 应用模型入口
导入分散在独立文件中的模型，使 Django 迁移系统能检测到它们。
"""
# 动态流模型（独立文件，避免与既有模块迁移冲突）
from .activity_models import Activity  # noqa: F401
# 敏感操作确认（N37）
from .confirmation_models import SensitiveConfirmation  # noqa: F401
# 多团队支持（N40）
from .team_models import Team, TeamMember, TeamMembershipEvent  # noqa: F401
# 审批流程（N41）
from .approval_models import ApprovalFlow, ApprovalRequest  # noqa: F401
# 自定义表单（N42）
from .form_models import CustomForm, FormSubmission  # noqa: F401
# 前端错误日志（N57 错误监控）
from .error_models import ErrorLog  # noqa: F401
