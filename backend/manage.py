#!/usr/bin/env python
"""Django 命令行管理工具"""
import os
import sys


def main():
    """运行管理命令"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请确认已安装 Django 并已激活虚拟环境。"
            "你是在虚拟环境中运行这个命令吗？"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
