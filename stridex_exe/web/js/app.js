// ===== 전역 상태 관리 =====
const STORE = { 
    subjects: {}, 
    current: null, 
    insoleDayIdx: 0 
};

function setSubjects(subjs) {
    STORE.subjects = subjs || {};
    console.log('[STORE] Subjects updated:', Object.keys(STORE.subjects));
}

function setCurrent(id) {
    STORE.current = id || null;
    STORE.insoleDayIdx = 0;
    console.log('[STORE] Current subject:', STORE.current);
}

function getCurrentSubject() {
    return STORE.current ? STORE.subjects[STORE.current] : null;
}

// ===== 유틸리티 함수 =====
const fmt = (v) => (v === null || v === undefined || isNaN(v) ? "-" : Number(v).toFixed(1));

function setTick(rowEl, LR) {
    const l = LR?.L, r = LR?.R;
    const valL = rowEl.querySelector(".val-L");
    const valR = rowEl.querySelector(".val-R");
    const tickL = rowEl.querySelector(".tick-L");
    const tickR = rowEl.querySelector(".tick-R");
    
    if (valL) valL.textContent = fmt(l);
    if (valR) valR.textContent = fmt(r);
    
    // 스케일 계산
    const scale = rowEl.dataset.scale || "0,100";
    const [min, max] = scale.split(",").map(Number);
    const pos = (v) => (v === null || isNaN(v) ? -1 : Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100)));
    
    // L 포인터 설정
    if (tickL) {
        tickL.style.left = (pos(l) < 0 ? "-9999px" : `${pos(l)}%`);
        tickL.setAttribute('data-value', fmt(l)); // 동그라미 위에 수치 표시
    }
    
    // R 포인터 설정
    if (tickR) {
        tickR.style.left = (pos(r) < 0 ? "-9999px" : `${pos(r)}%`);
        tickR.setAttribute('data-value', fmt(r)); // 동그라미 위에 수치 표시
    }
}

// ===== 섹션별 렌더링 =====
function renderSection(sectionName, dataObj) {
    console.log(`[RENDER] ${sectionName} section:`, dataObj);
    document.querySelectorAll(`[data-section="${sectionName}"][data-key]`).forEach(el => {
        const key = el.dataset.key;
        setTick(el, dataObj?.[key] || {L: null, R: null});
    });
}

function renderMeta(meta) {
    const tbody = document.querySelector("#meta_tbody");
    if (!tbody) return;
    
    tbody.innerHTML = "";
    console.log('[RENDER] Meta data:', meta);
    
    const m = meta || {};
    const p = m.patient || {};
    const pick = k => (p[k] ?? m[k] ?? '-');

    const order = ['id','gender','age','height','weight','bmi','foot_size','leg_length_L','leg_length_R','condition','symptom'];
    order.forEach(k => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${k}</td><td>${pick(k)}</td>`;
        tbody.appendChild(tr);
    });
}

function renderLabels(labels) {
    const tbody = document.querySelector("#labels_tbody");
    if (!tbody) return;
    
    tbody.innerHTML = "";
    console.log('[RENDER] Labels data:', labels);
    
    Object.entries(labels || {}).forEach(([k, v]) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${k}</td><td>${v ?? "-"}</td>`;
        tbody.appendChild(tr);
    });
}

function renderInsoleDays(insoleArr) {
    const dayChips = document.getElementById("dayChips");
    if (!dayChips) return;
    
    dayChips.innerHTML = "";
    console.log('[RENDER] Insole days:', insoleArr);
    
    (insoleArr || []).forEach((d, idx) => {
        const chip = document.createElement("button");
        chip.className = "day-chip" + (idx === STORE.insoleDayIdx ? " active" : "");
        chip.textContent = d.key.replace("day_", "Day ");
        chip.dataset.key = d.key;
        chip.onclick = () => {
            // active 토글
            [...dayChips.children].forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            STORE.insoleDayIdx = idx;
            renderInsoleDay(d);
        };
        dayChips.appendChild(chip);
    });
}

