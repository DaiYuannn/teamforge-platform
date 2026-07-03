# 将 SSL 证书放置于此目录（生产环境启用 HTTPS 时使用）
#   cert.pem  - 证书文件
#   key.pem   - 私钥文件
#
# 启用步骤:
#   1. 将证书文件放入此目录
#   2. 取消 nginx/default.prod.conf 中 HTTPS server 块的注释
#   3. 在 env/backend.prod.env 中设置 SECURE_SSL_REDIRECT=True
#   4. 重启 nginx: docker compose -f docker-compose.prod.yml restart nginx
