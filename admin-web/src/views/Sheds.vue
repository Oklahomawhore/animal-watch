<template>
  <div class="shed-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h2>圈舍管理</h2>
        <span class="subtitle">共 {{ totalSheds }} 个圈舍</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索圈舍名称"
          style="width: 240px"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>新增圈舍
        </el-button>
      </div>
    </div>

    <!-- 圈舍列表 -->
    <el-card>
      <el-table
        :data="shedList"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="圈舍名称" min-width="120">
          <template #default="{ row }">
            <div class="shed-name">
              <span class="name">{{ row.name }}</span>
              <el-tag v-if="row.status === 'warning'" type="warning" size="small">需关注</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="area" label="面积" width="100">
          <template #default="{ row }">
            {{ row.area }}㎡
          </template>
        </el-table-column>
        <el-table-column prop="capacity" label="容量" width="100">
          <template #default="{ row }">
            {{ row.animalCount }}/{{ row.capacity }}只
          </template>
        </el-table-column>
        <el-table-column prop="environment" label="环境" min-width="150">
          <template #default="{ row }">
            <div class="env-info">
              <span>🌡️ {{ row.temperature }}°C</span>
              <span>💧 {{ row.humidity }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="cameras" label="摄像头" width="120">
          <template #default="{ row }">
            <div class="camera-status">
              <el-icon :class="row.onlineCameras === row.totalCameras ? 'success' : 'warning'">
                <VideoCamera />
              </el-icon>
              <span>{{ row.onlineCameras }}/{{ row.totalCameras }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="manager" label="负责人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalSheds"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增圈舍' : '编辑圈舍'"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="圈舍名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入圈舍名称" />
        </el-form-item>
        <el-form-item label="面积" prop="area">
          <el-input-number v-model="formData.area" :min="1" :max="10000" style="width: 200px">
            <template #append>㎡</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="容量" prop="capacity">
          <el-input-number v-model="formData.capacity" :min="1" :max="500" style="width: 200px">
            <template #append>只</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="负责人" prop="manager">
          <el-input v-model="formData.manager" placeholder="请输入负责人姓名" />
        </el-form-item>
        <el-form-item label="摄像头" prop="cameras">
          <el-select
            v-model="formData.cameraIds"
            multiple
            placeholder="选择摄像头"
            style="width: 100%"
          >
            <el-option
              v-for="camera in availableCameras"
              :key="camera.id"
              :label="camera.name"
              :value="camera.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input
            v-model="formData.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 圈舍详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="圈舍详情"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentShed" class="shed-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="圈舍名称">{{ currentShed.name }}</el-descriptions-item>
          <el-descriptions-item label="面积">{{ currentShed.area }}㎡</el-descriptions-item>
          <el-descriptions-item label="容量">{{ currentShed.animalCount }}/{{ currentShed.capacity }}只</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentShed.manager }}</el-descriptions-item>
          <el-descriptions-item label="温度">{{ currentShed.temperature }}°C</el-descriptions-item>
          <el-descriptions-item label="湿度">{{ currentShed.humidity }}%</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentShed.status)">
              {{ getStatusText(currentShed.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentShed.createdAt }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 10px">摄像头列表</h4>
        <el-table :data="currentShed.cameras" size="small">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="serialNumber" label="序列号" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small">
                {{ row.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <h4 style="margin: 20px 0 10px">实时监控</h4>
        <div class="monitor-preview">
          <div v-for="camera in currentShed.cameras" :key="camera.id" class="camera-item">
            <div class="camera-placeholder">
              <el-icon size="32"><VideoCamera /></el-icon>
              <span>{{ camera.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, VideoCamera } from '@element-plus/icons-vue'

// 搜索和分页
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalSheds = ref(0)
const loading = ref(false)

// 表格数据
const shedList = ref([])
const selectedSheds = ref([])

// 对话框
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const detailVisible = ref(false)
const currentShed = ref(null)
const submitLoading = ref(false)

// 表单
const formRef = ref()
const formData = reactive({
  id: null,
  name: '',
  area: 100,
  capacity: 50,
  manager: '',
  cameraIds: [],
  remark: ''
})

const formRules = {
  name: [{ required: true, message: '请输入圈舍名称', trigger: 'blur' }],
  area: [{ required: true, message: '请输入面积', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'blur' }],
  manager: [{ required: true, message: '请输入负责人', trigger: 'blur' }]
}

// 可用摄像头
const availableCameras = ref([
  { id: 1, name: '摄像头-01' },
  { id: 2, name: '摄像头-02' },
  { id: 3, name: '摄像头-03' },
  { id: 4, name: '摄像头-04' }
])

// 获取状态类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    normal: 'success',
    warning: 'warning',
    error: 'danger',
    offline: 'info'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    normal: '正常',
    warning: '需关注',
    error: '异常',
    offline: '离线'
  }
  return map[status] || status
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟数据
    shedList.value = [
      {
        id: 1,
        name: '一号圈舍',
        area: 120,
        capacity: 50,
        animalCount: 32,
        temperature: 18,
        humidity: 65,
        onlineCameras: 4,
        totalCameras: 4,
        manager: '张师傅',
        status: 'normal',
        createdAt: '2024-01-15',
        cameras: [
          { id: 1, name: '东侧摄像头', serialNumber: 'CAM001', status: 'online' },
          { id: 2, name: '西侧摄像头', serialNumber: 'CAM002', status: 'online' }
        ]
      },
      {
        id: 2,
        name: '二号圈舍',
        area: 100,
        capacity: 40,
        animalCount: 28,
        temperature: 19,
        humidity: 62,
        onlineCameras: 3,
        totalCameras: 4,
        manager: '李师傅',
        status: 'warning',
        createdAt: '2024-01-15',
        cameras: [
          { id: 3, name: '北侧摄像头', serialNumber: 'CAM003', status: 'online' },
          { id: 4, name: '南侧摄像头', serialNumber: 'CAM004', status: 'offline' }
        ]
      },
      {
        id: 3,
        name: '三号圈舍',
        area: 150,
        capacity: 60,
        animalCount: 45,
        temperature: 17,
        humidity: 70,
        onlineCameras: 6,
        totalCameras: 6,
        manager: '王师傅',
        status: 'normal',
        createdAt: '2024-01-20',
        cameras: []
      }
    ]
    totalSheds.value = 3
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedSheds.value = selection
}

// 新增
const handleAdd = () => {
  dialogType.value = 'add'
  Object.assign(formData, {
    id: null,
    name: '',
    area: 100,
    capacity: 50,
    manager: '',
    cameraIds: [],
    remark: ''
  })
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row: any) => {
  dialogType.value = 'edit'
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    area: row.area,
    capacity: row.capacity,
    manager: row.manager,
    cameraIds: row.cameras?.map((c: any) => c.id) || [],
    remark: row.remark || ''
  })
  dialogVisible.value = true
}

// 查看详情
const handleView = (row: any) => {
  currentShed.value = row
  detailVisible.value = true
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除圈舍 "${row.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    // 调用删除API
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 取消删除
  }
}

// 提交表单
const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    // 调用保存API
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success(dialogType.value === 'add' ? '新增成功' : '修改成功')
    dialogVisible.value = false
    loadData()
  } finally {
    submitLoading.value = false
  }
}

// 分页
const handleSizeChange = (val: number) => {
  pageSize.value = val
  loadData()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.shed-management {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .header-left {
    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }
    .subtitle {
      color: #909399;
      font-size: 14px;
      margin-left: 10px;
    }
  }

  .header-right {
    display: flex;
    gap: 12px;
  }
}

.shed-name {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .name {
    font-weight: 500;
  }
}

.env-info {
  display: flex;
  gap: 16px;
  
  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.camera-status {
  display: flex;
  align-items: center;
  gap: 6px;
  
  .success {
    color: #67c23a;
  }
  .warning {
    color: #e6a23c;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.shed-detail {
  .monitor-preview {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    
    .camera-item {
      .camera-placeholder {
        aspect-ratio: 16/9;
        background: #f5f7fa;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #909399;
        gap: 8px;
        
        &:hover {
          background: #e4e7ed;
        }
      }
    }
  }
}
</style>