function renderInsoleDay(dayData) {
    console.log('[RENDER] Insole day data:', dayData);
    renderSection("insole-day", dayData);
}

// ===== 전체 렌더링 =====
function renderAll() {
    const subj = getCurrentSubject();
    console.log('[RENDER] Rendering all for subject:', STORE.current, subj);
    
    if (!subj) { 
        clearUI(); 
      return;
    }

    // 상단 IMU & Gait Pad
    renderSection("imu", subj.imu);
    renderSection("pad", subj.gait_pad);

    // Smart insole day
    renderInsoleDays(subj.insole);
    const day = subj.insole?.[STORE.insoleDayIdx || 0] || {};
    renderSection("insole-day", day);

    // 표
    renderMeta(subj.meta);
    renderLabels(subj.labels);
}

function clearUI() {
    console.log('[RENDER] Clearing UI');
    
    // 모든 섹션 초기화
    ["imu", "pad", "insole-day"].forEach(sec => {
        document.querySelectorAll(`[data-section="${sec}"][data-key] .val-L, [data-section="${sec}"][data-key] .val-R`).forEach(el => el.textContent = "-");
        document.querySelectorAll(`[data-section="${sec}"][data-key] .tick-L, [data-section="${sec}"][data-key] .tick-R`).forEach(el => el.style.left = "-9999px");
    });
    
    // 표들 초기화
    const metaTbody = document.querySelector("#meta_tbody");
    const labelsTbody = document.querySelector("#labels_tbody");
    if (metaTbody) metaTbody.innerHTML = "";
    if (labelsTbody) labelsTbody.innerHTML = "";
    
    // Day 칩 초기화
    const dayChips = document.getElementById("dayChips");
    if (dayChips) dayChips.innerHTML = "";
}

// ===== Subject 리스트 관리 =====
function renderSubjectList(subjects, ids) {
    const ul = document.getElementById("subjectList");
    if (!ul) return;
    
    ul.innerHTML = "";
    console.log('[RENDER] Subject list:', ids || Object.keys(subjects || {}));
    
    (ids || Object.keys(subjects || {})).forEach(id => {
        const li = document.createElement("li");
        li.className = "subject-item" + (STORE.current === id ? " active" : "");
        li.setAttribute('data-subject-id', id);
        
        const subj = subjects?.[id];
        const sensors = subj?.sensors || [];
        
        // 실제 데이터 존재 여부 확인
        const hasData = {
            imu: subj?.imu && Object.values(subj.imu).some(v => v?.L !== null || v?.R !== null),
            gait_pad: subj?.gait_pad && Object.values(subj.gait_pad).some(v => v?.L !== null || v?.R !== null),
            insole: subj?.insole && subj.insole.length > 0 && subj.insole.some(day => 
                Object.values(day).some(v => v?.L !== null || v?.R !== null)
            )
        };
        
        const dataCount = Object.values(hasData).filter(Boolean).length;
        const dataStatus = dataCount > 0 ? `데이터 ${dataCount}개 센서` : '데이터 없음';
        
        li.innerHTML = `
            <div class="subject-id">${id}</div>
            <div class="subject-sensors">${sensors.join(', ')}</div>
            <div class="subject-data-status">${dataStatus}</div>
        `;
        
        li.onclick = () => {
            setCurrent(id);
            renderAll();                 // ✅ 선택 후 즉시 렌더
            renderSubjectList(STORE.subjects, ids);
        };
        ul.appendChild(li);
    });
}


// ===== API Bridge =====
const API = {
    async getSubjects() {
        if (window.pywebview?.api) {
            return await window.pywebview.api.get_subjects();
        }
        return { ok: false, error: "API not available" };
    },

    async getSubject(subjId) {
        if (window.pywebview?.api) {
            return await window.pywebview.api.get_subject(subjId);
        }
        return { ok: false, error: "API not available" };
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
        return { ok: false, error: "API not available" };
    }
};

