// StrideX Web Dashboard - Blueprint JavaScript

// ===== Metric dictionary (KO/EN/unit) =====
const METRICS = {
  imu: {
    gait_cycle:           { ko: "보행 주기",           en: "gait_cycle",          unit: "s"   },
    knee_flexion_max:     { ko: "무릎 굴곡 최대각",     en: "knee_flexion_max",    unit: "deg" },
    knee_extension_max:   { ko: "무릎 신전 최대각",     en: "knee_extension_max",  unit: "deg" },
    foot_clearance:       { ko: "발 들림 높이",         en: "foot_clearance",      unit: "cm"  },
  },
  pad: {
    step_length:          { ko: "보폭",                 en: "step_length",         unit: "cm"  },
    velocity:             { ko: "보행 속도",            en: "velocity",            unit: "cm/s"},
    stance_phase_rate:    { ko: "입각기 비율",          en: "stance_phase_rate",   unit: "%"   },
    swing_phase_rate:     { ko: "유각기 비율",          en: "swing_phase_rate",    unit: "%"   },
    double_support_time:  { ko: "양측 지지시간",        en: "double_support_time", unit: "%"   },
  },
  insole: {
    gait_speed:           { ko: "보행 속도",            en: "gait_speed",          unit: "km/h"},
    balance:              { ko: "좌우 균형",            en: "balance",             unit: "%"   },
    foot_pressure_rear:   { ko: "후방 압력",            en: "foot_pressure_rear",  unit: "%"   },
    foot_pressure_mid:    { ko: "중앙 압력",            en: "foot_pressure_mid",   unit: "%"   },
    foot_pressure_fore:   { ko: "전방 압력",            en: "foot_pressure_fore",  unit: "%"   },
    foot_angle:           { ko: "발각도(0 내반슬 / 1 정상 / 2 외반슬)", en: "foot_angle", unit: "" },
    gait_distance:        { ko: "보행 거리",            en: "gait_distance",       unit: "m"   },
    stride_length:        { ko: "보폭",                 en: "stride_length",       unit: "cm"  },
  },
};

// 라벨 생성: "보행 주기 (s) / gait_cycle"
function metricLabel(section, key) {
  const meta = METRICS[section]?.[key] || { ko: key, en: key, unit: "" };
  const unit = meta.unit ? ` (${meta.unit})` : "";
  return `${meta.ko}${unit} / ${meta.en}`;
}

// ---------- 값 정규화 공통 ----------
const L_COLOR = "#1f77b4";  // 파랑
const R_COLOR = "#ff7f0e";  // 주황

