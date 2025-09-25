#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gait Physiological Signal Dashboard - StrideX (v13, Unified One-Page)
- 좌측: Subject ID 리스트 (파일들을 subjid 로 통합)
- 중앙: 한 화면에서 IMU → Gait Pad → Smart Insole 순서로 섹션 배치
  · 각 지표는 좌측 라벨 + 우측 게이지 바
  · L/R은 동일 바에 두 개의 마커(파랑=L, 주황=R)
  · Gait Pad: 보행주기(입각/유각) L/R 비율 바 포함
  · Smart Insole: Day 선택 콤보로 특정 Day 지표 표시
- 하단: Meta / Labels 표 + 저작권 문구
- 주석(지표 설명) 유지 + 토글
- 아이콘: exe(탐색기) + 창(타이틀/작업표시줄)
"""

import os, sys, json, gzip, re, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from typing import Any, Dict, List, Tuple, Optional, Union
import numpy as np

# 아이콘 변환 보조
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

APP_TITLE = "Gait Physiological Signal Dashboard - StrideX"
WIN_W, WIN_H = 1480, 920
COLORS = {"L": "#1f77b4", "R": "#ff7f0e"}  # L=blue, R=orange

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

# -------------------- 공통 유틸 --------------------
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
    rows=[]
    for ln in txt.splitlines():
        s=ln.strip()
        if not s: continue
        try: rows.append(json.loads(s))
        except: break
    if rows: return {"records": rows}
    raise ValueError("지원되지 않는 JSON 형식")

def _safe(d: Any, path: List[Union[str,int]]) -> Any:
    cur=d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur=cur[p]
        elif isinstance(cur, list) and isinstance(p,int) and 0<=p<len(cur):
            cur=cur[p]
        else:
            return None
    return cur

def _f(x: Any, default: Optional[float]=None) -> Optional[float]:
    try:
        if x is None: return default
        if isinstance(x,(int,float)): return float(x)
        return float(str(x).strip())
    except:
        return default

def flatten_kv(d: Dict[str, Any], parent: str = "") -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        key = f"{parent}.{k}" if parent else str(k)
        if isinstance(v, dict):
            items.extend(flatten_kv(v, key))
        elif isinstance(v, list):
            pv = v[:8]
            s = ", ".join(map(lambda x: str(x), pv))
            if len(v) > 8: s += f", …(+{len(v)-8})"
            items.append((key.split(".")[-1], f"[{s}]"))
        else:
            items.append((key.split(".")[-1], str(v)))
    return items

# -------------------- 테이블 --------------------
class KVTable(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self["columns"]=("value",)
        self.heading("#0", text="Key")
        self.heading("value", text="Value")
        self.column("#0", width=220, stretch=True)
        self.column("value", width=420, stretch=True)
    def load_from_dict(self, d: Dict[str, Any]):
        self.delete(*self.get_children())
        for k,v in flatten_kv(d):
            self.insert("", "end", text=k, values=(v,))

def prettify_labels(raw_labels: Dict[str, Any]) -> Dict[str, Any]:
    ann = raw_labels.get("annotation") if isinstance(raw_labels, dict) else None
    if isinstance(ann, dict):
        klass=ann.get("class"); side=ann.get("side"); region=ann.get("region")
        diag = raw_labels.get("diagnosis_text")
    else:
        klass=raw_labels.get("class"); side=raw_labels.get("side")
        region=raw_labels.get("region"); diag=raw_labels.get("diagnosis_text")
    def class_display(v):
        try: iv=int(v)
        except: return str(v) if v is not None else "None"
        return f"{iv} ({'정상' if iv==0 else '무릎관절염'})"
    return {
        "class (0:정상, 1:무릎관절염)": class_display(klass) if klass is not None else "None",
        "side (병변 측)": side if side is not None else "None",
        "region (부위)": region if region is not None else "None",
        "diagnosis_text (진단 내용)": diag if diag is not None else "None",
    }

# -------------------- 게이지 위젯 --------------------
class DualMarkerGaugeRow(ttk.Frame):
    """
    좌측 라벨 + 우측 범위바(배경구간) + L/R 두 개의 삼각 마커
    - L 마커: 파랑, R 마커: 주황
    """
    def __init__(self, master, label_ko: str, label_en: str = "", width=680, **kw):
        super().__init__(master, **kw)
        self.lbl = ttk.Label(self, text=f"{label_ko}\n{label_en}", width=18, anchor="w")
        self.lbl.grid(row=0, column=0, sticky="w", padx=(0,8))
        self.canvas = tk.Canvas(self, width=width, height=28, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)
        self.width, self.height = width, 28

    def draw(self, L: Optional[float], R: Optional[float],
             vmin: float, vmax: float,
             ranges: List[Tuple[float,float,str]],
             ticks: Optional[List[Tuple[float,str]]] = None):
        c=self.canvas; c.delete("all")
        w,h=self.width,self.height; x0,y0,x1,y1=2,2,w-2,h-2
        # 배경 구간
        for lo,hi,color in ranges:
            lx = x0 + (max(lo,vmin)-vmin)/(vmax-vmin)*(x1-x0)
            hx = x0 + (min(hi,vmax)-vmin)/(vmax-vmin)*(x1-x0)
            c.create_rectangle(lx,y0,hx,y1,fill=color,width=0)
        c.create_rectangle(x0,y0,x1,y1,outline="#b9c1cc")
        # 눈금
        if ticks:
            for tx,txt in ticks:
                px = x0 + (tx-vmin)/(vmax-vmin)*(x1-x0)
                c.create_line(px,y0,px,y1,fill="#e1e6ef")
                c.create_text(px,y1+10,text=txt,anchor="n",fill="#7a8391",font=("Segoe UI",8))
        # 마커
        def _mark(val, color, upwards=True):
            if val is None: return
            pv = max(min(val,vmax),vmin)
            px = x0 + (pv-vmin)/(vmax-vmin)*(x1-x0)
            if upwards:
                c.create_polygon(px, y0-7, px-6, y0, px+6, y0, fill=color, outline="")
                c.create_text(px, y0-9, text=f"{val:.2f}", anchor="s", font=("Segoe UI",9), fill=color)
            else:
                c.create_polygon(px, y1+7, px-6, y1, px+6, y1, fill=color, outline="")
                c.create_text(px, y1+9, text=f"{val:.2f}", anchor="n", font=("Segoe UI",9), fill=color)
        _mark(L, COLORS["L"], upwards=True)
        _mark(R, COLORS["R"], upwards=False)

class PhaseRatioRow(ttk.Frame):
    """보행주기 L/R: 입각기/유각기 두 줄 바"""
    def __init__(self, master, title="보행주기 (Stride time)", **kw):
        super().__init__(master, **kw)
        ttk.Label(self, text=title, width=18, anchor="w").grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0,8))
        self.barL = tk.Canvas(self, width=680, height=22, highlightthickness=0)
        self.barR = tk.Canvas(self, width=680, height=22, highlightthickness=0)
        self.barL.grid(row=0, column=1, sticky="ew", pady=2)
        self.barR.grid(row=1, column=1, sticky="ew", pady=2)
        self.columnconfigure(1, weight=1)

    def draw(self, stance_L: Optional[float], swing_L: Optional[float],
                   stance_R: Optional[float], swing_R: Optional[float]):
        stance_c="#cfead6"; swing_c="#d6ecfa"
        def _row(canvas, stance, swing, side):
            canvas.delete("all")
            w=int(canvas.winfo_width() or 680); h=22; x0,x1=2,w-2
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

# -------------------- 섹션(센서) --------------------
class IMUSection(ttk.Frame):
    """IMU 지표: DualMarkerGaugeRow 4개"""
    ORDER = [
        ("gait_cycle",        "보행 주기",        "(s)",   0.5, 2.0),
        ("knee_flexion_max",  "무릎 굴곡 최대각", "(deg)", 0.0, 140.0),
        ("knee_extension_max","무릎 신전 최대각", "(deg)", -10.0, 20.0),
        ("foot_clearance",    "발 들림 높이",     "(cm)",  0.0, 30.0),
    ]
    def __init__(self, master, show_notes_var: tk.BooleanVar):
        super().__init__(master, padding=(8,8))
        ttk.Label(self, text="IMU", font=("Segoe UI",13,"bold")).pack(anchor="w", pady=(0,4))
        self.rows: List[DualMarkerGaugeRow] = []
        for (key,ko,unit,vmin,vmax) in self.ORDER:
            row = DualMarkerGaugeRow(self, f"{ko} {unit}", key)
            row.pack(fill=tk.X, pady=4)
            self.rows.append(row)
        self.note = ttk.Label(self, justify="left",
            text=("[IMU]\n"
                  "gait_cycle : 보행 주기 (s)\n"
                  "knee_flexion_max : 무릎 굴곡 최대각 (deg)\n"
                  "knee_extension_max : 무릎 신전 최대각 (deg)\n"
                  "foot_clearance : 발 들림 높이 (cm)"))
        self.note.pack(anchor="w", pady=(6,0))
        # 노트 토글 연동
        self._bind_note(show_notes_var)

    def _bind_note(self, var: tk.BooleanVar):
        def _toggle(*_):
            self.note.configure(state=(tk.NORMAL if var.get() else tk.HIDDEN))
        var.trace_add("write", _toggle); _toggle()

    def update_from(self, values: Dict[str, Any]):
        for row,(key,ko,unit,vmin,vmax) in zip(self.rows,self.ORDER):
            val = values.get(key, {})
            L=_f(val.get("L")) if isinstance(val, dict) else _f(val)
            R=_f(val.get("R")) if isinstance(val, dict) else None
            row.draw(L, R, vmin, vmax,
                     ranges=[(vmin, (vmin+vmax)/2, "#d6ecfa"), ((vmin+vmax)/2, vmax, "#cfead6")],
                     ticks=[(vmin, f"{vmin:g}"), (vmax, f"{vmax:g}")])

class PadSection(ttk.Frame):
    def __init__(self, master, show_notes_var: tk.BooleanVar):
        super().__init__(master, padding=(8,8))
        ttk.Label(self, text="Gait Pad", font=("Segoe UI",13,"bold")).pack(anchor="w", pady=(0,4))
        # 게이지들
        self.step  = DualMarkerGaugeRow(self, "보폭 (cm)", "step_length");   self.step.pack(fill=tk.X, pady=4)
        self.vel   = DualMarkerGaugeRow(self, "보행 속도 (cm/s)", "velocity"); self.vel.pack(fill=tk.X, pady=4)
        self.st    = DualMarkerGaugeRow(self, "입각기 비율 (%)", "stance_phase_rate"); self.st.pack(fill=tk.X, pady=4)
        self.sw    = DualMarkerGaugeRow(self, "유각기 비율 (%)", "swing_phase_rate");  self.sw.pack(fill=tk.X, pady=4)
        self.ds    = DualMarkerGaugeRow(self, "양측 지지시간 (%)", "double_support_time"); self.ds.pack(fill=tk.X, pady=6)
        # 보행주기 비율 2줄
        self.cycle = PhaseRatioRow(self, "보행주기 (Stride time)"); self.cycle.pack(fill=tk.X, pady=(6,0))
        # 노트
        self.note = ttk.Label(self, justify="left",
            text=("[보행매트]\n"
                  "step_length: 보폭 객체(cm)\n"
                  "velocity: 보행 속도(cm/s)\n"
                  "stance_phase_rate: 입각기 비율 객체(%)\n"
                  "swing_phase_rate: 유각기 비율 객체(%)\n"
                  "double_support_time: 양측지지시간 객체(%)"))
        self.note.pack(anchor="w", pady=(6,0))
        self._bind_note(show_notes_var)

    def _bind_note(self, var: tk.BooleanVar):
        def _toggle(*_):
            self.note.configure(state=(tk.NORMAL if var.get() else tk.HIDDEN))
        var.trace_add("write", _toggle); _toggle()

    def update_from(self, values: Dict[str, Any]):
        def LR(metric):
            v = values.get(metric, {})
            if isinstance(v, dict): return _f(v.get("L")), _f(v.get("R"))
            return _f(v), None
        stepL,stepR = LR("step_length")
        velL, velR  = LR("velocity")   # velocity가 단일이면 L에만 들어갈 수 있음
        stL, stR    = LR("stance_phase_rate")
        swL, swR    = LR("swing_phase_rate")
        dsL, dsR    = LR("double_support_time")

        self.step.draw(stepL, stepR, 40, 120,
                       ranges=[(40,60,"#f7c6c5"),(60,90,"#d6ecfa"),(90,120,"#cfead6")],
                       ticks=[(40,"40"),(60,"60"),(90,"90"),(120,"120")])
        # velocity: 값 특성에 맞춰 범위 조정
        self.vel.draw(velL, velR, 80, 160,
                      ranges=[(80,110,"#f7c6c5"),(110,140,"#d6ecfa"),(140,160,"#cfead6")],
                      ticks=[(80,"80"),(110,"110"),(140,"140"),(160,"160")])
        self.st.draw(stL, stR, 30, 70,
                     ranges=[(30,40,"#d6ecfa"),(40,60,"#cfead6"),(60,70,"#f7c6c5")],
                     ticks=[(30,"30"),(40,"40"),(60,"60"),(70,"70")])
        self.sw.draw(swL, swR, 30, 70,
                     ranges=[(30,40,"#cfead6"),(40,60,"#d6ecfa"),(60,70,"#f7c6c5")],
                     ticks=[(30,"30"),(40,"40"),(60,"60"),(70,"70")])
        self.ds.draw(dsL, dsR, 10, 30,
                     ranges=[(10,15,"#cfead6"),(15,22,"#d6ecfa"),(22,30,"#f7c6c5")],
                     ticks=[(10,"10"),(15,"15"),(22,"22"),(30,"30")])

        # 보행주기 L/R 비율 (입각/유각) - 합 100 정규화
        def norm2(a,b):
            if a is None or b is None: return (None,None)
            s=max(a+b,1e-6); return (a/s*100.0, b/s*100.0)
        nL = norm2(stL, swL); nR = norm2(stR, swR)
        self.cycle.draw(nL[0], nL[1], nR[0], nR[1])

class InsoleSection(ttk.Frame):
    """Smart Insole: Day 선택 콤보 + 대표 지표들을 DualMarkerGaugeRow로"""
    METRICS = [
        ("gait_speed","보행 속도","(km/h)", 0.0, 8.0),
        ("balance","좌우 균형","(%)",        0.0, 100.0),
        ("foot_pressure_rear","후방 압력","(%)", 0.0, 100.0),
        ("foot_pressure_mid","중앙 압력","(%)",  0.0, 100.0),
        ("foot_pressure_fore","전방 압력","(%)", 0.0, 100.0),
        ("gait_distance","보행 거리","(m)",      0.0, 500.0),
        ("stride_length","보폭","(cm)",         0.0, 200.0),
        ("foot_angle","발각도","(idx)",         0.0, 2.0),
    ]
    def __init__(self, master, show_notes_var: tk.BooleanVar):
        super().__init__(master, padding=(8,8))
        top = ttk.Frame(self); top.pack(fill=tk.X)
        ttk.Label(top, text="Smart Insole", font=("Segoe UI",13,"bold")).pack(side=tk.LEFT)
        ttk.Label(top, text="Day:").pack(side=tk.LEFT, padx=(12,4))
        self.day_var = tk.StringVar(value="")
        self.day_combo = ttk.Combobox(top, textvariable=self.day_var, state="readonly", width=10)
        self.day_combo.pack(side=tk.LEFT)
        self.day_combo.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        self.rows: List[DualMarkerGaugeRow] = []
        for key,ko,unit,vmin,vmax in self.METRICS:
            rw = DualMarkerGaugeRow(self, f"{ko} {unit}", key)
            rw.pack(fill=tk.X, pady=4)
            self.rows.append(rw)

        self.note = ttk.Label(self, justify="left",
            text=("[스마트인솔]\n"
                  "gait_speed: 보행 속도(km/h)\n"
                  "foot_pressure_rear: 후방압력(%)\n"
                  "balance: 좌우 균형(%)\n"
                  "foot_pressure_mid: 중앙 압력(%)\n"
                  "foot_angle: 발각도(0: 내반슬, 1: 정상 정렬, 2: 외반슬)\n"
                  "foot_pressure_fore: 전방 압력(%)\n"
                  "gait_distance: 보행 거리(m)\n"
                  "stride_length: 보폭(cm)"))
        self.note.pack(anchor="w", pady=(6,0))
        self._bind_note(show_notes_var)

        self.values: Dict[str, Any] = {}
        self.day_keys: List[str] = []

    def _bind_note(self, var: tk.BooleanVar):
        def _toggle(*_):
            self.note.configure(state=(tk.NORMAL if var.get() else tk.HIDDEN))
        var.trace_add("write", _toggle); _toggle()

    def update_from(self, values: Dict[str, Any]):
        self.values = values or {}
        # day_* 키 정렬
        def day_num(k):
            m = re.match(r"day_(\d+)", k)
            return int(m.group(1)) if m else 0
        self.day_keys = sorted(list(self.values.keys()), key=day_num)
        opts = [k.replace("day_","Day ") for k in self.day_keys]
        self.day_combo["values"] = opts
        if opts:
            self.day_combo.current(0)
        else:
            self.day_var.set("")
        self._redraw()

    def _redraw(self):
        if not self.day_keys:
            for r in self.rows:
                r.draw(None, None, 0, 1, ranges=[(0,1,"#eee")])
            return
        sel = self.day_var.get()
        if not sel:
            dk = self.day_keys[0]
        else:
            idx = max(0, min(len(self.day_keys)-1, self.day_combo.current()))
            dk = self.day_keys[idx]

        dayv = self.values.get(dk, {})
        for (row,(key,ko,unit,vmin,vmax)) in zip(self.rows, self.METRICS):
            v = dayv.get(key)
            if isinstance(v, dict):
                L=_f(v.get("L")); R=_f(v.get("R"))
            else:
                L=_f(v); R=None
            row.draw(L, R, vmin, vmax,
                     ranges=[(vmin, (vmin+vmax)/2, "#d6ecfa"), ((vmin+vmax)/2, vmax, "#cfead6")],
                     ticks=[(vmin, f"{vmin:g}"), (vmax, f"{vmax:g}")])

# -------------------- Subject 인덱스 --------------------
class SubjectIndex:
    """파일들을 subject id로 통합"""
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
            if isinstance(doc.get("meta"), dict):
                info["meta"] = doc["meta"]
            if isinstance(doc.get("labels"), dict):
                info["labels"].append(doc["labels"])
            if _safe(doc, ["data","imu_sensor","values"]):
                info["imu"] = doc["data"]["imu_sensor"]["values"]
            if _safe(doc, ["data","gait_pad","values"]):
                info["pad"] = doc["data"]["gait_pad"]["values"]
            if _safe(doc, ["data","smart_insole","values"]):
                info["insole"] = doc["data"]["smart_insole"]["values"]
            self.files.append(p)

# -------------------- 스크롤 가능한 대시보드 컨테이너 --------------------
class ScrollDashboard(ttk.Frame):
    """캔버스에 프레임을 넣어 세로 스크롤 지원"""
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

# -------------------- 메인 App --------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry(f"{WIN_W}x{WIN_H}")
        self._set_icon()

        self.idx = SubjectIndex()
        self.show_notes = tk.BooleanVar(value=True)

        # 상단 바
        top = ttk.Frame(self); top.pack(side=tk.TOP, fill=tk.X, pady=(4,4))
        ttk.Button(top, text="데이터 추가", command=self.add_files).pack(side=tk.LEFT, padx=(0,6))
        ttk.Checkbutton(top, text="지표 설명 보기", variable=self.show_notes).pack(side=tk.LEFT)

        # 본문 2단: 좌측 리스트 / 우측 대시보드(+하단 표)
        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL); body.pack(fill=tk.BOTH, expand=True)

        # 좌: Subject 목록
        left = ttk.Frame(body, padding=(6,6)); body.add(left, weight=1)
        ttk.Label(left, text="Subjects").pack(anchor="w")
        self.listbox = tk.Listbox(left); self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 우: 대시보드 + 하단 표
        right = ttk.PanedWindow(body, orient=tk.VERTICAL); body.add(right, weight=3)

        # 대시보드(스크롤)
        self.dashboard = ScrollDashboard(right)
        right.add(self.dashboard, weight=3)

        # 섹션들 (IMU → Pad → Insole)
        self.sec_imu    = IMUSection(self.dashboard.inner, self.show_notes);    self.sec_imu.pack(fill=tk.X, pady=(6,2))
        ttk.Separator(self.dashboard.inner).pack(fill=tk.X, pady=6)
        self.sec_pad    = PadSection(self.dashboard.inner, self.show_notes);    self.sec_pad.pack(fill=tk.X, pady=(2,2))
        ttk.Separator(self.dashboard.inner).pack(fill=tk.X, pady=6)
        self.sec_insole = InsoleSection(self.dashboard.inner, self.show_notes); self.sec_insole.pack(fill=tk.X, pady=(2,6))

        # 하단 표
        bottom = ttk.PanedWindow(right, orient=tk.HORIZONTAL); right.add(bottom, weight=2)
        meta_f = ttk.Frame(bottom, padding=(4,2)); labels_f = ttk.Frame(bottom, padding=(4,2))
        bottom.add(meta_f, weight=1); bottom.add(labels_f, weight=1)
        hdr = tkfont.Font(size=12, weight="bold")
        ttk.Label(meta_f, text="Meta", anchor="center", font=hdr).pack(fill=tk.X)
        ttk.Label(labels_f, text="Labels", anchor="center", font=hdr).pack(fill=tk.X)
        self.meta_table = KVTable(meta_f); self.meta_table.pack(fill=tk.BOTH, expand=True)
        self.labels_table = KVTable(labels_f); self.labels_table.pack(fill=tk.BOTH, expand=True)

        # 저작권 풋터
        footer = ttk.Frame(self); footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer, text="GCU License  Copyright (c) 2025 Limminsik",
                  anchor="e", justify="right", font=tkfont.Font(size=8)).pack(side=tk.RIGHT, padx=8, pady=2)

        # 노트 토글 이벤트 -> 이미 섹션에서 바인딩했지만 초기값 반영 위해 강제 호출
        self.show_notes.set(self.show_notes.get())

    def _set_icon(self):
        try:
            ico_path = resource_path("assets/stridex.ico")
            png_path = resource_path("assets/stridex.png")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)  # 참조 유지
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
            have=[]
            info=self.idx.subjects[sid]
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

        # 하단 표: Meta / Labels
        meta = info.get("meta") or {}
        merged_labels: Dict[str, Any] = {}
        for lb in info.get("labels", []):
            if isinstance(lb, dict): merged_labels.update(lb)
        self.meta_table.load_from_dict(meta if isinstance(meta, dict) else {"meta": meta})
        self.labels_table.load_from_dict(prettify_labels(merged_labels))

        # 섹션 갱신
        if info.get("imu"):    self.sec_imu.update_from(info["imu"])
        else:                  self.sec_imu.update_from({})
        if info.get("pad"):    self.sec_pad.update_from(info["pad"])
        else:                  self.sec_pad.update_from({})
        if info.get("insole"): self.sec_insole.update_from(info["insole"])
        else:                  self.sec_insole.update_from({})

def main():
    app = App(); app.mainloop()

if __name__ == "__main__":
    main()



