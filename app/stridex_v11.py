#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gait Physiological Signal Dashboard - StrideX (v11)
- 좌측: 파일 리스트 + '데이터 추가'
- 중앙: 사진 같은 분석 레이아웃
  · 좌측 지표 텍스트, 우측 범위 게이지 바
  · 하단 보행주기 L/R 입각·유각 비율 바(두 줄)
- 하단: Meta / Labels 테이블, 우측 하단 저작권
- 아이콘: exe(탐색기) + 창(타이틀/작업표시줄) 모두 적용
"""

import os, sys, json, gzip, re, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from typing import Any, Dict, List, Tuple, Optional, Union

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# PIL (아이콘 변환/로드 보조)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

APP_TITLE = "Gait Physiological Signal Dashboard - StrideX"
WIN_W, WIN_H = 1400, 900

COLORS = {"L": "#1f77b4", "R": "#ff7f0e"}  # 파랑/주황

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

# ------------ 공통 유틸 ------------
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
        if isinstance(obj, dict):
            return obj
        return {"root": obj}
    except Exception:
        pass
    # JSONL fallback
    rows = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s:
            continue
        try:
            rows.append(json.loads(s))
        except Exception:
            break
    if rows:
        return {"records": rows}
    raise ValueError("지원되지 않는 JSON 형식")

def _safe(d: Any, path: List[Union[str, int]]) -> Any:
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return None
    return cur

def _f(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
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
            if len(v) > 8:
                s += f", …(+{len(v)-8})"
            items.append((key.split(".")[-1], f"[{s}]"))
        else:
            items.append((key.split(".")[-1], str(v)))
    return items

# ------------ Labels 표시 변환 ------------
def prettify_labels(raw_labels: Dict[str, Any]) -> Dict[str, Any]:
    ann = raw_labels.get("annotation") if isinstance(raw_labels, dict) else None
    if isinstance(ann, dict):
        klass = ann.get("class")
        side = ann.get("side")
        region = ann.get("region")
        diag = raw_labels.get("diagnosis_text")
    else:
        klass = raw_labels.get("class")
        side = raw_labels.get("side")
        region = raw_labels.get("region")
        diag = raw_labels.get("diagnosis_text")

    def class_display(v):
        try:
            iv = int(v)
        except Exception:
            return str(v) if v is not None else "None"
        return f"{iv} ({'정상' if iv == 0 else '무릎관절염'})"

    return {
        "class (0:정상, 1:무릎관절염)": class_display(klass) if klass is not None else "None",
        "side (병변 측)": side if side is not None else "None",
        "region (부위)": region if region is not None else "None",
        "diagnosis_text (진단 내용)": diag if diag is not None else "None",
    }

# ------------ 테이블 위젯 ------------
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

# ------------ 게이지/비율 위젯 ------------
class GaugeBarRow(ttk.Frame):
    """좌 텍스트 + 우 범위바"""
    def __init__(self, master, label_ko, label_en="", width=520, **kw):
        super().__init__(master, **kw)
        self.lbl = ttk.Label(self, text=f"{label_ko}\n{label_en}", width=18, anchor="w")
        self.lbl.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.canvas = tk.Canvas(self, width=width, height=26, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)
        self.width, self.height = width, 26

    def draw(self, value: Optional[float], vmin: float, vmax: float,
             ranges: List[Tuple[float, float, str]],
             ticks: Optional[List[Tuple[float, str]]] = None):
        c = self.canvas
        c.delete("all")
        w, h = self.width, self.height
        x0, y0, x1, y1 = 2, 2, w - 2, h - 2
        # 배경 구간
        for lo, hi, color in ranges:
            lx = x0 + (max(lo, vmin) - vmin) / (vmax - vmin) * (x1 - x0)
            hx = x0 + (min(hi, vmax) - vmin) / (vmax - vmin) * (x1 - x0)
            c.create_rectangle(lx, y0, hx, y1, fill=color, width=0)
        c.create_rectangle(x0, y0, x1, y1, outline="#b9c1cc")
        # 눈금
        if ticks:
            for tx, txt in ticks:
                px = x0 + (tx - vmin) / (vmax - vmin) * (x1 - x0)
                c.create_line(px, y0, px, y1, fill="#e1e6ef")
                c.create_text(px, y1 + 10, text=txt, anchor="n", fill="#7a8391", font=("Segoe UI", 8))
        # 값 마커
        if value is not None:
            pv = max(min(value, vmax), vmin)
            px = x0 + (pv - vmin) / (vmax - vmin) * (x1 - x0)
            c.create_polygon(px, y0 - 6, px - 6, y0, px + 6, y0, fill="#333", outline="")
            c.create_text(px, y0 - 8, text=f"{value:.2f}", anchor="s", font=("Segoe UI", 9))

class PhaseRatioRow(ttk.Frame):
    """보행주기 L/R: 입각기/유각기 두 줄"""
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
        stance_c = "#cfead6"  # 연녹
        swing_c  = "#d6ecfa"  # 연하늘

        def _row(canvas, stance, swing, side):
            canvas.delete("all")
            w = int(canvas.winfo_width() or 520); h = 22
            x0, x1 = 2, w - 2
            canvas.create_rectangle(x0, 2, x1, h - 2, outline="#b9c1cc")
            if stance is None or swing is None:
                canvas.create_text(w // 2, h // 2, text="—", fill="#999")
                canvas.create_text(x0 - 20, h // 2, text=("L" if side == "L" else "R"),
                                   fill=(COLORS["L"] if side == "L" else COLORS["R"]))
                return
            total = max(stance + swing, 1e-6)
            ws = (x1 - x0) * stance / total
            canvas.create_rectangle(x0, 2, x0 + ws, h - 2, fill=stance_c, width=0)
            canvas.create_rectangle(x0 + ws, 2, x1, h - 2, fill=swing_c, width=0)
            canvas.create_text(x0 + ws / 2, h // 2, text=f"입각기 {stance:.1f}%", fill="#333")
            canvas.create_text(x0 + ws + (x1 - (x0 + ws)) / 2, h // 2, text=f"유각기 {swing:.1f}%", fill="#333")
            canvas.create_text(x0 - 20, h // 2, text=("L" if side == "L" else "R"),
                               fill=(COLORS["L"] if side == "L" else COLORS["R"]))

        _row(self.barL, stance_L, swing_L, "L")
        _row(self.barR, stance_R, swing_R, "R")

# ------------ 분석 Pane (사진 스타일) ------------
class AnalysisBarsPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=(8, 6))
        self.grid_columnconfigure(1, weight=1)

        # 행 구성 (위에서 아래로)
        self.row_speed = GaugeBarRow(self, "보행속도", "Gait speed");        self.row_speed.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)
        self.row_step  = GaugeBarRow(self, "보폭", "Step length");           self.row_step.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
        self.row_arm   = GaugeBarRow(self, "팔 흔들기", "Arm swing");         self.row_arm.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
        self.row_asym  = GaugeBarRow(self, "하지 비대칭", "Lower limb asym."); self.row_asym.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)

        ttk.Separator(self).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8,6))

        self.row_trunk = GaugeBarRow(self, "상체 기울기", "Trunk flexion");    self.row_trunk.grid(row=5, column=0, columnspan=2, sticky="ew", pady=4)

        ttk.Separator(self).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8,6))

        self.row_cycle = PhaseRatioRow(self, title="보행주기 (Stride time)"); self.row_cycle.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4,0))

    def update_from_doc(self, doc: Dict[str, Any]):
        # >>> 실제 JSON 데이터 구조에 맞춰 매핑
        get = lambda p: _safe(doc, p)

        # 1. 보행속도 (gait_pad.velocity 또는 smart_insole 평균)
        speed = None
        if get(["data", "gait_pad", "values", "velocity"]):
            speed = _f(get(["data", "gait_pad", "values", "velocity"])) / 100.0  # cm/s → m/s
        elif get(["data", "smart_insole", "values", "day_1", "gait_speed"]):
            # 스마트인솔의 경우 여러 날 평균
            days = [f"day_{i}" for i in range(1, 11)]
            speeds = [_f(get(["data", "smart_insole", "values", day, "gait_speed"])) for day in days]
            speeds = [s for s in speeds if s is not None]
            speed = sum(speeds) / len(speeds) if speeds else None

        # 2. 보폭 (gait_pad.step_length 또는 smart_insole 평균)
        step = None
        if get(["data", "gait_pad", "values", "step_length", "L"]):
            step_L = _f(get(["data", "gait_pad", "values", "step_length", "L"]))
            step_R = _f(get(["data", "gait_pad", "values", "step_length", "R"]))
            if step_L is not None and step_R is not None:
                step = (step_L + step_R) / 2.0
        elif get(["data", "smart_insole", "values", "day_1", "stride_length", "L"]):
            # 스마트인솔의 경우 여러 날 평균
            days = [f"day_{i}" for i in range(1, 11)]
            steps = []
            for day in days:
                step_L = _f(get(["data", "smart_insole", "values", day, "stride_length", "L"]))
                step_R = _f(get(["data", "smart_insole", "values", day, "stride_length", "R"]))
                if step_L is not None and step_R is not None:
                    steps.append((step_L + step_R) / 2.0)
            step = sum(steps) / len(steps) if steps else None

        # 3. 팔 흔들기 (IMU 데이터에서 추정 - 임시값)
        arm = None
        if get(["data", "imu_sensor", "values", "gait_cycle", "L"]):
            # IMU 데이터가 있으면 보행주기 기반으로 추정
            cycle_L = _f(get(["data", "imu_sensor", "values", "gait_cycle", "L"]))
            cycle_R = _f(get(["data", "imu_sensor", "values", "gait_cycle", "R"]))
            if cycle_L is not None and cycle_R is not None:
                # 보행주기 차이로 팔 흔들기 비대칭 추정 (임시)
                arm = abs(cycle_L - cycle_R) * 50 + 30  # 30-50도 범위로 변환

        # 4. 하지 비대칭 (IMU 데이터에서 추정)
        asym = None
        if get(["data", "imu_sensor", "values", "knee_flexion_max", "L"]):
            flex_L = _f(get(["data", "imu_sensor", "values", "knee_flexion_max", "L"]))
            flex_R = _f(get(["data", "imu_sensor", "values", "knee_flexion_max", "R"]))
            if flex_L is not None and flex_R is not None:
                asym = abs(flex_L - flex_R) / max(flex_L, flex_R) * 100

        # 5. 상체 기울기 (IMU 데이터에서 추정)
        trunk = None
        if get(["data", "imu_sensor", "values", "foot_clearance", "L"]):
            clear_L = _f(get(["data", "imu_sensor", "values", "foot_clearance", "L"]))
            clear_R = _f(get(["data", "imu_sensor", "values", "foot_clearance", "R"]))
            if clear_L is not None and clear_R is not None:
                # 발 들림 높이 차이로 상체 기울기 추정 (임시)
                trunk = (clear_L - clear_R) * 0.5

        # 범위/눈금 (사진과 유사한 범위)
        self.row_speed.draw(speed, vmin=0.5, vmax=2.0,
            ranges=[(0.5,1.0,"#f7c6c5"), (1.0,1.5,"#d6ecfa"), (1.5,2.0,"#cfead6")],
            ticks=[(0.5,"0.5"),(1.0,"1.0"),(1.5,"1.5"),(2.0,"2.0")])
        self.row_step.draw(step, vmin=26, vmax=102,
            ranges=[(26,51,"#f7c6c5"), (51,76,"#d6ecfa"), (76,102,"#cfead6")],
            ticks=[(26,"26"),(51,"51"),(76,"76"),(102,"102")])
        self.row_arm.draw(arm, vmin=10, vmax=70,
            ranges=[(10,30,"#d6ecfa"), (30,50,"#cfead6"), (50,70,"#f7c6c5")],
            ticks=[(10,"10"),(30,"30"),(50,"50"),(70,"70")])
        self.row_asym.draw(asym, vmin=0, vmax=20,
            ranges=[(0,5,"#cfead6"), (5,10,"#d6ecfa"), (10,20,"#f7c6c5")],
            ticks=[(0,"0"),(5,"5"),(10,"10"),(20,"20")])
        self.row_trunk.draw(trunk, vmin=-10, vmax=20,
            ranges=[(-10,0,"#d6ecfa"), (0,10,"#cfead6"), (10,20,"#f7c6c5")],
            ticks=[(-6,"-6"),(-3,"-3"),(0,"0"),(7,"7"),(14,"14")])

        # 보행주기 입각/유각 비율 (L/R) - gait_pad 데이터 사용
        stance_L = _f(get(["data","gait_pad","values","stance_phase_rate","L"]))
        swing_L  = _f(get(["data","gait_pad","values","swing_phase_rate","L"]))
        stance_R = _f(get(["data","gait_pad","values","stance_phase_rate","R"]))
        swing_R  = _f(get(["data","gait_pad","values","swing_phase_rate","R"]))

        # 이미 퍼센트로 되어있으므로 그대로 사용
        self.row_cycle.draw(stance_L, swing_L, stance_R, swing_R)

# ------------ 메인 App ------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{WIN_W}x{WIN_H}")

        self._set_styles()
        self._set_icon()

        self.paths: List[str] = []
        self.cur_dir = os.getcwd()

        # 상단 컨트롤
        top = ttk.Frame(self); top.pack(side=tk.TOP, fill=tk.X, pady=(4,4))
        ttk.Button(top, text="데이터 추가", command=self.add_files).pack(side=tk.LEFT, padx=(0,4))

        # 본문 split
        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL); body.pack(fill=tk.BOTH, expand=True)

        # 좌측: 파일 리스트
        left = ttk.Frame(body, padding=(6,6))
        body.add(left, weight=1)
        self.listbox = tk.Listbox(left)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 우측: 분석 Pane + Meta/Labels
        right = ttk.PanedWindow(body, orient=tk.VERTICAL)
        body.add(right, weight=3)

        # 분석 Pane
        self.analysis = AnalysisBarsPane(right)
        right.add(self.analysis, weight=3)

        # 하단: Meta / Labels
        bottom = ttk.PanedWindow(right, orient=tk.HORIZONTAL)
        right.add(bottom, weight=2)

        meta_frame = ttk.Frame(bottom, padding=(4,2))
        labels_frame = ttk.Frame(bottom, padding=(4,2))
        bottom.add(meta_frame, weight=1)
        bottom.add(labels_frame, weight=1)

        header_font = tkfont.Font(size=12, weight="bold")
        meta_header = ttk.Label(meta_frame, text="Meta", anchor="center")
        meta_header.pack(fill=tk.X); meta_header.configure(font=header_font)
        self.meta_table = KVTable(meta_frame); self.meta_table.pack(fill=tk.BOTH, expand=True)

        labels_header = ttk.Label(labels_frame, text="Labels", anchor="center")
        labels_header.pack(fill=tk.X); labels_header.configure(font=header_font)
        self.labels_table = KVTable(labels_frame); self.labels_table.pack(fill=tk.BOTH, expand=True)

        # 하단 풋터
        footer = ttk.Frame(self); footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(
            footer,
            text="GCU License  Copyright (c) 2025 Limminsik",
            anchor="e", justify="right",
            font=tkfont.Font(size=8)
        ).pack(side=tk.RIGHT, padx=8, pady=2)

    # 스타일
    def _set_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Card.TFrame", relief="groove")
        style.configure("Hdr.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("HdrInfo.TLabel", foreground="#666")
        style.configure("CardTitle.TLabel", foreground="#666")
        style.configure("CardValue.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("CardUnit.TLabel", foreground="#666")
        style.configure("Note.TLabel", foreground="#333")

    # 아이콘(창/작업표시줄 + exe)
    def _set_icon(self):
        try:
            ico_path = resource_path("assets/stridex.ico")
            png_path = resource_path("assets/stridex.png")

            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)

            if os.path.exists(png_path):
                # 참조 유지(GC 방지)
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
            elif os.path.exists(ico_path) and PIL_AVAILABLE:
                # PNG 없으면 ICO를 PNG로 임시 변환 후 iconphoto에 사용 (옵션)
                tmp_png = os.path.join(tempfile.gettempdir(), "stridex_runtime.png")
                try:
                    Image.open(ico_path).save(tmp_png)
                    self._icon_img = tk.PhotoImage(file=tmp_png)
                    self.iconphoto(True, self._icon_img)
                except Exception:
                    pass
        except Exception as e:
            print("아이콘 설정 실패:", e)

    # 파일 추가
    def add_files(self):
        fs = filedialog.askopenfilenames(
            initialdir=self.cur_dir,
            title="JSON 파일 선택",
            filetypes=[("JSON files","*.json *.jsonl *.ndjson *.json.gz"),("All files","*.*")]
        )
        if fs:
            for f in fs:
                if f not in self.paths:
                    self.paths.append(f)
            self.update_listbox(select_last=True)

    def update_listbox(self, select_last: bool):
        self.listbox.delete(0, tk.END)
        for p in self.paths:
            self.listbox.insert(tk.END, os.path.basename(p))
        if self.paths:
            idx = len(self.paths)-1 if select_last else 0
            self.listbox.selection_set(idx)
            self.on_select()

    # 파일 선택 핸들러
    def on_select(self, e=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        file_map = {os.path.basename(p): p for p in self.paths}
        name = self.listbox.get(sel[0])
        path = file_map.get(name)
        if not path:
            return
        try:
            doc = load_json_any(path)
        except Exception as ex:
            messagebox.showerror("오류", f"로드 실패: {ex}")
            return

        # 하단 표 갱신
        meta = doc.get("meta", {})
        self.meta_table.load_from_dict(meta if isinstance(meta, dict) else {"meta": meta})
        raw_labels = doc.get("labels", {})
        self.labels_table.load_from_dict(prettify_labels(raw_labels))

        # 분석 레이아웃 갱신
        self.analysis.update_from_doc(doc)

# ------------ 엔트리 포인트 ------------
def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
