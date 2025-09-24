#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gait Physiological Signal Dashboard - StrideX (v12, Unified)
- 좌측: Subject ID 리스트(파일들을 ID로 통합)
- 중앙: 3개 센서(IMU / Gait Pad / Smart Insole) 탭 + 주석(설명) 토글
- 상단: '데이터 추가' 버튼
- 하단: Meta / Labels 표 + 저작권 문구
"""

import os, sys, json, gzip, re, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from typing import Any, Dict, List, Tuple, Optional, Union

import numpy as np

# ====== 기존 v11에서 쓰던 일부 유틸/위젯을 간단 복붙 ======
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
APP_TITLE = "Gait Physiological Signal Dashboard - StrideX"
WIN_W, WIN_H = 1480, 920
COLORS = {"L": "#1f77b4", "R": "#ff7f0e"}

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

def read_text(path: str) -> str:
    if path.lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json_any(path: str) -> Dict[str, Any]:
    txt = read_text(path)
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict): return obj
        return {"root": obj}
    except Exception:
        pass
    rows = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s: continue
        try:
            rows.append(json.loads(s))
        except Exception:
            break
    if rows:
        return {"records": rows}
    raise ValueError("지원되지 않는 JSON 형식")

def _safe(d: Any, path: List[Union[str,int]]) -> Any:
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and isinstance(p,int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return None
    return cur

def _f(x: Any, default: Optional[float]=None) -> Optional[float]:
    try:
        if x is None: return default
        if isinstance(x,(int,float)): return float(x)
        return float(str(x).strip())
    except Exception:
        return default

def flatten_kv(d: Dict[str, Any], parent: str = "") -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        key = f"{parent}.{k}" if parent else str(k)
        if isinstance(v, dict):
            items.extend(flatten_kv(v, key))
        elif isinstance(v, list):
            preview = v[:8]
            s = ", ".join(map(lambda x: str(x), preview))
            if len(v) > 8: s += f", …(+{len(v)-8})"
            items.append((key.split(".")[-1], f"[{s}]"))
        else:
            items.append((key.split(".")[-1], str(v)))
    return items

class KVTable(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self["columns"] = ("value",)
        self.heading("#0", text="Key")
        self.heading("value", text="Value")
        self.column("#0", width=220, stretch=True)
        self.column("value", width=400, stretch=True)
    def load_from_dict(self, d: Dict[str, Any]):
        self.delete(*self.get_children())
        for k, v in flatten_kv(d):
            self.insert("", "end", text=k, values=(v,))

def prettify_labels(raw_labels: Dict[str, Any]) -> Dict[str, Any]:
    ann = raw_labels.get("annotation") if isinstance(raw_labels, dict) else None
    if isinstance(ann, dict):
        klass = ann.get("class"); side = ann.get("side"); region = ann.get("region")
        diag = raw_labels.get("diagnosis_text")
    else:
        klass = raw_labels.get("class"); side = raw_labels.get("side")
        region = raw_labels.get("region"); diag = raw_labels.get("diagnosis_text")
    def class_display(v):
        try: iv = int(v)
        except Exception: return str(v) if v is not None else "None"
        return f"{iv} ({'정상' if iv==0 else '무릎관절염'})"
    return {
        "class (0:정상, 1:무릎관절염)": class_display(klass) if klass is not None else "None",
        "side (병변 측)": side if side is not None else "None",
        "region (부위)": region if region is not None else "None",
        "diagnosis_text (진단 내용)": diag if diag is not None else "None",
    }

# ====== v11의 GaugeBar/PhaseRatio 그대로 사용 ======
class GaugeBarRow(ttk.Frame):
    def __init__(self, master, label_ko, label_en="", width=520, **kw):
        super().__init__(master, **kw)
        self.lbl = ttk.Label(self, text=f"{label_ko}\n{label_en}", width=18, anchor="w")
        self.lbl.grid(row=0, column=0, sticky="w", padx=(0,8))
        self.canvas = tk.Canvas(self, width=width, height=26, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)
        self.width, self.height = width, 26
    def draw(self, value: Optional[float], vmin: float, vmax: float,
             ranges: List[Tuple[float,float,str]],
             ticks: Optional[List[Tuple[float,str]]] = None):
        c=self.canvas; c.delete("all")
        w,h=self.width,self.height; x0,y0,x1,y1=2,2,w-2,h-2
        for lo,hi,color in ranges:
            lx = x0 + (max(lo,vmin)-vmin)/(vmax-vmin)*(x1-x0)
            hx = x0 + (min(hi,vmax)-vmin)/(vmax-vmin)*(x1-x0)
            c.create_rectangle(lx,y0,hx,y1,fill=color,width=0)
        c.create_rectangle(x0,y0,x1,y1,outline="#b9c1cc")
        if ticks:
            for tx,txt in ticks:
                px = x0 + (tx-vmin)/(vmax-vmin)*(x1-x0)
                c.create_line(px,y0,px,y1,fill="#e1e6ef")
                c.create_text(px,y1+10,text=txt,anchor="n",fill="#7a8391",font=("Segoe UI",8))
        if value is not None:
            pv = max(min(value,vmax),vmin)
            px = x0 + (pv-vmin)/(vmax-vmin)*(x1-x0)
            c.create_polygon(px,y0-6,px-6,y0,px+6,y0,fill="#333",outline="")
            c.create_text(px,y0-8,text=f"{value:.2f}",anchor="s",font=("Segoe UI",9))

class PhaseRatioRow(ttk.Frame):
    def __init__(self, master, title="보행주기 (Stride time)", **kw):
        super().__init__(master, **kw)
        ttk.Label(self, text=title, width=18, anchor="w").grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0,8))
        self.barL = tk.Canvas(self, width=520, height=22, highlightthickness=0)
        self.barR = tk.Canvas(self, width=520, height=22, highlightthickness=0)
        self.barL.grid(row=0, column=1, sticky="ew", pady=2)
        self.barR.grid(row=1, column=1, sticky="ew", pady=2)
        self.columnconfigure(1, weight=1)
    def draw(self, stance_L: Optional[float], swing_L: Optional[float],
                   stance_R: Optional[float], swing_R: Optional[float]):
        stance_c="#cfead6"; swing_c="#d6ecfa"
        def _row(canvas, stance, swing, side):
            canvas.delete("all")
            w=int(canvas.winfo_width() or 520); h=22; x0,x1=2,w-2
            canvas.create_rectangle(x0,2,x1,h-2,outline="#b9c1cc")
            if stance is None or swing is None:
                canvas.create_text(w//2,h//2,text="—",fill="#999")
                canvas.create_text(x0-20,h//2,text=("L" if side=="L" else "R"),
                                   fill=(COLORS["L"] if side=="L" else COLORS["R"]))
                return
            s=max(stance+swing,1e-6); ws=(x1-x0)*stance/s
            canvas.create_rectangle(x0,2,x0+ws,h-2,fill=stance_c,width=0)
            canvas.create_rectangle(x0+ws,2,x1,h-2,fill=swing_c,width=0)
            canvas.create_text(x0+ws/2,h//2,text=f"입각기 {stance:.1f}%",fill="#333")
            canvas.create_text(x0+ws+(x1-(x0+ws))/2,h//2,text=f"유각기 {swing:.1f}%",fill="#333")
            canvas.create_text(x0-20,h//2,text=("L" if side=="L" else "R"),
                               fill=(COLORS["L"] if side=="L" else COLORS["R"]))
        _row(self.barL, stance_L, swing_L, "L")
        _row(self.barR, stance_R, swing_R, "R")

# ====== 센서 별 Pane ======
# 1) IMU : 2x2 L/R bar (간단 캔버스 버전)
class IMUPane(ttk.Frame):
    ORDER = [("gait_cycle","(s)"),
             ("knee_flexion_max","(deg)"),
             ("knee_extension_max","(deg)"),
             ("foot_clearance","(cm)")]
    def __init__(self, master):
        super().__init__(master, padding=(6,6))
        self.rows: List[tk.Canvas] = []
        grid = ttk.Frame(self); grid.pack(fill=tk.BOTH, expand=True)
        for r in range(2):
            frm = ttk.Frame(grid); frm.pack(fill=tk.X, expand=False, pady=4)
            for c in range(2):
                cv = tk.Canvas(frm, height=160, highlightthickness=0, bg="white")
                cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
                self.rows.append(cv)
        # 설명
        self.note = ttk.Label(self, justify="left",
            text=("[IMU]\n"
                  "gait_cycle : 보행 주기 (s)\n"
                  "knee_flexion_max : 무릎 굴곡 최대각 (deg)\n"
                  "knee_extension_max : 무릎 신전 최대각 (deg)\n"
                  "foot_clearance : 발 들림 높이 (cm)"))
        self.note.pack(anchor="w", pady=(6,0))
    def update_from(self, values: Dict[str, Any]):
        for i, (key,unit) in enumerate(self.ORDER):
            cv = self.rows[i]; cv.delete("all")
            val = values.get(key)
            title = f"{key} {unit}"
            cv.create_text(8, 12, text=title, anchor="w", font=("Segoe UI",10,"bold"))
            if not isinstance(val, dict):
                cv.create_text(200,80,text="데이터 없음",fill="#999"); continue
            L = _f(val.get("L")); R = _f(val.get("R"))
            xs=[120,220]; hs=[]
            if L is not None: hs.append(L)
            if R is not None: hs.append(R)
            if not hs: cv.create_text(200,80,text="데이터 없음",fill="#999"); continue
            ymin, ymax = min(hs), max(hs)
            if ymin==ymax: ymin-=1; ymax+=1
            # bar 박스
            def _bar(x, v, color, label):
                # normalize
                h = 120
                yb = 140
                ratio = (v - ymin)/(ymax-ymin) if ymax>ymin else 0.5
                bh = max(4, ratio*h)
                cv.create_rectangle(x-20, yb-bh, x+20, yb, fill=color, width=0)
                cv.create_text(x, yb-bh-12, text=f"{v:.2f}", fill="#333")
                cv.create_text(x, yb+14, text=label)
            if L is not None: _bar(xs[0], L, COLORS["L"], "L")
            if R is not None: _bar(xs[-1], R, COLORS["R"], "R")

# 2) Gait Pad : 지표 게이지 + 보행주기 비율
class PadPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=(8,6))
        self.row_step  = GaugeBarRow(self, "보폭", "Step length");     self.row_step.pack(fill=tk.X, pady=4)
        self.row_vel   = GaugeBarRow(self, "보행 속도", "Velocity");   self.row_vel.pack(fill=tk.X, pady=4)
        self.row_st    = GaugeBarRow(self, "입각기 비율", "Stance phase"); self.row_st.pack(fill=tk.X, pady=4)
        self.row_sw    = GaugeBarRow(self, "유각기 비율", "Swing phase");  self.row_sw.pack(fill=tk.X, pady=4)
        self.row_ds    = GaugeBarRow(self, "양측 지지시간", "Double support"); self.row_ds.pack(fill=tk.X, pady=6)
        ttk.Separator(self).pack(fill=tk.X, pady=(6,6))
        self.ratio = PhaseRatioRow(self, "보행주기 (Stride time)")
        self.ratio.pack(fill=tk.X)
        self.note = ttk.Label(self, justify="left",
            text=("[보행매트]\n"
                  "step_length: 보폭 객체(cm)\n"
                  "velocity: 보행 속도(cm/s)\n"
                  "stance_phase_rate: 입각기 비율 객체(%)\n"
                  "swing_phase_rate: 유각기 비율 객체(%)\n"
                  "double_support_time: 양측지지시간 객체(%)"))
        self.note.pack(anchor="w", pady=(6,0))
    def update_from(self, values: Dict[str, Any]):
        # 값 읽기
        stepL=_f(_safe(values,["step_length","L"])); stepR=_f(_safe(values,["step_length","R"]))
        vel=_f(values.get("velocity"))
        stL=_f(_safe(values,["stance_phase_rate","L"])); stR=_f(_safe(values,["stance_phase_rate","R"]))
        swL=_f(_safe(values,["swing_phase_rate","L"])); swR=_f(_safe(values,["swing_phase_rate","R"]))
        dsL=_f(_safe(values,["double_support_time","L"])); dsR=_f(_safe(values,["double_support_time","R"]))
        # 게이지 (범위는 샘플)
        def mid(a,b): 
            arr=[x for x in (a,b) if x is not None]; 
            return float(np.nanmean(arr)) if arr else None
        self.row_step.draw(mid(stepL,stepR), vmin=40, vmax=120,
                           ranges=[(40,60,"#f7c6c5"),(60,90,"#d6ecfa"),(90,120,"#cfead6")],
                           ticks=[(40,"40"),(60,"60"),(90,"90"),(120,"120")])
        self.row_vel.draw(vel, vmin=80, vmax=160,
                          ranges=[(80,110,"#f7c6c5"),(110,140,"#d6ecfa"),(140,160,"#cfead6")],
                          ticks=[(80,"80"),(110,"110"),(140,"140"),(160,"160")])
        self.row_st.draw(mid(stL,stR), vmin=30, vmax=70,
                         ranges=[(30,40,"#d6ecfa"),(40,60,"#cfead6"),(60,70,"#f7c6c5")],
                         ticks=[(30,"30"),(40,"40"),(60,"60"),(70,"70")])
        self.row_sw.draw(mid(swL,swR), vmin=30, vmax=70,
                         ranges=[(30,40,"#cfead6"),(40,60,"#d6ecfa"),(60,70,"#f7c6c5")],
                         ticks=[(30,"30"),(40,"40"),(60,"60"),(70,"70")])
        self.row_ds.draw(mid(dsL,dsR), vmin=10, vmax=30,
                         ranges=[(10,15,"#cfead6"),(15,22,"#d6ecfa"),(22,30,"#f7c6c5")],
                         ticks=[(10,"10"),(15,"15"),(22,"22"),(30,"30")])
        # 입각/유각 비율 바 (L/R)
        def _norm2(a,b):
            if a is None or b is None: return (None,None)
            s=max(a+b,1e-6); return (a/s*100,b/s*100)
        nL=_norm2(stL,swL); nR=_norm2(stR,swR)
        self.ratio.draw(nL[0], nL[1], nR[0], nR[1])

# 3) Smart Insole : Day 범위 슬라이더 + 라인
class InsolePane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=(6,6))
        # 컨트롤 영역
        ctrl = ttk.Frame(self); ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Day range").pack(side=tk.LEFT)
        self.s_from = tk.IntVar(value=1); self.s_to = tk.IntVar(value=10)
        self.scale_from = ttk.Scale(ctrl, from_=1, to=10, orient="horizontal",
                                    command=lambda v:self._on_scale("from", v))
        self.scale_to   = ttk.Scale(ctrl, from_=1, to=10, orient="horizontal",
                                    command=lambda v:self._on_scale("to", v))
        self.scale_from.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.scale_to.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        # 플롯 (matplotlib 한 장에 2x2 대표 지표 예시)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(8,4), dpi=100)
        self.axes = [self.fig.add_subplot(221), self.fig.add_subplot(222),
                     self.fig.add_subplot(223), self.fig.add_subplot(224)]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self); self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.note = ttk.Label(self, justify="left",
            text=("[스마트인솔]\n"
                  "gait_speed: 보행 속도(km/h)\n"
                  "foot_pressure_rear: 후방압력(%)\n"
                  "balance: 좌우 균형(%)\n"
                  "foot_pressure_mid: 중앙 압력(%)\n"
                  "foot_angle: 발각도(0: 내반슬, 1: 정상 정렬, 2: 외반슬)\n"
                  "foot_pressure_fore: 전방 압력(%)\n"
                  "gait_distance: 보행 거리(m)\n"
                  "stride_lenght: 보폭(cm)"))
        self.note.pack(anchor="w", pady=(6,0))
        self.values: Dict[str, Any] = {}
        self.day_keys: List[str] = []

    def _on_scale(self, which, v):
        v=int(float(v))
        if which=="from": self.s_from.set(v)
        else: self.s_to.set(v)
        self.redraw()

    def update_from(self, values: Dict[str, Any]):
        self.values = values or {}
        # day 키 정렬
        def day_num(k): 
            m=re.match(r"day_(\d+)", k); 
            return int(m.group(1)) if m else 0
        self.day_keys = sorted(list(values.keys()), key=day_num)
        n = max(1, len(self.day_keys))
        self.scale_from.configure(to=n); self.scale_to.configure(to=n)
        self.s_from.set(1); self.s_to.set(n)
        self.redraw()

    def redraw(self):
        if not self.values or not self.day_keys:
            for ax in self.axes: ax.clear(); ax.text(0.5,0.5,"데이터 없음",ha="center",va="center")
            self.canvas.draw_idle(); return
        a,b = self.s_from.get(), self.s_to.get()
        if a>b: a,b=b,a
        sub_days = self.day_keys[a-1:b]
        xs = list(range(a,b+1))
        # 대표 4지표 예시
        plots = [
            ("gait_speed", "gait_speed (km/h)"),
            ("stride_length", "stride_length (cm)"),
            ("balance", "balance (%)"),
            ("foot_pressure_mid", "mid pressure (%)"),
        ]
        for ax in self.axes: ax.clear()
        for ax,(metric,title) in zip(self.axes, plots):
            sample = self.values.get(sub_days[0],{}).get(metric)
            if isinstance(sample, dict) and any(k in sample for k in ("L","R")):
                ysL=[_f(self.values.get(d,{}).get(metric,{}).get("L")) for d in sub_days]
                ysR=[_f(self.values.get(d,{}).get(metric,{}).get("R")) for d in sub_days]
                ax.plot(xs, ysL, marker="o", label="L", color=COLORS["L"])
                ax.plot(xs, ysR, marker="o", label="R", color=COLORS["R"])
                ax.legend(fontsize=8)
            else:
                ys=[_f(self.values.get(d,{}).get(metric)) for d in sub_days]
                ax.plot(xs, ys, marker="o", color=COLORS["L"])
            ax.set_title(title); ax.set_xticks(xs); ax.set_xticklabels([f"Day {i}" for i in xs])
            ax.grid(True, alpha=0.25)
        self.fig.tight_layout(); self.canvas.draw_idle()

# ====== 데이터 인덱스(Subject 단위 통합) ======
class SubjectIndex:
    """여러 json 파일을 Subject ID로 묶어 {id: {"meta":..., "labels":[...], "imu":..., "pad":..., "insole":...}} 형태로 보관"""
    def __init__(self):
        self.subjects: Dict[str, Dict[str, Any]] = {}
        self.files: List[str] = []

    def add_files(self, paths: List[str]):
        for p in paths:
            if p in self.files: continue
            try:
                doc = load_json_any(p)
            except Exception:
                continue
            pid = _safe(doc, ["meta","patient","id"]) or "UNKNOWN"
            info = self.subjects.setdefault(pid, {"meta":None, "labels":[], "imu":None, "pad":None, "insole":None})
            # meta / labels 병합
            if isinstance(doc.get("meta"), dict):
                info["meta"] = doc["meta"]
            if isinstance(doc.get("labels"), dict):
                info["labels"].append(doc["labels"])
            # 센서 분류
            if _safe(doc, ["data","imu_sensor","values"]):     info["imu"] = doc["data"]["imu_sensor"]["values"]
            if _safe(doc, ["data","gait_pad","values"]):       info["pad"] = doc["data"]["gait_pad"]["values"]
            if _safe(doc, ["data","smart_insole","values"]):   info["insole"] = doc["data"]["smart_insole"]["values"]
            self.files.append(p)

# ====== 메인 App ======
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry(f"{WIN_W}x{WIN_H}")
        self._set_icon()
        self.idx = SubjectIndex()

        # 상단 바
        top = ttk.Frame(self); top.pack(side=tk.TOP, fill=tk.X, pady=(4,4))
        ttk.Button(top, text="데이터 추가", command=self.add_files).pack(side=tk.LEFT, padx=(0,6))
        self.show_notes = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="지표 설명 보기", variable=self.show_notes, command=self._toggle_notes).pack(side=tk.LEFT)

        # 본문
        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL); body.pack(fill=tk.BOTH, expand=True)

        # 좌측: Subject 리스트
        left = ttk.Frame(body, padding=(6,6)); body.add(left, weight=1)
        ttk.Label(left, text="Subjects").pack(anchor="w")
        self.listbox = tk.Listbox(left); self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 우측: 센서 탭 + Meta/Labels
        right = ttk.PanedWindow(body, orient=tk.VERTICAL); body.add(right, weight=3)
        # 탭
        self.tabs = ttk.Notebook(right)
        right.add(self.tabs, weight=3)
        self.p_imu   = IMUPane(self.tabs)
        self.p_pad   = PadPane(self.tabs)
        self.p_insole= InsolePane(self.tabs)
        self.tabs.add(self.p_imu, text="IMU")
        self.tabs.add(self.p_pad, text="Gait Pad")
        self.tabs.add(self.p_insole, text="Smart Insole")

        # 하단 표
        bottom = ttk.PanedWindow(right, orient=tk.HORIZONTAL); right.add(bottom, weight=2)
        meta_f = ttk.Frame(bottom, padding=(4,2)); labels_f = ttk.Frame(bottom, padding=(4,2))
        bottom.add(meta_f, weight=1); bottom.add(labels_f, weight=1)
        hdr = tkfont.Font(size=12, weight="bold")
        ttk.Label(meta_f, text="Meta", anchor="center", font=hdr).pack(fill=tk.X)
        ttk.Label(labels_f, text="Labels", anchor="center", font=hdr).pack(fill=tk.X)
        self.meta_table = KVTable(meta_f); self.meta_table.pack(fill=tk.BOTH, expand=True)
        self.labels_table = KVTable(labels_f); self.labels_table.pack(fill=tk.BOTH, expand=True)

        # 푸터
        footer = ttk.Frame(self); footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer, text="GCU License  Copyright (c) 2025 Limminsik",
                  anchor="e", justify="right", font=tkfont.Font(size=8)).pack(side=tk.RIGHT, padx=8, pady=2)

    def _toggle_notes(self):
        # 주석 표시 on/off
        disp = tk.NORMAL if self.show_notes.get() else tk.HIDDEN
        for w in (self.p_imu.note, self.p_pad.note, self.p_insole.note):
            w.configure(state=disp)

    def _set_icon(self):
        try:
            ico_path = resource_path("assets/stridex.ico")
            png_path = resource_path("assets/stridex.png")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
        except Exception as e:
            print("아이콘 설정 실패:", e)

    def add_files(self):
        fs = filedialog.askopenfilenames(
            title="JSON 파일 선택",
            filetypes=[("JSON files","*.json *.jsonl *.ndjson *.json.gz"),("All files","*.*")]
        )
        if not fs: return
        self.idx.add_files(list(fs))
        self._refresh_subjects(select_last=True)

    def _refresh_subjects(self, select_last=False):
        self.listbox.delete(0, tk.END)
        ids = sorted(self.idx.subjects.keys())
        for sid in ids:
            # 좌측에 'SUBJ_001  (IMU, PAD, INSOLE)' 같은 보유 센서 정보도 함께
            have = []
            info = self.idx.subjects[sid]
            if info.get("imu"): have.append("IMU")
            if info.get("pad"): have.append("PAD")
            if info.get("insole"): have.append("INSOLE")
            self.listbox.insert(tk.END, f"{sid}  ({', '.join(have)})")
        if ids:
            idx = len(ids)-1 if select_last else 0
            self.listbox.selection_set(idx); self.on_select()

    def on_select(self, e=None):
        sel = self.listbox.curselection()
        if not sel: return
        ids = sorted(self.idx.subjects.keys())
        sid = ids[sel[0]]
        info = self.idx.subjects[sid]

        # Meta/Labels
        meta = info.get("meta") or {}
        merged_labels: Dict[str, Any] = {}
        # 여러 라벨이 있으면 첫 항목 우선, 나머지는 덮어 씌우기
        for lb in info.get("labels", []):
            if isinstance(lb, dict): merged_labels.update(lb)
        self.meta_table.load_from_dict(meta if isinstance(meta, dict) else {"meta": meta})
        self.labels_table.load_from_dict(prettify_labels(merged_labels))

        # 센서 탭 갱신 (센서 없는 탭은 '데이터 없음' 처리)
        if info.get("imu"):    self.p_imu.update_from(info["imu"])
        else:                  self.p_imu.update_from({})
        if info.get("pad"):    self.p_pad.update_from(info["pad"])
        else:                  self.p_pad.update_from({})
        if info.get("insole"): self.p_insole.update_from(info["insole"])
        else:                  self.p_insole.update_from({})

def main():
    app = App(); app.mainloop()

if __name__ == "__main__":
    main()



