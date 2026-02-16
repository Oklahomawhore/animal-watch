const mongoose = require('mongoose');

const shedSchema = new mongoose.Schema({
  name: { type: String, required: true },
  code: { type: String, required: true, unique: true },
  capacity: { type: Number, default: 50 },
  currentCount: { type: Number, default: 0 },
  temperature: { type: Number, default: 18 },
  humidity: { type: Number, default: 65 },
  status: { 
    type: String, 
    enum: ['normal', 'warning', 'danger'], 
    default: 'normal' 
  },
  location: { type: String },
  cameras: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Camera' }],
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

const cameraSchema = new mongoose.Schema({
  name: { type: String, required: true },
  code: { type: String, required: true, unique: true },
  shedId: { type: mongoose.Schema.Types.ObjectId, ref: 'Shed', required: true },
  ipAddress: { type: String },
  status: { 
    type: String, 
    enum: ['online', 'offline', 'error'], 
    default: 'offline' 
  },
  streamUrl: { type: String },
  snapshotUrl: { type: String },
  lastHeartbeat: { type: Date },
  createdAt: { type: Date, default: Date.now }
});

const animalSchema = new mongoose.Schema({
  code: { type: String, required: true, unique: true },
  shedId: { type: mongoose.Schema.Types.ObjectId, ref: 'Shed', required: true },
  gender: { type: String, enum: ['male', 'female'] },
  birthDate: { type: Date },
  status: { 
    type: String, 
    enum: ['healthy', 'warning', 'sick', 'isolated'], 
    default: 'healthy' 
  },
  activityLevel: { type: Number, default: 100 },
  lastActivityTime: { type: Date },
  createdAt: { type: Date, default: Date.now }
});

const alertSchema = new mongoose.Schema({
  type: { 
    type: String, 
    enum: ['activity_low', 'activity_high', 'fall_detected', 'fight_detected', 'offline', 'other'],
    required: true 
  },
  level: { 
    type: String, 
    enum: ['urgent', 'warning', 'info'], 
    required: true 
  },
  shedId: { type: mongoose.Schema.Types.ObjectId, ref: 'Shed', required: true },
  cameraId: { type: mongoose.Schema.Types.ObjectId, ref: 'Camera' },
  animalId: { type: mongoose.Schema.Types.ObjectId, ref: 'Animal' },
  description: { type: String, required: true },
  snapshotUrl: { type: String },
  status: { 
    type: String, 
    enum: ['unhandled', 'handling', 'handled', 'ignored'], 
    default: 'unhandled' 
  },
  handledBy: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  handledAt: { type: Date },
  createdAt: { type: Date, default: Date.now }
});

const userSchema = new mongoose.Schema({
  openId: { type: String, unique: true, sparse: true },
  phone: { type: String, unique: true, sparse: true },
  name: { type: String, required: true },
  avatar: { type: String },
  role: { 
    type: String, 
    enum: ['super_admin', 'admin', 'operator', 'viewer'], 
    default: 'viewer' 
  },
  farmId: { type: mongoose.Schema.Types.ObjectId, ref: 'Farm' },
  isActive: { type: Boolean, default: true },
  lastLoginAt: { type: Date },
  createdAt: { type: Date, default: Date.now }
});

const farmSchema = new mongoose.Schema({
  name: { type: String, required: true },
  code: { type: String, required: true, unique: true },
  address: { type: String },
  contactName: { type: String },
  contactPhone: { type: String },
  totalAnimals: { type: Number, default: 0 },
  totalSheds: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now }
});

module.exports = {
  Shed: mongoose.model('Shed', shedSchema),
  Camera: mongoose.model('Camera', cameraSchema),
  Animal: mongoose.model('Animal', animalSchema),
  Alert: mongoose.model('Alert', alertSchema),
  User: mongoose.model('User', userSchema),
  Farm: mongoose.model('Farm', farmSchema)
};
