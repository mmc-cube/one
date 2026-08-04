const loginView = document.getElementById('loginView');
const adminView = document.getElementById('adminView');
const mainContent = document.getElementById('mainContent');
const toast = document.getElementById('toast');
const backdrop = document.getElementById('drawerBackdrop');
const pageNames = ['dashboard', 'questions', 'components', 'feedback', 'errors'];
const pageState = Object.fromEntries(pageNames.map(name => [name, { page: 1 }]));
let activePage = 'dashboard';
let activeRecord = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return date.toLocaleString('zh-CN', { hour12: false }).replaceAll('/', '-');
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(window.__adminToastTimer);
  window.__adminToastTimer = window.setTimeout(() => toast.classList.remove('show'), 2200);
}

function showLoginError(message = '') {
  document.getElementById('loginErrorText').textContent = message;
  document.getElementById('loginError').classList.toggle('hidden', !message);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: 'no-store',
    credentials: 'same-origin',
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json', ...(options.headers || {}) } : options.headers,
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== '/api/admin/login') {
    showLogin();
    throw new Error('管理员登录已失效，请重新登录');
  }
  if (!response.ok) throw new Error(data.error || '请求失败');
  return data;
}

function showLogin() {
  closeDrawers();
  adminView.classList.add('hidden');
  loginView.classList.remove('hidden');
  document.getElementById('password').value = '';
}

function showAdmin() {
  loginView.classList.add('hidden');
  adminView.classList.remove('hidden');
  showLoginError();
}

function closeDrawers() {
  document.querySelectorAll('.drawer').forEach(drawer => drawer.classList.remove('open'));
  mainContent.classList.remove('drawer-open');
  backdrop.classList.remove('open');
  activeRecord = null;
}

function openDrawer(id) {
  document.querySelectorAll('.drawer').forEach(drawer => drawer.classList.remove('open'));
  document.getElementById(id).classList.add('open');
  mainContent.classList.add('drawer-open');
  backdrop.classList.add('open');
}

function emptyRow(colspan, title = '暂无真实数据', detail = '数据会在测试活动产生后自动显示。') {
  return `<tr><td colspan="${colspan}"><div class="empty-state"><b>${escapeHtml(title)}</b>${escapeHtml(detail)}</div></td></tr>`;
}

function statusMarkup(status) {
  const className = ['已处理', '已解决', '已导出 PDF', '已生成方案'].includes(status) ? 'done' : status === '待处理' ? 'warn' : 'wait';
  return `<span class="status ${className}">${escapeHtml(status || '—')}</span>`;
}

function queryString(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== '' && value !== undefined && value !== null) params.set(key, value);
  });
  return params.toString();
}

function paginationMarkup(result, pageName) {
  const pages = Math.max(1, Math.ceil(result.total / result.page_size));
  const current = Math.min(result.page, pages);
  const buttons = [];
  for (let page = Math.max(1, current - 2); page <= Math.min(pages, current + 2); page += 1) {
    buttons.push(`<button class="page-btn ${page === current ? 'active' : ''}" data-page-number="${page}" data-page-target="${pageName}">${page}</button>`);
  }
  return `<div class="pagination"><span>共 ${result.total} 条</span><button class="page-btn" data-page-number="${Math.max(1, current - 1)}" data-page-target="${pageName}" ${current === 1 ? 'disabled' : ''}>‹</button>${buttons.join('')}<button class="page-btn" data-page-number="${Math.min(pages, current + 1)}" data-page-target="${pageName}" ${current === pages ? 'disabled' : ''}>›</button></div>`;
}

function lineChart(trend) {
  const values = trend.flatMap(item => [Number(item.evaluations || 0), Number(item.designs || 0), Number(item.pdf_exports || 0)]);
  const maximum = Math.max(1, ...values);
  const x = index => 48 + index * 74;
  const y = value => 178 - (Number(value || 0) / maximum) * 135;
  const polyline = key => trend.map((item, index) => `${x(index)},${y(item[key])}`).join(' ');
  return `<svg class="chart svg-chart" viewBox="0 0 540 220" role="img" aria-label="最近七天活动趋势">
    <line class="gridline" x1="42" y1="42" x2="520" y2="42"/><line class="gridline" x1="42" y1="110" x2="520" y2="110"/><line class="gridline" x1="42" y1="178" x2="520" y2="178"/>
    <polyline points="${polyline('evaluations')}" fill="none" stroke="#2f7cf6" stroke-width="3"/>
    <polyline points="${polyline('designs')}" fill="none" stroke="#20b26b" stroke-width="3"/>
    <polyline points="${polyline('pdf_exports')}" fill="none" stroke="#ff8a34" stroke-width="3"/>
    ${trend.map((item, index) => `<text x="${x(index)}" y="204" text-anchor="middle">${escapeHtml(item.date)}</text>`).join('')}
  </svg>`;
}

