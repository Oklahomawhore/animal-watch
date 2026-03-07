#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信服务商消息推送服务
支持服务号模板消息推送
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class WechatServiceProvider:
    """
    微信服务商模式消息推送
    
    文档: https://developers.weixin.qq.com/doc/oplatform/Third-party_Platforms/2.0/product/Third_party_platform_appid.html
    """
    
    BASE_URL = "https://api.weixin.qq.com"
    
    def __init__(self, component_appid: str, component_secret: str):
        self.component_appid = component_appid
        self.component_secret = component_secret
        self.component_access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    def _get_component_access_token(self) -> str:
        """获取服务商component_access_token"""
        if self.component_access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.component_access_token
        
        url = f"{self.BASE_URL}/cgi-bin/component/api_component_token"
        payload = {
            "component_appid": self.component_appid,
            "component_secret": self.component_secret
        }
        
        resp = requests.post(url, json=payload, timeout=30)
        result = resp.json()
        
        if "component_access_token" in result:
            self.component_access_token = result["component_access_token"]
            # token有效期2小时，预留5分钟缓冲
            self.token_expires_at = datetime.utcnow().timestamp() + result.get("expires_in", 7200) - 300
            return self.component_access_token
        else:
            logger.error(f"获取component_access_token失败: {result}")
            raise Exception(f"Wechat auth failed: {result.get('errmsg')}")
    
    def send_template_message(
        self,
        authorizer_appid: str,  # 客户公众号/小程序的appid
        openid: str,
        template_id: str,
        data: Dict,
        url: Optional[str] = None,
        miniprogram: Optional[Dict] = None
    ) -> bool:
        """
        发送模板消息
        
        Args:
            authorizer_appid: 授权方（客户）的appid
            openid: 用户openid
            template_id: 模板ID
            data: 模板数据 {"first": {"value": "xxx", "color": "#173177"}, ...}
            url: 点击跳转URL（服务号）
            miniprogram: 跳小程序 {"appid": "xxx", "pagepath": "xxx"}
        """
        try:
            # 获取授权方的access_token
            auth_token = self._get_authorizer_access_token(authorizer_appid)
            
            api_url = f"{self.BASE_URL}/cgi-bin/message/template/send?access_token={auth_token}"
            
            payload = {
                "touser": openid,
                "template_id": template_id,
                "data": data
            }
            
            if url:
                payload["url"] = url
            if miniprogram:
                payload["miniprogram"] = miniprogram
            
            resp = requests.post(api_url, json=payload, timeout=30)
            result = resp.json()
            
            if result.get("errcode") == 0:
                logger.info(f"模板消息发送成功: {openid}")
                return True
            else:
                logger.error(f"模板消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"发送模板消息异常: {e}")
            return False
    
    def _get_authorizer_access_token(self, authorizer_appid: str) -> str:
        """
        获取授权方的access_token
        实际项目中应该从数据库读取，这里简化处理
        """
        # TODO: 从数据库读取authorizer_refresh_token，然后刷新
        # 文档: https://developers.weixin.qq.com/doc/oplatform/Third-party_Platforms/2.0/api/ThirdParty/token/component_authorizer_token.html
        
        component_token = self._get_component_access_token()
        
        url = f"{self.BASE_URL}/cgi-bin/component/api_authorizer_token?component_access_token={component_token}"
        payload = {
            "component_appid": self.component_appid,
            "authorizer_appid": authorizer_appid,
            "authorizer_refresh_token": "xxx"  # 从数据库读取
        }
        
        resp = requests.post(url, json=payload, timeout=30)
        result = resp.json()
        
        if "authorizer_access_token" in result:
            return result["authorizer_access_token"]
        else:
            raise Exception(f"获取authorizer_access_token失败: {result}")


class WechatMessageTemplates:
    """微信消息模板定义"""
    
    # 告警通知模板
    ALARM_TEMPLATE = {
        "template_id": "xxx",  # 需要在微信后台申请
        "data": {
            "first": {"value": "林麝监测告警", "color": "#173177"},
            "keyword1": {"value": "{enclosure_name}", "color": "#173177"},
            "keyword2": {"value": "{alarm_type}", "color": "#FF0000"},
            "keyword3": {"value": "{alarm_time}", "color": "#173177"},
            "remark": {"value": "点击查看详情", "color": "#173177"}
        }
    }
    
    # 设备离线通知
    OFFLINE_TEMPLATE = {
        "template_id": "xxx",
        "data": {
            "first": {"value": "设备离线提醒", "color": "#173177"},
            "keyword1": {"value": "{device_name}", "color": "#173177"},
            "keyword2": {"value": "{offline_time}", "color": "#FF0000"},
            "remark": {"value": "请及时检查设备状态", "color": "#173177"}
        }
    }
    
    # 诊疗提醒
    MEDICAL_TEMPLATE = {
        "template_id": "xxx",
        "data": {
            "first": {"value": "诊疗随访提醒", "color": "#173177"},
            "keyword1": {"value": "{animal_tag}", "color": "#173177"},
            "keyword2": {"value": "{next_follow_up_date}", "color": "#FF0000"},
            "remark": {"value": "请及时进行随访记录", "color": "#173177"}
        }
    }


class NotificationService:
    """通知服务 - 统一入口"""
    
    def __init__(self):
        self.wechat: Optional[WechatServiceProvider] = None
        # 初始化微信服务商（配置了才启用）
        # self.wechat = WechatServiceProvider(component_appid, component_secret)
    
    def send_alarm_notification(
        self,
        client_id: int,
        user_id: int,
        alarm_type: str,
        enclosure_name: str,
        alarm_time: str,
        pic_url: Optional[str] = None
    ):
        """发送告警通知"""
        # TODO: 根据用户配置选择通知渠道
        # 1. 微信模板消息
        # 2. 短信
        # 3. 站内信
        
        if self.wechat:
            # 获取用户的微信openid
            # openid = get_user_wechat_openid(user_id)
            # self.wechat.send_template_message(...)
            pass
        
        logger.info(f"告警通知: client={client_id}, user={user_id}, type={alarm_type}")
    
    def send_offline_notification(self, client_id: int, device_name: str, offline_time: str):
        """发送设备离线通知"""
        logger.info(f"离线通知: client={client_id}, device={device_name}")
    
    def send_medical_reminder(self, client_id: int, animal_tag: str, next_date: str):
        """发送诊疗随访提醒"""
        logger.info(f"诊疗提醒: client={client_id}, animal={animal_tag}")


# 全局通知服务实例
notification_service = NotificationService()
