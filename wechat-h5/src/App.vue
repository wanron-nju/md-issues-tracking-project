<script setup lang="ts">
import 'vant/lib/index.css'
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { 
  showToast, 
  showLoadingToast, 
  showSuccessToast, 
  showFailToast,
  showImagePreview,
  FloatingBubble,
  showConfirmDialog
} from 'vant'

// Use environment-based API URL:
// - In development (local): http://127.0.0.1:8000
// - In production: /api (relative path)
const API_BASE = import.meta.env.MODE === 'production' 
  ? '/api' 
  : 'http://127.0.0.1:8000'

const STORE_EMPTY = ''
const STORE_ALL = 'All'
const STORE_EMPTY_LABEL = '请选择门店'

const STORES: string[] = [
  '1001 - 明都店',
  '1010 - 魏村店',
  '1020 - 横林1店',
  '1021 - 百丈店',
  '1022 - 东安1店',
  '1028 - 魏村大顺发',
  '1035 - 雪堰2店',
  '1043 - 南都店',
  '1048 - 郑陆2店',
  '1050 - 湟里店',
  '1052 - 横林大顺发',
  '1056 - 潘家店',
  '1057 - 漕桥店',
  '1063 - 安家3店',
  '1068 - 邹区店',
  '1069 - 镇江店',
  '1077 - 礼河店',
  '1003 - 奔牛1店',
  '1005 - 奔牛2店',
  '1009 - 卜弋店',
  '1015 - 郑陆1店',
  '1016 - 村前店',
  '1042 - 农发区店',
  '1051 - 中天店',
  '1055 - 紫云店',
  '1058 - 学府店',
  '1059 - 怀德店',
]

const trackingStoreColumns = [
  { text: '全部门店', value: STORE_ALL },
  ...STORES.map((s) => ({ text: s, value: s })),
]

const storeColumns = [
  { text: STORE_EMPTY_LABEL, value: STORE_EMPTY },
  ...STORES.map((s) => ({ text: s, value: s })),
]

const statusColumns = [
  { text: '待整改', value: '待整改' },
  { text: '已整改', value: '已整改' },
  { text: '全部', value: '全部' },
]

const deleteStatusColumns = [
  { text: '已整改', value: '已整改' },
  { text: '全部', value: '全部' },
]

// Map Chinese status to English for backend
const statusMap: Record<string, string> = {
  '已整改': 'completed',
  '全部': 'all',
}

const currentPage = ref<'home' | 'issue' | 'rectification' | 'tracking' | 'maintenance'>('home')
const storePickerRef = ref<any>(null)

const rectificationStore = ref(STORE_EMPTY)
const rectificationStorePicker = ref(false)
const pendingIssues = ref<any[]>([])

const rectifiedCache = ref<Record<number, any>>({})

const isLoadingRectification = ref(false)
const isSubmittingRectification = ref(false)

const submitDate = ref('')
const selectedStore = ref(STORE_EMPTY)
const content = ref('')
const fileList = ref<any[]>([])

const showCalendar = ref(false)
const showStorePicker = ref(false)
const isSubmitting = ref(false)

const trackingStatus = ref('待整改')
const trackingStatusPicker = ref(false)
const trackingStore = ref(STORE_ALL)
const trackingStorePicker = ref(false)
const trackingStartDate = ref('')
const trackingEndDate = ref('')
const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const isExporting = ref(false)

const maintenanceDate = ref('')
const maintenanceDatePicker = ref(false)
const maintenanceStatus = ref('已整改')
const maintenanceStatusPicker = ref(false)
const isDeleting = ref(false)

const getCurrentTimestamp = () => {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  return `${h}:${m}:${s}`
}