// ===== 이벤트 핸들러 =====
async function handleAddFiles() {
    try {
        console.log('[EVENT] Adding files...');
        const result = await API.addFiles();
        
        if (result.ok) {
            console.log('[EVENT] Files added successfully:', result);
            
            // subjects를 객체로 변환 (이미 전체 데이터가 포함됨)
            const subjectsObj = {};
            if (result.subjects) {
                result.subjects.forEach(subj => {
                    subjectsObj[subj.id] = subj;
                });
            }
            
            setSubjects(subjectsObj);
            const first = (result.ids && result.ids[0]) || Object.keys(subjectsObj)[0] || null;
            setCurrent(first);

            renderAll();                                  // ✅ 먼저 렌더
            renderSubjectList(STORE.subjects, result.ids);   // ✅ 그 다음 리스트 갱신
            
            showError(`파일 추가 완료: ${result.message || 'Success'}`);
      } else {
            showError(`파일 추가 실패: ${result.error}`);
      }
    } catch (err) {
        console.error('[EVENT] Add files error:', err);
        showError(`파일 추가 오류: ${err.message}`);
    }
  }

  async function handleClearData() {
    if (!confirm('모든 데이터를 삭제하시겠습니까?')) return;

    try {
        console.log('[EVENT] Clearing data...');
        const result = await API.clearData();
        
        if (result.ok) {
            console.log('[EVENT] Data cleared successfully');
            setSubjects({});
            setCurrent(null);
            clearUI();
            renderSubjectList({}, []);
            const sel = document.getElementById("insole-day");
            if (sel) sel.innerHTML = "";
            showError("데이터가 초기화되었습니다.");
      } else {
            showError(`초기화 실패: ${result.error}`);
      }
    } catch (err) {
        console.error('[EVENT] Clear data error:', err);
      showError(`초기화 오류: ${err.message}`);
    }
  }

async function loadSubjects() {
    try {
        console.log('[EVENT] Loading subjects...');
        const result = await API.getSubjects();
        
        if (result.ok) {
            console.log('[EVENT] Subjects loaded:', result.subjects);
            
            // subjects를 객체로 변환 (이미 전체 데이터가 포함됨)
            const subjectsObj = {};
            if (result.subjects) {
                result.subjects.forEach(subj => {
                    subjectsObj[subj.id] = subj;
                });
            }
            
            setSubjects(subjectsObj);
            renderSubjectList(STORE.subjects, result.ids);
            
            // 첫 Subject 자동 선택
            if (result.subjects && result.subjects.length > 0) {
                setCurrent(result.subjects[0].id);
                renderAll();
            }
        } else {
            showError(`Subjects 로딩 실패: ${result.error}`);
        }
    } catch (err) {
        console.error('[EVENT] Load subjects error:', err);
        showError(`Subjects 로딩 오류: ${err.message}`);
    }
}

// ===== UI 초기화 =====
function initApp() {
    console.log('[INIT] StrideX Desktop Dashboard 초기화됨');
    
    // DOM 요소들
    const subjectList = document.getElementById("subjectList");
    const errorBox = document.getElementById("errorBox");
    const addDataBtn = document.getElementById("btnAdd");
    const clearDataBtn = document.getElementById("btnReset");

    // 이벤트 리스너 등록
    if (addDataBtn) {
        addDataBtn.addEventListener("click", handleAddFiles);
    }
    
    if (clearDataBtn) {
        clearDataBtn.addEventListener("click", handleClearData);
    }

    // 초기 데이터 로드
    loadSubjects();
}

function showError(msg) {
    const errorBox = document.getElementById("errorBox");
    if (errorBox) {
        errorBox.textContent = msg;
        errorBox.style.display = 'block';
        setTimeout(() => {
            errorBox.style.display = 'none';
        }, 3000);
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
            add_files: async () => ({ok: false, subjects: []}),
            get_subject: async () => ({}),
            clear_data: async () => ({ok: true}),
            get_subjects: async () => ({ok: true, subjects: []})
        }
    };
    // 폴백 모드에서는 DOMContentLoaded로 실행
    document.addEventListener('DOMContentLoaded', initApp);
}
