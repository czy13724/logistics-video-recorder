// ==================== API配置 ====================
const API_BASE = '/api';

// 全局状态
let currentVideo = null;
let trendChartInstance = null;
let problemChartInstance = null;

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    updateDateTime();
    setInterval(updateDateTime, 1000);

    // 加载初始数据
    loadDashboard();
    loadVideos();
    loadExports();
});

// ==================== 导航控制 ====================
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);

            // 更新导航激活状态
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchPage(page) {
    document.querySelectorAll('.page-content').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');

    // 刷新对应页面数据
    if (page === 'dashboard') {
        loadDashboard();
    } else if (page === 'videos') {
        loadVideos();
    } else if (page === 'exports') {
        loadExports();
    }
}

// ==================== 时间显示 ====================
function updateDateTime() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    document.getElementById('currentDateTime').textContent =
        now.toLocaleString('zh-CN', options).replace(/\//g, '-');
}

// ==================== 数据加载 ====================
async function loadDashboard() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();

        // 更新统计卡片
        document.getElementById('totalVideos').textContent = stats.total_videos;
        document.getElementById('todayVideos').textContent = stats.today_videos;
        document.getElementById('totalProblems').textContent = stats.total_problems;
        document.getElementById('storageSize').textContent = stats.storage_used;
        document.getElementById('storageUsed').textContent = stats.storage_used;

        // 绘制图表
        drawTrendChart(stats.daily_trend);
        drawProblemChart(stats.problem_distribution);

    } catch (error) {
        showToast('加载统计数据失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadVideos(filters = {}) {
    showLoading();
    try {
        const params = new URLSearchParams();
        if (filters.search) params.append('search', filters.search);
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.has_problems !== undefined) params.append('has_problems', filters.has_problems);

        const response = await fetch(`${API_BASE}/videos?${params}`);
        const videos = await response.json();

        displayVideos(videos);

    } catch (error) {
        showToast('加载视频列表失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadExports() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/exports`);
        const exports = await response.json();

        displayExports(exports);

    } catch (error) {
        showToast('加载导出文件失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ==================== 数据显示 ====================
function displayVideos(videos) {
    const grid = document.getElementById('videoGrid');

    if (videos.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
                <div style="font-size: 4rem; margin-bottom: 1rem;">📹</div>
                <p style="font-size: 1.25rem;">暂无视频记录</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = videos.map(video => `
        <div class="video-card" onclick="openVideoModal('${video.tracking_number}', '${video.timestamp}')">
            <div class="video-thumbnail">
                🎬
                <div class="play-overlay">
                    <div class="play-icon">▶️</div>
                </div>
            </div>
            <div class="video-details">
                <div class="video-title">${video.tracking_number}</div>
                <div class="video-meta">
                    📅 ${video.timestamp}
                    ${video.duration ? ` | ⏱️ ${video.duration}秒` : ''}
                    ${video.size ? ` | 💾 ${formatBytes(video.size)}` : ''}
                </div>
                <div class="video-problems">
                    ${video.problems && video.problems.length > 0
            ? video.problems.map(p => `<span class="problem-tag">${p}</span>`).join('')
            : '<span class="no-problems">无问题标记</span>'
        }
                </div>
            </div>
        </div>
    `).join('');
}

function displayExports(exports) {
    const list = document.getElementById('exportList');

    if (exports.length === 0) {
        list.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                <div style="font-size: 4rem; margin-bottom: 1rem;">📁</div>
                <p style="font-size: 1.25rem;">暂无导出文件</p>
            </div>
        `;
        return;
    }

    list.innerHTML = exports.map(exp => `
        <div class="export-item">
            <div class="export-info">
                <div class="export-icon">${exp.type === 'pdf' ? '📄' : '📊'}</div>
                <div class="export-meta">
                    <div class="export-name">${exp.name}</div>
                    <div class="export-details">
                        ${exp.size} | ${new Date(exp.created).toLocaleString('zh-CN')}
                    </div>
                </div>
            </div>
            <a href="${API_BASE}/exports/${exp.name}" class="btn-download" download>
                ⬇️ 下载
            </a>
        </div>
    `).join('');
}

// ==================== 图表绘制 ====================
function drawTrendChart(data) {
    const ctx = document.getElementById('trendChart');

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date.substring(5)),
            datasets: [{
                label: '录制数量',
                data: data.map(d => d.count),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    }
                },
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    }
                }
            }
        }
    });
}

function drawProblemChart(data) {
    const ctx = document.getElementById('problemChart');

    if (problemChartInstance) {
        problemChartInstance.destroy();
    }

    const labels = Object.keys(data);
    const values = Object.values(data);

    if (labels.length === 0) {
        ctx.parentElement.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--text-muted);">暂无问题数据</div>';
        return;
    }

    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#f5576c',
        '#fa709a', '#fee140', '#30cfd0', '#330867'
    ];

    problemChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#cbd5e1',
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                }
            }
        }
    });
}

// ==================== 视频操作 ====================
async function openVideoModal(trackingNumber, timestamp) {
    currentVideo = { trackingNumber, timestamp };

    // 设置视频源
    const videoElement = document.getElementById('modalVideo');
    const timestampClean = timestamp.replace(/:/g, '').replace(/-/g, '').replace(/ /g, '_');
    videoElement.src = `${API_BASE}/videos/${trackingNumber}/stream?timestamp=${timestamp}`;

    // 设置标题
    document.getElementById('modalVideoTitle').textContent = trackingNumber;

    // 加载视频信息
    try {
        const response = await fetch(`${API_BASE}/videos?search=${trackingNumber}`);
        const videos = await response.json();
        const video = videos.find(v => v.tracking_number === trackingNumber && v.timestamp === timestamp);

        if (video) {
            // 显示问题标签
            const problemTags = document.getElementById('problemTags');
            if (video.problems && video.problems.length > 0) {
                problemTags.innerHTML = video.problems.map(p =>
                    `<span class="problem-tag">${p}</span>`
                ).join('');
            } else {
                problemTags.innerHTML = '<span class="no-problems">无问题标记</span>';
            }

            // 显示备注
            document.getElementById('videoNotes').value = video.notes || '';
        }
    } catch (error) {
        showToast('加载视频信息失败: ' + error.message, 'error');
    }

    // 显示模态框
    document.getElementById('videoModal').classList.add('active');
}

function closeVideoModal() {
    document.getElementById('videoModal').classList.remove('active');
    document.getElementById('modalVideo').pause();
    document.getElementById('modalVideo').src = '';
    currentVideo = null;
}

async function saveVideoInfo() {
    if (!currentVideo) return;

    const notes = document.getElementById('videoNotes').value;
    const problemTags = Array.from(document.querySelectorAll('#problemTags .problem-tag'))
        .map(tag => tag.textContent);

    showLoading();
    try {
        const response = await fetch(
            `${API_BASE}/videos/${currentVideo.trackingNumber}/problems?timestamp=${currentVideo.timestamp}`,
            {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    problems: problemTags,
                    notes: notes
                })
            }
        );

        if (response.ok) {
            showToast('保存成功', 'success');
            loadVideos();
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteVideo() {
    if (!currentVideo) return;

    if (!confirm(`确定要删除视频 ${currentVideo.trackingNumber} 吗？此操作不可恢复！`)) {
        return;
    }

    showLoading();
    try {
        const response = await fetch(
            `${API_BASE}/videos/${currentVideo.trackingNumber}?timestamp=${currentVideo.timestamp}`,
            { method: 'DELETE' }
        );

        if (response.ok) {
            showToast('删除成功', 'success');
            closeVideoModal();
            loadVideos();
            loadDashboard();
        } else {
            throw new Error('删除失败');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function openProblemModal() {
    document.getElementById('problemModal').classList.add('active');
}

function closeProblemModal() {
    document.getElementById('problemModal').classList.remove('active');
}

function addCustomProblem() {
    const input = document.getElementById('customProblem');
    const problem = input.value.trim();

    if (problem) {
        const problemTags = document.getElementById('problemTags');
        const tag = document.createElement('span');
        tag.className = 'problem-tag';
        tag.textContent = problem;
        tag.style.cursor = 'pointer';
        tag.title = '点击删除';
        tag.onclick = () => tag.remove();

        problemTags.appendChild(tag);
        input.value = '';
    }
}

// ==================== 搜索和筛选 ====================
function searchVideos() {
    const search = document.getElementById('searchInput').value;
    loadVideos({ search });
}

function applyFilters() {
    const filters = {
        search: document.getElementById('searchInput').value,
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value
    };

    const problemFilter = document.getElementById('problemFilter').value;
    if (problemFilter) {
        filters.has_problems = problemFilter === 'true';
    }

    loadVideos(filters);
}

// 搜索框回车事件
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchVideos();
            }
        });
    }
});

// ==================== 刷新数据 ====================
function refreshData() {
    const activePage = document.querySelector('.nav-item.active').dataset.page;

    if (activePage === 'dashboard') {
        loadDashboard();
    } else if (activePage === 'videos') {
        loadVideos();
    } else if (activePage === 'exports') {
        loadExports();
    }

    showToast('数据已刷新', 'success');
}

// ==================== UI辅助函数 ====================
function showLoading() {
    document.getElementById('loading').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('active');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show';

    // 根据类型设置样式
    if (type === 'success') {
        toast.style.borderLeft = '4px solid var(--success-color)';
    } else if (type === 'error') {
        toast.style.borderLeft = '4px solid var(--danger-color)';
    } else {
        toast.style.borderLeft = '4px solid var(--info-color)';
    }

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ==================== 模态框点击外部关闭 ====================
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
        if (e.target.id === 'videoModal') {
            document.getElementById('modalVideo').pause();
            document.getElementById('modalVideo').src = '';
        }
    }
});
