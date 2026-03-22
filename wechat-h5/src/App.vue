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
  showConfirmDialog
} from 'vant'

// Use environment-based API URL:
// - In development (local): http://127.0.0.1:8000
// - In production: /api (relative path)
const API_BASE = import.meta.env.MODE === 'production' 
  ? '/api' 
  : 'http://127.0.0.1:8000'

/**
 * Get full image URL from relative path
 * @param path - Relative path like '/uploads/filename.jpg' or full URL
 * @returns Full URL with API base prepended
 */
const getImageUrl = (path: string): string => {
  if (!path) return ''
  // If already a full URL, return as-is
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  // Prepend API_BASE for relative paths
  return `${API_BASE}${path}`
}

const STORE_EMPTY = ''
const STORE_ALL = 'All'
const OWNER_ALL = 'All'
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
  { text: '全部问题状态', value: '全部' },
  { text: '待整改', value: '待整改' },
  { text: '已整改', value: '已整改' },
]

const deleteStatusColumns = [
  { text: '已整改', value: '已整改' },
  { text: '全部', value: '全部' },
]

// Issue owner options (责任部门)
const ISSUE_OWNER_EMPTY = ''
const ISSUE_OWNER_UNASSIGNED = '<由营运组分派>'

const ISSUE_OWNERS: string[] = [
  '门店',
  '采购非食组',
  '采购农副组',
  '采购食品组',
  '品类组',
  '生鲜部（除水果组外）',
  '生鲜部（水果组）',
  '联营绿洁',
  '营运部',
  '财务部',
  '工程部',
  '企划部',
  '信息部',
]

// Full list with unassigned (for submission page)
const issueOwnerColumns = [
  { text: ISSUE_OWNER_UNASSIGNED, value: ISSUE_OWNER_UNASSIGNED },
  ...ISSUE_OWNERS.map((s) => ({ text: s, value: s })),
]

// Filtered list without unassigned (for rectification and assignment pages)
const issueOwnerColumnsFiltered = ISSUE_OWNERS.map((s) => ({ text: s, value: s }))

// Map Chinese status to English for backend
const statusMap: Record<string, string> = {
  '已整改': 'completed',
  '全部': 'all',
}

const currentPage = ref<'home' | 'issue' | 'rectification' | 'tracking' | 'maintenance' | 'assignment'>('home')

// ============ SUBMISSION PAGE STATE ============
const submitDate = ref('')
const selectedStore = ref(STORE_EMPTY)
const content = ref('')
const issueOwner = ref(ISSUE_OWNER_EMPTY)
const fileList = ref<any[]>([])

const showCalendar = ref(false)
const showStorePicker = ref(false)
const showIssueOwnerPicker = ref(false)
const isSubmitting = ref(false)

// ============ RECTIFICATION PAGE STATE ============
const rectificationStore = ref(STORE_EMPTY)
const rectificationStorePicker = ref(false)
const rectificationOwner = ref(ISSUE_OWNER_EMPTY)
const rectificationOwnerPicker = ref(false)
const pendingIssues = ref<any[]>([])
const rectifiedCache = ref<Record<number, { file?: any; comments?: string; originalComments?: string }>>({})
const isLoadingRectification = ref(false)
const isSubmittingRectification = ref(false)

// Rectification filter validation - both store AND owner required
const isRectificationFilterValid = computed(() => {
  return rectificationStore.value && rectificationOwner.value
})

// ============ ASSIGNMENT PAGE STATE ============
const assignmentDate = ref('')
const assignmentDatePicker = ref(false)
const assignmentOwnerPicker = ref(false)
const unassignedIssues = ref<any[]>([])
const assignmentCache = ref<Record<number, string>>({})
const isLoadingAssignment = ref(false)
const isSubmittingAssignment = ref(false)

// For per-card owner selection
const showAssignmentOwnerPicker = ref<Record<number, boolean>>({})
const currentAssigningIssue = ref<number | null>(null)

// ============ TRACKING PAGE STATE ============
const trackingStatus = ref('全部')
const trackingStatusPicker = ref(false)

// Status uses computed getter/setter pattern (like Store and Owner)
const trackingStatusDisplay = computed({
  get: () => trackingStatus.value === '全部' ? '全部问题状态' : trackingStatus.value,
  set: (v) => { trackingStatus.value = v }
})

