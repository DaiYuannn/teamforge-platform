"""
任务依赖关系模型
单独文件存放，避免与现有 models.py 产生迁移冲突
关键：禁止自依赖、禁止循环依赖
"""
from django.db import models


class TaskDependency(models.Model):
    """任务依赖关系"""

    # 依赖方任务（A 依赖 B，则 A 是 task，B 是 depends_on）
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='dependencies',
        verbose_name='任务',
    )
    # 被依赖的任务
    depends_on = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='dependents',
        verbose_name='依赖任务',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'task_dependencies'
        verbose_name = '任务依赖'
        verbose_name_plural = verbose_name
        # 同一对 (task, depends_on) 唯一
        unique_together = [('task', 'depends_on')]

    def __str__(self):
        return f'{self.task_id} depends on {self.depends_on_id}'

    def clean(self):
        """模型层校验：禁止自依赖"""
        from django.core.exceptions import ValidationError
        if self.task_id == self.depends_on_id:
            raise ValidationError('任务不能依赖自身')

    def save(self, *args, **kwargs):
        """保存前执行校验，并检测循环依赖"""
        from django.core.exceptions import ValidationError

        # 禁止自依赖
        if self.task_id == self.depends_on_id:
            raise ValidationError('任务不能依赖自身')

        # 检测循环依赖：如果 depends_on 已经（直接或间接）依赖 task，则形成环
        if self.task_id and self.depends_on_id:
            if self._creates_cycle(self.task_id, self.depends_on_id):
                raise ValidationError('该依赖关系会形成循环依赖')

        super().save(*args, **kwargs)

    @staticmethod
    def _creates_cycle(task_id, depends_on_id):
        """
        检测添加 task -> depends_on 后是否会形成环。
        即检查从 depends_on 出发能否（间接）到达 task。
        若 depends_on 可到达 task，则再加上 task -> depends_on 会形成环。
        使用 BFS 遍历 depends_on 的依赖链。
        """
        if task_id == depends_on_id:
            return True
        visited = set()
        queue = [depends_on_id]
        while queue:
            current = queue.pop(0)
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            # current 依赖哪些任务（current 作为 task 的依赖记录）
            next_ids = TaskDependency.objects.filter(
                task_id=current
            ).values_list('depends_on_id', flat=True)
            for nid in next_ids:
                if nid not in visited:
                    queue.append(nid)
        return False
