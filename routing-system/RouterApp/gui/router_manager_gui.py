"""
gui/router_manager_gui.py
=========================
RouterManagerGUI: single Tkinter window that manages all 4 routers.

Each router has its own tab with:
  - Connection status indicator
  - Routing table display
  - Link-cost update
  - Up/Down controls

A "Network" tab at top shows the live topology graph (read from the
controller's DB via direct TCP data_request, or locally).

Usage: python main_gui.py  (from RouterApp/)
"""

import sys
import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from network.tcp_client            import TCPClient
from service.registration_service  import RegistrationService
from service.topology_service      import TopologyService
from service.routing_table_service import RoutingTableService
from model.router                  import Router
from dao.router_dao                import RouterConfigDAO

# ─── Palette ────────────────────────────────────────────────────────────────
BG      = "#0f172a"
BG2     = "#1e293b"
BG3     = "#334155"
ACCENT  = "#3b82f6"
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARN    = "#f59e0b"
TEXT    = "#e2e8f0"
MUTED   = "#64748b"
FONT    = ("Segoe UI", 10)
FONT_B  = ("Segoe UI", 10, "bold")
FONT_M  = ("Consolas", 10)
FONT_L  = ("Segoe UI", 12, "bold")

CONFIGS = ["config/R1.json", "config/R2.json",
           "config/R3.json", "config/R4.json"]


def _style():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".", background=BG2, foreground=TEXT, font=FONT,
                fieldbackground=BG3, borderwidth=0)
    s.configure("TNotebook",     background=BG, tabmargins=[0,0,0,0])
    s.configure("TNotebook.Tab", background=BG3, foreground=MUTED,
                padding=[14,6], font=FONT_B)
    s.map("TNotebook.Tab",
          background=[("selected", BG2)],
          foreground=[("selected", TEXT)])
    s.configure("Treeview", background=BG2, foreground=TEXT,
                fieldbackground=BG2, rowheight=26, font=FONT_M)
    s.configure("Treeview.Heading", background=BG3, foreground=TEXT,
                font=FONT_B, relief="flat")
    s.map("Treeview", background=[("selected", ACCENT)])
    s.configure("TScrollbar", background=BG3, troughcolor=BG2, arrowcolor=TEXT)
    for name, fg in [("G.TButton", SUCCESS),("R.TButton", DANGER),
                     ("A.TButton", ACCENT),("W.TButton", WARN)]:
        s.configure(name, background=BG3, foreground=fg,
                    font=FONT_B, relief="flat", padding=[10,5])
        s.map(name, background=[("active", BG)])


# ════════════════════════════════════════════════════════════ RouterSession
class RouterSession:
    """Manages TCP lifecycle for one router."""

    def __init__(self, config_path: str):
        dao    = RouterConfigDAO(config_path)
        cfg    = dao.load_config()
        rcfg   = cfg["router"]
        ccfg   = cfg["controller"]

        self.router = Router(
            router_id = rcfg["router_id"],
            ip        = rcfg["ip"],
            port      = rcfg["port"],
            neighbors = rcfg["neighbors"],
            status    = rcfg.get("status", "ACTIVE"),
        )
        self.ctrl_host = ccfg["host"]
        self.ctrl_port = ccfg["port"]

        self.client    = TCPClient(self.ctrl_host, self.ctrl_port)
        self.connected = False
        self.reg_svc   = RegistrationService()
        self.topo_svc  = TopologyService()
        self.rt_svc    = RoutingTableService(
            f"data/{self.router.router_id}_routing_table.json")

    def connect_and_register(self) -> tuple[bool, str]:
        """Open socket, register, send topology. Returns (ok, message)."""
        try:
            self.client.connect()
            reg_msg  = self.reg_svc.create_registration_message(self.router)
            reg_resp = self.client.send_message(reg_msg)

            if reg_resp.get("type") == "ERROR":
                self.client.disconnect()
                return False, reg_resp.get("message", "Registration failed")

            topo_msg  = self.topo_svc.create_topology_message(self.router)
            topo_resp = self.client.send_message(topo_msg)

            table = self._extract_table(topo_resp)
            if table is not None:
                self.router.routing_table = table
                self.rt_svc.save_routing_table(self.router.router_id, table)

            self.connected = True
            return True, f"Router {self.router.router_id} connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.client.disconnect()
        self.connected = False

    def send(self, msg: dict) -> dict:
        resp = self.client.send_message(msg)
        table = self._extract_table(resp)
        if table is not None:
            self.router.routing_table = table
            self.rt_svc.save_routing_table(self.router.router_id, table)
        return resp

    @staticmethod
    def _extract_table(resp: dict):
        if resp.get("type") != "ROUTING_TABLE":
            return None
        return resp.get("routing_table", resp.get("table", []))


