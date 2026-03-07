#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信小程序消息推送服务（单小程序模式）
所有租户共用一个小程序，通过client_code区分
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List
from flask import current_app

logger = logging.getLogger(__name__)


class WechatMiniProgramService:
    """
    微信小程序消息推送服务
    
    文档: https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/access-token/auth.getAccessToken.html
    """
    
    BASE_URL = "https://api.weixin.qq.com"
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    def _get_access_token(self) -> str:
        """获取小程序access_token"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
        
        appid = current_app.config.get('WECHAT_APPID')
        secret = current_app.config.get('WECHAT_SECRET')
        
        if not appid or not secret:
            raise Exception("WECHAT_APPID or WECHAT_SECRET not configured")
        
        url = f"{self.BASE_URL}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        
        resp = requests.get(url, params=params, timeout=30)
        result = resp.json()
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            # token有效期2小时，预留5分钟缓冲
            expires_in = result.get("expires_in", 7200)
            self.token_expires_at = datetime.utcnow().timestamp() + expires_in - 300
            return self.access_token
        else:
            logger.error(f"获取access_token失败: {result}")
            raise Exception(f"Wechat auth failed: {result.get('errmsg')}")
    
    def send_subscribe_message(
        self,
        openid: str,
        template_id: str,
        page: str,
        data: Dict
    ) -> bool:
        """
        发送订阅消息
        
        Args:
            openid: 用户openid
            template_id: 模板ID
            page: 点击跳转页面路径
            data: 模板数据 {"thing1": {"value": "xxx"}, ...}
        """
        try:
            access_token = self._get_access_token()
            url = f"{self.BASE_URL}/cgi-bin/message/subscribe/send?access_token={access_token}"
            
            payload = {
                "touser": openid,
                "template_id": template_id,
                "page": page,
                "data": data
            }
            
            resp = requests.post(url, json=payload, timeout=30)
            result = resp.json()
            
            if result.get("errcode") == 0:
                logger.info(f"订阅消息发送成功: {openid}")
                return True
            else:
                logger.error(f"订阅消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"发送订阅消息异常: {e}")
            return False
    
    def get_phone_number(self, code: str) -> Optional[str]:
        """
        获取用户手机号（小程序登录）
        
        Args:
            code: 前端调用 wx.login 获取的 code
        """
        try:
            access_token = self._get_access_token()
            url = f"{self.BASE_URL}/wxa/business/getuserphonenumber?access_token={access_token}"
            
            payload = {"code": code}
            resp = requests.post(url, json=payload, timeout=30)
            result = resp.json()
            
            if result.get("errcode") == 0:
                phone_info = result.get("phone_info", {})
                return phone_info.get("phoneNumber")
            else:
                logger.error(f"获取手机号失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"获取手机号异常: {e}")
            return None
    
    def code_to_session(self, code: str) -> Optional[Dict]:
        """
        登录凭证校验（code换openid/session_key）
        
        Args:
            code: 前端调用 wx.login 获取的 code
        
        Returns:
            { "openid": "xxx", "session_key": "xxx", "unionid": "xxx" }
        """
        try:
            appid = current_app.config.get('WECHAT_APPID')
            secret = current_app.config.get('WECHAT_SECRET')
            
            url = f"{self.BASE_URL}/sns/jscode2session"
            params = {
                "appid": appid,
                "secret": secret,
                "js_code": code,
                "grant_type": "authorization_code"
            }
            
            resp = requests.get(url, params=params, timeout=30)
            result = resp.json()
            
            if "openid" in result:
                return result
            else:
                logger.error(f"code换session失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"code换session异常: {e}")
            return None


class WechatMessageTemplates:
    """微信小程序订阅消息模板"""
    
    # 告警通知模板
    ALARM = {
        "template_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # 需要在微信小程序后台申请
        "page": "pages/alarm/detail",
        "data": {
            "thing1": {"value": "{enclosure_name}"},      # 圈舍名称
            "thing2": {"value": "{alarm_type}"},          # 告警类型
            "time3": {"value": "{alarm_time}"},           # 告警时间
            "thing4": {"value": "{remark}"}               # 备注
        }
    }
    
    # 设备离线通知
    OFFLINE = {
        "template_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "page": "pages/device/index",
        "data": {
            "thing1": {"value": "{device_name}"},         # 设备名称
            "time2": {"value": "{offline_time}"},         # 离线时间
            "thing3": {"value": "请及时检查设备状态"}       # 提醒内容
        }
    }
    
    # 诊疗随访提醒
    MEDICAL = {
        "template_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "page": "pages/medical/detail",
        "data": {
            "thing1": {"value": "{animal_tag}"},          # 个体编号
            "time2": {"value": "{next_date}"},            # 下次随访日期
            "thing3": {"value": "请及时进行随访记录"}       # 提醒内容
        }
    }
    
    # 检测报告通知
    DETECTION = {
        "template_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "page": "pages/detection/detail",
        "data": {
            "thing1": {"value": "{enclosure_name}"},      # 圈舍名称
            "time2": {"value": "{detection_time}"},       # 检测时间
            "thing3": {"value": "检测到{animal_count}只林麝"}, # 检测结果
            "thing4": {"value": "{activity_level}"}       # 活动状态
        }
    }


# 全局微信服务实例
wechat_service = WechatMiniProgramService()
