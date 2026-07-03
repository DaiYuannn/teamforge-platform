"""
初始数据脚本
创建超级管理员账号、老师账号、测试成员账号

使用方法:
    python manage.py shell < scripts/init_data.py
或:
    python manage.py runscript init_data  (需安装 django-extensions)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.users.models import User


def create_users():
    """创建初始用户数据"""

    # ============ 1. 超级管理员账号 ============
    admin, created = User.objects.get_or_create(
        email='admin@example.com',
        defaults={
            'username': 'admin',
            'name': '系统管理员',
            'global_role': User.GlobalRole.SYS_ADMIN,
            'is_staff': True,
            'is_superuser': True,
            'is_student': False,
            'phone': '13800000000',
        }
    )
    if created:
        admin.set_password('admin123456')
        admin.save()
        print(f'[创建] 超级管理员: {admin.email} (密码: admin123456)')
    else:
        print(f'[已存在] 超级管理员: {admin.email}')

    # ============ 2. 老师账号 ============
    teacher, created = User.objects.get_or_create(
        email='teacher@example.com',
        defaults={
            'username': 'teacher',
            'name': '张老师',
            'global_role': User.GlobalRole.TEACHER,
            'is_staff': True,
            'is_student': False,
            'phone': '13800000001',
            'major': '计算机科学',
        }
    )
    if created:
        teacher.set_password('teacher123456')
        teacher.save()
        print(f'[创建] 老师账号: {teacher.email} (密码: teacher123456)')
    else:
        print(f'[已存在] 老师账号: {teacher.email}')

    # ============ 3. 敏感资料审批人账号 ============
    approver, created = User.objects.get_or_create(
        email='approver@example.com',
        defaults={
            'username': 'approver',
            'name': '李审批',
            'global_role': User.GlobalRole.SENS_APPROVER,
            'is_staff': True,
            'is_student': False,
            'phone': '13800000002',
        }
    )
    if created:
        approver.set_password('approver123456')
        approver.save()
        print(f'[创建] 敏感审批人: {approver.email} (密码: approver123456)')
    else:
        print(f'[已存在] 敏感审批人: {approver.email}')

    # ============ 4. 测试成员账号 ============
    test_members = [
        {
            'email': 'member1@example.com',
            'username': 'member1',
            'name': '王同学',
            'password': 'member123456',
            'phone': '13800000003',
            'grade': '2022级',
            'major': '软件工程',
        },
        {
            'email': 'member2@example.com',
            'username': 'member2',
            'name': '赵同学',
            'password': 'member123456',
            'phone': '13800000004',
            'grade': '2023级',
            'major': '计算机科学',
        },
        {
            'email': 'member3@example.com',
            'username': 'member3',
            'name': '钱同学',
            'password': 'member123456',
            'phone': '13800000005',
            'grade': '2021级',
            'major': '人工智能',
        },
    ]

    for member_data in test_members:
        password = member_data.pop('password')
        member, created = User.objects.get_or_create(
            email=member_data['email'],
            defaults={
                **member_data,
                'global_role': User.GlobalRole.MEMBER,
                'is_student': True,
            }
        )
        if created:
            member.set_password(password)
            member.save()
            print(f'[创建] 测试成员: {member.email} (密码: {password})')
        else:
            print(f'[已存在] 测试成员: {member.email}')

    print('\n========== 初始数据创建完成 ==========')
    print('账号清单:')
    print(f'  超级管理员: admin@example.com / admin123456')
    print(f'  老师:       teacher@example.com / teacher123456')
    print(f'  敏感审批人: approver@example.com / approver123456')
    print(f'  测试成员1:  member1@example.com / member123456')
    print(f'  测试成员2:  member2@example.com / member123456')
    print(f'  测试成员3:  member3@example.com / member123456')
    print('======================================')


if __name__ == '__main__':
    create_users()
else:
    # 支持 python manage.py shell < scripts/init_data.py
    create_users()
