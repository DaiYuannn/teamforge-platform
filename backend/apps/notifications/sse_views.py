"""
SSE (Server-Sent Events) 实时通知推送
客户端通过 EventSource 连接 /api/v1/notifications/sse/ 接收实时通知
"""
import json
import time

from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class NotificationSSEView(APIView):
    """
    SSE 通知推送
    GET /api/v1/notifications/sse/
    返回 text/event-stream，客户端用 EventSource 接收

    事件类型:
    - connected:    连接建立确认
    - notification: 新通知推送
    - heartbeat:    心跳保活
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        def event_stream():
            # 初始连接确认
            yield (
                f"event: connected\n"
                f"data: {json.dumps({'type': 'connected', 'message': 'SSE连接成功'}, ensure_ascii=False)}\n\n"
            )

            last_id = 0
            while True:
                # 查询未推送的通知
                from apps.notifications.models import Notification
                from apps.notifications.serializers import NotificationListSerializer

                new_notifications = Notification.objects.filter(
                    recipient=request.user,
                    id__gt=last_id,
                ).order_by('id')[:20]

                for notification in new_notifications:
                    last_id = notification.id
                    serializer = NotificationListSerializer(notification)
                    data = {
                        'type': 'notification',
                        'data': serializer.data,
                    }
                    yield (
                        f"event: notification\n"
                        f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
                    )

                # 心跳
                yield (
                    f"event: heartbeat\n"
                    f"data: {json.dumps({'time': int(time.time())})}\n\n"
                )

                time.sleep(5)  # 5秒轮询间隔

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Nginx 关闭缓冲
        return response
