<template>
  <div class="sheds-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2>圈舍管理</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>新增圈舍
      </el-button>
    </div>

    <!-- 搜索筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="圈舍名称">
          <el-input v-model="searchForm.name" placeholder="请输入圈舍名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="正常" value="normal" />
            <el-option label="警告" value="warning" />
            <el-option label="离线" value="offline" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 圈舍列表 -->
    <el-card>
      <el-table :data="shedList" v-loading="loading" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="name" label="圈舍名称" min-width="120">
          <template #default="{ row }">
            <div class="shed-name">
              <span class="shed-icon">🏠</span>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="area" label="面积" width="100">
          <template #default="{ row }">
            {{ row.area }}㎡
          </template>
        </el-table-column>
        <el-table-column prop="animalCount" label="存栏数" width="100" />
        <el-table-column prop="cameraCount" label="摄像头" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.onlineCameras === row.cameraCount ? 'success' : 'warning'">
              {{ row.onlineCameras }}/{{ row.cameraCount }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="temperature" label="温度" width="100">
          <template #default="{ row }">
            {{ row.temperature }}°C
          </template>
        </el-table-column>
        <el-table-column prop="humidity" label="湿度" width="100">
          <template #default="{ row }">
            {{ row.humidity }}%
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="manager" label="负责人" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">查看</el-button>
            <el-button link type="primary" size="small" @click="editShed(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteShed(row)">删除</el-button>
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
      :title="isEdit ? '编辑圈舍' : '新增圈舍'"
      width="600px"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="圈舍名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入圈舍名称" />
        </el-form-item>
        <el-form-item label="面积" prop="area">
          <el-input-number v-model="formData.area" :min="1" :max="10000" />
          <span class="unit">㎡</span>
        </el-form-item>
        <el-form-item label="存栏数" prop="animalCount">
          <el-input-number v-model="formData.animalCount" :min="0" :max="1000" />
          <span class="unit">只</span>
        </el-form-item>
        <el-form-item label="负责人" prop="manager">
          <el-input v-model="formData.manager" placeholder="请输入负责人姓名" />
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

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="圈舍详情" width="800px">
      <div v-if="currentShed" class="shed-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="圈舍名称">{{ currentShed.name }}</el-descriptions-item>
          <el-descriptions-item label="面积">{{ currentShed.area }}㎡</el-descriptions-item>
          <el-descriptions-item label="存栏数">{{ currentShed.animalCount }}只</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentShed.manager }}</el-descriptions-item>
          <el-descriptions-item label="温度">{{ currentShed.temperature }}°C</el-descriptions-item>
          <el-descriptions-item label="湿度">{{ currentShed.humidity }}%</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentShed.status)" size="small">
              {{ getStatusText(currentShed.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="摄像头">
            {{ currentShed.onlineCameras }}/{{ currentShed.cameraCount }} 在线
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ currentShed.remark || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 关联设备 -->
        <h4 class="section-title">关联设备</h4>
        <el-table :data="currentShed.cameras" size="small">
          <el-table-column prop="name" label="设备名称" />
          <el-table-column prop="serialNumber" label="序列号" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small">
                {{ row.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 搜索表单
const searchForm = reactive({
  name: '',
  status: ''
})

// 分页信息
const pageInfo = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 列表数据
const loading = ref(false)
const shedList = ref([
  {
    id: 1,
    name: '一号圈舍',
    area: 120,
    animalCount: 32,
    cameraCount: 4,
    onlineCameras: 4,
    temperature: 18,
    humidity: 65,
    status: 'normal',
    manager: '张师傅',
    remark: '母麝圈舍',
    cameras: [
      { name: 'CAM-01', serialNumber: 'SN001', status: 'online' },
      { name: 'CAM-02', serialNumber: 'SN002', status: 'online' }
    ]
  },
  {
    id: 2,
    name: '二号圈舍',
    area: 100,
    animalCount: 28,
    cameraCount: 4,
    onlineCameras: 3,
    temperature: 19,
    humidity: 62,
    status: 'warning',
    manager: '李师傅',
    remark: '公麝圈舍',
    cameras: [
      { name: 'CAM-03', serialNumber: 'SN003', status: 'online' },
      { name: 'CAM-04', serialNumber: 'SN004', status: 'offline' }
    ]
  },
  {
    id: 3,
    name: '三号圈舍',
    area: 150,
    animalCount: 45,
    cameraCount: 6,
    onlineCameras: 6,
    temperature: 17,
    humidity: 70,
    status: 'normal',
    manager: '王师傅',
    remark: '育幼圈舍',
    cameras: []
  }
])

// 对话框控制
const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()
const currentShed = ref<any>(null)

// 表单数据
const formData = reactive({
  id: null as number | null,
  name: '',
  area: 100,
  animalCount: 0,
  manager: '',
  remark: ''
})

// 表单规则
const formRules = {
  name: [{ required: true, message: '请输入圈舍名称', trigger: 'blur' }],
  area: [{ required: true, message: '请输入面积', trigger: 'blur' }],
  manager: [{ required: true, message: '请输入负责人', trigger: 'blur' }]
}

// 获取状态类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    normal: 'success',
    warning: 'warning',
    offline: 'danger'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    normal: '正常',
    warning: '警告',
    offline: '离线'
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
  searchForm.status = ''
  handleSearch()
}

// 加载数据
const loadData = async () => {
  loading.value = true
  // 实际项目中调用 API
  // const res = await api.getSheds({ ...searchForm, ...pageInfo })
  setTimeout(() => {
    loading.value = false
  }, 500)
}

// 显示新增对话框
const showAddDialog = () => {
  isEdit.value = false
  formData.id = null
  formData.name = ''
  formData.area = 100
  formData.animalCount = 0
  formData.manager = ''
  formData.remark = ''
  dialogVisible.value = true
}

// 编辑圈舍
const editShed = (row: any) => {
  isEdit.value = true
  Object.assign(formData, row)
  dialogVisible.value = true
}

// 查看详情
const viewDetail = (row: any) => {
  currentShed.value = row
  detailVisible.value = true
}

// 删除圈舍
const deleteShed = (row: any) => {
  ElMessageBox.confirm(
    `确定要删除圈舍 "${row.name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 实际项目中调用 API
    // await api.deleteShed(row.id)
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
    // 实际项目中调用 API
    // if (isEdit.value) {
    //   await api.updateShed(formData)
    // } else {
    //   await api.createShed(formData)
    // }
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
.sheds-page {
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

  .search-card {
    margin-bottom: 20px;
  }

  .shed-name {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .shed-icon {
      font-size: 20px;
    }
  }

  .unit {
    margin-left: 8px;
    color: #909399;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }

  .shed-detail {
    .section-title {
      margin: 20px 0 12px;
      font-size: 16px;
      font-weight: 600;
    }
  }
}
</style>
