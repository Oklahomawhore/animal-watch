<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e8f5e9;">🦌</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalAnimals }}</div>
              <div class="stat-label">总林麝数</div>
            </div>
          </div>
          <div class="stat-trend up">
            <el-icon><ArrowUp /></el-icon>
            <span>较昨日 +12只</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e3f2fd;">📹</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.onlineCameras }}/{{ stats.totalCameras }}</div>
              <div class="stat-label">在线设备</div>
            </div>
          </div>
          <div class="stat-trend down" v-if="stats.totalCameras - stats.onlineCameras > 0">
            <el-icon><Warning /></el-icon>
            <span>{{ stats.totalCameras - stats.onlineCameras }}台离线</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #fff3e0;">🔔</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.todayAlerts }}</div>
              <div class="stat-label">今日报警</div>
            </div>
          </div>
          <div class="stat-trend" :class="stats.unhandledAlerts > 0 ? 'down' : 'up'">
            <el-icon><WarningFilled v-if="stats.unhandledAlerts > 0" /><CircleCheck v-else /></el-icon>
            <span>{{ stats.unhandledAlerts > 0 ? stats.unhandledAlerts + '条待处理' : '全部已处理' }}</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #fce4ec;">💚</div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.healthRate }}%</div>
              <div class="stat-label">健康率</div>
            </div>
          </div>
          <div class="stat-trend up">
            <el-icon><CircleCheck /></el-icon>
            <span>正常</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>活动量趋势（近7天）</span>
              <el-radio-group v-model="timeRange" size="small">
                <el-radio-button label="week">近7天</el-radio-button>
                <el-radio-button label="month">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="chartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>报警类型分布</span>
          </template>
          <div class="alert-types">
            <div class="alert-type-item" v-for="item in alertTypes" :key="item.type">
              <div class="type-info">
                <span class="type-dot" :style="{ background: item.color }"></span>
                <span>{{ item.name }}</span>
              </div>
              <span class="type-value">{{ item.value }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时报警 -->
    <el-card class="alerts-card">
      <template #header>
        <div class="card-header">
          <span>实时报警</span>
          <el-button type="primary" size="small" @click="$router.push('/alerts')">查看全部</el-button>
        </div>
      </template>
      
      <el-table :data="recentAlerts" style="width: 100%">
        <el-table-column prop="time" label="时间" width="100" />
        <el-table-column prop="shed" label="圈舍" width="120" />
        <el-table-column prop="device" label="设备" width="120" />
        <el-table-column prop="type" label="报警类型" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '未处理' ? 'danger' : 'success'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleAlert(row)">处理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ArrowUp, Warning, WarningFilled, CircleCheck } from '@element-plus/icons-vue'

const timeRange = ref('week')
const chartRef = ref<HTMLElement>()

const stats = ref({
  totalAnimals: 1280,
  onlineCameras: 24,
  totalCameras: 26,
  todayAlerts: 3,
  unhandledAlerts: 1,
  healthRate: 98.5
})

const alertTypes = ref([
  { type: 'activity', name: '活动异常', value: 40, color: '#ff6b35' },
  { type: 'offline', name: '设备离线', value: 30, color: '#ffc107' },
  { type: 'other', name: '其他', value: 30, color: '#4caf50' }
])

const recentAlerts = ref([
  { time: '10:23:15', shed: '一号圈舍', device: 'CAM-01', type: '活动异常', status: '未处理' },
  { time: '09:45:32', shed: '二号圈舍', device: 'CAM-03', type: '设备离线', status: '已恢复' },
  { time: '08:12:08', shed: '三号圈舍', device: 'CAM-05', type: '活动偏低', status: '已处理' }
])

const handleAlert = (row: any) => {
  console.log('处理报警:', row)
}

onMounted(() => {
  // 初始化图表
})
</script>

<style scoped>
.dashboard {
  padding-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  .stat-content {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;
  }
  
  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
  }
  
  .stat-value {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    line-height: 1;
  }
  
  .stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 4px;
  }
  
  .stat-trend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    
    &.up {
      color: #67c23a;
    }
    
    &.down {
      color: #f56c6c;
    }
  }
}

.charts-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-types {
  padding: 10px 0;
}

.alert-type-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
  
  &:last-child {
    border-bottom: none;
  }
}

.type-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.type-value {
  font-weight: 600;
  color: #303133;
}

.alerts-card {
  margin-top: 20px;
}
</style>