const trackingStore = ref(STORE_ALL)
const trackingStorePicker = ref(false)

// Store uses computed getter/setter pattern
const trackingStoreDisplay = computed({
  get: () => trackingStore.value === STORE_ALL ? '全部门店' : trackingStore.value,
  set: (v) => { trackingStore.value = v }
})

// Owner uses computed getter/setter pattern
const trackingOwner = ref(OWNER_ALL)
const trackingOwnerPicker = ref(false)
const trackingOwnerDisplay = computed({
  get: () => trackingOwner.value === OWNER_ALL ? '全部责任部门' : trackingOwner.value,
  set: (v) => { trackingOwner.value = v }
})

// Issue owner columns for tracking page (includes "All" option with unassigned)
const issueOwnerColumnsForTracking = computed(() => [
  { text: '全部责任部门', value: OWNER_ALL },
  { text: '<由营运组分派>', value: ISSUE_OWNER_UNASSIGNED },
  ...ISSUE_OWNERS.map((s) => ({ text: s, value: s })),
])

const trackingStartDate = ref('')
const trackingEndDate = ref('')
const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const isExporting = ref(false)

// ============ MAINTENANCE PAGE STATE ============
const maintenanceDate = ref('')
const maintenanceDatePicker = ref(false)
const maintenanceStatus = ref('已整改')
const maintenanceStatusPicker = ref(false)
const isDeleting = ref(false)

// ============ REFS ============
const storePickerRef = ref<any>(null)
const rectificationPickerRef = ref<any>(null)
const issueOwnerPickerRef = ref<any>(null)
const assignmentOwnerPickerRef = ref<any>(null)

// ============ UTILITY FUNCTIONS ============
/**
 * Extract clean store name from full store string
 * e.g., "1010 - 魏村店" -> "魏村店"
 */
const getCleanStoreName = (store: string): string => {
  if (!store) return ''
  const parts = store.split(' - ')
  return parts.length > 1 ? parts[1] : store
}

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
  // Set both start and end dates to today by default
  const today = formatDate(new Date())
  trackingStartDate.value = today
  trackingEndDate.value = today
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  maintenanceDate.value = formatDate(thirtyDaysAgo)
  assignmentDate.value = today
}

onMounted(() => {
  initToday()
})

// ============ COMPUTED ============
// Submission validation - include issueOwner
const isSubmitDisabled = computed(() => {
  return (
    !submitDate.value ||
    !selectedStore.value ||
    !content.value.trim() ||
    fileList.value.length === 0 ||
    !issueOwner.value
  )
})

// Assignment - check if at least one card has owner selected
const hasAssignmentChanges = computed(() => {
  return Object.keys(assignmentCache.value).length > 0
})

const isAssignmentSubmitDisabled = computed(() => {
  return !hasAssignmentChanges.value || isSubmittingAssignment.value
})

// Rectification - check if any card has changes (comments or photo)
const rectificationChangesCount = computed(() => {
  return Object.keys(rectifiedCache.value).filter(id => {
    const cache = rectifiedCache.value[Number(id)]
    return cache && (cache.comments || cache.file)
  }).length
})

const isRectificationSubmitDisabled = computed(() => {
  return (
    pendingIssues.value.length === 0 ||
    rectificationChangesCount.value === 0 ||
    isSubmittingRectification.value
  )
})

// ============ SUBMISSION PAGE HANDLERS ============
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

const onIssueOwnerConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    issueOwner.value = selectedOptions[0].value
  }
  showIssueOwnerPicker.value = false
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

