"""
gui/controller_gui.py
=====================
ControllerGUI: Tkinter dashboard for the Centralized Routing System controller.

Panels:
  • Topology tab  – interactive draggable graph
  • Routers tab   – table with status controls (up/down/delete)
  • Tables tab    – all routing tables in a tree view
  • Path tab      – best path finder with visual highlight
  • Log tab       – live event log

The GUI runs in the main thread; TCP server and DB calls happen in threads.
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Allow imports from ControllerApp root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gui.topology_canvas import TopologyCanvas
from dao.router_dao        import RouterDAO
from dao.topology_dao      import TopologyDAO
from dao.routing_table_dao import RoutingTableDAO
from service.routing_service import RoutingService

# ─── Colour palette ─────────────────────────────────────────────────────────
BG      = "#0f172a"
BG2     = "#1e293b"
BG3     = "#334155"
ACCENT  = "#3b82f6"
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARN    = "#f59e0b"
TEXT    = "#e2e8f0"
MUTED   = "#64748b"
DISCON  = "#a855f7"   # purple for disconnected
FONT    = ("Segoe UI", 10)
FONT_B  = ("Segoe UI", 10, "bold")
FONT_M  = ("Consolas", 10)


def _style_ttk():
    """Configure ttk styles for the dark theme."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(".",
        background=BG2, foreground=TEXT,
        font=FONT, fieldbackground=BG3, borderwidth=0)

    style.configure("TNotebook",       background=BG,  tabmargins=[0,0,0,0])
    style.configure("TNotebook.Tab",   background=BG3, foreground=MUTED,
                    padding=[14,6], font=FONT_B)
    style.map("TNotebook.Tab",
        background=[("selected", BG2)],
        foreground=[("selected", TEXT)])

    style.configure("Treeview",        background=BG2, foreground=TEXT,
                    fieldbackground=BG2, rowheight=26, font=FONT_M)
    style.configure("Treeview.Heading",background=BG3, foreground=TEXT,
                    font=FONT_B, relief="flat")
    style.map("Treeview", background=[("selected", ACCENT)])

    style.configure("TScrollbar",      background=BG3, troughcolor=BG2,
                    arrowcolor=TEXT)

    style.configure("Card.TFrame",     background=BG2,
                    relief="flat", borderwidth=1)

    for name, fg in [("Success.TButton", SUCCESS),
                     ("Danger.TButton",  DANGER),
                     ("Warn.TButton",    WARN),
                     ("Accent.TButton",  ACCENT)]:
        style.configure(name, background=BG3, foreground=fg,
                        font=FONT_B, relief="flat", padding=[10,5])
        style.map(name, background=[("active", BG)])


