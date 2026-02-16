const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const shedRoutes = require('./routes/sheds');
const cameraRoutes = require('./routes/cameras');
const alertRoutes = require('./routes/alerts');
const dashboardRoutes = require('./routes/dashboard');
const animalRoutes = require('./routes/animals');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 数据库连接
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/linshe')
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// API 路由
app.use('/v1/auth', authRoutes);
app.use('/v1/sheds', shedRoutes);
app.use('/v1/cameras', cameraRoutes);
app.use('/v1/alerts', alertRoutes);
app.use('/v1/dashboard', dashboardRoutes);
app.use('/v1/animals', animalRoutes);

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 错误处理
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ message: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
