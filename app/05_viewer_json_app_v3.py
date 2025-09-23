import json
import os
import sys
import gzip
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


JsonType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip()
            if s == "":
                return None
            return float(s)
        return None
    except Exception:
        return None


def is_scalar_like(x: Any) -> bool:
    return isinstance(x, (int, float, str)) or x is None


def to_ndarray(value: Any) -> Optional[np.ndarray]:
    try:
        arr = np.array(value, dtype=float)
        if arr.size == 0:
            return None
        return arr
    except Exception:
        return None


def downsample_1d(arr: np.ndarray, max_points: int = 5000) -> np.ndarray:
    if arr.ndim != 1:
        return arr
    n = arr.shape[0]
    if n <= max_points:
        return arr
    idx = np.linspace(0, n - 1, max_points).astype(int)
    return arr[idx]


def summarize_array(arr: np.ndarray) -> Dict[str, float]:
    arr = np.asarray(arr, dtype=float).ravel()
    if arr.size == 0:
        return {"count": 0}
    return {
        "count": int(arr.size),
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr)),
        "min": float(np.nanmin(arr)),
        "median": float(np.nanmedian(arr)),
        "max": float(np.nanmax(arr)),
    }


def infer_sensor_type_from_path(path: str) -> str:
    p = path.lower()
    if any(k in p for k in ["imu", "accel", "gyro", "mag", "orientation"]):
        return "imu"
    if any(k in p for k in ["insole", "pressure", "grid", "sole", "foot"]):
        return "insole"
    if any(k in p for k in ["pad", "gait", "matrix", "plate"]):
        return "gait_pad"
    return "generic"


def collect_plot_candidates_anywhere(root: Any) -> List[Tuple[str, Any]]:
    results: List[Tuple[str, Any]] = []

    def walk(node: Any, path: List[str], depth: int = 0):
        if depth > 12:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [str(k)], depth + 1)
        elif isinstance(node, list):
            arr = to_ndarray(node)
            if arr is not None and arr.ndim in (1, 2):
                results.append(("/".join(path), node))
            else:
                for idx, v in enumerate(node[:100]):
                    walk(v, path + [f"[{idx}]"], depth + 1)
        else:
            f = safe_float(node)
            if f is not None:
                results.append(("/".join(path), [f]))

    walk(root, ["root"])  # search whole JSON
    seen = set()
    uniq: List[Tuple[str, Any]] = []
    for p, v in results:
        if p not in seen:
            seen.add(p)
            uniq.append((p, v))
    return uniq