const formatDate = (date: Date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const initToday = () => {
  if (!submitDate.value) {
    submitDate.value = formatDate(new Date())
  }
  trackingStartDate.value = ''
  trackingEndDate.value = formatDate(new Date())
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  maintenanceDate.value = formatDate(thirtyDaysAgo)
}

onMounted(() => {
  initToday()
})

const isSubmitDisabled = computed(() => {
  return (
    !submitDate.value ||
    !selectedStore.value ||
    !content.value.trim() ||
    fileList.value.length === 0
  )
})

const onConfirmCalendar = (value: Date | Date[]) => {
  const date = Array.isArray(value) ? value[0] : value
  submitDate.value = formatDate(date)
  showCalendar.value = false
}

const onCancelCalendar = () => {
  showCalendar.value = false
}

const onStoreConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    selectedStore.value = selectedOptions[0].value
  }
  showStorePicker.value = false
}

const goIssueSubmission = () => {
  currentPage.value = 'issue'
}

const goHome = () => {
  currentPage.value = 'home'
}

const goMaintenance = () => {
  currentPage.value = 'maintenance'
}

const rectificationPickerRef = ref<any>(null)

const goRectification = () => {
  currentPage.value = 'rectification'
}

const goTracking = () => {
  currentPage.value = 'tracking'
}

const handleRectificationPickerWheel = (event: WheelEvent) => {
  event.preventDefault()
  if (!rectificationPickerRef.value) return
  
  const delta = event.deltaY
  const currentIndex = storeColumns.findIndex(
    (col) => col.value === rectificationStore.value
  )
  
  let newIndex = currentIndex
  if (delta > 0) {
    newIndex = Math.min(currentIndex + 1, storeColumns.length - 1)
  } else {
    newIndex = Math.max(currentIndex - 1, 0)
  }
  
  if (newIndex !== currentIndex) {
    rectificationStore.value = storeColumns[newIndex].value
  }
}

const fetchPendingIssues = async () => {
  if (!rectificationStore.value) {
    showToast('请先选择门店')
    return
  }
  
  isLoadingRectification.value = true
  try {
    const response = await axios.get(`${API_BASE}/issues/pending`, {
      params: { store: rectificationStore.value }
    })
    pendingIssues.value = response.data
    rectifiedCache.value = {}
    
    if (pendingIssues.value.length === 0) {
      showToast('该门店暂无待整改问题')
    }
  } catch (e) {
    showToast('获取待整改问题失败')
    console.error('Failed to fetch pending issues:', e)
  } finally {
    isLoadingRectification.value = false
  }
}

const onRectificationStoreConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    rectificationStore.value = selectedOptions[0].value
    pendingIssues.value = []
    rectifiedCache.value = {}
  }
  rectificationStorePicker.value = false
}

const isIssueReady = (issueId: number) => {
  return !!rectifiedCache.value[issueId]
}

const readyCount = computed(() => {
  return Object.keys(rectifiedCache.value).length
})

const isRectificationSubmitDisabled = computed(() => {
  return (
    pendingIssues.value.length === 0 ||
    readyCount.value === 0 ||
    isSubmittingRectification.value
  )
})

const handleFixPhotoUpload = (issueId: number, file: any) => {
  if (file) {
    rectifiedCache.value[issueId] = file
  } else {
    delete rectifiedCache.value[issueId]
  }
}

const deleteFixPhoto = (issueId: number, event: Event) => {
  event.stopPropagation()
  delete rectifiedCache.value[issueId]
}

const previewIssuePhoto = (url: string) => {
  showImagePreview({
    images: [url],
    showIndex: false,
    closeable: true,
  })
}

const previewFixPhoto = (issueId: number) => {
  const file = rectifiedCache.value[issueId]
  if (file && file.objectUrl) {
    showImagePreview({
      images: [file.objectUrl],
      showIndex: false,
      closeable: true,
    })
  }
}

const submitRectifications = async () => {
  if (isRectificationSubmitDisabled.value) return

  const form = new FormData()
  
  const issueIds = Object.keys(rectifiedCache.value).map(Number)
  
  if (issueIds.length === 0) {
    showToast('请先上传整改照片')
    return
  }
  
  issueIds.forEach(id => {
    const file = rectifiedCache.value[id]
    if (file && file.file) {
      form.append('ids', id.toString())
      form.append('fix_photos', file.file)
    }
  })

  const loading = showLoadingToast({
    message: '正在提交...',
    forbidClick: true,
    duration: 0,
  })

  isSubmittingRectification.value = true
  try {
    await axios.post(`${API_BASE}/issues/rectifications`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    
    loading.close()
    showSuccessToast('提交成功！')
    
    rectifiedCache.value = {}
    await fetchPendingIssues()
  } catch (e) {
    loading.close()
    showFailToast('提交失败，请重试')
  } finally {
    isSubmittingRectification.value = false
  }
}

const onTrackingStatusConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    trackingStatus.value = selectedOptions[0].value
  }
  trackingStatusPicker.value = false
}

const onTrackingStoreConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    trackingStore.value = selectedOptions[0].value
  }
  trackingStorePicker.value = false
}

const onConfirmStartDate = (value: Date | Date[]) => {
  const date = Array.isArray(value) ? value[0] : value
  trackingStartDate.value = formatDate(date)
  showStartDatePicker.value = false
}

const onConfirmEndDate = (value: Date | Date[]) => {
  const date = Array.isArray(value) ? value[0] : value
  trackingEndDate.value = formatDate(date)
  showEndDatePicker.value = false
}

const exportToExcel = async () => {
  if (isExporting.value) return
  
  isExporting.value = true
  
  const loading = showLoadingToast({
    message: '正在导出...',
    forbidClick: true,
    duration: 0,
  })
  
  try {
    const params = new URLSearchParams()
    if (trackingStore.value !== STORE_ALL) {
      params.append('store', trackingStore.value)
    }
    if (trackingStartDate.value) {
      params.append('start_date', trackingStartDate.value)
    }
    if (trackingEndDate.value) {
      params.append('end_date', trackingEndDate.value)
    }
    params.append('status', trackingStatus.value)
    
    const url = `${API_BASE}/export-issues?${params.toString()}`
    
    window.open(url, '_blank')
    
    loading.close()
    showSuccessToast('导出成功！')
  } catch (e) {
    loading.close()
    showFailToast('导出失败，请重试')
  } finally {
    isExporting.value = false
  }
}

const onMaintenanceDateConfirm = (value: Date | Date[]) => {
  const date = Array.isArray(value) ? value[0] : value
  maintenanceDate.value = formatDate(date)
  maintenanceDatePicker.value = false
}

const onMaintenanceStatusConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    maintenanceStatus.value = selectedOptions[0].value
  }
  maintenanceStatusPicker.value = false
}