function funnelRow(label, value, maximum) {
  const percent = maximum ? Math.round((value / maximum) * 1000) / 10 : 0;
  return `<div class="funnel-row"><span>${escapeHtml(label)}</span><span class="funnel-bar-wrap"><i class="funnel-bar" style="width:${Math.max(3, percent)}%"></i></span><b>${value}（${percent}%）</b></div>`;
}

async function renderDashboard() {
  const data = await api('/api/admin/overview');
  const metrics = data.metrics;
  const funnel = data.funnel;
  const funnelMaximum = Math.max(1, funnel.opened);
  document.getElementById('page-dashboard').innerHTML = `
    <div class="page-title-row"><div><h1 class="page-title">数据概览</h1><div class="page-sub">真实测试活动数据 · 最近更新 ${formatDate(new Date())}</div></div><button class="ghost-btn" data-refresh="dashboard">刷新数据</button></div>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">今日使用人数</div><div class="stat-value">${metrics.users_today}</div><div class="stat-foot">按匿名会话去重</div></div>
      <div class="stat-card"><div class="stat-label">今日题目评估</div><div class="stat-value">${metrics.evaluations_today}</div><div class="stat-foot">成功返回的评估请求</div></div>
      <div class="stat-card"><div class="stat-label">今日方案生成</div><div class="stat-value">${metrics.designs_today}</div><div class="stat-foot">完成方案生成</div></div>
      <div class="stat-card"><div class="stat-label">今日 PDF 导出</div><div class="stat-value">${metrics.pdf_exports_today}</div><div class="stat-foot"><span class="orange">累计转化率 ${metrics.pdf_export_rate}%</span></div></div>
    </div>
    <div class="cards2"><div class="panel"><div class="panel-head">评估到 PDF 的使用漏斗</div><div class="panel-body funnel-wrap">
      ${funnelRow('产生会话', funnel.opened, funnelMaximum)}${funnelRow('完成评估', funnel.evaluated, funnelMaximum)}${funnelRow('配置元器件', funnel.configured, funnelMaximum)}${funnelRow('生成方案', funnel.generated, funnelMaximum)}${funnelRow('打开 PDF 导出', funnel.exported, funnelMaximum)}
    </div></div><div class="panel"><div class="panel-head"><span>最近 7 天趋势</span><span class="legend"><span><i style="background:#2f7cf6"></i>评估</span><span><i style="background:#20b26b"></i>方案</span><span><i style="background:#ff8a34"></i>PDF</span></span></div><div class="panel-body">${lineChart(data.trend)}</div></div></div>
    <div class="bottom-grid">
      <div class="panel list-panel"><div class="list-head"><span>热门题目</span></div><ol class="rank-list">${data.popular_topics.length ? data.popular_topics.map((item, index) => `<li><span class="name">${index + 1}　${escapeHtml(item.name)}</span><b>${item.count}</b></li>`).join('') : '<li>暂无题目数据</li>'}</ol></div>
      <div class="panel list-panel"><div class="list-head"><span>最近用户反馈</span></div><ul class="plain-list">${data.recent_feedback.length ? data.recent_feedback.map(item => `<li><span>${escapeHtml(item.content)}</span><small>${formatDate(item.created_at)}</small></li>`).join('') : '<li>尚未接入用户侧反馈，当前无数据</li>'}</ul></div>
      <div class="panel list-panel"><div class="list-head"><span>最近错误</span></div><ol class="rank-list">${data.recent_errors.length ? data.recent_errors.map((item, index) => `<li><span class="name">${index + 1}　${escapeHtml(item.type)}</span><b>${escapeHtml(item.status)}</b></li>`).join('') : '<li>暂无错误记录</li>'}</ol></div>
    </div>`;
}

