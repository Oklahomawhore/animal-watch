const jwt = require('jsonwebtoken');
const { User } = require('../models');

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// 验证 Token
const auth = async (req, res, next) => {
  try {
    const token = req.header('Authorization')?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ message: 'Access denied. No token provided.' });
    }
    
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await User.findById(decoded.userId);
    
    if (!user || !user.isActive) {
      return res.status(401).json({ message: 'User not found or inactive' });
    }
    
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ message: 'Invalid token' });
  }
};

// 生成 Token
const generateToken = (userId) => {
  return jwt.sign({ userId }, JWT_SECRET, { expiresIn: '7d' });
};

// 微信小程序登录
const wxLogin = async (code, userInfo) => {
  // 实际项目中调用微信 API 获取 openid
  // 这里简化处理
  const openId = `wx_${code}`;
  
  let user = await User.findOne({ openId });
  
  if (!user) {
    user = new User({
      openId,
      name: userInfo.nickName || '新用户',
      avatar: userInfo.avatarUrl
    });
    await user.save();
  }
  
  return {
    user,
    token: generateToken(user._id)
  };
};

module.exports = { auth, generateToken, wxLogin };