# ════════════════════════════════════════════════════════ RouterManagerGUI
class RouterManagerGUI:

    def __init__(self):
        self.sessions: dict[str, RouterSession] = {}
        self._load_sessions()

        self.root = tk.Tk()
        self.root.title("Router Manager — Centralized Routing System")
        self.root.geometry("1000x680")
        self.root.configure(bg=BG)
        self.root.minsize(800, 560)
        _style()

        self._build_ui()
        self._auto_refresh()

    def _load_sessions(self):
        for path in CONFIGS:
            try:
                sess = RouterSession(path)
                self.sessions[sess.router.router_id] = sess
            except Exception as e:
                print(f"[WARN] Could not load {path}: {e}")

    # ════════════════════════════════════════════════════════════════ UI
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG2, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⬡  Router Manager",
                 bg=BG2, fg=TEXT, font=("Segoe UI", 14, "bold")
                 ).pack(side="left", padx=16, pady=10)
        self._lbl_hdr_status = tk.Label(hdr, text="Todos desconectados",
            bg=BG2, fg=MUTED, font=FONT)
        self._lbl_hdr_status.pack(side="right", padx=16)

        # Global actions
        act = tk.Frame(self.root, bg=BG3, pady=8)
        act.pack(fill="x", padx=10, pady=(8,0))
        tk.Label(act, text="Acciones globales:", bg=BG3, fg=MUTED,
                 font=FONT).pack(side="left", padx=10)
        ttk.Button(act, text="⚡ Conectar todos",  style="G.TButton",
                   command=self._connect_all).pack(side="left", padx=4)
        ttk.Button(act, text="✖ Desconectar todos", style="R.TButton",
                   command=self._disconnect_all).pack(side="left", padx=4)
        ttk.Button(act, text="⟳ Actualizar tablas", style="A.TButton",
                   command=self._refresh_all_tables).pack(side="left", padx=4)
        ttk.Button(act, text="➕ Nuevo router", style="A.TButton",
                   command=self._add_new_router_dialog).pack(side="left", padx=4)

        # Notebook — one tab per router + log
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        self._router_tabs: dict[str, dict] = {}
        for rid, sess in sorted(self.sessions.items()):
            frame = ttk.Frame(nb)
            nb.add(frame, text=f"  {rid}  ")
            self._router_tabs[rid] = self._build_router_tab(frame, sess)

        # Log tab
        log_frame = ttk.Frame(nb)
        nb.add(log_frame, text="  📜 Log  ")
        self._build_log_tab(log_frame)

    # ════════════════════════════════════════════════ single router tab
    def _build_router_tab(self, frame: ttk.Frame, sess: RouterSession) -> dict:
        rid = sess.router.router_id
        refs = {}

        # ── Status bar ──────────────────────────────────────────────────────
        sb = tk.Frame(frame, bg=BG2, pady=10)
        sb.pack(fill="x", padx=10, pady=(10,0))

        dot = tk.Label(sb, text="●", fg=DANGER, bg=BG2,
                       font=("Segoe UI", 16))
        dot.pack(side="left", padx=(10,4))
        refs["dot"] = dot

        info = tk.Label(sb,
            text=f"{rid}  |  {sess.router.ip}:{sess.router.port}  |  "
                 f"Vecinos: {', '.join(n['neighbor_id'] for n in sess.router.neighbors)}",
            bg=BG2, fg=TEXT, font=FONT_B)
        info.pack(side="left")

        lbl_status = tk.Label(sb, text="Desconectado", fg=DANGER,
                               bg=BG2, font=FONT)
        lbl_status.pack(side="right", padx=14)
        refs["lbl_status"] = lbl_status

        # ── Control buttons ─────────────────────────────────────────────────
        cb = tk.Frame(frame, bg=BG, pady=8)
        cb.pack(fill="x", padx=10)

        for text, style, cmd in [
            ("⚡ Conectar",      "G.TButton", lambda r=rid: self._connect_one(r)),
            ("✖ Desconectar",   "R.TButton", lambda r=rid: self._disconnect_one(r)),
            ("⬆ Activar (up)",  "G.TButton", lambda r=rid: self._router_up(r)),
            ("⬇ Desactivar",    "R.TButton", lambda r=rid: self._router_down(r)),
        ]:
            ttk.Button(cb, text=text, style=style, command=cmd
                       ).pack(side="left", padx=4)

        # ── Link cost update ─────────────────────────────────────────────────
        lc = tk.Frame(frame, bg=BG2, pady=8)
        lc.pack(fill="x", padx=10, pady=(4,0))
        tk.Label(lc, text="Actualizar costo:", bg=BG2, fg=MUTED,
                 font=FONT).pack(side="left", padx=8)

        # Pre-fill neighbor dropdown
        neighbor_ids = [n["neighbor_id"] for n in sess.router.neighbors]
        nb_var = tk.StringVar(value=neighbor_ids[0] if neighbor_ids else "")
        nb_menu = ttk.Combobox(lc, textvariable=nb_var,
                               values=neighbor_ids, width=6,
                               state="readonly", font=FONT_M)
        nb_menu.pack(side="left", padx=4)
        refs["nb_var"] = nb_var

        tk.Label(lc, text="costo:", bg=BG2, fg=MUTED, font=FONT
                 ).pack(side="left", padx=(8,2))
        cost_entry = tk.Entry(lc, width=6, bg=BG3, fg=TEXT,
                              insertbackground=TEXT, font=FONT_M,
                              relief="flat")
        cost_entry.insert(0, "1")
        cost_entry.pack(side="left", padx=4)
        refs["cost_entry"] = cost_entry

        ttk.Button(lc, text="Aplicar", style="A.TButton",
                   command=lambda r=rid: self._update_cost(r)
                   ).pack(side="left", padx=6)

        # ── Routing table ────────────────────────────────────────────────────
        tk.Label(frame, text=f"Tabla de enrutamiento — {rid}",
                 bg=BG, fg=MUTED, font=FONT
                 ).pack(anchor="w", padx=14, pady=(12,2))

        cols = ("Destino", "Next Hop", "Costo")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                             selectmode="browse", height=8)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center",
                        width={"Destino": 130,"Next Hop": 130,"Costo": 90}[c])

        sb_rt = ttk.Scrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=sb_rt.set)
        tree.pack(fill="both", expand=True, padx=10, side="left")
        sb_rt.pack(fill="y", padx=(0,10), side="right")
        refs["tree"] = tree

        return refs

    # ════════════════════════════════════════════════════════════════ LOG tab
    def _build_log_tab(self, frame: ttk.Frame):
        bar = tk.Frame(frame, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6,0))
        tk.Label(bar, text="Log de eventos", bg=BG2, fg=MUTED,
                 font=FONT).pack(side="left", padx=8)
        tk.Button(bar, text="Limpiar", font=FONT, bg=BG3, fg=MUTED,
                  relief="flat",
                  command=lambda: [
                      self._log_box.config(state="normal"),
                      self._log_box.delete("1.0","end"),
                      self._log_box.config(state="disabled")]
                  ).pack(side="right", padx=6)

        self._log_box = tk.Text(frame, bg="#0a0a1a", fg=TEXT, font=FONT_M,
                                 relief="flat", wrap="word", state="disabled")
        sb = ttk.Scrollbar(frame, command=self._log_box.yview)
        self._log_box.configure(yscrollcommand=sb.set)
        self._log_box.pack(fill="both", expand=True, padx=8, pady=8, side="left")
        sb.pack(fill="y", padx=(0,8), pady=8, side="right")
        self._log_box.tag_configure("error", foreground=DANGER)
        self._log_box.tag_configure("ok",    foreground=SUCCESS)
        self._log_box.tag_configure("warn",  foreground=WARN)

    def _log(self, msg: str, tag: str = "ok"):
        import datetime
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}\n"
        def _a():
            self._log_box.config(state="normal")
            self._log_box.insert("end", line, tag)
            self._log_box.see("end")
            self._log_box.config(state="disabled")
        self.root.after(0, _a)

    # ════════════════════════════════════════════════════ connection actions
    def _connect_one(self, rid: str):
        sess = self.sessions[rid]
        if sess.connected:
            self._log(f"{rid} ya está conectado.", "warn"); return

        def _do():
            ok, msg = sess.connect_and_register()
            self._log(msg, "ok" if ok else "error")
            self.root.after(0, lambda: self._update_tab_status(rid))
            if ok:
                self.root.after(0, lambda: self._fill_table(rid))
        threading.Thread(target=_do, daemon=True).start()

    def _disconnect_one(self, rid: str):
        sess = self.sessions[rid]
        sess.disconnect()
        self._log(f"{rid} desconectado.", "warn")
        self.root.after(0, lambda: self._update_tab_status(rid))

    def _connect_all(self):
        for rid in sorted(self.sessions):
            self._connect_one(rid)

    def _disconnect_all(self):
        for rid in sorted(self.sessions):
            self._disconnect_one(rid)

    def _router_up(self, rid: str):
        sess = self.sessions[rid]
        if not sess.connected:
            messagebox.showwarning("Sin conexión",
                f"Conecta {rid} primero."); return
        def _do():
            try:
                from service.routing_table_service import RoutingTableService
                msg  = RoutingTableService.create_router_up_message(rid)
                resp = sess.send(msg)
                self._log(f"{rid} → UP  resp={resp.get('type')}")
            except Exception as e:
                self._log(f"[ERROR] up {rid}: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _router_down(self, rid: str):
        sess = self.sessions[rid]
        if not sess.connected:
            messagebox.showwarning("Sin conexión",
                f"Conecta {rid} primero."); return
        if not messagebox.askyesno("Confirmar",
                f"¿Marcar {rid} como INACTIVE?"):
            return
        def _do():
            try:
                from service.routing_table_service import RoutingTableService
                msg  = RoutingTableService.create_router_down_message(rid)
                resp = sess.send(msg)
                self._log(f"{rid} → DOWN  resp={resp.get('type')}", "warn")
            except Exception as e:
                self._log(f"[ERROR] down {rid}: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _update_cost(self, rid: str):
        sess     = self.sessions[rid]
        refs     = self._router_tabs[rid]
        neighbor = refs["nb_var"].get().strip().upper()
        cost_str = refs["cost_entry"].get().strip()

        if not sess.connected:
            messagebox.showwarning("Sin conexión",
                f"Conecta {rid} primero."); return
        try:
            cost = float(cost_str)
            if cost < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El costo debe ser >= 0"); return

        def _do():
            try:
                from service.routing_table_service import RoutingTableService
                msg  = RoutingTableService.create_link_cost_update_message(
                    rid, neighbor, cost)
                resp = sess.send(msg)
                self._log(
                    f"{rid}↔{neighbor} cost={cost}  resp={resp.get('type')}")
                self.root.after(0, lambda: self._fill_table(rid))
            except Exception as e:
                self._log(f"[ERROR] update-cost {rid}: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    # ════════════════════════════════════════════════ table display
    def _fill_table(self, rid: str):
        sess = self.sessions[rid]
        refs = self._router_tabs[rid]
        tree = refs["tree"]
        tree.delete(*tree.get_children())
        for e in sess.router.routing_table:
            tree.insert("", "end",
                        values=(e["destination"], e["next_hop"], e["cost"]))

    def _refresh_all_tables(self):
        for rid in self.sessions:
            self.root.after(0, lambda r=rid: self._fill_table(r))

    # ════════════════════════════════════════════════ status updates
    def _update_tab_status(self, rid: str):
        sess = self.sessions[rid]
        refs = self._router_tabs[rid]
        if sess.connected:
            refs["dot"].config(fg=SUCCESS)
            refs["lbl_status"].config(text="Conectado", fg=SUCCESS)
        else:
            refs["dot"].config(fg=DANGER)
            refs["lbl_status"].config(text="Desconectado", fg=DANGER)

        connected = sum(1 for s in self.sessions.values() if s.connected)
        total     = len(self.sessions)
        self._lbl_hdr_status.config(
            text=f"{connected}/{total} conectados",
            fg=SUCCESS if connected == total else
               WARN    if connected > 0      else MUTED)

    def _auto_refresh(self):
        for rid, sess in self.sessions.items():
            if sess.connected:
                self._fill_table(rid)
                self._update_tab_status(rid)
        self.root.after(4000, self._auto_refresh)


    def _add_new_router_dialog(self):
        """
        Dialog to configure and connect a brand new router.
        Creates the config JSON on disk and opens a new session.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar nuevo router")
        dialog.geometry("460x400")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Nuevo Router",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")
                 ).pack(pady=(16,2))
        tk.Label(dialog,
                 text="Crea la config y conecta el router automáticamente.",
                 bg=BG, fg=MUTED, font=FONT).pack(pady=(0,10))

        frame = tk.Frame(dialog, bg=BG)
        frame.pack(padx=24, fill="x")

        def lbl(text, row):
            tk.Label(frame, text=text, bg=BG, fg=TEXT,
                     font=FONT_B, anchor="e", width=14
                     ).grid(row=row, column=0, sticky="e", pady=5, padx=(0,8))

        entries = {}
        defaults = [("id","R5"), ("ip","127.0.0.1"), ("port","5005"),
                    ("ctrl_host","127.0.0.1"), ("ctrl_port","9000"),
                    ("neighbors","R1:3 R2:7")]
        labels   = ["Router ID", "IP", "Puerto",
                    "Controller IP", "Controller Puerto",
                    "Vecinos (ID:costo)"]
        for i, ((key, dflt), lbl_text) in enumerate(zip(defaults, labels)):
            lbl(lbl_text, i)
            e = tk.Entry(frame, width=28, bg=BG3, fg=TEXT,
                         insertbackground=TEXT, font=FONT_M, relief="flat")
            e.insert(0, dflt)
            e.grid(row=i, column=1, sticky="w", pady=5)
            entries[key] = e

        msg_var = tk.StringVar()
        tk.Label(dialog, textvariable=msg_var, bg=BG, fg=DANGER,
                 font=FONT, wraplength=420).pack(pady=4)

        def on_create():
            rid       = entries["id"].get().strip().upper()
            ip        = entries["ip"].get().strip()
            port_s    = entries["port"].get().strip()
            ctrl_host = entries["ctrl_host"].get().strip()
            ctrl_port_s = entries["ctrl_port"].get().strip()
            nb_raw    = entries["neighbors"].get().strip()

            if not all([rid, ip, port_s, ctrl_host, ctrl_port_s]):
                msg_var.set("Todos los campos son obligatorios.")
                return
            try:
                port      = int(port_s)
                ctrl_port = int(ctrl_port_s)
            except ValueError:
                msg_var.set("Puerto debe ser un número entero.")
                return

            neighbors = []
            for token in nb_raw.split():
                if not token:
                    continue
                if ":" not in token:
                    msg_var.set(f"Formato inválido: '{token}'. Use ID:costo")
                    return
                nb_id, cost_s = token.split(":", 1)
                try:
                    cost = float(cost_s)
                except ValueError:
                    msg_var.set(f"Costo inválido: '{cost_s}'")
                    return
                neighbors.append({"neighbor_id": nb_id.upper(), "cost": cost})

            # Build config dict
            import json, os
            cfg = {
                "router": {
                    "router_id": rid,
                    "ip": ip,
                    "port": port,
                    "status": "ACTIVE",
                    "neighbors": neighbors
                },
                "controller": {"host": ctrl_host, "port": ctrl_port}
            }

            # Save config file
            config_path = f"config/{rid}.json"
            try:
                os.makedirs("config", exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(cfg, f, indent=2)
            except Exception as e:
                msg_var.set(f"Error guardando config: {e}")
                return

            # Create session and add tab
            try:
                from dao.router_dao import RouterConfigDAO
                sess = RouterSession(config_path)
                self.sessions[rid] = sess
            except Exception as e:
                msg_var.set(f"Error cargando sesión: {e}")
                return

            # Add new tab to notebook
            nb = None
            for w in self.root.winfo_children():
                for c in w.winfo_children():
                    if isinstance(c, ttk.Notebook):
                        nb = c
                        break

            if nb:
                frame_tab = ttk.Frame(nb)
                nb.add(frame_tab, text=f"  {rid}  ")
                self._router_tabs[rid] = self._build_router_tab(frame_tab, sess)

            dialog.destroy()
            self._log(f"Router '{rid}' agregado — config guardada en {config_path}")

            # Auto-connect
            self._connect_one(rid)

        btn_f = tk.Frame(dialog, bg=BG)
        btn_f.pack(pady=12)
        tk.Button(btn_f, text="  Crear y Conectar  ",
                  font=FONT_B, bg=SUCCESS, fg="white", relief="flat",
                  command=on_create).pack(side="left", padx=8)
        tk.Button(btn_f, text="Cancelar", font=FONT,
                  bg=BG3, fg=MUTED, relief="flat",
                  command=dialog.destroy).pack(side="left", padx=8)

    def run(self):
        self.root.mainloop()
