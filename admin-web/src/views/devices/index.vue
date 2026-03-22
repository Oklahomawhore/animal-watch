<template>
  <div class="devices-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2>设备管理</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>添加设备
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">设备总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-value">{{ stats.online }}</div>
          <div class="stat-label">在线设备</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card warning">
          <div class="stat-value">{{ stats.offline }}</div>
          <div class="stat-label">离线设备</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.alarm }}</div>
          <div class="stat-label">告警设备</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="设备名称">
          <el-input v-model="searchForm.name" placeholder="请输入设备名称" clearable />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="searchForm.serialNumber" placeholder="请输入序列号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="告警" value="alarm" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属圈舍">
          <el-select v-model="searchForm.shedId" placeholder="全部圈舍" clearable>
            <el-option 
              v-for="shed in shedOptions" 
              :key="shed.id" 
              :label="shed.name" 
              :value="shed.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 设备列表 -->
    <el-card>
      <el-table :data="deviceList" v-loading="loading" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="name" label="设备名称" min-width="120" />
        <el-table-column prop="serialNumber" label="序列号" min-width="140" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="shedName" label="所属圈舍" min-width="120" />
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastOnlineTime" label="最后在线" min-width="160" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewLive(row)">预览</el-button>
            <el-button link type="primary" size="small" @click="capture(row)">抓拍</el-button>
            <el-button link type="primary" size="small" @click="editDevice(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteDevice(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pageInfo.page"
          v-model:page-size="pageInfo.pageSize"
          :total="pageInfo.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '添加设备'"
      width="600px"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="序列号" prop="serialNumber">
          <el-input v-model="formData.serialNumber" placeholder="请输入设备序列号" />
        </el-form-item>
        <el-form-item label="设备类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择设备类型" style="width: 100%">
            <el-option label="网络摄像头" value="camera" />
            <el-option label="温湿度传感器" value="sensor" />
            <el-option label="门禁设备" value="access" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属圈舍" prop="shedId">
          <el-select v-model="formData.shedId" placeholder="请选择圈舍" style="width: 100%">
            <el-option 
              v-for="shed in shedOptions" 
              :key="shed.id" 
              :label="shed.name" 
              :value="shed.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="formData.ip" placeholder="请输入IP地址" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="formData.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="设备登录用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="formData.password" type="password" placeholder="设备登录密码" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="formData.remark" type="textarea" rows="3" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 实时预览对话框 -->
    <el-dialog v-model="previewVisible" title="实时预览" width="800px" destroy-on-close>
      <div class="video-container">
        <div v-if="currentDevice" class="video-player">
          <!-- 实际项目中接入视频流 -->
          <div class="video-placeholder">
            <el-icon size="64"><VideoCamera /></el-icon>
            <p>{{ currentDevice.name }}</p>
            <p class="sub">视频流预览区域</p>
          </div>
        </div>
      </div>
      <div class="preview-controls">
        <el-button @click="capture(currentDevice)">抓拍</el-button>
        <el-button @click="startRecord" v-if="!isRecording">开始录像</el-button>
        <el-button type="danger" @click="stopRecord" v-else>停止录像</el-button>
        <el-button @click="fullScreen">全屏</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus, VideoCamera } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 统计数据
const stats = reactive({
  total: 26,
  online: 24,
  offline: 2,
  alarm: 0
})

// 搜索表单
const searchForm = reactive({
  name: '',
  serialNumber: '',
  status: '',
  shedId: null as number | null
})

// 分页信息
const pageInfo = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 圈舍选项
const shedOptions = ref([
  { id: 1, name: '一号圈舍' },
  { id: 2, name: '二号圈舍' },
  { id: 3, name: '三号圈舍' }
])

