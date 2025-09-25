#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05 Viewer — Sensor Dashboard (v6)
개선 사항:
- 좌측: "데이터 추가" 버튼만 표시 (재귀 스캔/폴더 열기 제거, 파일명만 표시)
- 하단 Meta/Labels: 키를 마지막 segment만 표시 (예: patient.id → id)
- 상단 시각화: legend에서 센서명 괄호 제거, tight_layout 적용으로 자동 크기 조정
"""

import json, os, gzip, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Dict, List, Tuple, Union, Optional

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

APP_TITLE = "05 Viewer — Sensor Dashboard (v6)"
WIN_W, WIN_H = 1400, 900

# ---------- helpers ----------
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

def to_float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        if isinstance(x, str):
            s = x.strip()
            if s == "": return None
            return float(s)
    except Exception:
        return None
    return None

def flatten_kv(d: Dict[str, Any], parent: str = "") -> List[Tuple[str, str]]:
    """dict -> [(last_key, value_str)]"""
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

def get_path(d: Dict[str, Any], path: List[str]) -> Any:
    cur: Any = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

def is_imu(doc: Dict[str, Any]) -> bool:
    return isinstance(get_path(doc, ["data","imu_sensor","values"]), dict)

def is_pad(doc: Dict[str, Any]) -> bool:
    return isinstance(get_path(doc, ["data","gait_pad","values"]), dict)

def is_insole(doc: Dict[str, Any]) -> bool:
    values = get_path(doc, ["data","smart_insole","values"])
    if not isinstance(values, dict): return False
    return any(re.match(r"day_\d+", k) for k in values.keys())

# ---------- plotting ----------
class PlotPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.fig = Figure(figsize=(10,5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.info = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.info).pack(anchor="w")

    def _bars_lr(self, data: Dict[str, Dict[str, Any]], title_prefix: str):
        metrics = list(data.keys())
        n = len(metrics)
        cols = 3
        rows = int(np.ceil(n / cols)) if n else 1
        self.fig.clf()
        for i, m in enumerate(metrics, 1):
            ax = self.fig.add_subplot(rows, cols, i)
            val = data[m]
            if isinstance(val, dict) and any(k in val for k in ("L","R")):
                L = to_float(val.get("L"))
                R = to_float(val.get("R"))
                xs = np.arange(2)
                ys = [L if L is not None else np.nan, R if R is not None else np.nan]
                ax.bar(xs, ys)
                ax.set_xticks(xs); ax.set_xticklabels(["L","R"])
            else:
                f = to_float(val)
                ax.bar([0], [f if f is not None else np.nan])
                ax.set_xticks([0]); ax.set_xticklabels(["value"])
            ax.set_title(m)
            ax.grid(True, axis="y", alpha=0.25)
        self.fig.suptitle(title_prefix.replace("(smart insole)", "").strip())
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _lines_days(self, days: Dict[str, Dict[str, Any]], title_prefix: str):
        def day_num(k: str) -> int:
            m = re.match(r"day_(\d+)", k)
            return int(m.group(1)) if m else 0
        day_keys = sorted(days.keys(), key=day_num)
        metrics: List[str] = []
        for d in day_keys:
            for m in days[d].keys():
                if m not in metrics:
                    metrics.append(m)
        metrics = metrics[:8] if len(metrics) > 8 else metrics
        cols = 2
        rows = int(np.ceil(len(metrics) / cols)) if metrics else 1
        self.fig.clf()
        for i, m in enumerate(metrics, 1):
            ax = self.fig.add_subplot(rows, cols, i)
            xs = list(range(1, len(day_keys)+1))
            sample = days[day_keys[0]].get(m)
            if isinstance(sample, dict) and any(k in sample for k in ("L","R")):
                ysL, ysR = [], []
                for d in day_keys:
                    v = days[d].get(m, {})
                    ysL.append(to_float(v.get("L")) if isinstance(v, dict) else np.nan)
                    ysR.append(to_float(v.get("R")) if isinstance(v, dict) else np.nan)
                ax.plot(xs, ysL, marker="o", label="L")
                ax.plot(xs, ysR, marker="o", label="R")
                ax.legend(fontsize=8)
            else:
                ys = [to_float(days[d].get(m)) for d in day_keys]
                ax.plot(xs, ys, marker="o")
            ax.set_title(m)
            ax.set_xticks(xs); ax.set_xticklabels([str(day_num(k)) for k in day_keys])
            ax.grid(True, alpha=0.25)
        self.fig.suptitle(title_prefix.replace("(smart insole)", "").strip())
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def render(self, doc: Dict[str, Any]):
        self.info.set("")
        try:
            if is_pad(doc):
                values = doc["data"]["gait_pad"]["values"]
                self._bars_lr(values, "Gait Pad")
                self.info.set("Pad: L/R 비교 지표를 막대그래프로 표시")
                return
            if is_imu(doc):
                values = doc["data"]["imu_sensor"]["values"]
                self._bars_lr(values, "IMU")
                self.info.set("IMU: L/R 비교 지표를 막대그래프로 표시")
                return
            if is_insole(doc):
                days = doc["data"]["smart_insole"]["values"]
                self._lines_days(days, "Smart Insole")
                self.info.set("Insole: day별 시계열을 선 그래프로 표시")
                return
            self.fig.clf()
            ax = self.fig.add_subplot(111)
            ax.text(0.5,0.5,"시각화할 수 있는 data 없음", ha="center", va="center")
            self.canvas.draw_idle()
        except Exception as e:
            self.fig.clf()
            ax = self.fig.add_subplot(111)
            ax.text(0.5,0.5,f"Render error: {e}", ha="center", va="center")
            self.canvas.draw_idle()

# ---------- key-value tables ----------
class KVTable(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self["columns"] = ("value",)
        self.heading("#0", text="Key")
        self.heading("value", text="Value")
        self.column("#0", width=200, stretch=True)
        self.column("value", width=400, stretch=True)

    def load_from_dict(self, d: Dict[str, Any]):
        self.delete(*self.get_children())
        for k, v in flatten_kv(d):
            self.insert("", "end", text=k, values=(v,))

# ---------- app ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry(f"{WIN_W}x{WIN_H}")

        self.paths: List[str] = []
        self.cur_dir = os.getcwd()

        # 상단 컨트롤: "데이터 추가"만
        top = ttk.Frame(self); top.pack(side=tk.TOP, fill=tk.X, pady=(4,4))
        ttk.Button(top, text="데이터 추가", command=self.add_files).pack(side=tk.LEFT, padx=(0,4))

        # 본문 split
        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL); body.pack(fill=tk.BOTH, expand=True)

        # 좌측 파일 리스트
        left = ttk.Frame(body); body.add(left, weight=1)
        self.listbox = tk.Listbox(left)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 우측: 상단 plot, 하단 meta/labels
        right = ttk.PanedWindow(body, orient=tk.VERTICAL); body.add(right, weight=3)
        self.plot = PlotPane(right); right.add(self.plot, weight=3)
        bottom = ttk.PanedWindow(right, orient=tk.HORIZONTAL); right.add(bottom, weight=2)
        meta_frame = ttk.Frame(bottom); labels_frame = ttk.Frame(bottom)
        bottom.add(meta_frame, weight=1); bottom.add(labels_frame, weight=1)
        ttk.Label(meta_frame, text="Meta").pack(anchor="w")
        self.meta_table = KVTable(meta_frame); self.meta_table.pack(fill=tk.BOTH, expand=True)
        ttk.Label(labels_frame, text="Labels").pack(anchor="w")
        self.labels_table = KVTable(labels_frame); self.labels_table.pack(fill=tk.BOTH, expand=True)

    def add_files(self):
        fs = filedialog.askopenfilenames(
            initialdir=self.cur_dir,
            title="JSON 파일 선택",
            filetypes=[("JSON files","*.json *.jsonl *.ndjson *.json.gz"),("All files","*.*")]
        )
        if fs:
            for f in fs:
                if f not in self.paths: self.paths.append(f)
            self.update_listbox(select_last=True)

    def update_listbox(self, select_last: bool):
        self.listbox.delete(0, tk.END)
        for p in self.paths:
            self.listbox.insert(tk.END, os.path.basename(p))
        if self.paths:
            idx = len(self.paths)-1 if select_last else 0
            self.listbox.selection_set(idx); self.on_select()

    def on_select(self, e=None):
        sel = self.listbox.curselection()
        if not sel: return
        file_map = {os.path.basename(p): p for p in self.paths}
        name = self.listbox.get(sel[0])
        path = file_map.get(name)
        if not path: return
        try:
            doc = load_json_any(path)
        except Exception as ex:
            messagebox.showerror("오류", f"로드 실패: {ex}")
            return
        meta = doc.get("meta", {})
        labels = doc.get("labels", {})
        self.meta_table.load_from_dict(meta if isinstance(meta, dict) else {"meta": meta})
        self.labels_table.load_from_dict(labels if isinstance(labels, dict) else {"labels": labels})
        self.plot.render(doc)

def main():
    app = App(); app.mainloop()

if __name__ == "__main__":
    main()
