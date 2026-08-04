const pages = ['input', 'results', 'config', 'solution'];
const counts = { display: 1, sensor: 3, actuator: 2 };
const componentCatalog = {
  display: {
    label: '显示器',
    icon: '屏',
    items: [
      { id: 'oled-096', name: '0.96寸 OLED', model: 'SSD1306', selected: true, quantity: 1 },
      { id: 'lcd-1602', name: 'LCD1602', model: 'HD44780', selected: false, quantity: 1 },
      { id: 'oled-13', name: '1.3寸 OLED', model: 'SH1106', selected: false, quantity: 1 },
      { id: 'tft-24', name: '2.4寸 TFT', model: 'ILI9341', selected: false, quantity: 1 },
      { id: 'segment-tm1637', name: '四位数码管', model: 'TM1637', selected: false, quantity: 1 },
      { id: 'epaper-29', name: '2.9寸电子墨水屏', model: 'SSD1680', selected: false, quantity: 1 },
    ],
  },
  sensor: {
    label: '传感器',
    icon: '感',
    twoRows: true,
    items: [
      { id: 'encoder', name: '增量式编码器', model: 'AB 相', selected: true, quantity: 1 },
      { id: 'current', name: '电流传感器', model: 'ACS712', selected: true, quantity: 1 },
      { id: 'button-module', name: '独立按键模块', model: '参数设置', selected: true, quantity: 1, supplemental: true },
      { id: 'hall', name: '霍尔传感器', model: 'A3144', selected: false, quantity: 1 },
      { id: 'temperature', name: '温度传感器', model: 'DS18B20', selected: false, quantity: 1 },
      { id: 'speed', name: '光电测速模块', model: 'LM393', selected: true, quantity: 1 },
      { id: 'voltage', name: '电压检测模块', model: '分压检测', selected: false, quantity: 1 },
      { id: 'temperature-humidity', name: '温湿度传感器', model: 'SHT30', selected: false, quantity: 1 },
      { id: 'imu', name: '六轴姿态传感器', model: 'MPU6050', selected: false, quantity: 1 },
      { id: 'distance', name: '超声波测距模块', model: 'HC-SR04', selected: false, quantity: 1 },
      { id: 'pressure', name: '气压传感器', model: 'BMP280', selected: false, quantity: 1 },
    ],
  },
  actuator: {
    label: '执行驱动器',
    icon: '驱',
    twoRows: true,
    items: [
      { id: 'tb6612', name: 'TB6612FNG', model: '双路 H 桥', selected: true, quantity: 1 },
      { id: 'dc-motor', name: '直流减速电机', model: '12V 减速电机', selected: true, quantity: 1 },
      { id: 'drv8871', name: 'DRV8871', model: '单路 H 桥', selected: false, quantity: 1 },
      { id: 'bts7960', name: 'BTS7960', model: '大电流驱动', selected: false, quantity: 1 },
      { id: 'relay', name: '继电器模块', model: '5V 继电器', selected: false, quantity: 1 },
      { id: 'buzzer', name: '蜂鸣器', model: '有源蜂鸣器', selected: false, quantity: 1 },
      { id: 'mosfet', name: 'MOSFET 驱动模块', model: '大功率开关', selected: false, quantity: 1 },
      { id: 'servo', name: '舵机', model: 'MG996R', selected: false, quantity: 1 },
      { id: 'pump', name: '直流水泵', model: '12V 水泵', selected: false, quantity: 1 },
      { id: 'fan', name: '直流风扇', model: '12V 风扇', selected: false, quantity: 1 },
    ],
  },
};
const baseComponentOptions = Object.fromEntries(
  Object.entries(componentCatalog).map(([type, category]) => [
    type,
    category.items.map(item => ({ ...item, selected: false, quantity: 1 })),
  ]),
);
const targetCategorySizes = { display: 2, sensor: 11, actuator: 7 };
let chosenTopic = '';
let evaluatedTopics = [];
let evaluationEngine = 'rules';
let generatedSolution = null;
let recommendationRequestId = 0;

