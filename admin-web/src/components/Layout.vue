<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <span class="logo-icon">🦌</span>
        <span class="logo-text">林麝监测</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#fff"
        text-color="#606266"
        active-text-color="#2E7D32"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><VideoCamera /></el-icon>
          <span>设备管理</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Bell /></el-icon>
          <span>报警中心</span>
        </el-menu-item>
        <el-menu-item index="/animals">
          <el-icon><User /></el-icon>
          <span>林麝管理</span>
        </el-menu-item>
        <el-menu-item index="/data">
          <el-icon><TrendCharts /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <breadcrumb />
        <div class="header-right">
          <el-badge :value="3" class="message-badge">
            <el-icon :size="20"><Bell /></el-icon>
          </el-badge>
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span>管理员</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item>修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { 
  HomeFilled, 
  VideoCamera, 
  Bell, 
  User, 
  TrendCharts, 
  UserFilled, 
  Setting,
  ArrowDown 
} from '@element-plus/icons-vue'

const router = useRouter()

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid #e4e7ed;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #2E7D32;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.message-badge {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
}
</style>
