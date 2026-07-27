"""Canonical choice sets used to keep generated OpenAPI enum names stable."""

from apps.common.error_models import ErrorLog
from apps.competitions.models import Competition
from apps.contributions.models import Contribution
from apps.exports.scheduled_report_models import ScheduledReport
from apps.files.models import FileAsset
from apps.finance.models import FinanceExpense
from apps.imports.models import ImportTask
from apps.intellectual_property.models import IntellectualPropertyApplication
from apps.notifications.models import Notification
from apps.projects.knowledge_models import KnowledgeArticle
from apps.projects.models import Project
from apps.tasks.models import Task


FINANCE_CATEGORY_CHOICES = FinanceExpense.Category.choices
KNOWLEDGE_CATEGORY_CHOICES = KnowledgeArticle.Category.choices
IP_STATUS_CHOICES = IntellectualPropertyApplication.Status.choices
PROJECT_STATUS_CHOICES = Project.Status.choices
COMPETITION_STATUS_CHOICES = Competition.Status.choices
CONTRIBUTION_STATUS_CHOICES = Contribution.Status.choices
SCHEDULED_REPORT_STATUS_CHOICES = ScheduledReport.RunStatus.choices
IMPORT_STATUS_CHOICES = ImportTask.Status.choices
ERROR_LEVEL_CHOICES = ErrorLog.Level.choices
COMPETITION_LEVEL_CHOICES = Competition.Level.choices
FILE_LEVEL_CHOICES = FileAsset.Level.choices
TASK_PRIORITY_CHOICES = Task.Priority.choices
NOTIFICATION_PRIORITY_CHOICES = Notification.Priority.choices
PROJECT_PRIORITY_CHOICES = Project.Priority.choices
TASK_STATUS_CHOICES = Task.Status.choices
PROJECT_STAGE_CHOICES = Project.Stage.choices

# These aggregate/request-only choices do not belong to database models.
REVIEW_DECISION_CHOICES = [('approved', 'approved'), ('rejected', 'rejected')]
OBJECTION_ACTION_CHOICES = [
    ('leader_review', 'leader_review'),
    ('teacher_confirm', 'teacher_confirm'),
]
MATERIAL_CHECK_STATUS_CHOICES = [
    ('complete', 'complete'),
    ('incomplete', 'incomplete'),
    ('missing', 'missing'),
]
