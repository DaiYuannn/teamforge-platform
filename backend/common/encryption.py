"""
字段加密工具（架构预留，第三期使用）
使用 cryptography.fernet 对称加密/解密敏感字段
"""
import os
import base64
from cryptography.fernet import Fernet


class FieldCipher:
    """
    字段加密器
    使用 Fernet 对称加密算法对敏感字段进行加密/解密
    第三期敏感资料模块使用
    """

    def __init__(self, key=None):
        """
        初始化加密器
        :param key: 加密密钥（Fernet key），不传则从环境变量读取
        """
        if key is None:
            key = os.environ.get('FIELD_ENCRYPTION_KEY')
        if key is None:
            # 开发环境自动生成密钥（生产环境必须从环境变量配置）
            key = Fernet.generate_key()
        elif isinstance(key, str):
            # 字符串密钥转 bytes
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext):
        """
        加密明文
        :param plaintext: 明文字符串
        :return: 加密后的字符串（base64编码）
        """
        if plaintext is None:
            return None
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        encrypted = self._fernet.encrypt(plaintext)
        return encrypted.decode('utf-8')

    def decrypt(self, ciphertext):
        """
        解密密文
        :param ciphertext: 加密字符串（base64编码）
        :return: 明文字符串
        """
        if ciphertext is None:
            return None
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode('utf-8')
        decrypted = self._fernet.decrypt(ciphertext)
        return decrypted.decode('utf-8')

    @staticmethod
    def generate_key():
        """生成新的 Fernet 密钥，用于初始化配置"""
        return Fernet.generate_key().decode('utf-8')


# 全局单例（延迟初始化）
_field_cipher_instance = None


def get_field_cipher():
    """获取全局加密器实例"""
    global _field_cipher_instance
    if _field_cipher_instance is None:
        _field_cipher_instance = FieldCipher()
    return _field_cipher_instance