const input = document.getElementById('topicInput');
const charCount = document.getElementById('charCount');
const evaluateButton = document.getElementById('evaluateBtn');
const analysisState = document.getElementById('analysisState');

function setAnalysisState(state) {
  if (analysisState) analysisState.textContent = state;
}

async function updateAIStatus() {
  const status = document.getElementById('aiStatus');
  if (!status) return;
  try {
    const response = await fetch('/api/health', { cache: 'no-store' });
    const data = await response.json();
    const configured = Boolean(data.ai && data.ai.configured);
    status.className = `ai-status ${configured ? 'connected' : 'offline'}`;
    status.textContent = configured
      ? `AI 已连接 · ${data.ai.model}`
      : data.ai && data.ai.model
        ? `已选择 ${data.ai.model} · 等待配置 Key`
        : 'AI 未配置 · 使用规则引擎';
  } catch {
    status.className = 'ai-status offline';
    status.textContent = '后端连接异常';
  }
}

function updateCount() {
  charCount.textContent = input.value.length;
}

function setBusy(button, busy, busyText, normalText) {
  button.disabled = busy;
  button.textContent = busy ? busyText : normalText;
}

async function request(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || '服务器请求失败');
  return data;
}

async function getJSON(path) {
  const response = await fetch(path, { cache: 'no-store' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || '服务器请求失败');
  return data;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function goTo(name) {
  pages.forEach(page => document.getElementById(`page-${page}`).classList.toggle('active', page === name));
  document.querySelectorAll('.topnav button').forEach(button => button.classList.toggle('active', button.dataset.nav === name));
  updateSteps(name);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateSteps(name) {
  const order = ['input', 'results', 'config', 'solution'];
  const current = order.indexOf(name);
  document.getElementById('stepbar').style.display = name === 'guide' ? 'none' : 'grid';
  document.querySelectorAll('.step').forEach((element, index) => {
    element.classList.toggle('active', index === current);
    element.classList.toggle('done', index < current);
  });
}

function scoreMarkup(label, value, className = '') {
  return `<div class="score ${className}"><label>${label}</label><strong>${value}</strong><small>/10</small></div>`;
}

function engineLabel(engine) {
  return engine === 'ai' ? 'AI 智能生成' : '规则引擎生成';
}

function renderResults(topics, engine) {
  const list = document.getElementById('resultsList');
  document.getElementById('resultsSummary').textContent = `已识别 ${topics.length} 个题目 · ${engineLabel(engine)}。请结合评分与原因选择。`;
  list.innerHTML = topics.map((topic, index) => `
    <article class="topic-card">
      <div class="topic-main">
        <div class="rank ${index === 0 ? 'green' : ''}">${index + 1}</div>
        <div>
          <div class="topic-title">${escapeHtml(topic.title)}</div>
          <div class="scores">
            ${scoreMarkup('硬件可完成度', topic.hardware_score)}
            ${scoreMarkup('软件可完成度', topic.software_score, 'software')}
            ${scoreMarkup('综合推荐度', topic.total_score, 'total')}
          </div>
        </div>
      </div>
      <div>
        <div class="verdict ${topic.total_score > 8 ? 'warn' : ''}">
          <b>完成建议：${escapeHtml(topic.conclusion)}</b>
          <p>${escapeHtml(topic.reason)}</p>
        </div>
        <div class="card-actions">
          <button class="small-primary" data-topic-index="${index}">选择此题</button>
        </div>
      </div>
    </article>
  `).join('');
}

async function evaluateTopics() {
  if (!input.value.trim()) {
    showToast('请先输入题目');
    return;
  }
  setBusy(evaluateButton, true, '正在评估…', '开始智能评估 →');
  setAnalysisState('RUNNING');
  try {
    const data = await request('/api/topics/evaluate', { text: input.value });
    evaluatedTopics = data.topics;
    evaluationEngine = data.engine || 'rules';
    renderResults(evaluatedTopics, evaluationEngine);
    if (data.warning) showToast(data.warning);
    goTo('results');
    setAnalysisState('COMPLETE');
  } catch (error) {
    showToast(error.message);
    setAnalysisState('ERROR');
  } finally {
    setBusy(evaluateButton, false, '正在评估…', '开始智能评估 →');
  }
}

function chooseTopicByIndex(index, triggerButton) {
  const topic = evaluatedTopics[index];
  if (!topic) return;
  chooseTopic(topic.title, triggerButton);
}

function setTopicChoiceBusy(triggerButton, busy) {
  document.querySelectorAll('[data-topic-index]').forEach(button => {
    button.disabled = busy;
    button.textContent = button === triggerButton && busy ? '正在推荐元器件...' : '选择此题';
  });
}

async function chooseTopic(title, triggerButton = null) {
  chosenTopic = title;
  document.getElementById('selectedTopic').textContent = chosenTopic;
  setTopicChoiceBusy(triggerButton, true);
  setAnalysisState('RECOMMENDING');
  const ready = await recommendComponents(chosenTopic);
  setTopicChoiceBusy(triggerButton, false);
  if (ready && chosenTopic === title) {
    goTo('config');
    setAnalysisState('COMPLETE');
  }
}

function componentKey(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]/g, '');
}

function componentTokens(value) {
  const ignored = new Set(['传感器', '元器件库', '显示屏', '显示', '驱动模块', '模块', '电机', '驱动']);
  return String(value)
    .split(/[\s/·+（）()_-]+/)
    .map(componentKey)
    .filter(token => token.length >= 2 && !ignored.has(token));
}

function componentsOverlap(left, right) {
  const leftKey = componentKey(left);
  const rightKey = componentKey(right);
  const tokens = [...componentTokens(left), ...componentTokens(right)];
  return leftKey === rightKey
    || leftKey.includes(rightKey)
    || rightKey.includes(leftKey)
    || tokens.some(token => leftKey.includes(token) && rightKey.includes(token));
}

function matchingBaseOption(type, name) {
  const key = componentKey(name);
  if (!key) return undefined;
  return baseComponentOptions[type].find(option => {
    const optionKey = componentKey(`${option.name}${option.model}`);
    const modelKey = componentKey(option.model);
    const tokens = componentTokens(`${option.name} ${option.model}`);
    return optionKey === key
      || optionKey.includes(key)
      || key.includes(optionKey)
      || (modelKey.length >= 3 && key.includes(modelKey))
      || tokens.some(token => key.includes(token));
  });
}

function applyCatalogOptions(data) {
  Object.entries(componentCatalog).forEach(([type]) => {
    const options = Array.isArray(data?.options?.[type]) ? data.options[type] : [];
    if (!options.length) return;
    baseComponentOptions[type] = options.map((item, index) => ({
      id: String(item.id || `catalog-${type}-${index}`),
      name: String(item.name || '未命名元器件'),
      model: String(item.model || '元器件库'),
      selected: false,
      quantity: 1,
      supplemental: Boolean(item.supplemental),
      usageCount: Number(item.usage_count || 0),
      hasLibrary: Boolean(item.has_library),
    }));
  });
}

function applyComponentRecommendations(data) {
  Object.entries(componentCatalog).forEach(([type, category]) => {
    const recommendations = Array.isArray(data.recommendations?.[type])
      ? data.recommendations[type]
      : [];
    const recommendedItems = recommendations.map((component, index) => {
      const name = String(component?.name || '').trim();
      const base = matchingBaseOption(type, name);
      return {
        id: `recommended-${type}-${index}`,
        name: name || `${category.label} ${index + 1}`,
        model: base?.model || (data.engine === 'ai' ? 'AI 推荐' : '规则推荐'),
        selected: true,
        quantity: 1,
        recommended: true,
        matchedBaseId: base?.id,
        supplemental: Boolean(component?.supplemental),
      };
    });
    const recommendedKeys = new Set(recommendedItems.map(item => componentKey(item.name)));
    const matchedBaseIds = new Set(recommendedItems.map(item => item.matchedBaseId).filter(Boolean));
    const alternativeLimit = Math.max(0, (targetCategorySizes[type] || 8) - recommendedItems.length);
    const alternatives = baseComponentOptions[type]
      .filter(item => !matchedBaseIds.has(item.id)
        && ![...recommendedKeys].some(key => componentsOverlap(key, `${item.name} ${item.model}`)))
      .slice(0, alternativeLimit)
      .map(item => ({ ...item }));
    category.items = [...recommendedItems, ...alternatives];
  });
  syncCounts();
  renderComponentSelectors();
  updateSummary();
}

async function recommendComponents(topic) {
  const requestId = ++recommendationRequestId;
  const status = document.getElementById('recommendationStatus');
  const generateButton = document.querySelector('.generate-btn');
  status.className = 'recommendation-status loading';
  status.textContent = '正在根据题目推荐元器件...';
  generateButton.disabled = true;
  try {
    const catalogPromise = getJSON(`/api/components/catalog?topic=${encodeURIComponent(topic)}`).catch(() => null);
    const [data, catalogData] = await Promise.all([
      request('/api/components/recommend', { topic }),
      catalogPromise,
    ]);
    if (requestId !== recommendationRequestId) return false;
    if (catalogData) applyCatalogOptions(catalogData);
    applyComponentRecommendations(data);
    status.className = 'recommendation-status success';
    status.textContent = data.engine === 'ai'
      ? 'AI 已推荐：1 个显示器、3 个传感器 + 1 个按键、2 个执行驱动器'
      : '规则已推荐：1 个显示器、3 个传感器 + 1 个按键、2 个执行驱动器';
    if (data.warning) showToast(data.warning);
    return true;
  } catch (error) {
    if (requestId !== recommendationRequestId) return false;
    status.className = 'recommendation-status error';
    status.textContent = '推荐失败，已保留默认配置';
    showToast(error.message);
    return true;
  } finally {
    if (requestId === recommendationRequestId) generateButton.disabled = false;
  }
}

function categoryCount(type) {
  return componentCatalog[type].items.reduce(
    (total, item) => total + (item.selected && !item.supplemental ? item.quantity : 0),
    0,
  );
}

function supplementalCount(type) {
  return componentCatalog[type].items.reduce(
    (total, item) => total + (item.selected && item.supplemental ? item.quantity : 0),
    0,
  );
}

function syncCounts() {
  Object.keys(componentCatalog).forEach(type => {
    counts[type] = categoryCount(type);
  });
}

function componentOptionMarkup(type, item) {
  const selected = item.selected;
  return `
    <article class="component-option ${selected ? 'selected' : ''}">
      <button
        class="component-toggle"
        type="button"
        data-component-toggle="${escapeHtml(type)}"
        data-component-id="${escapeHtml(item.id)}"
        aria-pressed="${selected}"
        aria-label="${selected ? '取消选择' : '选择'}${escapeHtml(item.name)}"
      >
        <span class="component-name">${escapeHtml(item.name)}</span>
        <span class="component-model">${escapeHtml(item.model)}</span>
      </button>
      <span class="selection-mark" aria-hidden="true">${selected ? '✓' : '+'}</span>
      ${selected ? `
        <div class="quantity-stepper" aria-label="${escapeHtml(item.name)}数量">
          <button type="button" data-quantity-change="-1" data-component-type="${escapeHtml(type)}" data-component-id="${escapeHtml(item.id)}" aria-label="减少${escapeHtml(item.name)}数量">−</button>
          <output>${item.quantity}</output>
          <button type="button" data-quantity-change="1" data-component-type="${escapeHtml(type)}" data-component-id="${escapeHtml(item.id)}" aria-label="增加${escapeHtml(item.name)}数量">+</button>
        </div>` : ''}
    </article>`;
}

function renderComponentSelectors() {
  const selectors = document.getElementById('componentSelectors');
  const scrollPositions = Object.fromEntries(
    [...selectors.querySelectorAll('[data-component-viewport]')]
      .map(viewport => [viewport.dataset.componentViewport, viewport.scrollLeft]),
  );
  selectors.innerHTML = Object.entries(componentCatalog).map(([type, category]) => `
    <section class="config-category ${escapeHtml(type)}" aria-labelledby="category-${escapeHtml(type)}">
      <div class="category-label">
        <span class="category-icon" aria-hidden="true">${escapeHtml(category.icon)}</span>
        <b id="category-${escapeHtml(type)}">${escapeHtml(category.label)}</b>
      </div>
      <button class="carousel-button" type="button" data-scroll-category="${escapeHtml(type)}" data-scroll-direction="-1" aria-label="向左查看更多${escapeHtml(category.label)}">‹</button>
      <div class="component-viewport" data-component-viewport="${escapeHtml(type)}">
        <div class="component-track ${category.twoRows ? 'two-row' : ''}">
          ${category.items.map(item => componentOptionMarkup(type, item)).join('')}
        </div>
      </div>
      <button class="carousel-button" type="button" data-scroll-category="${escapeHtml(type)}" data-scroll-direction="1" aria-label="向右查看更多${escapeHtml(category.label)}">›</button>
    </section>
  `).join('');
  Object.entries(scrollPositions).forEach(([type, scrollLeft]) => {
    const viewport = selectors.querySelector(`[data-component-viewport="${type}"]`);
    if (viewport) viewport.scrollLeft = scrollLeft;
  });
}

function findComponent(type, id) {
  return componentCatalog[type]?.items.find(item => item.id === id);
}

function toggleComponent(type, id) {
  const item = findComponent(type, id);
  if (!item) return;
  if (item.selected && componentCatalog[type].items.filter(option => option.selected).length === 1) {
    showToast(`请至少保留 1 个${componentCatalog[type].label}`);
    return;
  }
  if (!item.selected && !item.supplemental && categoryCount(type) >= 8) {
    showToast(`${componentCatalog[type].label}合计最多选择 8 个`);
    return;
  }
  item.selected = !item.selected;
  item.quantity = Math.max(1, item.quantity);
  syncCounts();
  renderComponentSelectors();
  updateSummary();
}

function changeComponentQuantity(type, id, delta) {
  const item = findComponent(type, id);
  if (!item || !item.selected) return;
  if (!item.supplemental && delta > 0 && categoryCount(type) >= 8) {
    showToast(`${componentCatalog[type].label}合计最多选择 8 个`);
    return;
  }
  item.quantity = Math.max(1, Math.min(8, item.quantity + delta));
  syncCounts();
  renderComponentSelectors();
  updateSummary();
}

function selectedComponents() {
  return Object.fromEntries(Object.entries(componentCatalog).map(([type, category]) => [
    type,
    category.items
      .filter(item => item.selected)
      .map(item => ({ name: item.name, model: item.model, quantity: item.quantity, supplemental: Boolean(item.supplemental) })),
  ]));
}

function showConfigError(message = '') {
  const error = document.getElementById('configError');
  if (!error) return;
  error.textContent = message;
  error.classList.toggle('visible', Boolean(message));
}

function updateSummary() {
  const buttonCount = supplementalCount('sensor');
  document.getElementById('configSummary').textContent =
    `已选择：显示器 ${counts.display} 个、传感器 ${counts.sensor} 个 + 按键 ${buttonCount} 个、执行驱动器 ${counts.actuator} 个`;
}

function solutionCard(className, prefix, title, layer) {
  const components = Array.isArray(layer.components) && layer.components.length
    ? layer.components
    : (layer.items || []).map(name => ({ name, description: '该器件用于完成本层级对应功能。' }));
  const tags = components.map(component => `<span class="tag">${escapeHtml(component.name)}</span>`).join('');
  const descriptions = components
    .map(component => `${escapeHtml(component.name)}：${escapeHtml(component.description)}`)
    .join('<br />');
  return `
    <article class="solution-card ${className}">
      <h3>${prefix}. ${title}（共 ${components.length} 个）</h3>
      <div class="solution-body">
        <div class="solution-block"><label>推荐模块 / 器件</label><div class="parts">${tags}</div></div>
        <div class="solution-block"><label>器件功能说明</label><p>${descriptions}</p></div>
      </div>
    </article>`;
}

function listMarkup(items) {
  return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function oledPreviewMarkup(pages) {
  if (!Array.isArray(pages) || !pages.length) return '';
  const total = pages.length;
  return `<div class="oled-pages">${pages.map((page, index) => {
    const lines = Array.isArray(page.lines) ? page.lines.slice(0, 4) : [];
    if (lines.length !== 4) return '';
    return `<figure class="oled-page">
      <figcaption>页面 ${index + 1} / ${total} · ${escapeHtml(page.title || 'OLED 页面')}</figcaption>
      <div class="oled-bezel" aria-label="OLED 页面 ${index + 1}">
        <div class="oled-screen">${lines.map(line => `<div class="oled-line">${escapeHtml(line)}</div>`).join('')}</div>
      </div>
    </figure>`;
  }).join('')}</div>`;
}

function logicCard(logic) {
  const displayPages = Array.isArray(logic.oled_pages) && logic.oled_pages.length
    ? `<div class="solution-block oled-design"><label>OLED 页面预览</label><p class="oled-hint">每页固定 4 行；按 KEY1 可在页面间切换。</p>${oledPreviewMarkup(logic.oled_pages)}</div>`
    : Array.isArray(logic.display_design) && logic.display_design.length
      ? `<div class="solution-block"><label>OLED 页面设计</label>${listMarkup(logic.display_design)}</div>`
    : '';
  const networking = logic.networking.enabled
    ? `<div class="solution-block"><label>联网功能</label><p>${escapeHtml(logic.networking.note)}</p></div>`
    : '';
  return `
    <article class="solution-card logic">
      <h3>D. 功能设计</h3>
      <div class="solution-body">
        <div class="solution-block"><label>主控芯片</label><p><b>${escapeHtml(logic.controller.name)}</b></p></div>
        <div class="solution-block"><label>核心功能</label>${listMarkup(logic.function_lines)}</div>
        ${displayPages}
        ${networking}
      </div>
    </article>`;
}

async function generateSolution() {
  if (!chosenTopic) {
    showToast('请先选择题目');
    goTo('results');
    return;
  }
  const button = document.querySelector('.generate-btn');
  showConfigError();
  setBusy(button, true, '正在生成…', '生成完整功能方案 →');
  setAnalysisState('RUNNING');
  try {
    const data = await request('/api/designs/generate', {
      topic: chosenTopic,
      counts,
      components: selectedComponents(),
      requirements: document.getElementById('specialRequirement').value.trim(),
    });
    const solution = data.solution;
    generatedSolution = solution;
    const evaluation = evaluatedTopics.find(topic => topic.title === chosenTopic);
    document.getElementById('solutionMeta').textContent =
      `基于题目：${solution.topic}　｜　${engineLabel(data.engine)}　｜　配置：显示器 ${counts.display} 个、传感器 ${counts.sensor} 个、执行驱动器 ${counts.actuator} 个`;
    const printValues = {
      printHardwareScore: evaluation?.hardware_score ?? '—',
      printSoftwareScore: evaluation?.software_score ?? '—',
      printTotalScore: evaluation?.total_score ?? '—',
      printConclusion: evaluation?.conclusion ?? '未评估',
      printReason: evaluation?.reason ?? '本方案未关联选题评分记录。',
    };
    Object.entries(printValues).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
    document.getElementById('solutionGrid').innerHTML = [
      solutionCard('sensor', 'A', '传感器方案', solution.sensors),
      solutionCard('display', 'B', '显示屏方案', solution.displays),
      solutionCard('actuator', 'C', '执行驱动器方案', solution.actuators),
      logicCard(solution.design_logic),
    ].join('');
    goTo('solution');
    setAnalysisState('COMPLETE');
    if (data.warning) showToast(data.warning);
  } catch (error) {
    showConfigError(error.message);
    showToast(error.message);
    setAnalysisState('ERROR');
  } finally {
    setBusy(button, false, '正在生成…', '生成完整功能方案 →');
  }
}

async function exportDatasheets() {
  if (!generatedSolution) {
    showToast('请先生成功能方案');
    return;
  }
  const button = document.getElementById('exportDatasheetBtn');
  button.disabled = true;
  button.textContent = '正在打包...';
  try {
    const names = [
      ...(generatedSolution.sensors?.components || []).map(c => c.name),
      ...(generatedSolution.displays?.components || []).map(c => c.name),
      ...(generatedSolution.actuators?.components || []).map(c => c.name),
    ];
    const response = await fetch('/api/components/datasheets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ components: names }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: '导出失败' }));
      throw new Error(error.error || '导出失败');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${generatedSolution.topic.replace(/[\\/:*?"<>|]/g, '-').slice(0, 40)}_硬件资料包.zip`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('硬件资料包已下载');
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = '⇩ 导出硬件资料包';
  }
}

function exportSolutionPDF() {
  if (!generatedSolution) {
    showToast('请先生成功能方案');
    return;
  }
  const originalTitle = document.title;
  const safeTopic = generatedSolution.topic.replace(/[\\/:*?"<>|]/g, '-').slice(0, 60);
  document.title = `${safeTopic}-功能方案`;
  const restoreTitle = () => {
    document.title = originalTitle;
    window.removeEventListener('afterprint', restoreTitle);
  };
  window.addEventListener('afterprint', restoreTitle);
  fetch('/api/events/pdf-export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic: generatedSolution.topic, status: 'opened' }),
    keepalive: true,
  }).catch(() => {});
  window.print();
  window.setTimeout(restoreTitle, 1000);
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

input.addEventListener('input', updateCount);
updateCount();
evaluateButton.addEventListener('click', evaluateTopics);
document.getElementById('resultsList').addEventListener('click', event => {
  const button = event.target.closest('[data-topic-index]');
  if (button) chooseTopicByIndex(Number(button.dataset.topicIndex), button);
});
document.getElementById('componentSelectors').addEventListener('click', event => {
  showConfigError();
  const quantityButton = event.target.closest('[data-quantity-change]');
  if (quantityButton) {
    changeComponentQuantity(
      quantityButton.dataset.componentType,
      quantityButton.dataset.componentId,
      Number(quantityButton.dataset.quantityChange),
    );
    return;
  }
  const toggleButton = event.target.closest('[data-component-toggle]');
  if (toggleButton) {
    toggleComponent(toggleButton.dataset.componentToggle, toggleButton.dataset.componentId);
    return;
  }
  const scrollButton = event.target.closest('[data-scroll-category]');
  if (scrollButton) {
    const viewport = document.querySelector(`[data-component-viewport="${scrollButton.dataset.scrollCategory}"]`);
    viewport?.scrollBy({ left: Number(scrollButton.dataset.scrollDirection) * 430, behavior: 'smooth' });
  }
});
document.getElementById('specialRequirement').addEventListener('input', () => showConfigError());
document.querySelectorAll('[data-nav]').forEach(button => button.addEventListener('click', () => goTo(button.dataset.nav)));

window.goTo = goTo;
window.chooseTopic = chooseTopic;
window.generateSolution = generateSolution;
window.exportSolutionPDF = exportSolutionPDF;
window.exportDatasheets = exportDatasheets;
window.showToast = showToast;
syncCounts();
renderComponentSelectors();
updateSummary();
updateAIStatus();
