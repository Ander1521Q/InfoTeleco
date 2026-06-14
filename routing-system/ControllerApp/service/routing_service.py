"""
service/routing_service.py
===========================
RoutingService: Dijkstra correcto + generacion de tablas + mejor ruta.

CORRECCIONES:
  - _next_hop() reescrito: ahora reconstruye el camino completo y toma
    el segundo nodo, lo cual es correcto para saltos directos Y multisalto.
  - generate_all_routing_tables() solo incluye routers con status ACTIVE/ACTIVO.
  - get_full_path() usa el mismo recorrido correcto.
"""
import heapq
import math


class RoutingService:
    # Solo ACTIVE pasa al grafo. INACTIVE, DISCONNECTED, MAINTENANCE quedan fuera.
    ACTIVE_STATUSES = {"ACTIVE", "ACTIVO"}

    def __init__(self, topology_dao, router_dao=None):
        self.topology_dao = topology_dao
        self.router_dao   = router_dao

    # ═══════════════════════════════════════════════════════════ Dijkstra
    def dijkstra(self, start: str) -> tuple:
        """
        Dijkstra de fuente única desde 'start' sobre el grafo activo.

        Retorna:
            dist (dict): {router_id: costo_minimo}
            prev (dict): {router_id: predecesor_en_camino_optimo}
        """
        topology = self._get_active_topology()
        if not topology:
            return {}, {}

        # Conjunto de todos los nodos del grafo activo
        nodes = set(topology.keys())
        for neighbors in topology.values():
            for nb in neighbors:
                nodes.add(nb["neighbor_id"])

        if start not in nodes:
            return {}, {}

        dist = {n: math.inf for n in nodes}
        prev = {}
        dist[start] = 0.0
        heap = [(0.0, start)]

        while heap:
            cur_cost, cur_node = heapq.heappop(heap)

            # Entrada obsoleta en el heap — ignorar
            if cur_cost > dist[cur_node]:
                continue

            for nb in topology.get(cur_node, []):
                nid      = nb["neighbor_id"]
                new_cost = cur_cost + float(nb["cost"])

                if new_cost < dist.get(nid, math.inf):
                    dist[nid]  = new_cost
                    prev[nid]  = cur_node
                    heapq.heappush(heap, (new_cost, nid))

        return dist, prev

    # ═══════════════════════════════════════════════════ tabla de un router
    def generate_routing_table(self, start: str) -> list:
        """
        Genera la tabla de enrutamiento para 'start'.
        Solo incluye destinos alcanzables (costo < inf).
        """
        dist, prev = self.dijkstra(start)
        table = []
        for dest, cost in dist.items():
            if dest == start or cost == math.inf:
                continue
            nh = self._next_hop(start, dest, prev)
            if nh is None:
                continue
            table.append({
                "destination": dest,
                "next_hop":    nh,
                "cost":        round(cost, 4)
            })
        return sorted(table, key=lambda e: e["destination"])

    # ═══════════════════════════════════════════════ todas las tablas
    def generate_all_routing_tables(self) -> dict:
        """
        Genera tablas para TODOS los routers activos.
        Solo aparecen routers con status ACTIVE/ACTIVO.
        """
        active_ids = self._active_ids()
        if active_ids is None:
            # Sin router_dao: usar todos los nodos de la topología
            topology = self._get_active_topology()
            all_nodes = set(topology.keys())
            for nbs in topology.values():
                for nb in nbs:
                    all_nodes.add(nb["neighbor_id"])
            active_ids = all_nodes

        if not active_ids:
            return {}

        return {
            rid: self.generate_routing_table(rid)
            for rid in sorted(active_ids)
        }

    # ═══════════════════════════════════════════════════ mejor ruta completa
    def get_full_path(self, start: str, destination: str) -> tuple:
        """
        Devuelve el camino completo más corto y su costo total.

        Retorna:
            (path: list[str], cost: float)
            path vacío y cost=inf si no hay ruta.
        """
        dist, prev = self.dijkstra(start)

        if destination not in dist or dist[destination] == math.inf:
            return [], math.inf

        if start == destination:
            return [start], 0.0

        # Reconstruir el camino desde destino hacia origen
        path    = []
        current = destination
        visited = set()

        while current is not None and current not in visited:
            path.append(current)
            visited.add(current)
            if current == start:
                break
            current = prev.get(current)

        if not path or path[-1] != start:
            return [], math.inf

        path.reverse()
        return path, dist[destination]

    # ═══════════════════════════════════════════════════════════ helpers
    def _next_hop(self, start: str, destination: str, prev: dict):
        """
        Determina el primer salto desde 'start' hacia 'destination'.

        CORRECCIÓN: reconstruye el camino completo y devuelve el segundo
        nodo. Esto es correcto tanto para saltos directos (R1→R4, donde
        prev[R4]=R1 y el next_hop ES R4) como para rutas multi-salto
        (R1→R2→R3, donde next_hop es R2).

        Bug anterior: el while `prev.get(current) != start` saltaba
        el caso de salto directo porque la condición era falsa desde
        el primer momento (prev[dest]==start ya es el start).
        """
        if destination not in prev:
            return None

        # Reconstruir el camino completo hacia atrás
        path    = []
        current = destination
        visited = set()

        while current is not None and current not in visited:
            path.append(current)
            visited.add(current)
            if current == start:
                break
            current = prev.get(current)

        if not path or path[-1] != start:
            return None

        path.reverse()  # ahora: [start, hop1, hop2, ..., destination]

        # El next_hop es el segundo elemento (índice 1)
        if len(path) < 2:
            return None
        return path[1]

    def _get_active_topology(self) -> dict:
        """Topología filtrada solo a routers activos."""
        topology = self.topology_dao.get_topology()
        active   = self._active_ids()
        if active is None:
            return topology

        result = {}
        for rid, nbs in topology.items():
            if rid not in active:
                continue
            # Solo incluir enlaces hacia vecinos que también estén activos
            active_nbs = [nb for nb in nbs if nb["neighbor_id"] in active]
            if active_nbs:
                result[rid] = active_nbs
        return result

    def _active_ids(self):
        """Conjunto de IDs de routers activos, o None si no hay router_dao."""
        if self.router_dao is None:
            return None
        return {
            r.router_id
            for r in self.router_dao.get_all_routers()
            if r.status.upper() in self.ACTIVE_STATUSES
        }
