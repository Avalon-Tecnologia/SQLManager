import threading
import hashlib
import json
import time

class DatabaseWatcher:
    def __init__(self, db, socketio):
        self.db       = db
        self.socketio = socketio
        self._tables  = {}
        self._running = False
        self._thread  = None

    def watch(self, table_name: str, interval: int = 5, query: str = None):
        self._tables[table_name] = {
            'interval':   interval,
            'last_hash':  None,
            'last_check': 0,
            'query':      query or f"SELECT * FROM {table_name}"
        }

    def _get_hash(self, table_name: str, conn) -> str | None:
        cfg = self._tables[table_name]
        try:
            cursor = conn.cursor()
            cursor.execute(cfg['query'])
            rows = cursor.fetchall()
            cursor.close()
            content = json.dumps([list(r) for r in rows], default=str)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            print(f'[Watcher] Erro ao verificar {table_name}: {e}')
            return None

    def _loop(self):
        # Pega uma conexão dedicada do pool para o watcher
        conn = None
        try:
            conn = self.db._get_connection()
            conn.autocommit = True
            print('[Watcher] Conexão dedicada obtida')
        except Exception as e:
            print(f'[Watcher] Falha ao obter conexão: {e}')
            return

        while self._running:
            now = time.time()

            for table_name, cfg in self._tables.items():
                if now - cfg['last_check'] < cfg['interval']:
                    continue

                cfg['last_check'] = now
                current_hash = self._get_hash(table_name, conn)

                if current_hash is None:
                    continue

                if cfg['last_hash'] is None:
                    cfg['last_hash'] = current_hash
                    continue

                if current_hash != cfg['last_hash']:
                    cfg['last_hash'] = current_hash
                    print(f'[Watcher] Mudança detectada em {table_name}')
                    self.socketio.emit(
                        'db_notification',
                        {'action': 'external_change', 'table': table_name},
                        room=table_name.upper()
                    )

            time.sleep(1)

        # Devolve conexão ao pool ao parar
        if conn:
            self.db._return_connection(conn)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f'[Watcher] Iniciado monitorando {len(self._tables)} tabela(s)')

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)