def guess_meta_labels_sections(root: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    meta: Dict[str, Any] = {}
    labels: Dict[str, Any] = {}

    def is_shallow_descriptive_dict(d: Dict[str, Any]) -> bool:
        if not isinstance(d, dict):
            return False
        if len(d) == 0:
            return False
        deep_keys = sum(1 for v in d.values() if isinstance(v, (dict, list)))
        scalar_keys = sum(1 for v in d.values() if is_scalar_like(v))
        return scalar_keys >= max(2, deep_keys)

    if isinstance(root, dict):
        if "meta" in root and isinstance(root["meta"], dict):
            meta = root["meta"]
        if "labels" in root and isinstance(root["labels"], (dict, list)):
            labels = root["labels"] if isinstance(root["labels"], dict) else {"labels": root["labels"]}

        if not meta:
            for k, v in root.items():
                if isinstance(v, dict) and is_shallow_descriptive_dict(v):
                    meta = v
                    break

        if not labels:
            for k, v in root.items():
                if isinstance(v, list) and len(v) > 0 and all(is_scalar_like(x) and safe_float(x) is None for x in v[:50]):
                    labels = {k: v}
                    break

    return meta, labels


def read_text_with_fallback(data: bytes) -> str:
    # Try utf-8 then cp949 as a pragmatic fallback
    for enc in ("utf-8", "cp949"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def load_json_file(path: str) -> Tuple[Optional[Any], List[str]]:
    logs: List[str] = []
    try:
        if path.lower().endswith(".gz"):
            with gzip.open(path, "rb") as f:
                raw = f.read()
            text = read_text_with_fallback(raw)
            # guess if jsonl
            if path.lower().endswith((".jsonl.gz", ".ndjson.gz")):
                items = []
                for i, line in enumerate(text.splitlines()):
                    if not line.strip():
                        continue
                    try:
                        items.append(json.loads(line))
                    except Exception as e:
                        logs.append(f"line {i+1} parse error: {e}")
                return items, logs
            else:
                return json.loads(text), logs
        else:
            # Plain text files
            if path.lower().endswith((".jsonl", ".ndjson")):
                items: List[Any] = []
                with open(path, "rb") as fb:
                    for i, line in enumerate(fb):
                        s = line.decode("utf-8", errors="ignore").strip()
                        if not s:
                            continue
                        try:
                            items.append(json.loads(s))
                        except Exception as e:
                            logs.append(f"line {i+1} parse error: {e}")
                return items, logs
            else:
                with open(path, "rb") as f:
                    text = read_text_with_fallback(f.read())
                return json.loads(text), logs
    except Exception as e:
        logs.append(f"load error: {e}")
        return None, logs


class JsonTree(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self["columns"] = ("value",)
        self.heading("#0", text="Key")
        self.heading("value", text="Value")
        self.column("#0", stretch=True)
        self.column("value", stretch=True)

    def load(self, data: JsonType):
        self.delete(*self.get_children())

        def insert_item(parent: str, key: str, value: Any):
            if isinstance(value, dict):
                node_id = self.insert(parent, "end", text=str(key), values=("{...}",))
                for k, v in value.items():
                    insert_item(node_id, k, v)
            elif isinstance(value, list):
                preview = f"[{len(value)} items]"
                node_id = self.insert(parent, "end", text=str(key), values=(preview,))
                for idx, v in enumerate(value[:20]):
                    insert_item(node_id, f"[{idx}]", v)
                if len(value) > 20:
                    self.insert(node_id, "end", text="…", values=(f"(+{len(value)-20})",))
            else:
                self.insert(parent, "end", text=str(key), values=(str(value),))

        insert_item("", "root", data)
        for child in self.get_children(""):
            self.item(child, open=True)


class DataViewer(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.root_json: Optional[Any] = None

        ctrl = ttk.Frame(self)
        ctrl.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(ctrl, text="경로:").pack(side=tk.LEFT, padx=(0, 4))
        self.combo = ttk.Combobox(ctrl, state="readonly")
        self.combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.redraw())

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.stats_text = tk.Text(self, height=5)
        self.stats_text.configure(state=tk.DISABLED)
        self.stats_text.pack(side=tk.BOTTOM, fill=tk.X)

        self.path_to_value: Dict[str, Any] = {}

    def set_root(self, root_json: Any):
        self.root_json = root_json
        candidates = collect_plot_candidates_anywhere(root_json)
        self.path_to_value = {p: v for p, v in candidates}
        paths = list(self.path_to_value.keys())
        self.combo["values"] = paths
        if paths:
            self.combo.current(0)
        self.redraw()

    def _plot_line(self, arr: np.ndarray, title: str):
        self.ax.clear()
        arr = downsample_1d(arr)
        self.ax.plot(np.arange(arr.shape[0]), arr, lw=1)
        self.ax.set_title(title)
        self.ax.set_xlabel("index")
        self.ax.set_ylabel("value")
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()

    def _plot_heatmap(self, arr: np.ndarray, title: str):
        self.ax.clear()
        self.ax.imshow(arr, aspect="auto", origin="lower", cmap="viridis")
        self.ax.set_title(title)
        self.ax.set_xlabel("col")
        self.ax.set_ylabel("row")
        self.canvas.draw_idle()

    def _update_stats(self, arr: Optional[np.ndarray]):
        self.stats_text.configure(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        if arr is None:
            self.stats_text.insert(tk.END, "표시할 수 없는 값 또는 지원되지 않는 차원입니다.\n")
        else:
            s = summarize_array(arr)
            self.stats_text.insert(
                tk.END,
                "\n".join([f"{k}: {v}" for k, v in s.items()]) + "\n",
            )
        self.stats_text.configure(state=tk.DISABLED)

    def redraw(self):
        self.ax.clear()
        self.canvas.draw_idle()
        self._update_stats(None)

        sel = self.combo.get()
        if not sel:
            return
        node = self.path_to_value.get(sel)
        if node is None:
            return

        arr = to_ndarray(node)
        if arr is None:
            self._update_stats(None)
            self.ax.text(0.5, 0.5, "시각화할 수 없는 값", ha="center", va="center")
            self.canvas.draw_idle()
            return

        sensor = infer_sensor_type_from_path(sel)
        if arr.ndim == 1:
            self._plot_line(arr, sel)
            self._update_stats(arr)
            return
        if arr.ndim == 2:
            if sensor == "imu":
                r, c = arr.shape
                if r <= 8 and c > r:
                    self.ax.clear()
                    x = np.arange(c)
                    for i in range(r):
                        self.ax.plot(x, downsample_1d(arr[i, :]), lw=1, label=f"ch{i}")
                    self.ax.set_title(sel + " (multi-channel)")
                    self.ax.legend(loc="upper right", fontsize=8, ncols=2)
                    self.ax.grid(True, alpha=0.3)
                    self.canvas.draw_idle()
                    self._update_stats(arr)
                    return
            self._plot_heatmap(arr, sel)
            self._update_stats(arr)
            return

        self.ax.text(0.5, 0.5, f"{arr.ndim}D 데이터는 미지원", ha="center", va="center")
        self.canvas.draw_idle()
        self._update_stats(None)


class App(tk.Tk):
    def __init__(self, initial_dir: Optional[str] = None):
        super().__init__()
        self.title("JSON Viewer v3 (folder+files, jsonl/gz, logs)")
        self.geometry("1400x900")

        self.current_dir = initial_dir or os.getcwd()
        self.recursive_var = tk.BooleanVar(value=True)

        # file registry: path -> (json, logs)
        self.registry: Dict[str, Tuple[Optional[Any], List[str]]] = {}
        self.current_path: Optional[str] = None

        self._build_ui()
        self._load_directory(self.current_dir)

    def _build_ui(self):
        root = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(root)
        bar = ttk.Frame(left)
        bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(bar, text="폴더 열기", command=self.browse_dir).pack(side=tk.LEFT)
        ttk.Checkbutton(bar, text="재귀", variable=self.recursive_var, command=self.refresh_dir).pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text="파일 추가", command=self.add_files).pack(side=tk.LEFT)

        self.dir_var = tk.StringVar(value=self.current_dir)
        ttk.Entry(bar, textvariable=self.dir_var).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.file_list = tk.Listbox(left)
        self.file_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.file_list.bind("<<ListboxSelect>>", self.on_select_file)

        root.add(left, weight=1)

        right = ttk.Notebook(root)
        root.add(right, weight=3)

        meta_tab = ttk.Frame(right)
        self.meta_tree = JsonTree(meta_tab)
        self.meta_tree.pack(fill=tk.BOTH, expand=True)
        self.meta_summary = tk.StringVar(value="")
        ttk.Label(meta_tab, textvariable=self.meta_summary).pack(side=tk.BOTTOM, fill=tk.X)
        right.add(meta_tab, text="Meta")

        data_tab = ttk.Frame(right)
        self.data_viewer = DataViewer(data_tab)
        self.data_viewer.pack(fill=tk.BOTH, expand=True)
        right.add(data_tab, text="Data")

        labels_tab = ttk.Frame(right)
        self.labels_tree = JsonTree(labels_tab)
        self.labels_tree.pack(fill=tk.BOTH, expand=True)
        right.add(labels_tab, text="Labels")

        logs_tab = ttk.Frame(right)
        self.logs_text = tk.Text(logs_tab)
        self.logs_text.pack(fill=tk.BOTH, expand=True)
        right.add(logs_tab, text="Logs")

    def refresh_dir(self):
        self._load_directory(self.current_dir)

    def browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.current_dir)
        if path:
            self._load_directory(path)

    def add_files(self):
        paths = filedialog.askopenfilenames(title="JSON 파일 선택", filetypes=[
            ("JSON and variants", "*.json *.jsonl *.ndjson *.json.gz *.jsonl.gz *.ndjson.gz"),
            ("All files", "*.*"),
        ])
        if not paths:
            return
        for p in paths:
            self._register_file(p)
        self._refresh_file_list()

    def _register_file(self, path: str):
        data, logs = load_json_file(path)
        # auto-wrap non-dict roots
        if data is not None and not isinstance(data, dict):
            data = {"root": data}
            logs.append("wrapped non-dict root into {'root': ...}")
        self.registry[path] = (data, logs)

    def _scan_dir(self, path: str, recursive: bool) -> List[str]:
        exts = (".json", ".jsonl", ".ndjson", ".json.gz", ".jsonl.gz", ".ndjson.gz")
        found: List[str] = []
        if recursive:
            for dirpath, _, filenames in os.walk(path):
                for name in filenames:
                    if name.lower().endswith(exts):
                        found.append(os.path.join(dirpath, name))
        else:
            try:
                for name in os.listdir(path):
                    if name.lower().endswith(exts):
                        found.append(os.path.join(path, name))
            except Exception:
                pass
        return sorted(found)

    def _load_directory(self, path: str):
        self.current_dir = path
        self.dir_var.set(path)
        files = self._scan_dir(path, self.recursive_var.get())
        for f in files:
            if f not in self.registry:
                self._register_file(f)
        self._refresh_file_list()
        if files:
            self.file_list.selection_clear(0, tk.END)
            self.file_list.selection_set(0)
            self.on_select_file()
        else:
            self._clear_views()

    def _refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for p in sorted(self.registry.keys()):
            status = "OK" if self.registry[p][0] is not None else "ERR"
            self.file_list.insert(tk.END, f"[{status}] {p}")

    def _clear_views(self):
        self.current_path = None
        self.meta_tree.load({})
        self.labels_tree.load({})
        self.meta_summary.set("")
        self.data_viewer.set_root({})
        self.logs_text.delete("1.0", tk.END)

    def on_select_file(self, event=None):
        selection = self.file_list.curselection()
        if not selection:
            return
        display = self.file_list.get(selection[0])
        # extract actual path after status prefix
        path = display.split("] ", 1)[-1]
        self.current_path = path
        data, logs = self.registry.get(path, (None, ["not loaded"]))

        if data is None:
            self._clear_views()
            self.logs_text.insert(tk.END, "\n".join(logs))
            return

        meta, labels = guess_meta_labels_sections(data)

        self.meta_tree.load(meta if meta else data)
        self.meta_summary.set(self._summarize_meta(meta))

        self.data_viewer.set_root(data)

        self.labels_tree.load(labels if labels else {})

        self.logs_text.delete("1.0", tk.END)
        if logs:
            self.logs_text.insert(tk.END, "\n".join(logs))

    def _summarize_meta(self, meta: Dict[str, Any]) -> str:
        patient = meta.get("patient") if isinstance(meta, dict) else None
        if isinstance(patient, dict):
            pid = patient.get("id", "?")
            age = patient.get("age", "?")
            gender = patient.get("gender", "?")
            condition = patient.get("condition", "?")
            return f"ID: {pid} | age: {age} | gender: {gender} | condition: {condition}"
        return ""


def main():
    initial_dir = None
    if len(sys.argv) >= 2:
        candidate = sys.argv[1]
        if os.path.isdir(candidate):
            initial_dir = candidate
        else:
            messagebox.showwarning("알림", f"폴더가 아닙니다: {candidate}. 현재 작업 디렉토리를 사용합니다.")
    app = App(initial_dir)
    app.mainloop()


if __name__ == "__main__":
    main()