// 숫자 변환: 10, "10", "10.2" -> number / 그 외 -> null
function toNum(v) {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

// 안전 포맷: null -> "–", 숫자 -> 소수 1자리(필요시 바꾸세요)
function fmt1(v) {
  const n = toNum(v);
  return n === null ? "–" : n.toFixed(1);
}

// L/R 오브젝트/단일값을 통일된 형태로
function normalizeLR(x) {
  if (x === null || x === undefined) return {L: null, R: null};
  if (typeof x === "object" && ("L" in x || "R" in x)) {
    return { L: toNum(x.L), R: toNum(x.R) };
  }
  // 단일값이면 L에만 넣음
  return { L: toNum(x), R: null };
}

// 데이터 키 오타/별칭 정리(있으면 여기에 추가)
function aliasKey(k) {
  const map = {
    "stride_lenght": "stride_length",
    "step_len": "step_length",
    // 필요시 추가
  };
  return map[k] || k;
}

// ---------- 게이지 & 페이즈 ----------
function pct(val, min, max) {
  const n = toNum(val);
  if (n === null) return null;
  const clamped = Math.min(Math.max(n, min), max);
  return ((clamped - min) / (max - min)) * 100;
}

  function drawGauge(el, raw, min, max) {
    if (!el) return;
    el.innerHTML = "";
    const bg = document.createElement("div");
    bg.className = "bar-bg";
    el.appendChild(bg);

    const {L, R} = normalizeLR(raw);

    // 좌측 텍스트 채우기
    const base = el.id;
    const setTxt = (id, v) => { const s=document.getElementById(id); if(s) s.textContent=fmt1(v); };
    setTxt(base+"_L", L); setTxt(base+"_R", R);

    const addDot = (cls, val) => {
      const n = toNum(val); if (n===null) return;
      const p = pct(n, min, max); if (p===null) return;
      const d = document.createElement("div");
      d.className = "dot "+cls; d.style.left = p + "%";
      d.title = `${cls.toUpperCase()}: ${fmt1(n)}`;
      bg.appendChild(d);
    };

    addDot("l", L);
    addDot("r", R);
  }

function drawPhase(el, stance, swing) {
  if (!el) return;
  el.innerHTML = "";
  const s = toNum(stance), w = toNum(swing);
  if (s === null || w === null) {
    el.style.background = "#eef1f5";
    return;
  }
  const total = s + w;
  const ps = (s / (total || 1)) * 100;
  const pw = (w / (total || 1)) * 100;

  const sdiv = document.createElement("div");
  sdiv.className = "stance-bar";
  sdiv.style.width = ps+"%";
  sdiv.style.height = "100%";
  sdiv.style.background = L_COLOR;
  sdiv.style.display = "inline-block";
  sdiv.style.textAlign = "center";
  sdiv.style.lineHeight = "20px";
  sdiv.style.fontSize = "12px";
  sdiv.style.color = "white";
  sdiv.textContent = `입각기 ${fmt1(s)}%`;
  
  const wdiv = document.createElement("div");
  wdiv.className = "swing-bar";
  wdiv.style.width = pw+"%";
  wdiv.style.height = "100%";
  wdiv.style.background = R_COLOR;
  wdiv.style.display = "inline-block";
  wdiv.style.textAlign = "center";
  wdiv.style.lineHeight = "20px";
  wdiv.style.fontSize = "12px";
  wdiv.style.color = "white";
  wdiv.textContent = `유각기 ${fmt1(w)}%`;

  el.appendChild(sdiv); 
  el.appendChild(wdiv);
}

// ===== API Bridge (pywebview ↔ JavaScript) =====
const API = {
  async getSubjects() {
    if (window.pywebview?.api) {
      return await window.pywebview.api.get_subjects();
    }
    // 브라우저에서 실행 시 fallback
    try {
      const response = await fetch('/api/subjects');
      return await response.json();
    } catch (e) {
      return { ok: false, error: "API not available" };
    }
  },

  async getSubject(subjId) {
    if (window.pywebview?.api) {
      return await window.pywebview.api.get_subject(subjId);
    }
    // 브라우저에서 실행 시 fallback
    try {
      const response = await fetch(`/api/patient/${subjId}`);
      return await response.json();
    } catch (e) {
      return { ok: false, error: "API not available" };
    }
  },

  async addFiles() {
    if (window.pywebview?.api) {
      return await window.pywebview.api.add_files();
    }
    alert("데스크톱 앱에서만 가능한 기능입니다.");
    return { ok: false, error: "Desktop app only" };
  },

  async clearData() {
    if (window.pywebview?.api) {
      return await window.pywebview.api.clear_data();
    }
    // 브라우저에서 실행 시 fallback
    try {
      const response = await fetch('/api/clear-data', { method: 'POST' });
      return await response.json();
    } catch (e) {
      return { ok: false, error: "API not available" };
    }
  }
};

// ===== pywebview API 준비 이벤트 대기 =====
function initApp() {
  console.log('StrideX Desktop Dashboard 초기화됨');
  
  // DOM 요소들
  const subjectList = document.getElementById("subjectList");
  const errorBox = document.getElementById("errorBox");
  const fileInput = document.getElementById("fileInput");
  const addDataBtn = document.getElementById("btnAdd");
  const clearDataBtn = document.getElementById("btnReset");

  // 현재 선택된 Subject
  let currentSubject = null;
  let currentData = null;

  // 1) Subjects 로드
  loadSubjects();

      // 2) Event Listeners
      console.log('버튼 요소 확인:', { addDataBtn, clearDataBtn, fileInput });
      
      if (addDataBtn) {
        addDataBtn.addEventListener("click", () => {
          console.log('데이터 추가 버튼 클릭됨');
          handleAddFiles();
        });
      } else {
        console.error('데이터 추가 버튼을 찾을 수 없습니다!');
      }
      
      if (fileInput) {
        fileInput.addEventListener("change", handleFileUpload);
      } else {
        console.error('파일 입력 요소를 찾을 수 없습니다!');
      }
      
      if (clearDataBtn) {
        clearDataBtn.addEventListener("click", () => {
          console.log('데이터 초기화 버튼 클릭됨');
          handleClearData();
        });
      } else {
        console.error('데이터 초기화 버튼을 찾을 수 없습니다!');
      }

  // Functions
  async function loadSubjects() {
    try {
      const result = await API.getSubjects();
      if (!result.ok) {
        throw new Error(result.error || 'Failed to load subjects');
      }
      const {subjects} = result;
      
      console.log('Subjects 로드 성공:', subjects);
      
      subjectList.innerHTML = '';
      subjects.forEach(subject => {
        const item = document.createElement('div');
        item.className = 'subject-item';
        item.setAttribute('data-subject-id', subject.id);
        item.innerHTML = `
          <div class="subject-id">${subject.id}</div>
          <div class="subject-sensors">${subject.sensors.join(', ')}</div>
        `;
        item.addEventListener('click', (event) => selectSubject(subject.id, event.currentTarget));
        subjectList.appendChild(item);
      });
      
      if (subjects.length > 0) {
        selectSubject(subjects[0].id, null);
      }
    } catch (err) {
      showError(`Subjects 로딩 실패: ${err.message}`);
    }
  }

  async function selectSubject(subjectId, eventTarget) {
    try {
      clearError();
      
      // UI 업데이트
      document.querySelectorAll('.subject-item').forEach(item => {
        item.classList.remove('active');
      });
      if (eventTarget) {
        eventTarget.classList.add('active');
      } else {
        // eventTarget이 없으면 해당 subject ID를 가진 요소를 찾아서 활성화
        const targetItem = document.querySelector(`[data-subject-id="${subjectId}"]`);
        if (targetItem) {
          targetItem.classList.add('active');
        }
      }
      
      console.log(`Subject 선택: ${subjectId}`);
      
      const result = await API.getSubject(subjectId);
      if (!result.ok) {
        throw new Error(result.error || 'Failed to load subject data');
      }
      
      currentData = result;
      currentSubject = subjectId;
      
      console.log('데이터 로드 성공:', currentData);
      console.log('데이터 구조:', {
        imu: currentData?.data?.imu_sensor?.values,
        pad: currentData?.data?.gait_pad?.values,
        insole: currentData?.data?.smart_insole?.values
      });
      
      // 라벨 설정
      setSectionLabels();
      
      // 모든 섹션 업데이트
      updateIMUData();
      updatePadData();
      updateInsoleData();
      updateMetaLabels();
      
    } catch (err) {
      showError(`Patient 로딩 실패: ${err.message}`);
    }
  }

  function updateIMUData() {
    const imuData = currentData?.data?.imu_sensor?.values;
    if (!imuData) {
      console.log("IMU 데이터 없음");
      return;
    }

    console.log("IMU 데이터:", imuData);

    // IMU 메트릭들 업데이트 - 새로운 ID 구조 사용
    drawGauge(document.getElementById("imu_gait_cycle"), imuData.gait_cycle, 0.5, 2.0);
    drawGauge(document.getElementById("imu_knee_flexion_max"), imuData.knee_flexion_max, 0, 140);
    drawGauge(document.getElementById("imu_knee_extension_max"), imuData.knee_extension_max, -10, 20);
    drawGauge(document.getElementById("imu_foot_clearance"), imuData.foot_clearance, 0, 30);
  }

  function updatePadData() {
    const padData = currentData?.data?.gait_pad?.values;
    if (!padData) {
      console.log("Gait Pad 데이터 없음");
      return;
    }

    console.log("Gait Pad 데이터:", padData);

    // Gait Pad 메트릭들 업데이트 - 새로운 ID 구조 사용
    drawGauge(document.getElementById("pad_step_length"), padData.step_length ?? padData.step_len, 40, 120);
    drawGauge(document.getElementById("pad_velocity"), padData.velocity, 80, 160);
    drawGauge(document.getElementById("pad_stance_phase_rate"), padData.stance_phase_rate, 30, 70);
    drawGauge(document.getElementById("pad_swing_phase_rate"), padData.swing_phase_rate, 30, 70);
    drawGauge(document.getElementById("pad_double_support_time"), padData.double_support_time, 10, 30);

    // 보행주기 비율 바 업데이트 - 새로운 ID 구조 사용
    drawPhase(document.getElementById("pad_phase_L"), (padData.stance_phase_rate||{}).L, (padData.swing_phase_rate||{}).L);
    drawPhase(document.getElementById("pad_phase_R"), (padData.stance_phase_rate||{}).R, (padData.swing_phase_rate||{}).R);
  }

  function updateInsoleData() {
    const insoleData = currentData?.data?.smart_insole?.values;
    if (!insoleData) {
      console.log("Smart Insole 데이터 없음");
      return;
    }

    console.log("Smart Insole 데이터:", insoleData);

    // ---- INSOLE ----
    const ins = insoleData || {};
    buildDayChips(ins);
  }

  function buildDayChips(daysObj) {
    const wrap = document.getElementById("dayChips");
    wrap.innerHTML = "";
    const keys = Object.keys(daysObj || {}).sort((a, b) => {
      const A = parseInt(a.replace(/\D/g, "") || "0", 10);
      const B = parseInt(b.replace(/\D/g, "") || "0", 10);
      return A - B;
    });

    keys.forEach((k, i) => {
      const chip = document.createElement("button");
      chip.className = "day-chip" + (i === 0 ? " active" : "");
      chip.textContent = k.replace("day_", "Day ");
      chip.dataset.key = k;
      chip.onclick = () => {
        // active 토글
        [...wrap.children].forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        renderInsoleDay(daysObj[k]);   // ← 해당 day 렌더
      };
      wrap.appendChild(chip);
    });

    // 첫 day 자동 렌더
    if (keys.length) renderInsoleDay(daysObj[keys[0]]);
  }

  function renderInsoleDay(dayData) {
    // alias: stride_lenght -> stride_length
    if (dayData && dayData.stride_lenght != null && dayData.stride_length == null) {
      dayData.stride_length = dayData.stride_lenght;
    }
    // 게이지 바인딩
    drawGauge(document.getElementById("ins_gait_speed"), dayData?.gait_speed, 0, 8);
    drawGauge(document.getElementById("ins_balance"), dayData?.balance, 0, 100);
    drawGauge(document.getElementById("ins_foot_pressure_rear"), dayData?.foot_pressure_rear, 0, 100);
    drawGauge(document.getElementById("ins_foot_pressure_mid"), dayData?.foot_pressure_mid, 0, 100);
    drawGauge(document.getElementById("ins_foot_pressure_fore"), dayData?.foot_pressure_fore, 0, 100);
    drawGauge(document.getElementById("ins_gait_distance"), dayData?.gait_distance, 0, 500);
    drawGauge(document.getElementById("ins_stride_length"), dayData?.stride_length, 0, 200);
    drawGauge(document.getElementById("ins_foot_angle"), dayData?.foot_angle, 0, 2);
  }

  // 기존 updateMetric 함수들은 drawGauge/drawPhase로 대체됨

  function updateMetaLabels() {
    // Meta 테이블 업데이트
    renderMeta(currentData?.meta?.patient);
    
    // Labels 테이블 업데이트
    renderLabels(currentData?.labels);
  }

  // ===== set metric labels (once per render) =====
  function setSectionLabels() {
    // IMU
    ["gait_cycle","knee_flexion_max","knee_extension_max","foot_clearance"].forEach(k=>{
      const el = document.getElementById(`label_imu_${k}`);
      if (el) el.textContent = metricLabel("imu", k);
    });
    // Gait Pad
    ["step_length","velocity","stance_phase_rate","swing_phase_rate","double_support_time"].forEach(k=>{
      const el = document.getElementById(`label_pad_${k}`);
      if (el) el.textContent = metricLabel("pad", k);
    });
    // Insole
    ["gait_speed","balance","foot_pressure_rear","foot_pressure_mid","foot_pressure_fore","gait_distance","stride_length","foot_angle"].forEach(k=>{
      const el = document.getElementById(`label_insole_${k}`);
      if (el) el.textContent = metricLabel("insole", k);
    });
  }

  // Meta/Labels 우측 렌더 함수
  function lastKey(k) { 
    const p = k.split("."); 
    return p[p.length-1]; 
  }
  
  function flattenKV(obj, parent="") {
    const out = [];
    for (const [k, v] of Object.entries(obj || {})) {
      const key = parent ? `${parent}.${k}` : k;
      if (v && typeof v === "object" && !Array.isArray(v)) {
        out.push(...flattenKV(v, key));
      } else {
        out.push([lastKey(key), String(v)]);
      }
    }
    return out;
  }
  
  function renderMeta(meta) {
    const tbody = document.getElementById("meta_tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    flattenKV(meta || {}).forEach(([k, v]) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${k}</td><td>${v}</td>`;
      tbody.appendChild(tr);
    });
  }
  
  function prettyLabels(label) {
    const ann = label?.annotation || {};
    let cls = ann.class ?? label.class;
    let side = ann.side ?? label.side;
    let region = ann.region ?? label.region;
    const diag = label.diagnosis_text ?? "";
    const clsTxt = (cls === 0 || cls === "0") ? "0 (정상)" : (cls === 1 || cls === "1") ? "1 (무릎관절염)" : (cls ?? "None");
    return [
      ["class (0:정상, 1:무릎관절염)", clsTxt],
      ["side (병변 측)", side ?? "None"],
      ["region (부위)", region ?? "None"],
      ["diagnosis_text (진단 내용)", diag || "None"],
    ];
  }
  
  function renderLabels(labels) {
    const tbody = document.getElementById("labels_tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    // 최신 라벨 1개만 표시(원하시면 loop로 여러 줄 보여도 됩니다)
    const L = Array.isArray(labels) && labels.length ? labels[labels.length-1] : {};
    prettyLabels(L).forEach(([k, v]) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${k}</td><td>${v}</td>`;
      tbody.appendChild(tr);
    });
  }


  function showError(msg) {
    if (errorBox) {
      errorBox.style.display = 'block';
      errorBox.textContent = msg;
      setTimeout(() => {
        errorBox.style.display = 'none';
      }, 5000);
    } else {
      console.error(msg);
    }
  }
  
  function clearError() {
    if (errorBox) errorBox.style.display = 'none';
  }

  // 파일 추가 처리 (데스크톱 앱용)
  async function handleAddFiles() {
    try {
      showError("파일 선택 중...");
      
      const result = await API.addFiles();
      
      if (result.ok) {
        showError(result.message || "파일 추가 완료");
        
        // Subjects 목록 새로고침
        await loadSubjects();
      } else {
        showError(`파일 추가 실패: ${result.error}`);
      }
    } catch (err) {
      showError(`파일 추가 오류: ${err.message}`);
    }
  }

  // 파일 업로드 처리 (웹 브라우저용 fallback)
  async function handleFileUpload(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      showError("파일 업로드 중...");
      
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      if (result.success) {
        showError(`업로드 완료: ${result.uploaded_files.length}개 파일, ${result.total_subjects}개 Subject`);
        
        // Subjects 목록 새로고침
        await loadSubjects();
        
        // 파일 입력 초기화
        fileInput.value = '';
      } else {
        showError(`업로드 실패: ${result.message}`);
      }
    } catch (err) {
      showError(`업로드 오류: ${err.message}`);
    }
  }

  // 데이터 초기화 처리
  async function handleClearData() {
    if (!confirm('모든 데이터를 삭제하시겠습니까?')) return;

    try {
      const result = await API.clearData();
      
      if (result.ok) {
        showError("데이터가 초기화되었습니다.");
        
        // Subjects 목록 새로고침
        await loadSubjects();
        
        // 현재 데이터 초기화
        currentData = null;
        currentSubject = null;
      } else {
        showError(`초기화 실패: ${result.error}`);
      }
    } catch (err) {
      showError(`초기화 오류: ${err.message}`);
    }
  }
}

// ===== pywebview 준비 이벤트 대기 =====
if (window.pywebview) {
  // 이미 주입되어 있으면 바로 실행
  initApp();
} else {
  // pywebview가 준비되면 실행
  document.addEventListener('pywebviewready', initApp);
}

// 브라우저에서 테스트할 땐 다음 폴백을 써도 OK (서버 없이 디자인 확인용)
if (!window.pywebview) {
  window.pywebview = { 
    api: {
      add_files: async () => ({ok:false, subjects:{}}),
      get_subject: async () => ({}),
      reset: async () => ({ok:true}),
      get_subjects: async () => ({ok:true, subjects:[]}),
      clear_data: async () => ({ok:true})
    }
  };
  // 폴백 모드에서는 DOMContentLoaded로 실행
  document.addEventListener('DOMContentLoaded', initApp);
}