// 列表数据
const loading = ref(false)
const deviceList = ref([
  {
    id: 1,
    name: 'CAM-01',
    serialNumber: 'GF6830765',
    type: '网络摄像头',
    shedId: 1,
    shedName: '一号圈舍',
    ip: '192.168.1.101',
    status: 'online',
    lastOnlineTime: '2026-03-13 17:15:32'
  },
  {
    id: 2,
    name: 'CAM-02',
    serialNumber: 'GG3425740',
    type: '网络摄像头',
    shedId: 2,
    shedName: '二号圈舍',
    ip: '192.168.1.102',
    status: 'offline',
    lastOnlineTime: '2026-03-13 10:23:15'
  },
  {
    id: 3,
    name: 'CAM-03',
    serialNumber: 'FU7533003',
    type: '网络摄像头',
    shedId: 3,
    shedName: '三号圈舍',
    ip: '192.168.1.103',
    status: 'online',
    lastOnlineTime: '2026-03-13 17:14:58'
  }
])

// 对话框控制
const dialogVisible = ref(false)
const previewVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const isRecording = ref(false)
const formRef = ref()
const currentDevice = ref<any>(null)

// 表单数据
const formData = reactive({
  id: null as number | null,
  name: '',
  serialNumber: '',
  type: 'camera',
  shedId: null as number | null,
  ip: '',
  port: 80,
  username: '',
  password: '',
  remark: ''
})

// 表单规则
const formRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  serialNumber: [{ required: true, message: '请输入序列号', trigger: 'blur' }],
  type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
  shedId: [{ required: true, message: '请选择所属圈舍', trigger: 'change' }],
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }]
}

// 获取状态类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    online: 'success',
    offline: 'danger',
    alarm: 'warning'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    online: '在线',
    offline: '离线',
    alarm: '告警'
  }
  return map[status] || status
}

// 搜索
const handleSearch = () => {
  pageInfo.page = 1
  loadData()
}

// 重置搜索
const resetSearch = () => {
  searchForm.name = ''
  searchForm.serialNumber = ''
  searchForm.status = ''
  searchForm.shedId = null
  handleSearch()
}

// 加载数据
const loadData = async () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 500)
}

// 显示新增对话框
const showAddDialog = () => {
  isEdit.value = false
  formData.id = null
  formData.name = ''
  formData.serialNumber = ''
  formData.type = 'camera'
  formData.shedId = null
  formData.ip = ''
  formData.port = 80
  formData.username = ''
  formData.password = ''
  formData.remark = ''
  dialogVisible.value = true
}

// 编辑设备
const editDevice = (row: any) => {
  isEdit.value = true
  Object.assign(formData, row)
  dialogVisible.value = true
}

// 查看实时预览
const viewLive = (row: any) => {
  currentDevice.value = row
  previewVisible.value = true
}

// 抓拍
const capture = (row: any) => {
  ElMessage.success(`设备 ${row.name} 抓拍成功`)
}

// 开始录像
const startRecord = () => {
  isRecording.value = true
  ElMessage.success('开始录像')
}

// 停止录像
const stopRecord = () => {
  isRecording.value = false
  ElMessage.success('录像已保存')
}

// 全屏
const fullScreen = () => {
  ElMessage.info('全屏功能开发中')
}

// 删除设备
const deleteDevice = (row: any) => {
  ElMessageBox.confirm(
    `确定要删除设备 "${row.name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('删除成功')
    loadData()
  })
}

// 提交表单
const submitForm = async () => {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

// 分页变化
const handleSizeChange = (val: number) => {
  pageInfo.pageSize = val
  loadData()
}

const handlePageChange = (val: number) => {
  pageInfo.page = val
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.devices-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }
  }

  .stats-row {
    margin-bottom: 20px;
  }

  .stat-card {
    text-align: center;
    
    .stat-value {
      font-size: 32px;
      font-weight: 600;
      color: #303133;
    }
    
    .stat-label {
      font-size: 14px;
      color: #909399;
      margin-top: 8px;
    }
    
    &.success .stat-value {
      color: #67c23a;
    }
    
    &.warning .stat-value {
      color: #f56c6c;
    }
  }

  .search-card {
    margin-bottom: 20px;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }

  .video-container {
    background: #000;
    border-radius: 8px;
    overflow: hidden;
  }

  .video-placeholder {
    height: 400px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    
    p {
      margin: 8px 0 0;
      font-size: 16px;
      
      &.sub {
        font-size: 14px;
        color: #999;
      }
    }
  }

  .preview-controls {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 16px;
  }
}
</style>