const handleDeleteIssues = async () => {
  if (!maintenanceDate.value) {
    showToast('请选择日期')
    return
  }

  const statusText = maintenanceStatus.value
  
  try {
    const confirmed = await showConfirmDialog({
      title: '确认删除',
      message: `此操作不可逆，确定要永久删除 ${maintenanceDate.value} 之前的${statusText}数据及图片吗？`,
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    
    if (!confirmed) return
    
    isDeleting.value = true
    
    const loading = showLoadingToast({
      message: '正在删除...',
      forbidClick: true,
      duration: 0,
    })
    
    // Map Chinese status to English for backend
    const statusFilter = statusMap[maintenanceStatus.value] || 'all'
    
    const response = await axios.post(`${API_BASE}/delete-issues`, {
      before_date: maintenanceDate.value,
      status_filter: statusFilter,
    })
    
    loading.close()
    showSuccessToast(response.data.message || '删除成功！')
  } catch (e: any) {
    if (e !== 'cancel') {
      showFailToast('删除失败，请重试')
    }
  } finally {
    isDeleting.value = false
  }
}

const handlePickerWheel = (event: WheelEvent) => {
  event.preventDefault()
  if (!storePickerRef.value) return
  
  const delta = event.deltaY
  const currentIndex = storeColumns.findIndex(
    (col) => col.value === selectedStore.value
  )
  
  let newIndex = currentIndex
  if (delta > 0) {
    newIndex = Math.min(currentIndex + 1, storeColumns.length - 1)
  } else {
    newIndex = Math.max(currentIndex - 1, 0)
  }
  
  if (newIndex !== currentIndex) {
    selectedStore.value = storeColumns[newIndex].value
  }
}

const handleSubmit = async () => {
  if (isSubmitDisabled.value || isSubmitting.value) return

  const photo = fileList.value[0]?.file
  if (!photo) {
    showToast('请选择问题照片')
    return
  }

  const timestamp = getCurrentTimestamp()
  const submitDateTime = `${submitDate.value} ${timestamp}`

  const form = new FormData()
  form.append('submit_date', submitDateTime)
  form.append('store', selectedStore.value)
  form.append('content', content.value.trim())
  form.append('issue_photo', photo)

  const loading = showLoadingToast({
    message: '正在提交...',
    forbidClick: true,
    duration: 0,
  })

  isSubmitting.value = true
  try {
    await axios.post(`${API_BASE}/submit-issue`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    
    loading.close()
    showSuccessToast('提交成功！')
    
    content.value = ''
    fileList.value = []
  } catch (e) {
    loading.close()
    showFailToast('提交失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar v-if="currentPage === 'home'" fixed>
      <template #right>
        <div class="maintenance-trigger" @click="goMaintenance"></div>
      </template>
    </van-nav-bar>

    <div v-else class="sticky-header">
      <div class="home-button" @click="goHome">
        <van-icon 
          name="wap-home-o" 
          size="22" 
        />
        <span class="home-button-text">返回</span>
      </div>
      <h1 class="header-title">
        {{ currentPage === 'issue' ? '问题提交' : currentPage === 'rectification' ? '整改反馈' : currentPage === 'tracking' ? '状态追踪' : '数据维护' }}
      </h1>
    </div>

    <div class="page-body">
      <template v-if="currentPage === 'home'">
        <section class="home-hero">
          <h1 class="home-title">明都巡店问题追踪系统</h1>
          <p class="home-subtitle">门店巡检 · 问题管理</p>
        </section>

        <section class="menu-card">
          <p class="menu-intro">
            请选择需要的操作：问题提交、整改反馈或状态追踪。
          </p>
        </section>

        <section class="menu-buttons">
          <van-button
            block
            round
            size="large"
            class="menu-button btn-blue"
            @click="goIssueSubmission"
          >
            <span class="menu-button-title">问题提交</span>
          </van-button>

          <van-button
            block
            round
            size="large"
            class="menu-button btn-blue"
            @click="goRectification"
          >
            <span class="menu-button-title">整改反馈</span>
          </van-button>

          <van-button
            block
            round
            size="large"
            class="menu-button btn-blue"
            @click="goTracking"
          >
            <span class="menu-button-title">状态追踪</span>
          </van-button>
        </section>
      </template>

      <template v-else-if="currentPage === 'issue'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="submitDate"
              label="提交日期"
              readonly
              clickable
              placeholder="请选择日期"
              @click="showCalendar = true"
            >
              <template #right-icon>
                <van-icon name="calendar-o" class="field-icon" />
              </template>
            </van-field>

            <van-field
              v-model="selectedStore"
              label="门店"
              readonly
              is-link
              clickable
              placeholder="请选择门店"
              @click="showStorePicker = true"
            />

            <van-field
              v-model="content"
              type="textarea"
              label="问题描述"
              rows="6"
              autosize
              maxlength="500"
              show-word-limit
              placeholder="请描述现场发现的问题"
            />

            <div class="uploader-row">
              <div class="uploader-label">问题照片</div>
              <van-uploader
                v-model="fileList"
                :max-count="1"
                accept="image/*"
              />
            </div>
          </van-cell-group>

          <div class="submit-wrapper">
            <van-button
              block
              round
              class="btn-submit btn-blue"
              :loading="isSubmitting"
              :disabled="isSubmitDisabled"
              @click="handleSubmit"
            >
              提交问题
            </van-button>
          </div>
        </section>
      </template>

      <template v-else-if="currentPage === 'rectification'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="rectificationStore"
              label="门店"
              readonly
              is-link
              clickable
              placeholder="请选择门店"
              @click="rectificationStorePicker = true"
            />
          </van-cell-group>

          <div class="submit-wrapper">
            <van-button
              block
              round
              class="btn-submit btn-blue"
              :loading="isLoadingRectification"
              :disabled="!rectificationStore"
              @click="fetchPendingIssues"
            >
              获取待整改问题
            </van-button>
          </div>
        </section>

        <section v-if="pendingIssues.length > 0" class="issues-list">
          <van-card
            v-for="issue in pendingIssues"
            :key="issue.id"
            class="issue-card"
            :class="{ 'issue-ready': isIssueReady(issue.id) }"
          >
            <template #thumb>
              <img 
                :src="issue.issue_photo_url" 
                class="issue-photo" 
                @click="previewIssuePhoto(issue.issue_photo_url)"
              />
            </template>
            
            <template #title>
              <div class="issue-title-row">
                <span class="issue-date">{{ issue.submitted_at }}</span>
              </div>
            </template>

            <template #desc>
              <div class="issue-desc-text">
                {{ issue.content }}
              </div>
            </template>

            <template #footer>
              <div class="issue-fix-photo-left">
                <template v-if="isIssueReady(issue.id)">
                  <div class="thumbnail-wrapper" @click="previewFixPhoto(issue.id)">
                    <img 
                      :src="rectifiedCache[issue.id]?.objectUrl" 
                      class="fix-photo-preview"
                    />
                    <van-icon 
                      name="clear" 
                      class="delete-icon"
                      @click="(e) => deleteFixPhoto(issue.id, e)"
                    />
                  </div>
                </template>
                <template v-else>
                  <van-uploader
                    :model-value="rectifiedCache[issue.id] ? [rectifiedCache[issue.id]] : []"
                    :max-count="1"
                    accept="image/*"
                    @update:model-value="(files) => handleFixPhotoUpload(issue.id, files?.[0])"
                  >
                    <van-button size="small" class="btn-light-grey-blue btn-press-effect">
                      上传整改照片
                    </van-button>
                  </van-uploader>
                </template>
              </div>
            </template>
          </van-card>

          <div
            v-if="readyCount > 0"
            class="custom-fab btn-press-effect"
            @click="submitRectifications"
          >
            上传整改
          </div>
        </section>
      </template>

      <template v-else-if="currentPage === 'tracking'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="trackingStatus"
              label="问题状态"
              readonly
              is-link
              clickable
              placeholder="请选择状态"
              @click="trackingStatusPicker = true"
            />

            <van-field
              v-model="trackingStore"
              label="门店"
              readonly
              is-link
              clickable
              placeholder="请选择门店"
              @click="trackingStorePicker = true"
            />

            <van-field
              v-model="trackingStartDate"
              label="开始日期"
              readonly
              clickable
              placeholder="可以留空不填"
              @click="showStartDatePicker = true"
            >
              <template #right-icon>
                <van-icon name="calendar-o" class="field-icon" />
              </template>
            </van-field>

            <van-field
              v-model="trackingEndDate"
              label="结束日期"
              readonly
              clickable
              placeholder="请选择结束日期"
              @click="showEndDatePicker = true"
            >
              <template #right-icon>
                <van-icon name="calendar-o" class="field-icon" />
              </template>
            </van-field>
          </van-cell-group>

          <div class="submit-wrapper">
            <van-button
              block
              round
              class="btn-submit btn-blue"
              :loading="isExporting"
              @click="exportToExcel"
            >
              导出 Excel
            </van-button>
          </div>
        </section>
      </template>

      <template v-else-if="currentPage === 'maintenance'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="maintenanceDate"
              label="截止日期"
              readonly
              clickable
              placeholder="请选择截止日期"
              @click="maintenanceDatePicker = true"
            >
              <template #right-icon>
                <van-icon name="calendar-o" class="field-icon" />
              </template>
            </van-field>

            <van-field
              v-model="maintenanceStatus"
              label="问题状态"
              readonly
              is-link
              clickable
              placeholder="请选择状态"
              @click="maintenanceStatusPicker = true"
            />
          </van-cell-group>

          <div class="submit-wrapper">
            <van-button
              block
              round
              class="btn-submit btn-danger btn-press-effect"
              :loading="isDeleting"
              @click="handleDeleteIssues"
            >
              删除问题数据及对应图片
            </van-button>
          </div>

          <div class="warning-card">
            <p class="warning-text">
              ⚠️ 警告：此操作将永久删除指定日期之前的问题记录及对应的图片文件，且无法恢复。请谨慎操作！
            </p>
          </div>
        </section>
      </template>
    </div>

    <van-calendar
      v-model:show="showCalendar"
      color="#3b82f6"
      :show-confirm="true"
      :min-date="new Date(2020, 0, 1)"
      @confirm="onConfirmCalendar"
      @cancel="onCancelCalendar"
    />

    <van-calendar
      v-model:show="showStartDatePicker"
      color="#3b82f6"
      :show-confirm="true"
      :min-date="new Date(2020, 0, 1)"
      @confirm="onConfirmStartDate"
      @cancel="showStartDatePicker = false"
    />

    <van-calendar
      v-model:show="showEndDatePicker"
      color="#3b82f6"
      :show-confirm="true"
      :min-date="new Date(2020, 0, 1)"
      @confirm="onConfirmEndDate"
      @cancel="showEndDatePicker = false"
    />

    <van-calendar
      v-model:show="maintenanceDatePicker"
      color="#dc3545"
      :show-confirm="true"
      :min-date="new Date(2020, 0, 1)"
      @confirm="onMaintenanceDateConfirm"
      @cancel="maintenanceDatePicker = false"
    />

    <van-popup
      v-model:show="showStorePicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
      @wheel.prevent="handlePickerWheel"
    >
      <van-picker
        v-if="showStorePicker"
        ref="storePickerRef"
        :model-value="[selectedStore]"
        :columns="storeColumns"
        title="选择门店"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (selectedStore = (v && v[0]) ?? '')"
        @confirm="onStoreConfirm"
        @cancel="showStorePicker = false"
      />
    </van-popup>

    <van-popup
      v-model:show="rectificationStorePicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
      @wheel.prevent="handleRectificationPickerWheel"
    >
      <van-picker
        ref="rectificationPickerRef"
        :model-value="[rectificationStore]"
        :columns="storeColumns"
        title="选择门店"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (rectificationStore = (v && v[0]) ?? '')"
        @confirm="onRectificationStoreConfirm"
        @cancel="rectificationStorePicker = false"
      />
    </van-popup>

    <van-popup
      v-model:show="trackingStatusPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '40%' }"
    >
      <van-picker
        :model-value="[trackingStatus]"
        :columns="statusColumns"
        title="选择问题状态"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (trackingStatus = (v && v[0]) ?? '')"
        @confirm="onTrackingStatusConfirm"
        @cancel="trackingStatusPicker = false"
      />
    </van-popup>

    <van-popup
      v-model:show="trackingStorePicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
    >
      <van-picker
        :model-value="[trackingStore]"
        :columns="trackingStoreColumns"
        title="选择门店"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (trackingStore = (v && v[0]) ?? '')"
        @confirm="onTrackingStoreConfirm"
        @cancel="trackingStorePicker = false"
      />
    </van-popup>

    <van-popup
      v-model:show="maintenanceStatusPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '40%' }"
    >
      <van-picker
        :model-value="[maintenanceStatus]"
        :columns="deleteStatusColumns"
        title="选择问题状态"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (maintenanceStatus = (v && v[0]) ?? '')"
        @confirm="onMaintenanceStatusConfirm"
        @cancel="maintenanceStatusPicker = false"
      />
    </van-popup>
  </div>
</template>

<script lang="ts">
export default {
  data() {
    return {
      xy: { x: 20, y: 20 } as { x: number; y: number }
    }
  }
}
</script>

<style scoped>
.page {
  min-height: 100dvh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.page-body {
  flex: 1;
  padding: 56px 12px 100px;
  box-sizing: border-box;
  max-width: 640px;
  margin: 0 auto;
  width: 100%;
  overflow-y: auto;
}

.maintenance-trigger {
  width: 50px;
  height: 30px;
  opacity: 0;
  cursor: pointer;
}

.sticky-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.home-button {
  position: absolute;
  left: 16px;
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #ff9800;
  font-weight: bold;
}

.home-button-text {
  margin-left: 4px;
  font-size: 14px;
}

.header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #323233;
}

.home-hero {
  margin-top: 40px;
  margin-bottom: 24px;
  text-align: center;
}

.home-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  line-height: 1.3;
}

.home-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #6b7280;
}

.form-card {
  margin-top: 12px;
}

.field-icon {
  font-size: 18px;
  color: #9ca3af;
}

.uploader-row {
  display: flex;
  align-items: center;
  padding: 12px 16px 16px;
}

.uploader-label {
  width: 70px;
  font-size: 14px;
  color: #323233;
}

.submit-wrapper {
  margin: 20px 12px 0;
}

.menu-card {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(59, 130,246, 0.06);
  border: 1px solid rgba(59,130,246, 0.16);
}

.menu-intro {
  margin: 0;
  font-size: 13px;
  color: #374151;
}

.menu-buttons {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.menu-button {
  height: 72px;
  padding: 12px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s ease;
}

.menu-button:active {
  transform: scale(0.97);
}

.menu-button-title {
  font-size: 17px;
  font-weight: 600;
  color: white;
  text-align: center;
}

.btn-blue {
  background-color: rgb(116, 140, 171) !important;
  border-color: rgb(116, 140, 171) !important;
  color: white !important;
  transition: transform 0.1s ease;
}

.btn-blue:hover,
.btn-blue:active {
  background-color: rgb(100, 122, 155) !important;
  border-color: rgb(100, 122, 155) !important;
}

.btn-blue:active {
  transform: scale(0.97);
}

.btn-danger {
  background-color: #dc3545 !important;
  border-color: #dc3545 !important;
  color: white !important;
  transition: transform 0.1s ease;
}

.btn-danger:hover,
.btn-danger:active {
  background-color: #c82333 !important;
  border-color: #c82333 !important;
}

.btn-danger:active {
  transform: scale(0.97);
}

.btn-light-grey-blue {
  background-color: rgb(175, 187, 205) !important;
  border-color: rgb(175, 187, 205) !important;
  color: black !important;
  transition: transform 0.1s ease;
}

.btn-light-grey-blue:active {
  transform: scale(0.97);
}

.custom-fab {
  position: fixed !important;
  bottom: 30px !important;
  right: 20px !important;
  z-index: 9999 !important;
  width: 130px !important;
  height: 48px !important;
  border-radius: 24px !important;
  background: rgba(2, 44, 72, 0.4) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: white !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  cursor: pointer;
  transition: transform 0.1s ease;
}

.custom-fab:active {
  transform: scale(0.95);
}

.btn-press-effect {
  transition: transform 0.1s ease;
}

.btn-press-effect:active {
  transform: scale(0.97);
}

.warning-card {
  margin: 20px 12px 0;
  padding: 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
}

.warning-text {
  margin: 0;
  font-size: 13px;
  color: #856404;
  line-height: 1.5;
}

.issues-list {
  margin-top: 16px;
  padding: 0 12px 80px;
  position: relative;
}

.issue-card {
  margin-bottom: 12px;
  transition: background-color 0.3s ease;
  border-bottom: 1px solid #eeeeee;
}

.issue-ready {
  background-color: #d4edda !important;
}

.issue-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.issue-date {
  font-weight: 500;
  color: #555;
  font-size: 12px;
}

.issue-desc-text {
  margin-top: 4px;
  color: #333;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  text-align: left;
}

.issue-photo {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
}

.issue-fix-photo-left {
  margin-top: 8px;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
}

.thumbnail-wrapper {
  position: relative;
  display: inline-block;
}

.fix-photo-preview {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  border: 2px solid #28a745;
  cursor: pointer;
}

.delete-icon {
  position: absolute;
  top: -6px;
  right: -6px;
  background-color: #dc3545;
  color: white;
  border-radius: 50%;
  font-size: 14px;
  padding: 2px;
  cursor: pointer;
}

@media (min-width: 768px) {
  .page-body {
    padding: 64px 24px 120px;
  }

  .submit-wrapper {
    margin-inline: 24px;
  }
}
</style>
