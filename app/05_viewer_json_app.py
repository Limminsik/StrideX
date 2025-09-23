import json
import os
import sys
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


def infer_sensor_type(data_node: Dict[str, Any]) -> str:
    keys_text = " ".join(map(str, list(data_node.keys()))).lower()
    if any(k in keys_text for k in ["imu", "accel", "gyro", "mag", "orientation"]):
        return "imu"
    if any(k in keys_text for k in ["insole", "pressure", "grid", "sole", "foot"]):
        return "insole"
    if any(k in keys_text for k in ["pad", "gait", "matrix", "plate"]):
        return "gait_pad"
    return "generic"


def collect_plot_candidates(data_root: Dict[str, Any]) -> List[Tuple[str, Any]]:
    results: List[Tuple[str, Any]] = []

    def walk(node: Any, path: List[str]):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [str(k)])
        elif isinstance(node, list):
            arr = to_ndarray(node)
            if arr is not None and arr.ndim in (1, 2):
                results.append(("/".join(path), node))
        else:
            f = safe_float(node)
            if f is not None:
                results.append(("/".join(path), [f]))

    walk(data_root, ["data"])
    return results


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
        self.data: Optional[Dict[str, Any]] = None
        self.sensor_type: str = "generic"

        ctrl = ttk.Frame(self)
        ctrl.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(ctrl, text="채널/키:").pack(side=tk.LEFT, padx=(0, 4))
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

    def set_data(self, data: Dict[str, Any]):
        self.data = data
        self.sensor_type = infer_sensor_type(data) if isinstance(data, dict) else "generic"
        candidates = collect_plot_candidates(data)
        keys = [k for k, _ in candidates]
        self.combo["values"] = keys
        if keys:
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
        if self.data is None:
            return
        sel = self.combo.get()
        if not sel:
            return

        parts = sel.split("/")
        node: Any = self.data
        try:
            for p in parts[1:]:
                if isinstance(node, dict):
                    node = node[p]
                elif isinstance(node, list):
                    if p.startswith("[") and p.endswith("]"):
                        node = node[int(p[1:-1])]
                    else:
                        raise KeyError(p)
                else:
                    break
        except Exception:
            node = None

        if node is None:
            messagebox.showwarning("경고", "선택한 키를 찾을 수 없습니다.")
            return

        arr = to_ndarray(node)
        title = sel
        if arr is None:
            self._update_stats(None)
            self.ax.text(0.5, 0.5, "시각화할 수 없는 값", ha="center", va="center")
            self.canvas.draw_idle()
            return

        if arr.ndim == 1:
            self._plot_line(arr, title)
            self._update_stats(arr)
            return
        if arr.ndim == 2:
            if infer_sensor_type({}) == "imu":
                pass
            self._plot_heatmap(arr, title)
            self._update_stats(arr)
            return

        self.ax.text(0.5, 0.5, f"{arr.ndim}D 데이터는 미지원", ha="center", va="center")
        self.canvas.draw_idle()
        self._update_stats(None)


class App(tk.Tk):
    def __init__(self, initial_dir: Optional[str] = None):
        super().__init__()
        self.title("JSON Viewer (meta/data/labels)")
        self.geometry("1200x800")

        self.current_dir = initial_dir or os.getcwd()
        self.current_json: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._load_directory(self.current_dir)

    def _build_ui(self):
        root = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(root)
        bar = ttk.Frame(left)
        bar.pack(side=tk.TOP, fill=tk.X)

        self.dir_var = tk.StringVar(value=self.current_dir)
        ttk.Entry(bar, textvariable=self.dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bar, text="열기", command=self.browse_dir).pack(side=tk.RIGHT)

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

    def browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.current_dir)
        if path:
            self._load_directory(path)

    def _load_directory(self, path: str):
        try:
            files = [f for f in os.listdir(path) if f.lower().endswith('.json')]
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 읽을 수 없습니다: {e}")
            return

        self.current_dir = path
        self.dir_var.set(path)
        self.file_list.delete(0, tk.END)
        for f in sorted(files):
            self.file_list.insert(tk.END, f)

        if files:
            self.file_list.selection_clear(0, tk.END)
            self.file_list.selection_set(0)
            self.on_select_file()
        else:
            self._clear_views()

    def _clear_views(self):
        self.current_json = None
        self.meta_tree.load({})
        self.labels_tree.load({})
        self.meta_summary.set("")
        self.data_viewer.set_data({})

    def on_select_file(self, event=None):
        selection = self.file_list.curselection()
        if not selection:
            return
        filename = self.file_list.get(selection[0])
        full_path = os.path.join(self.current_dir, filename)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("오류", f"JSON 로드 실패: {e}")
            return

        self.current_json = data if isinstance(data, dict) else {"root": data}
        meta = self.current_json.get("meta", {})
        data_node = self.current_json.get("data", {})
        labels = self.current_json.get("labels", {})

        self.meta_tree.load(meta)
        self.meta_summary.set(self._summarize_meta(meta))

        self.data_viewer.set_data({"data": data_node})

        self.labels_tree.load(labels)

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