function topicDetail(item) {
  activeRecord = item;
  const components = item.selected_components || {};
  const tags = Object.values(components).flat().map(name => `<span class="tag green">${escapeHtml(name)}</span>`).join('') || '<span class="detail-text">尚未生成方案</span>';
  const drawer = document.getElementById('questionDrawer');
  drawer.querySelector('.drawer-body').innerHTML = `
    <div class="detail-section"><div class="detail-title">完整题目</div><div class="detail-text">${escapeHtml(item.title)}</div></div>
    <div class="detail-section"><div class="detail-title">评估结果</div><div class="detail-kv"><b>综合评分：</b><span>${item.total_score ?? '—'}</span><b>硬件完成度：</b><span>${item.hardware_score ?? '—'}</span><b>软件完成度：</b><span>${item.software_score ?? '—'}</span><b>分析引擎：</b><span>${escapeHtml(item.engine)}</span></div></div>
    <div class="detail-section"><div class="detail-title">评估说明</div><div class="detail-text">${escapeHtml(item.reason || '—')}</div></div>
    <div class="detail-section"><div class="detail-title">用户最终选择的元器件</div>${tags}</div>
    <div class="detail-section"><div class="detail-title">PDF 导出</div><div class="detail-kv"><b>导出次数：</b><span>${item.pdf_export_count || 0}</span><b>最近打开：</b><span>${formatDate(item.pdf_exported_at)}</span></div></div>`;
  drawer.querySelector('.drawer-foot').innerHTML = '<button class="primary-btn" type="button" data-close-drawer>关闭详情</button>';
  openDrawer('questionDrawer');
}