class ControllerGUI:
    """Main controller dashboard window."""

    def __init__(self, router_dao: RouterDAO, topology_dao: TopologyDAO,
                 routing_table_dao: RoutingTableDAO,
                 routing_service: RoutingService,
                 host: str, port: int):
        self.router_dao        = router_dao
        self.topology_dao      = topology_dao
        self.routing_table_dao = routing_table_dao
        self.routing_service   = routing_service
        self.host = host
        self.port = port

        self.root = tk.Tk()
        self.root.title("Centralized Routing System — Controller Dashboard")
        self.root.geometry("1100x720")
        self.root.configure(bg=BG)
        self.root.minsize(900, 600)

        _style_ttk()
        self._build_ui()
        self._schedule_refresh()

    # ════════════════════════════════════════════════════════════════ UI build
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG2, height=52)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⬡  Centralized Routing System",
                 bg=BG2, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(
                 side="left", padx=16, pady=10)

        self._lbl_status = tk.Label(
            hdr, text=f"Controller: {self.host}:{self.port}",
            bg=BG2, fg=SUCCESS, font=FONT_B)
        self._lbl_status.pack(side="right", padx=16)

        self._lbl_routers = tk.Label(hdr, text="Routers: 0",
            bg=BG2, fg=MUTED, font=FONT)
        self._lbl_routers.pack(side="right", padx=8)

        # ── Notebook ─────────────────────────────────────────────────────────
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(6,10))

        self._tab_topo   = ttk.Frame(nb);  nb.add(self._tab_topo,   text=" 🗺  Topología ")
        self._tab_routers= ttk.Frame(nb);  nb.add(self._tab_routers, text=" 🖥  Routers ")
        self._tab_tables = ttk.Frame(nb);  nb.add(self._tab_tables,  text=" 📋  Tablas de ruta ")
        self._tab_path   = ttk.Frame(nb);  nb.add(self._tab_path,    text=" 🔍  Mejor ruta ")
        self._tab_log    = ttk.Frame(nb);  nb.add(self._tab_log,     text=" 📜  Log ")

        self._build_topology_tab()
        self._build_routers_tab()
        self._build_tables_tab()
        self._build_path_tab()
        self._build_log_tab()

    # ════════════════════════════════════════════════════════════════ TOPOLOGY
    def _build_topology_tab(self):
        f = self._tab_topo

        # Toolbar
        bar = tk.Frame(f, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6,0))

        tk.Label(bar, text="Topología de red — arrastra los nodos",
                 bg=BG2, fg=MUTED, font=FONT).pack(side="left", padx=8)

        tk.Button(bar, text="⟳  Actualizar", font=FONT_B,
                  bg=BG3, fg=ACCENT, relief="flat",
                  command=self._refresh_topology
                  ).pack(side="right", padx=6)

        # Link cost update inline
        cost_frame = tk.Frame(bar, bg=BG2)
        cost_frame.pack(side="right", padx=10)
        tk.Label(cost_frame, text="Actualizar costo:", bg=BG2, fg=MUTED,
                 font=FONT).pack(side="left")

        self._upd_r1  = tk.Entry(cost_frame, width=4, bg=BG3, fg=TEXT,
                                  insertbackground=TEXT, font=FONT_M,
                                  relief="flat")
        self._upd_r1.pack(side="left", padx=(4,1))
        self._upd_r1.insert(0, "R1")

        tk.Label(cost_frame, text="↔", bg=BG2, fg=TEXT).pack(side="left")

        self._upd_r2  = tk.Entry(cost_frame, width=4, bg=BG3, fg=TEXT,
                                  insertbackground=TEXT, font=FONT_M,
                                  relief="flat")
        self._upd_r2.pack(side="left", padx=(1,4))
        self._upd_r2.insert(0, "R2")

        tk.Label(cost_frame, text="=", bg=BG2, fg=TEXT).pack(side="left")

        self._upd_cost = tk.Entry(cost_frame, width=5, bg=BG3, fg=TEXT,
                                   insertbackground=TEXT, font=FONT_M,
                                   relief="flat")
        self._upd_cost.pack(side="left", padx=(4,6))
        self._upd_cost.insert(0, "1")

        tk.Button(cost_frame, text="Aplicar", font=FONT_B,
                  bg=ACCENT, fg="white", relief="flat",
                  command=self._apply_cost_update
                  ).pack(side="left")

        # Canvas
        self._topo_canvas = TopologyCanvas(f)
        self._topo_canvas.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_topology(self):
        def _do():
            try:
                topo    = self.topology_dao.get_topology()
                routers = self.router_dao.get_all_routers()
                statuses = {r.router_id: r.status for r in routers}
                self.root.after(0, lambda: self._topo_canvas.update_topology(
                    topo, statuses))
                self._log(f"Topology refreshed — {len(topo)} nodes")
            except Exception as e:
                self._log(f"[ERROR] Topology refresh: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _apply_cost_update(self):
        r1   = self._upd_r1.get().strip().upper()
        r2   = self._upd_r2.get().strip().upper()
        cost_str = self._upd_cost.get().strip()
        try:
            cost = float(cost_str)
            if cost < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El costo debe ser un número >= 0")
            return

        def _do():
            try:
                self.topology_dao.update_link_cost(r1, r2, cost)
                tables = self.routing_service.generate_all_routing_tables()
                for rid, tbl in tables.items():
                    self.routing_table_dao.save_routing_table(rid, tbl)
                self.root.after(0, self._refresh_topology)
                self.root.after(0, self._refresh_tables)
                self._log(f"Link {r1}↔{r2} cost={cost} — routes recalculated")
            except Exception as e:
                self._log(f"[ERROR] update link: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    # ══════════════════════════════════════════════════════════════== ROUTERS
    def _build_routers_tab(self):
        f = self._tab_routers

        # Toolbar
        bar = tk.Frame(f, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6,0))

        for text, style, cmd in [
            ("⬆  Activar",   "Success.TButton", self._router_up),
            ("⬇  Desactivar","Danger.TButton",  self._router_down),
            ("🗑  Eliminar",  "Warn.TButton",    self._router_delete),
            ("➕  Agregar",   "Accent.TButton",  self._router_add),
            ("⟳  Actualizar","Accent.TButton",   self._refresh_routers),
        ]:
            ttk.Button(bar, text=text, style=style, command=cmd
                       ).pack(side="left", padx=4)

        # Treeview
        cols = ("ID", "IP", "Puerto", "Estado", "Rutas")
        self._tree_routers = ttk.Treeview(f, columns=cols,
                                           show="headings", selectmode="browse")
        widths = [80, 140, 70, 100, 60]
        for c, w in zip(cols, widths):
            self._tree_routers.heading(c, text=c)
            self._tree_routers.column(c, width=w, anchor="center")

        self._tree_routers.tag_configure("active",   foreground=SUCCESS)
        self._tree_routers.tag_configure("inactive", foreground=DANGER)
        self._tree_routers.tag_configure("disconnected", foreground="#a855f7")

        sb = ttk.Scrollbar(f, command=self._tree_routers.yview)
        self._tree_routers.configure(yscrollcommand=sb.set)

        self._tree_routers.pack(fill="both", expand=True, padx=8, pady=8,
                                 side="left")
        sb.pack(fill="y", padx=(0,8), pady=8, side="right")

    def _refresh_routers(self):
        def _do():
            try:
                routers = self.router_dao.get_all_routers()
                tables  = self.routing_table_dao.get_all_routing_tables()
                rows = []
                for r in routers:
                    n_routes = len(tables.get(r.router_id, []))
                    s = r.status.upper()
                    if s in ("ACTIVE","ACTIVO"):
                        tag = "active"
                    elif s == "DISCONNECTED":
                        tag = "disconnected"
                    else:
                        tag = "inactive"
                    rows.append((r.router_id, r.ip, r.port, r.status, n_routes, tag))

                def _update():
                    self._tree_routers.delete(*self._tree_routers.get_children())
                    for row in rows:
                        self._tree_routers.insert("", "end",
                            values=row[:5], tags=(row[5],))
                    self._lbl_routers.config(
                        text=f"Routers: {len(routers)}")
                self.root.after(0, _update)
            except Exception as e:
                self._log(f"[ERROR] Refresh routers: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _selected_router(self):
        sel = self._tree_routers.selection()
        if not sel:
            messagebox.showwarning("Selección", "Selecciona un router primero.")
            return None
        return self._tree_routers.item(sel[0])["values"][0]

    def _router_up(self):
        rid = self._selected_router()
        if not rid:
            return
        def _do():
            try:
                self.router_dao.set_status(rid, "ACTIVE")
                tables = self.routing_service.generate_all_routing_tables()
                for r, t in tables.items():
                    self.routing_table_dao.save_routing_table(r, t)
                self.root.after(0, self._refresh_routers)
                self.root.after(0, self._refresh_topology)
                self.root.after(0, self._refresh_tables)
                self._log(f"Router {rid} → ACTIVE  (routes recalculated)")
            except Exception as e:
                self._log(f"[ERROR] up {rid}: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _router_down(self):
        rid = self._selected_router()
        if not rid:
            return
        if not messagebox.askyesno("Confirmar",
                f"¿Marcar {rid} como INACTIVE?\nLas rutas se recalcularán."):
            return
        def _do():
            try:
                self.router_dao.set_status(rid, "INACTIVE")
                tables = self.routing_service.generate_all_routing_tables()
                for r, t in tables.items():
                    self.routing_table_dao.save_routing_table(r, t)
                self.root.after(0, self._refresh_routers)
                self.root.after(0, self._refresh_topology)
                self.root.after(0, self._refresh_tables)
                self._log(f"Router {rid} → INACTIVE  (routes recalculated)")
            except Exception as e:
                self._log(f"[ERROR] down {rid}: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _router_delete(self):
        rid = self._selected_router()
        if not rid:
            return
        if not messagebox.askyesno("Confirmar",
                f"¿Eliminar {rid} definitivamente?\nEsta acción no se puede deshacer."):
            return
        def _do():
            try:
                self.router_dao.delete_router(rid)
                tables = self.routing_service.generate_all_routing_tables()
                for r, t in tables.items():
                    self.routing_table_dao.save_routing_table(r, t)
                self.root.after(0, self._refresh_routers)
                self.root.after(0, self._refresh_topology)
                self.root.after(0, self._refresh_tables)
                self._log(f"Router {rid} DELETED")
            except Exception as e:
                self._log(f"[ERROR] delete {rid}: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()


    def _router_add(self):
        """Dialog to add a new router to the network."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar nuevo router")
        dialog.geometry("480x420")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Agregar nuevo router",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")
                 ).pack(pady=(16,4))
        tk.Label(dialog, text="Los campos de vecinos son opcionales.",
                 bg=BG, fg=MUTED, font=FONT).pack(pady=(0,12))

        fields_frame = tk.Frame(dialog, bg=BG)
        fields_frame.pack(fill="x", padx=24)

        def lbl(text, row):
            tk.Label(fields_frame, text=text, bg=BG, fg=TEXT,
                     font=FONT_B, anchor="e", width=14
                     ).grid(row=row, column=0, sticky="e", pady=5, padx=(0,8))

        entries = {}
        for i, (key, placeholder) in enumerate([
            ("id",    "R5"),
            ("ip",    "127.0.0.1"),
            ("port",  "5005"),
            ("nb1",   "R1:3  (vecino:costo, dejar vacío si no aplica)"),
            ("nb2",   "R2:7"),
            ("nb3",   "R3:2"),
        ]):
            labels = ["Router ID", "IP", "Puerto",
                      "Vecino 1", "Vecino 2", "Vecino 3"]
            lbl(labels[i], i)
            e = tk.Entry(fields_frame, width=30, bg=BG3, fg=TEXT,
                         insertbackground=TEXT, font=FONT_M, relief="flat")
            e.insert(0, placeholder if i < 3 else "")
            e.grid(row=i, column=1, sticky="w", pady=5)
            entries[key] = e

        msg_var = tk.StringVar()
        tk.Label(dialog, textvariable=msg_var, bg=BG, fg=DANGER,
                 font=FONT, wraplength=420).pack(pady=4)

        def on_add():
            rid  = entries["id"].get().strip().upper()
            ip   = entries["ip"].get().strip()
            port_str = entries["port"].get().strip()
            if not rid or not ip or not port_str:
                msg_var.set("ID, IP y Puerto son obligatorios.")
                return
            try:
                port = int(port_str)
            except ValueError:
                msg_var.set("Puerto debe ser un número entero.")
                return

            neighbors = []
            for key in ("nb1", "nb2", "nb3"):
                val = entries[key].get().strip()
                if not val:
                    continue
                if ":" not in val:
                    msg_var.set(f"Formato de vecino inválido: '{val}'. Use ID:COSTO")
                    return
                nb_id, cost_s = val.split(":", 1)
                try:
                    cost = float(cost_s)
                except ValueError:
                    msg_var.set(f"Costo inválido para {nb_id}: '{cost_s}'")
                    return
                neighbors.append({"neighbor_id": nb_id.upper(), "cost": cost})

            def _do():
                try:
                    from model.router import Router
                    router = Router(router_id=rid, ip=ip, port=port,
                                    status="ACTIVE")
                    self.router_dao.save_router(router)
                    if neighbors:
                        self.topology_dao.save_topology(rid, neighbors)
                    tables = self.routing_service.generate_all_routing_tables()
                    for r, t in tables.items():
                        self.routing_table_dao.save_routing_table(r, t)
                    self.root.after(0, self._refresh_routers)
                    self.root.after(0, self._refresh_topology)
                    self.root.after(0, self._refresh_tables)
                    self._log(
                        f"Router '{rid}' agregado ({ip}:{port}) "
                        f"con {len(neighbors)} vecino(s). Rutas recalculadas."
                    )
                    self.root.after(0, dialog.destroy)
                except Exception as e:
                    self.root.after(0, lambda: msg_var.set(str(e)))
            threading.Thread(target=_do, daemon=True).start()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.pack(pady=14)
        tk.Button(btn_frame, text="  Agregar  ", font=FONT_B,
                  bg=SUCCESS, fg="white", relief="flat",
                  command=on_add).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancelar", font=FONT,
                  bg=BG3, fg=MUTED, relief="flat",
                  command=dialog.destroy).pack(side="left", padx=8)


    # ══════════════════════════════════════════════════════════════ TABLES
    def _build_tables_tab(self):
        f = self._tab_tables

        bar = tk.Frame(f, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6,0))
        tk.Label(bar, text="Tablas de enrutamiento calculadas por Dijkstra",
                 bg=BG2, fg=MUTED, font=FONT).pack(side="left", padx=8)
        ttk.Button(bar, text="⟳  Recalcular", style="Accent.TButton",
                   command=self._recalculate_and_refresh
                   ).pack(side="right", padx=6)

        # Treeview with 2-level hierarchy: router → entries
        cols = ("Destino", "Next Hop", "Costo")
        self._tree_tables = ttk.Treeview(f, columns=cols,
                                          show="tree headings",
                                          selectmode="browse")
        self._tree_tables.heading("#0", text="Router")
        self._tree_tables.column("#0", width=100)
        for c in cols:
            self._tree_tables.heading(c, text=c)
            self._tree_tables.column(c, width=110, anchor="center")

        sb = ttk.Scrollbar(f, command=self._tree_tables.yview)
        self._tree_tables.configure(yscrollcommand=sb.set)
        self._tree_tables.pack(fill="both", expand=True, padx=8, pady=8,
                                side="left")
        sb.pack(fill="y", padx=(0,8), pady=8, side="right")

    def _refresh_tables(self):
        def _do():
            try:
                tables = self.routing_table_dao.get_all_routing_tables()
                def _update():
                    self._tree_tables.delete(*self._tree_tables.get_children())
                    for rid in sorted(tables):
                        parent = self._tree_tables.insert(
                            "", "end", text=f"  {rid}", open=True)
                        for e in tables[rid]:
                            self._tree_tables.insert(
                                parent, "end",
                                values=(e["destination"],
                                        e["next_hop"],
                                        e["cost"]))
                self.root.after(0, _update)
            except Exception as e:
                self._log(f"[ERROR] Refresh tables: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _recalculate_and_refresh(self):
        def _do():
            try:
                tables = self.routing_service.generate_all_routing_tables()
                for rid, tbl in tables.items():
                    self.routing_table_dao.save_routing_table(rid, tbl)
                self.root.after(0, self._refresh_tables)
                self._log("Routes recalculated manually")
            except Exception as e:
                self._log(f"[ERROR] Recalculate: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════ PATH
    def _build_path_tab(self):
        f = self._tab_path

        # Input panel
        inp = tk.Frame(f, bg=BG2, pady=14)
        inp.pack(fill="x", padx=16, pady=(14,0))

        tk.Label(inp, text="Origen:", bg=BG2, fg=TEXT, font=FONT_B
                 ).grid(row=0, column=0, sticky="e", padx=(0,6))
        self._path_src = tk.Entry(inp, width=8, bg=BG3, fg=TEXT,
                                   insertbackground=TEXT, font=FONT_M,
                                   relief="flat")
        self._path_src.grid(row=0, column=1, padx=(0,14))
        self._path_src.insert(0, "R1")

        tk.Label(inp, text="Destino:", bg=BG2, fg=TEXT, font=FONT_B
                 ).grid(row=0, column=2, sticky="e", padx=(0,6))
        self._path_dst = tk.Entry(inp, width=8, bg=BG3, fg=TEXT,
                                   insertbackground=TEXT, font=FONT_M,
                                   relief="flat")
        self._path_dst.grid(row=0, column=3, padx=(0,14))
        self._path_dst.insert(0, "R4")

        tk.Button(inp, text="  Calcular ruta  ", font=FONT_B,
                  bg=ACCENT, fg="white", relief="flat",
                  command=self._find_path
                  ).grid(row=0, column=4, padx=6)

        tk.Button(inp, text="Limpiar", font=FONT,
                  bg=BG3, fg=MUTED, relief="flat",
                  command=self._clear_path
                  ).grid(row=0, column=5, padx=4)

        # Result display
        res_frame = tk.Frame(f, bg=BG2, pady=8)
        res_frame.pack(fill="x", padx=16, pady=(8,0))

        self._lbl_path_result = tk.Label(
            res_frame, text="", bg=BG2, fg=SUCCESS,
            font=("Segoe UI", 13, "bold"), wraplength=700, justify="center")
        self._lbl_path_result.pack()

        self._lbl_path_cost = tk.Label(
            res_frame, text="", bg=BG2, fg=WARN,
            font=("Segoe UI", 11), justify="center")
        self._lbl_path_cost.pack(pady=2)

        # Embedded topology canvas for path highlight
        tk.Label(f, text="Red con la ruta resaltada:", bg=BG,
                 fg=MUTED, font=FONT).pack(anchor="w", padx=16, pady=(10,2))

        self._path_canvas = TopologyCanvas(f)
        self._path_canvas.pack(fill="both", expand=True, padx=16, pady=(0,10))

    def _find_path(self):
        src = self._path_src.get().strip().upper()
        dst = self._path_dst.get().strip().upper()
        if not src or not dst:
            messagebox.showwarning("Entrada", "Ingresa origen y destino.")
            return

        def _do():
            try:
                path, cost = self.routing_service.get_full_path(src, dst)
                topo    = self.topology_dao.get_topology()
                routers = self.router_dao.get_all_routers()
                statuses = {r.router_id: r.status for r in routers}

                def _update():
                    if not path:
                        self._lbl_path_result.config(
                            text=f"No hay ruta entre {src} y {dst}.",
                            fg=DANGER)
                        self._lbl_path_cost.config(text="")
                    else:
                        arrow = "  →  ".join(path)
                        self._lbl_path_result.config(
                            text=f"Ruta: {arrow}", fg=SUCCESS)
                        self._lbl_path_cost.config(
                            text=f"Costo total: {cost}", fg=WARN)
                    self._path_canvas.update_topology(topo, statuses)
                    self._path_canvas.highlight_path(path)
                    # Also highlight on topology tab
                    self._topo_canvas.update_topology(topo, statuses)
                    self._topo_canvas.highlight_path(path)

                self.root.after(0, _update)
                self._log(f"Best path {src}→{dst}: {path}  cost={cost}")
            except Exception as e:
                self._log(f"[ERROR] Path {src}→{dst}: {e}", error=True)
        threading.Thread(target=_do, daemon=True).start()

    def _clear_path(self):
        self._lbl_path_result.config(text="")
        self._lbl_path_cost.config(text="")
        self._path_canvas.clear_path()
        self._topo_canvas.clear_path()

    # ══════════════════════════════════════════════════════════════════ LOG
    def _build_log_tab(self):
        f = self._tab_log

        bar = tk.Frame(f, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6,0))
        tk.Label(bar, text="Log de eventos en tiempo real",
                 bg=BG2, fg=MUTED, font=FONT).pack(side="left", padx=8)
        tk.Button(bar, text="Limpiar", font=FONT, bg=BG3, fg=MUTED,
                  relief="flat",
                  command=lambda: self._log_box.config(state="normal") or
                                  self._log_box.delete("1.0","end") or
                                  self._log_box.config(state="disabled")
                  ).pack(side="right", padx=6)

        self._log_box = tk.Text(f, bg="#0a0a1a", fg=TEXT, font=FONT_M,
                                 relief="flat", wrap="word", state="disabled",
                                 insertbackground=TEXT)
        sb = ttk.Scrollbar(f, command=self._log_box.yview)
        self._log_box.configure(yscrollcommand=sb.set)

        self._log_box.pack(fill="both", expand=True, padx=8, pady=8,
                            side="left")
        sb.pack(fill="y", padx=(0,8), pady=8, side="right")

        self._log_box.tag_configure("error", foreground=DANGER)
        self._log_box.tag_configure("warn",  foreground=WARN)
        self._log_box.tag_configure("ok",    foreground=SUCCESS)

    def _log(self, msg: str, error: bool = False, warn: bool = False):
        import datetime
        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        tag = "error" if error else ("warn" if warn else "ok")
        line = f"[{ts}]  {msg}\n"

        def _append():
            self._log_box.config(state="normal")
            self._log_box.insert("end", line, tag)
            self._log_box.see("end")
            self._log_box.config(state="disabled")
        self.root.after(0, _append)

    # ══════════════════════════════════════════════════════════════ refresh
    def _schedule_refresh(self):
        """Auto-refresh all tabs every 5 seconds."""
        self._refresh_topology()
        self._refresh_routers()
        self._refresh_tables()
        self.root.after(3000, self._schedule_refresh)

    def notify_disconnect(self, router_id: str):
        """
        Called by the controller when a router TCP connection drops.
        Triggers an immediate GUI refresh without waiting for the 5s cycle.
        """
        self._log(f"Router '{router_id}' disconnected — updating display", warn=True)
        # Schedule immediate refresh on the Tk main thread
        self.root.after(0, self._refresh_routers)
        self.root.after(0, self._refresh_topology)
        self.root.after(0, self._refresh_tables)

    def notify_reconnect(self, router_id: str):
        """Called when a router reconnects and is marked ACTIVE again."""
        self._log(f"Router '{router_id}' reconnected and is now ACTIVE")
        self.root.after(0, self._refresh_routers)
        self.root.after(0, self._refresh_topology)
        self.root.after(0, self._refresh_tables)

    def run(self):
        self.root.mainloop()