const handleIssueOwnerPickerWheel = (event: WheelEvent) => {
  event.preventDefault()
  if (!issueOwnerPickerRef.value) return
  
  const delta = event.deltaY
  const currentIndex = issueOwnerColumns.findIndex(
    (col) => col.value === issueOwner.value
  )
  
  let newIndex = currentIndex
  if (delta > 0) {
    newIndex = Math.min(currentIndex + 1, issueOwnerColumns.length - 1)
  } else {
    newIndex = Math.max(currentIndex - 1, 0)
  }
  
  if (newIndex !== currentIndex) {
    issueOwner.value = issueOwnerColumns[newIndex].value
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
  form.append('issue_owner', issueOwner.value)

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
    
    // Retention: Keep Date and Store, reset others
    content.value = ''
    fileList.value = []
    issueOwner.value = ISSUE_OWNER_EMPTY
  } catch (e) {
    loading.close()
    showFailToast('提交失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}

// ============ NAVIGATION ============
const goIssueSubmission = () => {
  currentPage.value = 'issue'
}

const goHome = () => {
  currentPage.value = 'home'
}

const goMaintenance = () => {
  currentPage.value = 'maintenance'
}

const goRectification = () => {
  currentPage.value = 'rectification'
}

const goTracking = () => {
  currentPage.value = 'tracking'
}

const goAssignment = () => {
  currentPage.value = 'assignment'
}

// ============ RECTIFICATION PAGE HANDLERS ============
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
  if (!rectificationOwner.value) {
    showToast('请先选择责任部门')
    return
  }
  
  isLoadingRectification.value = true
  try {
    const params: any = {}
    // Add owner filter (required)
    params.owner = rectificationOwner.value
    
    // Add store filter only if selected (optional)
    if (rectificationStore.value) {
      params.store = rectificationStore.value
    }
    
    const response = await axios.get(`${API_BASE}/issues/pending`, {
      params
    })
    pendingIssues.value = response.data
    rectifiedCache.value = {}
    
    // Pre-populate cache with original fix_comments for display
    pendingIssues.value.forEach((issue: any) => {
      if (issue.fix_comments) {
        rectifiedCache.value[issue.id] = {
          comments: issue.fix_comments,
          originalComments: issue.fix_comments
        }
      }
    })
    
    if (pendingIssues.value.length === 0) {
      showToast('暂无待整改问题')
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

const onRectificationOwnerConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    rectificationOwner.value = selectedOptions[0].value
    pendingIssues.value = []
    rectifiedCache.value = {}
  }
  rectificationOwnerPicker.value = false
}

// Dynamic card background based on changes
// Only trigger colored background if user MANUALLY changed from original
const getRectificationCardClass = (issueId: number): string => {
  const cache = rectifiedCache.value[issueId]
  if (!cache) return ''
  if (cache.file) return 'issue-fixed-photo'
  // Orange if comments exist and differ from original (or original was empty/undefined)
  if (cache.comments) {
    // If originalComments is undefined, it started as empty, so any non-empty comments = changed
    if (cache.originalComments === undefined || cache.comments !== cache.originalComments) {
      return 'issue-comments-changed'
    }
  }
  return ''
}

const isIssueReady = (issueId: number) => {
  const cache = rectifiedCache.value[issueId]
  return !!(cache && (cache.file || cache.comments))
}

const readyCount = computed(() => {
  return Object.keys(rectifiedCache.value).filter(id => {
    const cache = rectifiedCache.value[Number(id)]
    return cache && (cache.file || cache.comments)
  }).length
})

const handleFixPhotoUpload = (issueId: number, file: any) => {
  if (!rectifiedCache.value[issueId]) {
    rectifiedCache.value[issueId] = {}
  }
  if (file) {
    rectifiedCache.value[issueId].file = file
  } else {
    delete rectifiedCache.value[issueId].file
  }
}

const handleFixCommentsChange = (issueId: number, comments: string) => {
  if (!rectifiedCache.value[issueId]) {
    rectifiedCache.value[issueId] = {}
  }
  if (comments && comments.trim()) {
    rectifiedCache.value[issueId].comments = comments.trim()
  } else {
    delete rectifiedCache.value[issueId].comments
  }
}

const deleteFixPhoto = (issueId: number, event: Event) => {
  event.stopPropagation()
  if (rectifiedCache.value[issueId]) {
    delete rectifiedCache.value[issueId].file
    // If no comments either, remove the entry
    if (!rectifiedCache.value[issueId].comments) {
      delete rectifiedCache.value[issueId]
    }
  }
}

const previewIssuePhoto = (url: string) => {
  showImagePreview({
    images: [url],
    showIndex: false,
    closeable: true,
  })
}

const previewFixPhoto = (issueId: number) => {
  const file = rectifiedCache.value[issueId]?.file
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
  
  // Get all issues with changes
  const issueIds = Object.keys(rectifiedCache.value)
    .filter(id => {
      const cache = rectifiedCache.value[Number(id)]
      return cache && (cache.file || cache.comments)
    })
    .map(Number)
  
  if (issueIds.length === 0) {
    showToast('请先添加整改照片或回复')
    return
  }
  
  // Add IDs
  issueIds.forEach(id => {
    form.append('ids', id.toString())
  })
  
  // Add photos (use empty string for issues without photo changes)
  issueIds.forEach(id => {
    const cache = rectifiedCache.value[id]
    if (cache && cache.file && cache.file.file) {
      form.append('fix_photos', cache.file.file)
    }
    // Note: Can't add empty placeholders in multipart, handled by backend
  })
  
  // Add comments as JSON array (only for issues with comments)
  const commentsList: (string | null)[] = issueIds.map(id => {
    const cache = rectifiedCache.value[id]
    return cache?.comments || null
  })
  form.append('fix_comments', JSON.stringify(commentsList))

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

// ============ ASSIGNMENT PAGE HANDLERS ============
const onAssignmentDateConfirm = (value: Date | Date[]) => {
  const date = Array.isArray(value) ? value[0] : value
  assignmentDate.value = formatDate(date)
  assignmentDatePicker.value = false
}

const fetchUnassignedIssues = async () => {
  isLoadingAssignment.value = true
  try {
    const params: any = {}
    // For backlog logic: only use end_date to get all issues up to and including that date
    if (assignmentDate.value) {
      params.end_date = assignmentDate.value
    }
    
    const response = await axios.get(`${API_BASE}/api/issues/unassigned`, {
      params
    })
    unassignedIssues.value = response.data
    assignmentCache.value = {}
    
    if (unassignedIssues.value.length === 0) {
      showToast('暂无待分配问题')
    }
  } catch (e) {
    showToast('获取待分配问题失败')
    console.error('Failed to fetch unassigned issues:', e)
  } finally {
    isLoadingAssignment.value = false
  }
}

const handleAssignmentOwnerChange = (issueId: number, owner: string) => {
  if (owner) {
    assignmentCache.value[issueId] = owner
  } else {
    delete assignmentCache.value[issueId]
  }
}

const getAssignmentCardClass = (issueId: number): string => {
  if (assignmentCache.value[issueId]) {
    return 'issue-assigned'
  }
  return ''
}

const submitAssignments = async () => {
  if (isAssignmentSubmitDisabled.value) return

  const assignments = Object.entries(assignmentCache.value).map(([id, owner]) => ({
    id: Number(id),
    issue_owner: owner
  }))
  
  const loading = showLoadingToast({
    message: '正在提交...',
    forbidClick: true,
    duration: 0,
  })

  isSubmittingAssignment.value = true
  try {
    await axios.post(`${API_BASE}/issues/assignments`, {
      assignments
    })
    
    loading.close()
    showSuccessToast('提交成功！')
    
    assignmentCache.value = {}
    await fetchUnassignedIssues()
  } catch (e) {
    loading.close()
    showFailToast('提交失败，请重试')
  } finally {
    isSubmittingAssignment.value = false
  }
}

// ============ TRACKING PAGE HANDLERS ============
const onTrackingStatusConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    // Update the value (computed setter will update display)
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

const onTrackingOwnerConfirm = ({
  selectedOptions,
}: {
  selectedOptions: { text: string; value: string }[]
}) => {
  if (selectedOptions && selectedOptions[0]) {
    // Update the value (computed setter will update display)
    trackingOwner.value = selectedOptions[0].value
  }
  trackingOwnerPicker.value = false
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
    
    // Use the backend value directly (trackingStatus.value)
    params.append('status', trackingStatus.value)
    
    // Add owner filter if not "All"
    if (trackingOwner.value !== OWNER_ALL) {
      params.append('owner', trackingOwner.value)
    }
    
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

// ============ MAINTENANCE PAGE HANDLERS ============
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
        <van-icon name="wap-home-o" size="22" />
        <span class="home-button-text">返回</span>
      </div>
      <h1 class="header-title">
        {{ 
          currentPage === 'issue' ? '问题提交' : 
          currentPage === 'rectification' ? '整改反馈' : 
          currentPage === 'tracking' ? '状态追踪' : 
          currentPage === 'assignment' ? '责任分派' : 
          '数据维护' 
        }}
      </h1>
    </div>

    <div class="page-body">
      <!-- ============ HOME PAGE ============ -->
      <template v-if="currentPage === 'home'">
        <section class="home-hero">
          <h1 class="home-title">明都巡店问题追踪系统</h1>
          <p class="home-subtitle">门店巡检 · 问题管理</p>
        </section>

        <section class="menu-card">
          <p class="menu-intro">
            请选择需要的操作：问题提交、责任分派、整改反馈或状态追踪。
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
            @click="goAssignment"
          >
            <span class="menu-button-title">责任分派</span>
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

      <!-- ============ ISSUE SUBMISSION PAGE ============ -->
      <template v-else-if="currentPage === 'issue'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="submitDate"
              label="提交日期"
              label-width="6.5em"
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
              label-width="6.5em"
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
              label-width="6.5em"
              rows="6"
              autosize
              maxlength="500"
              show-word-limit
              placeholder="请描述现场发现的问题"
            />

            <van-field
              v-model="issueOwner"
              label="责任部门"
              label-width="6.5em"
              readonly
              is-link
              clickable
              placeholder="请选择责任部门"
              @click="showIssueOwnerPicker = true"
            />

            <van-field
              label="问题照片"
              label-width="6.5em"
            >
              <template #input>
                <div class="uploader-wrapper">
                  <van-uploader
                    v-model="fileList"
                    :max-count="1"
                    accept="image/*"
                  />
                </div>
              </template>
            </van-field>
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

      <!-- ============ RECTIFICATION PAGE ============ -->
      <template v-else-if="currentPage === 'rectification'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="rectificationOwner"
              label="责任部门"
              readonly
              is-link
              clickable
              placeholder="请选择责任部门"
              @click="rectificationOwnerPicker = true"
            />

            <van-field
              v-model="rectificationStore"
              label="门店"
              readonly
              is-link
              clickable
              placeholder="请选择门店（可留空）"
              @click="rectificationStorePicker = true"
            />
          </van-cell-group>

          <div class="submit-wrapper">
            <van-button
              block
              round
              class="btn-submit btn-blue"
              :loading="isLoadingRectification"
              :disabled="!rectificationOwner"
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
            :class="getRectificationCardClass(issue.id)"
          >
            <template #thumb>
              <img 
                :src="getImageUrl(issue.issue_photo_url)" 
                class="issue-photo" 
                @click="previewIssuePhoto(getImageUrl(issue.issue_photo_url))"
              />
            </template>
            
            <template #title>
              <!-- Row 1: Date -->
              <div class="issue-header-row">
                <span class="issue-date">{{ issue.submitted_at }}</span>
              </div>
              <!-- Row 2: Tags -->
              <div class="issue-tags-row">
                <span class="issue-store">{{ getCleanStoreName(issue.store) }}</span>
                <span class="issue-owner-badge">{{ issue.issue_owner }}</span>
              </div>
            </template>

            <template #desc>
              <div class="issue-desc-text">
                {{ issue.content }}
              </div>
            </template>

            <template #footer>
              <div class="rectification-content">
                <!-- Fix Comments -->
                <van-field
                  :model-value="rectifiedCache[issue.id]?.comments || ''"
                  type="textarea"
                  rows="2"
                  autosize
                  maxlength="500"
                  placeholder="整改回复（选填）"
                  class="fix-comments-field"
                  @update:model-value="(v) => handleFixCommentsChange(issue.id, v || '')"
                />
                
                <!-- Fix Photo -->
                <div class="issue-fix-photo-left">
                  <template v-if="rectifiedCache[issue.id]?.file">
                    <div class="thumbnail-wrapper" @click="previewFixPhoto(issue.id)">
                      <img 
                        :src="rectifiedCache[issue.id]?.file?.objectUrl" 
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
                      :model-value="rectifiedCache[issue.id]?.file ? [rectifiedCache[issue.id].file] : []"
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
              </div>
            </template>
          </van-card>

          <div
            v-if="rectificationChangesCount > 0"
            class="custom-fab btn-press-effect"
            @click="submitRectifications"
          >
            确认提交
          </div>
        </section>
      </template>

      <!-- ============ ASSIGNMENT PAGE ============ -->
      <template v-else-if="currentPage === 'assignment'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="assignmentDate"
              label="日期截至"
              readonly
              clickable
              placeholder="可以留空"
              @click="assignmentDatePicker = true"
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
              :loading="isLoadingAssignment"
              @click="fetchUnassignedIssues"
            >
              获取尚无责任归属的问题
            </van-button>
          </div>
        </section>

        <section v-if="unassignedIssues.length > 0" class="issues-list">
          <van-card
            v-for="issue in unassignedIssues"
            :key="issue.id"
            class="issue-card"
            :class="getAssignmentCardClass(issue.id)"
          >
            <template #thumb>
              <img 
                :src="getImageUrl(issue.issue_photo_url)" 
                class="issue-photo" 
                @click="previewIssuePhoto(getImageUrl(issue.issue_photo_url))"
              />
            </template>
            
            <template #title>
              <!-- Row 1: Date -->
              <div class="issue-header-row">
                <span class="issue-date">{{ issue.submitted_at }}</span>
              </div>
              <!-- Row 2: Tags -->
              <div class="issue-tags-row">
                <span class="issue-store">{{ getCleanStoreName(issue.store) }}</span>
              </div>
            </template>

            <template #desc>
              <div class="issue-desc-text">
                {{ issue.content }}
              </div>
            </template>

            <template #footer>
              <van-field
                :model-value="assignmentCache[issue.id] || ''"
                label="分派责任部门"
                readonly
                is-link
                clickable
                placeholder="选择责任部门"
                class="assignment-field"
                @click="() => { currentAssigningIssue = issue.id; assignmentOwnerPicker = true }"
              />
            </template>
          </van-card>

          <div
            v-if="hasAssignmentChanges"
            class="custom-fab btn-press-effect"
            @click="submitAssignments"
          >
            提交分派
          </div>
        </section>
      </template>

      <!-- ============ TRACKING PAGE ============ -->
      <template v-else-if="currentPage === 'tracking'">
        <section class="form-card">
          <van-cell-group inset>
            <van-field
              v-model="trackingStatusDisplay"
              label="问题状态"
              readonly
              is-link
              clickable
              placeholder="请选择状态"
              @click="trackingStatusPicker = true"
            />

            <!-- Owner filter ABOVE Store filter -->
            <van-field
              v-model="trackingOwnerDisplay"
              label="责任部门"
              readonly
              is-link
              clickable
              placeholder="请选择责任部门"
              @click="trackingOwnerPicker = true"
            />

            <van-field
              v-model="trackingStoreDisplay"
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

      <!-- ============ MAINTENANCE PAGE ============ -->
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

    <!-- ============ CALENDARS ============ -->
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

    <van-calendar
      v-model:show="assignmentDatePicker"
      color="#3b82f6"
      :show-confirm="true"
      :min-date="new Date(2020, 0, 1)"
      @confirm="onAssignmentDateConfirm"
      @cancel="assignmentDatePicker = false"
    />

    <!-- ============ PICKERS ============ -->
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
      v-model:show="showIssueOwnerPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
      @wheel.prevent="handleIssueOwnerPickerWheel"
    >
      <van-picker
        v-if="showIssueOwnerPicker"
        ref="issueOwnerPickerRef"
        :model-value="[issueOwner]"
        :columns="issueOwnerColumns"
        title="选择责任部门"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (issueOwner = (v && v[0]) ?? '')"
        @confirm="onIssueOwnerConfirm"
        @cancel="showIssueOwnerPicker = false"
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
      v-model:show="rectificationOwnerPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
    >
      <van-picker
        :model-value="[rectificationOwner]"
        :columns="issueOwnerColumnsFiltered"
        title="选择责任部门"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (rectificationOwner = (v && v[0]) ?? '')"
        @confirm="onRectificationOwnerConfirm"
        @cancel="rectificationOwnerPicker = false"
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
        :model-value="[trackingStatusDisplay]"
        :columns="statusColumns"
        title="选择问题状态"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (trackingStatusDisplay = (v && v[0]) ?? '')"
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

    <!-- Tracking Owner Picker -->
    <van-popup
      v-model:show="trackingOwnerPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
    >
      <van-picker
        :model-value="[trackingOwnerDisplay]"
        :columns="issueOwnerColumnsForTracking"
        title="选择责任部门"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => (trackingOwnerDisplay = (v && v[0]) ?? '')"
        @confirm="onTrackingOwnerConfirm"
        @cancel="trackingOwnerPicker = false"
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

    <!-- Assignment Owner Picker (for all cards) -->
    <van-popup
      v-model:show="assignmentOwnerPicker"
      position="bottom"
      round
      teleport="body"
      class="store-picker-popup"
      :style="{ height: '50%' }"
    >
      <van-picker
        :model-value="currentAssigningIssue ? [assignmentCache[currentAssigningIssue] || ''] : ['']"
        :columns="issueOwnerColumnsFiltered"
        title="选择责任部门"
        :item-height="44"
        :visible-option-num="5"
        :swipe-duration="800"
        allow-force-render
        @update:model-value="(v) => { if (currentAssigningIssue) { handleAssignmentOwnerChange(currentAssigningIssue, (v && v[0]) || '') } }"
        @confirm="() => { assignmentOwnerPicker = false; currentAssigningIssue = null }"
        @cancel="() => { assignmentOwnerPicker = false; currentAssigningIssue = null }"
      />
    </van-popup>
  </div>
</template>

<style>
/* Global Overflow Lockdown - apply to all elements */
html, body {
  overflow-x: hidden !important;
  max-width: 100vw;
}

#app {
  overflow-x: hidden !important;
  max-width: 100vw;
}
</style>

<style scoped>
* {
  box-sizing: border-box;
}

.page {
  min-height: 100dvh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  width: 100%;
}

.page-body {
  flex: 1;
  padding: 56px 12px 100px;
  box-sizing: border-box;
  max-width: 640px;
  margin: 0 auto;
  width: 100%;
  overflow-x: hidden;
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

/* Uploader wrapper - removed margin to align with inputs */
.uploader-wrapper {
  /* margin-left removed */
}

/* Target van-uploader inside van-field for precise alignment */
.uploader-wrapper :deep(.van-field__value) {
  padding-left: 0;
}

/* Alternative: add padding to the uploader container itself */
.uploader-wrapper :deep(.van-uploader) {
  padding-left: 12px;
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
  z-index: 100 !important;
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

.fab-button {
  position: fixed !important;
  bottom: 30px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  z-index: 9999 !important;
  width: 200px !important;
  height: 48px !important;
  border-radius: 24px !important;
  background: rgba(2, 44, 72, 0.4) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  color: white !important;
  font-weight: 600 !important;
  font-size: 15px !important;
}

.fab-button[disabled] {
  background: rgb(200, 200, 200) !important;
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
  padding: 0 12px 100px;
  position: relative;
}

.issue-card {
  margin-bottom: 16px;
  transition: background-color 0.3s ease;
  border-bottom: 1px solid #bbbbbb;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box !important;
}

/* Dynamic Card Backgrounds */
.issue-ready {
  background-color: #d4edda !important;
}

/* Rectification: comments changed - light orange */
.issue-comments-changed {
  background-color: #fff3e0 !important;
}

/* Rectification: fix photo uploaded - light green */
.issue-fixed-photo {
  background-color: #e8f5e9 !important;
}

/* Assignment: owner selected - light green */
.issue-assigned {
  background-color: #f0f9eb !important;
}

/* Card Header - Date Row */
.issue-header-row {
  display: block;
  margin-bottom: 6px;
  text-align: left;
}

.issue-date {
  font-weight: 500;
  color: #555;
  font-size: 12px;
  text-align: left;
  display: block;
}

/* Card Header - Tags Row with flex-wrap */
.issue-tags-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.issue-owner-badge,
.issue-store {
  font-size: 11px;
  padding: 2px 6px;
  background: #e6f1fe;
  border-radius: 4px;
  color: #333;
  white-space: nowrap;
}

.issue-desc-text {
  margin-top: 8px;
  margin-right: 8px;
  color: #333;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  text-align: left;
  word-wrap: break-word;
  overflow-wrap: break-word;
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

.rectification-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fix-comments-field {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 4px;
}

.assignment-owner-select {
  margin-top: 8px;
}

.assignment-field {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 4px;
  padding: 8px 12px;
}

.selected-owner {
  color: #4caf50;
  font-weight: 600;
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
