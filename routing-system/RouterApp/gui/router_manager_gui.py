"""
gui/router_manager_gui.py
=========================
RouterManagerGUI: ventana única que gestiona TODOS los routers.

BUGS CORREGIDOS:
  1. Nuevo router no aparecía en pestañas: se guarda referencia directa
     al Notebook en self._notebook en lugar de buscarlo con winfo_children().
  2. R1/R3 mostraban tablas vacías: el controller envía ACK + ROUTING_TABLE
     en secuencia. Ahora se usa send_and_get_table() que espera el
     ROUTING_TABLE después del ACK inicial.
  3. Tablas inconsistentes: después de conectar, se leen mensajes pendientes
     (tablas de otros routers enviadas por el controller tras recalcular)
     y se actualizan todas las sesiones.
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

# ── Paleta de colores ────────────────────────────────────────────────────────
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

# Configs de routers por defecto
CONFIGS = [
    "config/R1.json",
    "config/R2.json",
    "config/R3.json",
    "config/R4.json",
]


def _apply_styles():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".", background=BG2, foreground=TEXT,
                font=FONT, fieldbackground=BG3, borderwidth=0)
    s.configure("TNotebook",     background=BG, tabmargins=[0, 0, 0, 0])
    s.configure("TNotebook.Tab", background=BG3, foreground=MUTED,
                padding=[14, 6], font=FONT_B)
    s.map("TNotebook.Tab",
          background=[("selected", BG2)],
          foreground=[("selected", TEXT)])
    s.configure("Treeview",
                background=BG2, foreground=TEXT,
                fieldbackground=BG2, rowheight=26, font=FONT_M)
    s.configure("Treeview.Heading",
                background=BG3, foreground=TEXT,
                font=FONT_B, relief="flat")
    s.map("Treeview", background=[("selected", ACCENT)])
    s.configure("TScrollbar",
                background=BG3, troughcolor=BG2, arrowcolor=TEXT)
    s.configure("TCombobox",
                fieldbackground=BG3, background=BG3,
                foreground=TEXT, arrowcolor=TEXT)
    for name, fg in [
        ("G.TButton", SUCCESS),
        ("R.TButton", DANGER),
        ("A.TButton", ACCENT),
        ("W.TButton", WARN),
    ]:
        s.configure(name, background=BG3, foreground=fg,
                    font=FONT_B, relief="flat", padding=[10, 5])
        s.map(name, background=[("active", BG)])


# ════════════════════════════════════════════════════════════ RouterSession
class RouterSession:
    """
    Gestiona el ciclo de vida TCP de un router individual.

    Responsabilidades:
      - Conectar al controller y mantener el socket abierto
      - Enviar REGISTER_ROUTER y esperar ACK
      - Enviar TOPOLOGY_UPDATE y esperar ROUTING_TABLE
      - Guardar y exponer la tabla de enrutamiento recibida
    """

    def __init__(self, config_path: str):
        dao  = RouterConfigDAO(config_path)
        cfg  = dao.load_config()
        rcfg = cfg["router"]
        ccfg = cfg["controller"]

        self.router = Router(
            router_id=rcfg["router_id"],
            ip=rcfg["ip"],
            port=rcfg["port"],
            neighbors=rcfg.get("neighbors", []),
            status=rcfg.get("status", "ACTIVE"),
        )
        self.ctrl_host = ccfg["host"]
        self.ctrl_port = int(ccfg["port"])

        self.client    = TCPClient(self.ctrl_host, self.ctrl_port)
        self.connected = False
        self._reg_svc  = RegistrationService()
        self._topo_svc = TopologyService()
        self._rt_svc   = RoutingTableService(
            f"data/{self.router.router_id}_routing_table.json"
        )

    def connect_and_register(self) -> tuple:
        """
        1. Abre socket TCP
        2. Envía REGISTER_ROUTER → espera ACK
        3. Envía TOPOLOGY_UPDATE → espera ROUTING_TABLE
           (CORRECCIÓN BUG 2: usa send_and_get_table para leer
            ACK + ROUTING_TABLE correctamente)

        Retorna (ok: bool, mensaje: str)
        """
        try:
            self.client.connect()
        except Exception as e:
            return False, f"No se pudo conectar: {e}"

        try:
            # ── Paso 1: Registro ──────────────────────────────────────────
            reg_msg  = self._reg_svc.create_registration_message(self.router)
            reg_resp = self.client.send_message(reg_msg)

            if reg_resp.get("type") == "ERROR":
                self.client.disconnect()
                return False, f"Registro rechazado: {reg_resp.get('message','')}"

            # ── Paso 2: Topología ─────────────────────────────────────────
            # CORRECCIÓN BUG 2: send_and_get_table lee ACK + ROUTING_TABLE
            topo_msg = self._topo_svc.create_topology_message(self.router)
            _ack, rt_resp = self.client.send_and_get_table(topo_msg)

            if rt_resp is not None:
                table = rt_resp.get("routing_table",
                                    rt_resp.get("table", []))
                self.router.routing_table = table
                self._rt_svc.save_routing_table(self.router.router_id, table)

            self.connected = True
            return True, f"Router {self.router.router_id} conectado"

        except Exception as e:
            self.client.disconnect()
            return False, str(e)

    def disconnect(self):
        """Cierra el socket TCP."""
        self.client.disconnect()
        self.connected = False

    def send(self, msg: dict) -> dict:
        """
        Envía un mensaje y espera respuesta. Si la respuesta es
        ROUTING_TABLE, actualiza la tabla local automáticamente.
        """
        try:
            resp = self.client.send_message(msg)
        except Exception as e:
            return {"type": "ERROR", "message": str(e)}

        self._update_table_from_resp(resp)
        return resp

    def send_expect_table(self, msg: dict) -> tuple:
        """
        Como send() pero espera explícitamente ROUTING_TABLE.
        Retorna (resp_inicial, tabla_o_None).
        """
        try:
            first, rt = self.client.send_and_get_table(msg)
        except Exception as e:
            return {"type": "ERROR", "message": str(e)}, None

        if rt is not None:
            table = rt.get("routing_table", rt.get("table", []))
            self.router.routing_table = table
            self._rt_svc.save_routing_table(self.router.router_id, table)
        return first, rt

    def read_pending_tables(self):
        """
        Lee mensajes pendientes en el buffer (tablas enviadas por el
        controller tras recalcular porque otro router se conectó).
        Actualiza la tabla local si encuentra un ROUTING_TABLE.

        CORRECCIÓN BUG 3: permite que R1 reciba su tabla actualizada
        cuando R2, R3 o R4 se conectan después.
        """
        if not self.connected:
            return
        try:
            messages = self.client.recv_pending()
            for msg in messages:
                if msg.get("type") == "ROUTING_TABLE":
                    rid = msg.get("router_id", "")
                    if rid == self.router.router_id:
                        table = msg.get("routing_table",
                                        msg.get("table", []))
                        self.router.routing_table = table
                        self._rt_svc.save_routing_table(
                            self.router.router_id, table)
        except Exception:
            pass

    def _update_table_from_resp(self, resp: dict):
        if resp.get("type") == "ROUTING_TABLE":
            table = resp.get("routing_table", resp.get("table", []))
            self.router.routing_table = table
            self._rt_svc.save_routing_table(self.router.router_id, table)


# ════════════════════════════════════════════════════════ RouterManagerGUI
class RouterManagerGUI:
    """
    Ventana principal del Router Manager.

    Mantiene:
      self._notebook  — referencia DIRECTA al Notebook (fix Bug 1)
      self.sessions   — {router_id: RouterSession}
      self._router_tabs — {router_id: dict de widgets}
    """

    def __init__(self):
        self.sessions: dict     = {}
        self._router_tabs: dict = {}
        self._notebook          = None   # CORRECCIÓN BUG 1

        self._load_initial_sessions()

        self.root = tk.Tk()
        self.root.title("Router Manager — Centralized Routing System")
        self.root.geometry("1060x700")
        self.root.configure(bg=BG)
        self.root.minsize(860, 580)
        _apply_styles()

        self._build_ui()
        self._auto_refresh()

    # ────────────────────────────────────────────────────────── carga inicial
    def _load_initial_sessions(self):
        """Carga las sesiones de los archivos de config por defecto."""
        for path in CONFIGS:
            try:
                sess = RouterSession(path)
                self.sessions[sess.router.router_id] = sess
            except Exception as e:
                print(f"[WARN] No se pudo cargar {path}: {e}")

    # ────────────────────────────────────────────────────────── construcción UI
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG2, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="⬡  Router Manager",
            bg=BG2, fg=TEXT, font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=16, pady=10)

        self._lbl_status = tk.Label(
            hdr, text="0/0 conectados",
            bg=BG2, fg=MUTED, font=FONT
        )
        self._lbl_status.pack(side="right", padx=16)

        # ── Barra de acciones globales ────────────────────────────────────
        act = tk.Frame(self.root, bg=BG3, pady=8)
        act.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(
            act, text="Acciones globales:",
            bg=BG3, fg=MUTED, font=FONT
        ).pack(side="left", padx=10)

        ttk.Button(
            act, text="⚡ Conectar todos",
            style="G.TButton", command=self._connect_all
        ).pack(side="left", padx=4)

        ttk.Button(
            act, text="✖ Desconectar todos",
            style="R.TButton", command=self._disconnect_all
        ).pack(side="left", padx=4)

        ttk.Button(
            act, text="⟳ Actualizar tablas",
            style="A.TButton", command=self._refresh_all_tables
        ).pack(side="left", padx=4)

        ttk.Button(
            act, text="➕ Nuevo router",
            style="A.TButton", command=self._show_add_dialog
        ).pack(side="left", padx=4)

        # ── Notebook ─────────────────────────────────────────────────────
        # CORRECCIÓN BUG 1: guardamos referencia directa en self._notebook
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=10, pady=8)

        # Pestaña por cada router
        for rid in sorted(self.sessions):
            self._add_router_tab(rid, self.sessions[rid])

        # Pestaña de log (siempre al final)
        self._log_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._log_frame, text="  📜 Log  ")
        self._build_log_tab(self._log_frame)

    def _add_router_tab(self, rid: str, sess: RouterSession):
        """
        Crea y añade una pestaña de router al notebook.

        Lógica:
          - Si la pestaña Log YA existe (router agregado en runtime):
            inserta ANTES de ella para que Log quede siempre al final.
          - Si Log todavía no existe (construcción inicial de la UI):
            usa add() — insert() con índice -1 causa TclError.

        CORRECCIÓN ERROR: "Slave index 0 out of bounds"
          El error ocurría porque durante _build_ui() se llamaba a
          _add_router_tab() ANTES de crear la pestaña Log. En ese
          momento index("end")-1 = -1, y insert(-1,...) lanzaba
          TclError. Ahora se detecta si Log existe por su texto.
        """
        frame = ttk.Frame(self._notebook)

        # Buscar el índice real de la pestaña Log por su texto
        log_idx = None
        try:
            n_tabs = self._notebook.index("end")
            for i in range(n_tabs):
                if "Log" in self._notebook.tab(i, "text"):
                    log_idx = i
                    break
        except Exception:
            log_idx = None

        if log_idx is not None:
            # Log existe → insertar justo antes
            self._notebook.insert(log_idx, frame, text=f"  {rid}  ")
        else:
            # Log aún no existe → añadir al final
            self._notebook.add(frame, text=f"  {rid}  ")

        self._router_tabs[rid] = self._build_router_tab_content(frame, sess)

    # ────────────────────────────────────────────────────────── pestaña router
    def _build_router_tab_content(self, frame: ttk.Frame,
                                   sess: RouterSession) -> dict:
        """Construye el contenido completo de la pestaña de un router."""
        rid  = sess.router.router_id
        refs = {}

        # ── Barra de estado ───────────────────────────────────────────────
        sb = tk.Frame(frame, bg=BG2, pady=10)
        sb.pack(fill="x", padx=10, pady=(10, 0))

        dot = tk.Label(sb, text="●", fg=DANGER, bg=BG2,
                       font=("Segoe UI", 18))
        dot.pack(side="left", padx=(10, 6))
        refs["dot"] = dot

        neighbors_str = ", ".join(
            f"{n['neighbor_id']}(cost={n['cost']})"
            for n in sess.router.neighbors
        ) or "Sin vecinos"

        tk.Label(
            sb,
            text=f"{rid}  |  {sess.router.ip}:{sess.router.port}"
                 f"  |  Vecinos: {neighbors_str}",
            bg=BG2, fg=TEXT, font=FONT_B
        ).pack(side="left")

        lbl_conn = tk.Label(sb, text="Desconectado", fg=DANGER,
                             bg=BG2, font=FONT)
        lbl_conn.pack(side="right", padx=14)
        refs["lbl_conn"] = lbl_conn

        # ── Botones de control ────────────────────────────────────────────
        cb = tk.Frame(frame, bg=BG, pady=8)
        cb.pack(fill="x", padx=10)

        for text, style, cmd in [
            ("⚡ Conectar",    "G.TButton", lambda r=rid: self._connect_one(r)),
            ("✖ Desconectar", "R.TButton", lambda r=rid: self._disconnect_one(r)),
            ("⬆ Activar",     "G.TButton", lambda r=rid: self._router_up(r)),
            ("⬇ Desactivar",  "R.TButton", lambda r=rid: self._router_down(r)),
        ]:
            ttk.Button(cb, text=text, style=style, command=cmd
                       ).pack(side="left", padx=4)

        # ── Actualizar costo de enlace ────────────────────────────────────
        lc = tk.Frame(frame, bg=BG2, pady=8)
        lc.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(lc, text="Actualizar costo:",
                 bg=BG2, fg=MUTED, font=FONT
                 ).pack(side="left", padx=8)

        nb_ids = [n["neighbor_id"] for n in sess.router.neighbors]
        nb_var = tk.StringVar(value=nb_ids[0] if nb_ids else "")
        nb_cb  = ttk.Combobox(
            lc, textvariable=nb_var, values=nb_ids,
            width=6, state="readonly", font=FONT_M
        )
        nb_cb.pack(side="left", padx=4)
        refs["nb_var"] = nb_var

        tk.Label(lc, text="costo:", bg=BG2, fg=MUTED,
                 font=FONT).pack(side="left", padx=(8, 2))

        cost_e = tk.Entry(lc, width=7, bg=BG3, fg=TEXT,
                          insertbackground=TEXT, font=FONT_M, relief="flat")
        cost_e.insert(0, "1")
        cost_e.pack(side="left", padx=4)
        refs["cost_entry"] = cost_e

        ttk.Button(
            lc, text="Aplicar", style="A.TButton",
            command=lambda r=rid: self._update_cost(r)
        ).pack(side="left", padx=6)

        # ── Tabla de enrutamiento ─────────────────────────────────────────
        tk.Label(
            frame, text=f"Tabla de enrutamiento — {rid}",
            bg=BG, fg=MUTED, font=FONT
        ).pack(anchor="w", padx=14, pady=(12, 2))

        cols = ("Destino", "Next Hop", "Costo")
        tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            selectmode="browse", height=10
        )
        for c in cols:
            w = {"Destino": 160, "Next Hop": 160, "Costo": 100}[c]
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=w, minwidth=80)

        tree.tag_configure("highlight", background=BG3)

        sb_y = ttk.Scrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=sb_y.set)
        tree.pack(fill="both", expand=True, padx=(10, 0),
                  pady=(0, 8), side="left")
        sb_y.pack(fill="y", padx=(0, 10), pady=(0, 8), side="right")
        refs["tree"] = tree

        return refs

    # ────────────────────────────────────────────────────────── pestaña log
    def _build_log_tab(self, frame: ttk.Frame):
        bar = tk.Frame(frame, bg=BG2, pady=6)
        bar.pack(fill="x", padx=8, pady=(6, 0))

        tk.Label(bar, text="Log de eventos",
                 bg=BG2, fg=MUTED, font=FONT
                 ).pack(side="left", padx=8)

        tk.Button(
            bar, text="Limpiar", font=FONT, bg=BG3, fg=MUTED,
            relief="flat",
            command=self._clear_log
        ).pack(side="right", padx=6)

        self._log_box = tk.Text(
            frame, bg="#0a0a1a", fg=TEXT, font=FONT_M,
            relief="flat", wrap="word", state="disabled"
        )
        sb = ttk.Scrollbar(frame, command=self._log_box.yview)
        self._log_box.configure(yscrollcommand=sb.set)
        self._log_box.pack(fill="both", expand=True,
                            padx=8, pady=8, side="left")
        sb.pack(fill="y", padx=(0, 8), pady=8, side="right")

        self._log_box.tag_configure("error", foreground=DANGER)
        self._log_box.tag_configure("ok",    foreground=SUCCESS)
        self._log_box.tag_configure("warn",  foreground=WARN)

    def _clear_log(self):
        self._log_box.config(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.config(state="disabled")

    def _log(self, msg: str, tag: str = "ok"):
        import datetime
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}\n"

        def _append():
            self._log_box.config(state="normal")
            self._log_box.insert("end", line, tag)
            self._log_box.see("end")
            self._log_box.config(state="disabled")

        self.root.after(0, _append)

    # ────────────────────────────────────────────────────────── conexiones
    def _connect_one(self, rid: str):
        sess = self.sessions.get(rid)
        if not sess:
            return
        if sess.connected:
            self._log(f"{rid} ya está conectado.", "warn")
            return

        def _do():
            ok, msg = sess.connect_and_register()
            self._log(msg, "ok" if ok else "error")
            self.root.after(0, lambda: self._update_status(rid))
            if ok:
                self.root.after(0, lambda: self._fill_table(rid))
                # CORRECCIÓN BUG 3: pequeña pausa y leer tablas pendientes
                # que el controller pudo haber enviado al recalcular
                import time; time.sleep(0.5)
                self.root.after(0, self._read_all_pending)

        threading.Thread(target=_do, daemon=True).start()

    def _disconnect_one(self, rid: str):
        sess = self.sessions.get(rid)
        if not sess:
            return
        sess.disconnect()
        self._log(f"{rid} desconectado.", "warn")
        self.root.after(0, lambda: self._update_status(rid))

    def _connect_all(self):
        """Conecta todos los routers con una pequeña pausa entre cada uno."""
        def _do():
            for rid in sorted(self.sessions):
                sess = self.sessions[rid]
                if not sess.connected:
                    ok, msg = sess.connect_and_register()
                    self._log(msg, "ok" if ok else "error")
                    self.root.after(0, lambda r=rid: self._update_status(r))
                    if ok:
                        self.root.after(0, lambda r=rid: self._fill_table(r))
                import time; time.sleep(0.4)
            # Leer pendientes después de conectar todos
            import time; time.sleep(0.8)
            self.root.after(0, self._read_all_pending)
            self.root.after(0, self._refresh_all_tables)

        threading.Thread(target=_do, daemon=True).start()

    def _disconnect_all(self):
        for rid in list(self.sessions):
            self._disconnect_one(rid)

    # ────────────────────────────────────────────────────────── acciones router
    def _router_up(self, rid: str):
        sess = self.sessions.get(rid)
        if not sess or not sess.connected:
            messagebox.showwarning("Sin conexión",
                                   f"Conecta {rid} primero.")
            return

        def _do():
            msg   = RoutingTableService.create_router_up_message(rid)
            first, rt = sess.send_expect_table(msg)
            self._log(f"{rid} → ACTIVE  ({first.get('type','?')})")
            self.root.after(0, lambda: self._fill_table(rid))

        threading.Thread(target=_do, daemon=True).start()

    def _router_down(self, rid: str):
        sess = self.sessions.get(rid)
        if not sess or not sess.connected:
            messagebox.showwarning("Sin conexión",
                                   f"Conecta {rid} primero.")
            return
        if not messagebox.askyesno("Confirmar",
                                    f"¿Marcar {rid} como INACTIVE?"):
            return

        def _do():
            msg   = RoutingTableService.create_router_down_message(rid)
            resp  = sess.send(msg)
            self._log(f"{rid} → INACTIVE  ({resp.get('type','?')})",
                      "warn")

        threading.Thread(target=_do, daemon=True).start()

    def _update_cost(self, rid: str):
        sess = self.sessions.get(rid)
        if not sess or not sess.connected:
            messagebox.showwarning("Sin conexión",
                                   f"Conecta {rid} primero.")
            return

        refs     = self._router_tabs[rid]
        neighbor = refs["nb_var"].get().strip().upper()
        cost_str = refs["cost_entry"].get().strip()

        try:
            cost = float(cost_str)
            if cost < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El costo debe ser un número >= 0")
            return

        def _do():
            msg = RoutingTableService.create_link_cost_update_message(
                rid, neighbor, cost)
            first, rt = sess.send_expect_table(msg)
            self._log(
                f"{rid}↔{neighbor} cost={cost} → {first.get('type','?')}")
            self.root.after(0, lambda: self._fill_table(rid))
            # Actualizar tablas de otros routers que cambiaron
            import time; time.sleep(0.4)
            self.root.after(0, self._read_all_pending)

        threading.Thread(target=_do, daemon=True).start()

    # ────────────────────────────────────────────────────────── tabla display
    def _fill_table(self, rid: str):
        """Rellena el TreeView con la tabla actual de la sesión."""
        sess = self.sessions.get(rid)
        refs = self._router_tabs.get(rid)
        if not sess or not refs:
            return

        tree = refs["tree"]
        tree.delete(*tree.get_children())

        table = sess.router.routing_table or []
        for entry in table:
            tree.insert("", "end", values=(
                entry.get("destination", "?"),
                entry.get("next_hop",    "?"),
                entry.get("cost",        "?"),
            ))

        # Mostrar placeholder si vacía
        if not table:
            tree.insert("", "end", values=("—", "—", "—"),
                        tags=("highlight",))

    def _refresh_all_tables(self):
        """Refresca los TreeViews de todos los routers."""
        for rid in self.sessions:
            self._fill_table(rid)

    def _read_all_pending(self):
        """
        CORRECCIÓN BUG 3: lee mensajes pendientes en todos los sockets
        activos. El controller envía ROUTING_TABLE actualizada a TODOS
        los routers cuando uno nuevo se conecta. Este método asegura
        que todos los routers locales reciban y muestren su tabla.
        """
        for rid, sess in self.sessions.items():
            if sess.connected:
                sess.read_pending_tables()
                self._fill_table(rid)

    # ────────────────────────────────────────────────────────── estado UI
    def _update_status(self, rid: str):
        sess = self.sessions.get(rid)
        refs = self._router_tabs.get(rid)
        if not sess or not refs:
            return

        if sess.connected:
            refs["dot"].config(fg=SUCCESS)
            refs["lbl_conn"].config(text="Conectado ●", fg=SUCCESS)
        else:
            refs["dot"].config(fg=DANGER)
            refs["lbl_conn"].config(text="Desconectado ○", fg=DANGER)

        connected = sum(1 for s in self.sessions.values() if s.connected)
        total     = len(self.sessions)
        color = SUCCESS if connected == total and total > 0 else \
                WARN    if connected > 0 else MUTED
        self._lbl_status.config(
            text=f"{connected}/{total} conectados", fg=color)

    # ────────────────────────────────────────────────────────── auto-refresco
    def _auto_refresh(self):
        """
        Refresco automático cada 4 segundos:
          - Lee mensajes pendientes (tablas nuevas del controller)
          - Actualiza todos los TreeViews
        """
        self._read_all_pending()
        self._refresh_all_tables()
        self.root.after(4000, self._auto_refresh)

    # ────────────────────────────────────────────────────────── agregar router
    def _show_add_dialog(self):
        """
        Diálogo para agregar un router nuevo en runtime.
        CORRECCIÓN BUG 1: usa self._notebook directamente para añadir
        la nueva pestaña, sin buscar el Notebook con winfo_children().
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar nuevo router")
        dialog.geometry("480x430")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)

        tk.Label(
            dialog, text="Agregar nuevo router",
            bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")
        ).pack(pady=(18, 4))

        tk.Label(
            dialog,
            text="Crea la config JSON y conecta al controller automáticamente.",
            bg=BG, fg=MUTED, font=FONT
        ).pack(pady=(0, 12))

        frm = tk.Frame(dialog, bg=BG)
        frm.pack(padx=28, fill="x")

        fields = [
            ("Router ID",        "id",        "R5"),
            ("IP del router",    "ip",        "127.0.0.1"),
            ("Puerto",           "port",      "5005"),
            ("Controller IP",    "ctrl_host", "127.0.0.1"),
            ("Controller Puerto","ctrl_port", "9000"),
            ("Vecinos (ID:costo)","neighbors", "R1:3 R2:7"),
        ]

        entries = {}
        for row, (label, key, default) in enumerate(fields):
            tk.Label(
                frm, text=label + ":", bg=BG, fg=TEXT,
                font=FONT_B, anchor="e", width=18
            ).grid(row=row, column=0, sticky="e", pady=6, padx=(0, 10))

            e = tk.Entry(
                frm, width=26, bg=BG3, fg=TEXT,
                insertbackground=TEXT, font=FONT_M, relief="flat"
            )
            e.insert(0, default)
            e.grid(row=row, column=1, sticky="w", pady=6)
            entries[key] = e

        err_var = tk.StringVar()
        tk.Label(
            dialog, textvariable=err_var,
            bg=BG, fg=DANGER, font=FONT, wraplength=440
        ).pack(pady=4)

        def _validate_and_create():
            rid        = entries["id"].get().strip().upper()
            ip         = entries["ip"].get().strip()
            port_s     = entries["port"].get().strip()
            ctrl_host  = entries["ctrl_host"].get().strip()
            ctrl_port_s= entries["ctrl_port"].get().strip()
            nb_raw     = entries["neighbors"].get().strip()

            if not all([rid, ip, port_s, ctrl_host, ctrl_port_s]):
                err_var.set("Todos los campos son obligatorios.")
                return

            try:
                port      = int(port_s)
                ctrl_port = int(ctrl_port_s)
            except ValueError:
                err_var.set("Puerto debe ser un número entero.")
                return

            if rid in self.sessions:
                err_var.set(f"Ya existe un router con ID '{rid}'.")
                return

            neighbors = []
            for token in nb_raw.split():
                if not token:
                    continue
                if ":" not in token:
                    err_var.set(f"Formato inválido: '{token}'. Use ID:costo")
                    return
                nb_id, cost_s = token.split(":", 1)
                try:
                    neighbors.append({
                        "neighbor_id": nb_id.strip().upper(),
                        "cost": float(cost_s.strip())
                    })
                except ValueError:
                    err_var.set(f"Costo inválido: '{cost_s}'")
                    return

            # Construir y guardar config JSON
            config = {
                "router": {
                    "router_id": rid,
                    "ip":        ip,
                    "port":      port,
                    "status":    "ACTIVE",
                    "neighbors": neighbors,
                },
                "controller": {
                    "host": ctrl_host,
                    "port": ctrl_port,
                },
            }

            config_path = f"config/{rid}.json"
            try:
                os.makedirs("config", exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
            except Exception as ex:
                err_var.set(f"Error guardando config: {ex}")
                return

            # Crear sesión
            try:
                sess = RouterSession(config_path)
            except Exception as ex:
                err_var.set(f"Error creando sesión: {ex}")
                return

            # Registrar sesión
            self.sessions[rid] = sess

            # CORRECCIÓN BUG 1: añadir pestaña con self._notebook directamente
            self._add_router_tab(rid, sess)

            dialog.destroy()
            self._log(
                f"Router '{rid}' creado — config en {config_path}")

            # Conectar automáticamente
            self.root.after(200, lambda: self._connect_one(rid))

        btn_f = tk.Frame(dialog, bg=BG)
        btn_f.pack(pady=14)

        tk.Button(
            btn_f, text="  Crear y Conectar  ",
            font=FONT_B, bg=SUCCESS, fg="white",
            relief="flat", cursor="hand2",
            command=_validate_and_create
        ).pack(side="left", padx=8)

        tk.Button(
            btn_f, text="Cancelar",
            font=FONT, bg=BG3, fg=MUTED,
            relief="flat", cursor="hand2",
            command=dialog.destroy
        ).pack(side="left", padx=8)

    # ────────────────────────────────────────────────────────── run
    def run(self):
        self.root.mainloop()