async function renderQuestions() {
  const state = pageState.questions;
  const data = await api(`/api/admin/topics?${queryString({ page: state.page, page_size: 10, search: state.search, domain: state.domain, engine: state.engine, status: state.status })}`);
  state.items = data.items;
  document.getElementById('page-questions').innerHTML = `
    <div class="page-title-row"><div><h1 class="page-title">题目库</h1><div class="page-sub">共 ${data.total} 条真实评估记录</div></div><div class="toolbar"><div class="inputbox" style="width:250px"><input id="topicSearch" value="${escapeHtml(state.search || '')}" placeholder="搜索题目名称或关键词"></div><button class="ghost-btn" data-export="topics">导出 CSV</button></div></div>
    <div class="filterbar">
      <div class="filter-group"><span class="filter-label">题目领域</span><div class="selectbox"><select data-filter="domain" data-target="questions"><option value="">全部</option>${['电机控制','环境监测','智能农业','安防门禁','健康监护','智能车辆','物联网','电源电子','其他'].map(value => `<option ${state.domain === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div></div>
      <div class="filter-group"><span class="filter-label">分析引擎</span><div class="selectbox"><select data-filter="engine" data-target="questions"><option value="">全部</option><option value="ai" ${state.engine === 'ai' ? 'selected' : ''}>AI</option><option value="rules" ${state.engine === 'rules' ? 'selected' : ''}>规则引擎</option></select></div></div>
      <div class="filter-group"><span class="filter-label">评估状态</span><div class="selectbox"><select data-filter="status" data-target="questions"><option value="">全部</option>${['已评估','已生成方案','已导出 PDF'].map(value => `<option ${state.status === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div></div>
      <button class="ghost-btn" data-search-topics>搜索</button><button class="ghost-btn" data-refresh="questions">刷新</button>
    </div>
    <div class="table-card"><table class="wide"><thead><tr><th style="width:28%">题目名称</th><th>题目领域</th><th>综合评分</th><th>硬件完成度</th><th>软件完成度</th><th>分析引擎</th><th>状态</th><th>PDF 次数</th><th style="width:145px">创建时间</th><th style="width:60px">操作</th></tr></thead><tbody>${data.items.length ? data.items.map(item => `<tr data-topic-id="${escapeHtml(item.id)}"><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.domain)}</td><td>${item.total_score ?? '—'}</td><td>${item.hardware_score ?? '—'}</td><td>${item.software_score ?? '—'}</td><td>${escapeHtml(item.engine)}</td><td>${statusMarkup(item.status)}</td><td>${item.pdf_export_count || 0}</td><td>${formatDate(item.created_at)}</td><td class="link">查看</td></tr>`).join('') : emptyRow(10)}</tbody></table>${paginationMarkup(data, 'questions')}</div>`;
}

function rankList(items) {
  return items.length ? items.map(([name, count], index) => `<li><span>${index + 1}　${escapeHtml(name)}</span><b>${count}</b></li>`).join('') : '<li>暂无数据</li>';
}

async function renderComponents() {
  const state = pageState.components;
  const data = await api(`/api/admin/components?${queryString({ page: state.page, page_size: 10, domain: state.domain, category: state.category })}`);
  state.items = data.items;
  const categoryLabel = { display: '显示器', sensor: '传感器', actuator: '执行驱动器' };
  document.getElementById('page-components').innerHTML = `
    <div class="page-title-row"><div><h1 class="page-title">元器件反馈</h1><div class="page-sub">对比 AI 推荐与用户生成方案时的最终选择</div></div><div class="toolbar"><div class="selectbox"><select data-filter="domain" data-target="components"><option value="">全部领域</option>${['电机控制','环境监测','智能农业','安防门禁','健康监护','智能车辆','物联网','电源电子','其他'].map(value => `<option ${state.domain === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div><div class="selectbox"><select data-filter="category" data-target="components"><option value="">全部类型</option><option value="display" ${state.category === 'display' ? 'selected' : ''}>显示器</option><option value="sensor" ${state.category === 'sensor' ? 'selected' : ''}>传感器</option><option value="actuator" ${state.category === 'actuator' ? 'selected' : ''}>执行驱动器</option></select></div><button class="ghost-btn" data-export="components">导出 CSV</button></div></div>
    <div class="mini-stats"><div class="mini-stat"><div class="stat-label">AI 推荐总量</div><div class="stat-value">${data.metrics.recommended}</div></div><div class="mini-stat"><div class="stat-label">用户保留率</div><div class="stat-value">${data.metrics.retention_rate}%</div></div><div class="mini-stat"><div class="stat-label">用户主动新增</div><div class="stat-value">${data.metrics.added}</div></div><div class="mini-stat"><div class="stat-label">用户主动移除</div><div class="stat-value">${data.metrics.removed}</div></div></div>
    <div class="component-layout"><div class="component-main"><div class="table-card"><table class="wide"><thead><tr><th style="width:24%">题目名称</th><th>领域</th><th>类型</th><th style="width:24%">AI 推荐</th><th style="width:24%">用户最终选择</th><th>保留 / 移除 / 新增</th><th style="width:145px">时间</th></tr></thead><tbody>${data.items.length ? data.items.map(item => `<tr><td>${escapeHtml(item.topic)}</td><td>${escapeHtml(item.domain)}</td><td>${categoryLabel[item.category] || escapeHtml(item.category)}</td><td>${escapeHtml(item.recommended.join('、') || '—')}</td><td>${escapeHtml(item.selected.join('、') || '—')}</td><td><span class="tag green">${item.retained.length}</span><span class="tag red">${item.removed.length}</span><span class="tag orange">${item.added.length}</span></td><td>${formatDate(item.created_at)}</td></tr>`).join('') : emptyRow(7)}</tbody></table>${paginationMarkup(data, 'components')}</div></div>
      <aside class="component-rank"><div class="rank-box"><h4>最常被保留</h4><ol class="rank-list">${rankList(data.rankings.retained)}</ol></div><div class="rank-box"><h4>最常被移除</h4><ol class="rank-list">${rankList(data.rankings.removed)}</ol></div><div class="rank-box"><h4>最常主动添加</h4><ol class="rank-list">${rankList(data.rankings.added)}</ol></div></aside>
    </div>`;
}

function feedbackDetail(item) {
  activeRecord = item;
  const drawer = document.getElementById('feedbackDrawer');
  drawer.querySelector('.drawer-body').innerHTML = `<div class="detail-section"><div class="detail-title">完整反馈内容</div><div class="detail-text">${escapeHtml(item.content)}</div></div><div class="detail-section"><div class="detail-title">关联信息</div><div class="detail-kv"><b>题目：</b><span>${escapeHtml(item.topic || '—')}</span><b>所在步骤：</b><span>${escapeHtml(item.step || '—')}</span><b>联系方式：</b><span>${escapeHtml(item.contact || '未填写')}</span></div></div><div class="detail-section"><div class="detail-title">处理状态</div><div class="selectbox" style="width:100%"><select id="feedbackStatus"><option>待处理</option><option>处理中</option><option>已处理</option></select></div></div><div class="detail-section"><div class="detail-title">管理员备注</div><textarea class="textarea" id="feedbackNote">${escapeHtml(item.admin_note || '')}</textarea></div>`;
  drawer.querySelector('#feedbackStatus').value = item.status;
  drawer.querySelector('.drawer-foot').innerHTML = '<button class="primary-btn" type="button" data-save-feedback>保存处理结果</button>';
  openDrawer('feedbackDrawer');
}

async function renderFeedback() {
  const state = pageState.feedback;
  const data = await api(`/api/admin/feedback?${queryString({ page: state.page, page_size: 10, status: state.status })}`);
  state.items = data.items;
  document.getElementById('page-feedback').innerHTML = `
    <div class="page-title-row"><div><h1 class="page-title">用户反馈</h1><div class="page-sub">用户侧反馈入口暂未启用，本页保留真实数据接口</div></div><button class="ghost-btn" data-export="feedback">导出 CSV</button></div>
    <div class="mini-stats"><div class="mini-stat"><div class="stat-label">反馈总数</div><div class="stat-value">${data.metrics.total}</div></div><div class="mini-stat"><div class="stat-label">平均满意度</div><div class="stat-value">${data.metrics.average_rating}</div></div><div class="mini-stat"><div class="stat-label">待处理数量</div><div class="stat-value">${data.metrics.pending}</div></div><div class="mini-stat"><div class="stat-label">已处理数量</div><div class="stat-value">${data.metrics.resolved}</div></div></div>
    <div class="filterbar"><div class="filter-group"><span class="filter-label">处理状态</span><div class="selectbox"><select data-filter="status" data-target="feedback"><option value="">全部</option>${['待处理','处理中','已处理'].map(value => `<option ${state.status === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div></div><button class="ghost-btn" data-refresh="feedback">刷新</button></div>
    <div class="table-card"><table class="wide"><thead><tr><th>满意度</th><th style="width:28%">反馈内容</th><th>反馈类型</th><th style="width:22%">关联题目</th><th>所在步骤</th><th>联系方式</th><th>处理状态</th><th style="width:145px">提交时间</th><th>操作</th></tr></thead><tbody>${data.items.length ? data.items.map(item => `<tr data-feedback-id="${escapeHtml(item.id)}"><td>${item.rating || '—'}</td><td>${escapeHtml(item.content)}</td><td>${escapeHtml(item.type)}</td><td>${escapeHtml(item.topic)}</td><td>${escapeHtml(item.step)}</td><td>${escapeHtml(item.contact || '未填写')}</td><td>${statusMarkup(item.status)}</td><td>${formatDate(item.created_at)}</td><td class="link">查看</td></tr>`).join('') : emptyRow(9, '暂未启用用户侧反馈', '按你的要求，本阶段不在用户端增加反馈提交入口。')}</tbody></table>${paginationMarkup(data, 'feedback')}</div>`;
}

function errorDetail(item) {
  activeRecord = item;
  const drawer = document.getElementById('errorDrawer');
  drawer.querySelector('.drawer-body').innerHTML = `<div class="detail-section"><div class="detail-title">完整错误信息</div><div class="detail-text">${escapeHtml(item.message)}</div></div><div class="detail-section"><div class="detail-title">请求信息</div><div class="detail-kv"><b>接口：</b><span>${escapeHtml(item.endpoint)}</span><b>状态码：</b><span>${item.status_code}</span><b>分析引擎：</b><span>${escapeHtml(item.engine || '—')}</span><b>耗时：</b><span>${item.duration_ms || 0} ms</span><b>会话标识：</b><span>${escapeHtml(item.session_id)}</span><b>关联题目：</b><span>${escapeHtml(item.topic || '—')}</span></div></div><div class="detail-section"><div class="detail-title">处理状态</div><div class="selectbox" style="width:100%"><select id="errorStatus"><option>待处理</option><option>处理中</option><option>已解决</option></select></div></div><div class="detail-section"><div class="detail-title">管理员备注</div><textarea class="textarea" id="errorNote">${escapeHtml(item.admin_note || '')}</textarea></div>`;
  drawer.querySelector('#errorStatus').value = item.status;
  drawer.querySelector('.drawer-foot').innerHTML = '<button class="danger-btn" type="button" data-save-error>保存处理结果</button>';
  openDrawer('errorDrawer');
}

async function renderErrors() {
  const state = pageState.errors;
  const data = await api(`/api/admin/errors?${queryString({ page: state.page, page_size: 10, status: state.status, endpoint: state.endpoint })}`);
  state.items = data.items;
  const endpoints = data.endpoint_distribution.map(([endpoint]) => endpoint);
  document.getElementById('page-errors').innerHTML = `
    <div class="page-title-row"><div><h1 class="page-title">错误记录</h1><div class="page-sub">真实 API、AI 降级和 PDF 导出错误</div></div><div class="toolbar"><div class="selectbox"><select data-filter="status" data-target="errors"><option value="">全部状态</option>${['待处理','处理中','已解决'].map(value => `<option ${state.status === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div><div class="selectbox"><select data-filter="endpoint" data-target="errors"><option value="">全部接口</option>${endpoints.map(value => `<option value="${escapeHtml(value)}" ${state.endpoint === value ? 'selected' : ''}>${escapeHtml(value)}</option>`).join('')}</select></div><button class="ghost-btn" data-refresh="errors">刷新</button><button class="ghost-btn" data-export="errors">导出 CSV</button></div></div>
    <div class="mini-stats"><div class="mini-stat"><div class="stat-label">错误总数</div><div class="stat-value">${data.metrics.total}</div></div><div class="mini-stat"><div class="stat-label">受影响会话</div><div class="stat-value">${data.metrics.affected_users}</div></div><div class="mini-stat"><div class="stat-label">API 请求失败率</div><div class="stat-value">${data.metrics.failure_rate ?? 0}%</div></div><div class="mini-stat"><div class="stat-label">未处理错误</div><div class="stat-value">${data.metrics.unresolved}</div></div></div>
    <div class="panel" style="margin-bottom:14px"><div class="panel-head">错误接口分布</div><div class="panel-body"><div class="toolbar">${data.endpoint_distribution.length ? data.endpoint_distribution.map(([endpoint, count]) => `<span class="tag red">${escapeHtml(endpoint)} · ${count}</span>`).join('') : '<span class="detail-text">暂无错误记录</span>'}</div></div></div>
    <div class="table-card"><table class="wide"><thead><tr><th>错误级别</th><th style="width:18%">错误类型</th><th>请求接口</th><th>HTTP 状态码</th><th>分析引擎</th><th style="width:20%">关联题目</th><th>会话标识</th><th style="width:145px">发生时间</th><th>处理状态</th><th>操作</th></tr></thead><tbody>${data.items.length ? data.items.map(item => `<tr data-error-id="${escapeHtml(item.id)}"><td><span class="error-kind ${item.level === '高' ? 'red' : item.level === '中' ? 'orange' : 'yellow'}">${escapeHtml(item.level)}</span></td><td>${escapeHtml(item.type)}</td><td>${escapeHtml(item.endpoint)}</td><td>${item.status_code}</td><td>${escapeHtml(item.engine || '—')}</td><td>${escapeHtml(item.topic || '—')}</td><td>${escapeHtml(item.session_id)}</td><td>${formatDate(item.occurred_at)}</td><td>${statusMarkup(item.status)}</td><td class="link">查看</td></tr>`).join('') : emptyRow(10)}</tbody></table>${paginationMarkup(data, 'errors')}</div>`;
}

const renderers = { dashboard: renderDashboard, questions: renderQuestions, components: renderComponents, feedback: renderFeedback, errors: renderErrors };

async function switchPage(name, { refresh = false } = {}) {
  if (!pageNames.includes(name)) name = 'dashboard';
  activePage = name;
  document.querySelectorAll('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.page === name));
  document.querySelectorAll('.page').forEach(page => page.classList.toggle('active', page.id === `page-${name}`));
  closeDrawers();
  history.replaceState(null, '', `#${name}`);
  const section = document.getElementById(`page-${name}`);
  if (refresh || !section.dataset.loaded) {
    section.setAttribute('aria-busy', 'true');
    try {
      await renderers[name]();
      section.dataset.loaded = 'true';
    } catch (error) {
      section.innerHTML = `<div class="empty-state"><b>数据加载失败</b>${escapeHtml(error.message)}</div>`;
    } finally {
      section.removeAttribute('aria-busy');
    }
  }
}

async function login() {
  const button = document.getElementById('loginBtn');
  const username = document.getElementById('account').value.trim();
  const password = document.getElementById('password').value;
  showLoginError();
  if (!username || !password) {
    showLoginError('请输入管理员账号和密码');
    return;
  }
  button.disabled = true;
  button.textContent = '正在登录...';
  try {
    await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    showAdmin();
    await switchPage(location.hash.slice(1) || 'dashboard', { refresh: true });
  } catch (error) {
    showLoginError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = '登录';
  }
}

async function saveRecord(collection) {
  if (!activeRecord) return;
  const isFeedback = collection === 'feedback';
  const status = document.getElementById(isFeedback ? 'feedbackStatus' : 'errorStatus').value;
  const adminNote = document.getElementById(isFeedback ? 'feedbackNote' : 'errorNote').value.trim();
  await api(`/api/admin/${collection}/${encodeURIComponent(activeRecord.id)}/status`, { method: 'POST', body: JSON.stringify({ status, admin_note: adminNote }) });
  closeDrawers();
  document.getElementById(`page-${isFeedback ? 'feedback' : 'errors'}`).dataset.loaded = '';
  await switchPage(isFeedback ? 'feedback' : 'errors', { refresh: true });
  showToast('处理结果已保存');
}

document.getElementById('togglePassword').addEventListener('click', () => {
  const password = document.getElementById('password');
  password.type = password.type === 'password' ? 'text' : 'password';
});
document.getElementById('loginBtn').addEventListener('click', login);
document.getElementById('password').addEventListener('keydown', event => {
  if (event.key === 'Enter') login();
});
document.getElementById('logoutBtn').addEventListener('click', async () => {
  await api('/api/admin/logout', { method: 'POST', body: '{}' }).catch(() => {});
  showLogin();
});
document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', () => switchPage(item.dataset.page)));
document.querySelectorAll('.drawer-close').forEach(button => button.addEventListener('click', closeDrawers));
backdrop.addEventListener('click', closeDrawers);

document.addEventListener('click', async event => {
  const refresh = event.target.closest('[data-refresh]');
  if (refresh) {
    await switchPage(refresh.dataset.refresh, { refresh: true });
    showToast('数据已刷新');
    return;
  }
  const exportButton = event.target.closest('[data-export]');
  if (exportButton) {
    window.location.href = `/api/admin/export?dataset=${encodeURIComponent(exportButton.dataset.export)}`;
    return;
  }
  const pageButton = event.target.closest('[data-page-number]');
  if (pageButton && !pageButton.disabled) {
    const target = pageButton.dataset.pageTarget;
    pageState[target].page = Number(pageButton.dataset.pageNumber);
    await switchPage(target, { refresh: true });
    return;
  }
  if (event.target.closest('[data-search-topics]')) {
    pageState.questions.search = document.getElementById('topicSearch').value.trim();
    pageState.questions.page = 1;
    await switchPage('questions', { refresh: true });
    return;
  }
  const topicRow = event.target.closest('[data-topic-id]');
  if (topicRow) {
    const item = pageState.questions.items.find(record => record.id === topicRow.dataset.topicId);
    if (item) topicDetail(item);
    return;
  }
  const feedbackRow = event.target.closest('[data-feedback-id]');
  if (feedbackRow) {
    const item = pageState.feedback.items.find(record => record.id === feedbackRow.dataset.feedbackId);
    if (item) feedbackDetail(item);
    return;
  }
  const errorRow = event.target.closest('[data-error-id]');
  if (errorRow) {
    const item = pageState.errors.items.find(record => record.id === errorRow.dataset.errorId);
    if (item) errorDetail(item);
    return;
  }
  if (event.target.closest('[data-save-feedback]')) await saveRecord('feedback');
  if (event.target.closest('[data-save-error]')) await saveRecord('errors');
  if (event.target.closest('[data-close-drawer]')) closeDrawers();
});

document.addEventListener('change', async event => {
  const filter = event.target.closest('[data-filter]');
  if (!filter) return;
  const target = filter.dataset.target;
  pageState[target][filter.dataset.filter] = filter.value;
  pageState[target].page = 1;
  await switchPage(target, { refresh: true });
});

(async function initialize() {
  try {
    const session = await api('/api/admin/session');
    if (session.authenticated) {
      showAdmin();
      await switchPage(location.hash.slice(1) || 'dashboard', { refresh: true });
    } else {
      showLogin();
      if (!session.configured) showLoginError('管理员密码尚未配置，请先在 .env 设置 ADMIN_PASSWORD');
    }
  } catch (error) {
    showLogin();
    showLoginError(error.message);
  }
})();
