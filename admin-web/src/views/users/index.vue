<template>
  <div class="users-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>新增用户
      </el-button>
    </div>

    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="用户名">
          <el-input v-model="searchForm.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="全部角色" clearable>
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="观察员" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="userList" v-loading="loading" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="realName" label="姓名" min-width="100" />
        <el-table-column prop="phone" label="手机号" min-width="130" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">{{ getRoleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assignedSheds" label="负责圈舍" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="shed in row.assignedSheds" :key="shed" size="small" class="shed-tag">
              {{ shed }}
            </el-tag>
            <span v-if="!row.assignedSheds?.length" style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.status" active-value="active" inactive-value="disabled"
              @change="toggleStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="lastLogin" label="最后登录" min-width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editUser(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="resetPassword(row)">重置密码</el-button>
            <el-button link type="danger" size="small" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pageInfo.page" v-model:page-size="pageInfo.pageSize"
          :total="pageInfo.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next"
          @size-change="loadData" @current-change="loadData" />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="550px">
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="realName">
          <el-input v-model="formData.realName" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="观察员" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责圈舍" prop="assignedSheds">
          <el-select v-model="formData.assignedSheds" multiple placeholder="请选择圈舍" style="width: 100%">
            <el-option v-for="shed in shedOptions" :key="shed.id" :label="shed.name" :value="shed.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="formData.password" type="password" placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const searchForm = reactive({ username: '', role: '', status: '' })
const pageInfo = reactive({ page: 1, pageSize: 10, total: 0 })
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const shedOptions = ref([
  { id: 1, name: '一号圈舍' },
  { id: 2, name: '二号圈舍' },
  { id: 3, name: '三号圈舍' },
  { id: 4, name: '四号圈舍' }
])

const userList = ref([
  { id: 1, username: 'admin', realName: '系统管理员', phone: '138****0001', role: 'admin', assignedSheds: [], status: 'active', lastLogin: '2026-03-13 17:30:00' },
  { id: 2, username: 'zhangsan', realName: '张三', phone: '138****0002', role: 'operator', assignedSheds: ['一号圈舍', '二号圈舍'], status: 'active', lastLogin: '2026-03-13 09:15:00' },
  { id: 3, username: 'lisi', realName: '李四', phone: '138****0003', role: 'operator', assignedSheds: ['三号圈舍'], status: 'active', lastLogin: '2026-03-12 16:45:00' },
  { id: 4, username: 'wangwu', realName: '王五', phone: '138****0004', role: 'viewer', assignedSheds: ['四号圈舍'], status: 'disabled', lastLogin: '2026-03-01 10:00:00' }
])

const formData = reactive({
  id: null as number | null,
  username: '', realName: '', phone: '', role: 'operator',
  assignedSheds: [] as string[], password: ''
})

const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  realName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }]
}

const getRoleType = (r: string) => ({ admin: 'danger', operator: '', viewer: 'info' }[r] || 'info')
const getRoleText = (r: string) => ({ admin: '管理员', operator: '操作员', viewer: '观察员' }[r] || r)

const handleSearch = () => { pageInfo.page = 1; loadData() }
const resetSearch = () => { Object.assign(searchForm, { username: '', role: '', status: '' }); handleSearch() }
const loadData = async () => { loading.value = true; setTimeout(() => { loading.value = false }, 300) }

const showAddDialog = () => {
  isEdit.value = false
  Object.assign(formData, { id: null, username: '', realName: '', phone: '', role: 'operator', assignedSheds: [], password: '' })
  dialogVisible.value = true
}

const editUser = (row: any) => {
  isEdit.value = true
  Object.assign(formData, { ...row, password: '' })
  dialogVisible.value = true
}

const toggleStatus = (row: any) => {
  ElMessage.success(`用户 ${row.realName} 已${row.status === 'active' ? '启用' : '禁用'}`)
}

const resetPassword = (row: any) => {
  ElMessageBox.confirm(`确定重置 "${row.realName}" 的密码？`, '确认').then(() => {
    ElMessage.success('密码已重置为默认密码')
  })
}

const deleteUser = (row: any) => {
  ElMessageBox.confirm(`确定删除 "${row.realName}"？`, '确认删除', { type: 'warning' }).then(() => {
    ElMessage.success('删除成功')
    loadData()
  })
}

const submitForm = async () => {
  const valid = await formRef.value?.validate()
  if (!valid) return
  submitting.value = true
  try {
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.users-page {
  .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
    h2 { margin: 0; font-size: 24px; font-weight: 600; }
  }
  .search-card { margin-bottom: 20px; }
  .pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 20px; }
  .shed-tag { margin: 2px; }
}
</style>
