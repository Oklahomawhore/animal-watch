<template>
  <div class="alerts-page">
    <div class="page-header">
      <h2>告警规则配置</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>新增规则
      </el-button>
    </div>

    <!-- 告警统计 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.totalRules }}</div>
          <div class="stat-label">规则总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-value">{{ stats.enabledRules }}</div>
          <div class="stat-label">已启用</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card warning">
          <div class="stat-value">{{ stats.todayTriggered }}</div>
          <div class="stat-label">今日触发</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.unhandled }}</div>
          <div class="stat-label">待处理</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 规则列表 -->
    <el-card>
      <el-table :data="ruleList" v-loading="loading" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="name" label="规则名称" min-width="160" />
        <el-table-column prop="eventType" label="事件类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getEventText(row.eventType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="condition" label="触发条件" min-width="200" />
        <el-table-column prop="severity" label="严重级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notifyMethod" label="通知方式" width="150">
          <template #default="{ row }">
            <span v-for="m in row.notifyMethod" :key="m" class="notify-tag">{{ getNotifyText(m) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="triggerCount" label="触发次数" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editRule(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 告警历史 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>告警历史</span>
          <el-button type="primary" size="small" @click="exportAlerts">导出</el-button>
        </div>
      </template>
      <el-table :data="alertHistory" style="width: 100%">
        <el-table-column prop="time" label="时间" width="160" />
        <el-table-column prop="ruleName" label="触发规则" min-width="160" />
        <el-table-column prop="shed" label="圈舍" width="120" />
        <el-table-column prop="detail" label="详情" min-width="200" />
        <el-table-column prop="severity" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '已处理' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" v-if="row.status !== '已处理'" @click="handleAlert(row)">处理</el-button>
            <span v-else style="color: #999; font-size: 12px">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑规则对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑规则' : '新增规则'" width="600px">
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="eventType">
          <el-select v-model="formData.eventType" placeholder="请选择事件类型" style="width: 100%">
            <el-option label="活动量异常" value="activity_abnormal" />
            <el-option label="进食异常" value="eating_abnormal" />
            <el-option label="饮水异常" value="drinking_abnormal" />
            <el-option label="长时间无活动" value="no_activity" />
            <el-option label="设备离线" value="device_offline" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件" prop="condition">
          <el-input v-model="formData.condition" placeholder="如：活动量 < 20 持续 30分钟" />
        </el-form-item>
        <el-form-item label="阈值" prop="threshold">
          <el-input-number v-model="formData.threshold" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="持续时间" prop="duration">
          <el-input-number v-model="formData.duration" :min="1" :max="1440" />
          <span class="unit">分钟</span>
        </el-form-item>
        <el-form-item label="严重级别" prop="severity">
          <el-radio-group v-model="formData.severity">
            <el-radio label="低">低</el-radio>
            <el-radio label="中">中</el-radio>
            <el-radio label="高">高</el-radio>
            <el-radio label="紧急">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="通知方式" prop="notifyMethod">
          <el-checkbox-group v-model="formData.notifyMethod">
            <el-checkbox label="app">App推送</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="wechat">微信</el-checkbox>
            <el-checkbox label="email">邮件</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="适用圈舍" prop="sheds">
          <el-select v-model="formData.sheds" multiple placeholder="全部圈舍" style="width: 100%">
            <el-option v-for="s in shedOptions" :key="s.id" :label="s.name" :value="s.name" />
          </el-select>
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

const stats = reactive({ totalRules: 5, enabledRules: 4, todayTriggered: 3, unhandled: 1 })
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const shedOptions = ref([
  { id: 1, name: '一号圈舍' }, { id: 2, name: '二号圈舍' },
  { id: 3, name: '三号圈舍' }, { id: 4, name: '四号圈舍' }
])

const ruleList = ref([
  { id: 1, name: '活动量过低告警', eventType: 'activity_abnormal', condition: '活动量 < 20 持续 30分钟', severity: '高', notifyMethod: ['app', 'sms'], enabled: true, triggerCount: 12 },
  { id: 2, name: '长时间未进食', eventType: 'eating_abnormal', condition: '超过 6小时无进食记录', severity: '中', notifyMethod: ['app'], enabled: true, triggerCount: 5 },
  { id: 3, name: '饮水异常', eventType: 'drinking_abnormal', condition: '超过 8小时无饮水记录', severity: '中', notifyMethod: ['app', 'wechat'], enabled: true, triggerCount: 2 },
  { id: 4, name: '设备离线告警', eventType: 'device_offline', condition: '设备离线超过 10分钟', severity: '紧急', notifyMethod: ['app', 'sms', 'wechat'], enabled: true, triggerCount: 8 },
  { id: 5, name: '夜间活动异常', eventType: 'no_activity', condition: '22:00-06:00 活动量 > 80', severity: '低', notifyMethod: ['app'], enabled: false, triggerCount: 0 }
])

const alertHistory = ref([
  { time: '2026-03-13 10:23', ruleName: '活动量过低告警', shed: '二号圈舍', detail: '活动量评分 15, 低于阈值 20, 持续 45分钟', severity: '高', status: '未处理' },
  { time: '2026-03-13 08:15', ruleName: '设备离线告警', shed: '二号圈舍', detail: 'CAM-04 离线, 持续 12分钟', severity: '紧急', status: '已处理' },
  { time: '2026-03-12 16:30', ruleName: '长时间未进食', shed: '三号圈舍', detail: '已超过 7小时无进食记录', severity: '中', status: '已处理' }
])

const formData = reactive({
  id: null as number | null, name: '', eventType: '', condition: '',
  threshold: 20, duration: 30, severity: '中',
  notifyMethod: ['app'] as string[], sheds: [] as string[]
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重级别', trigger: 'change' }]
}

const getEventText = (t: string) => ({
  activity_abnormal: '活动异常', eating_abnormal: '进食异常',
  drinking_abnormal: '饮水异常', no_activity: '无活动', device_offline: '设备离线'
}[t] || t)

const getSeverityType = (s: string) => ({
  '低': 'info', '中': 'warning', '高': 'danger', '紧急': 'danger'
}[s] || 'info')

const getNotifyText = (m: string) => ({
  app: '📱App', sms: '📩短信', wechat: '💬微信', email: '📧邮件'
}[m] || m)

const showAddDialog = () => {
  isEdit.value = false
  Object.assign(formData, { id: null, name: '', eventType: '', condition: '', threshold: 20, duration: 30, severity: '中', notifyMethod: ['app'], sheds: [] })
  dialogVisible.value = true
}

const editRule = (row: any) => { isEdit.value = true; Object.assign(formData, row); dialogVisible.value = true }
const toggleRule = (row: any) => { ElMessage.success(`规则 "${row.name}" 已${row.enabled ? '启用' : '禁用'}`) }
const deleteRule = (row: any) => { ElMessageBox.confirm(`确定删除 "${row.name}"？`, '确认', { type: 'warning' }).then(() => { ElMessage.success('删除成功') }) }
const handleAlert = (row: any) => { row.status = '已处理'; ElMessage.success('已处理') }
const exportAlerts = () => { ElMessage.success('导出功能开发中') }
const loadData = async () => { loading.value = true; setTimeout(() => { loading.value = false }, 300) }

const submitForm = async () => {
  const valid = await formRef.value?.validate()
  if (!valid) return
  submitting.value = true
  try { ElMessage.success(isEdit.value ? '更新成功' : '创建成功'); dialogVisible.value = false }
  finally { submitting.value = false }
}

onMounted(() => loadData())
</script>

<style scoped lang="scss">
.alerts-page {
  .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
    h2 { margin: 0; font-size: 24px; font-weight: 600; }
  }
  .stats-row { margin-bottom: 20px; }
  .stat-card { text-align: center;
    .stat-value { font-size: 32px; font-weight: 600; color: #303133; }
    .stat-label { font-size: 14px; color: #909399; margin-top: 8px; }
    &.success .stat-value { color: #67c23a; }
    &.warning .stat-value { color: #e6a23c; }
  }
  .card-header { display: flex; justify-content: space-between; align-items: center; }
  .notify-tag { margin-right: 4px; font-size: 12px; }
  .unit { margin-left: 8px; color: #909399; }
}
</style>
