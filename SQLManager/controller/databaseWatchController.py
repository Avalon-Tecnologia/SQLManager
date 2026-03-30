# DatabaseWatcher.py
import threading
import hashlib
import json
import time

class DatabaseWatcher:
    """
    Monitora tabelas do banco em background.
    Quando detecta mudança, emite evento via WebSocket.
    
    Uso:
        watcher = DatabaseWatcher(db, socketio)
        watcher.watch('AnalisysGroupInfo', interval=5)
        watcher.watch('ProductsTable', interval=10)
        watcher.start()
    """

    def __init__(self, db, socketio):
        self.db       = db
        self.socketio = socketio
        self._tables  = {}   # {table_name: {interval, last_hash, query}}
        self._running = False
        self._thread  = None

    def watch(self, table_name: str, interval: int = 5, query: str = None):
        """
        Registra uma tabela para monitoramento.
        
        Args:
            table_name: Nome da tabela no banco
            interval:   Intervalo de verificação em segundos
            query:      Query customizada (padrão: SELECT * FROM table)
        """
        self._tables[table_name] = {
            'interval':   interval,
            'last_hash':  None,
            'last_check': 0,
            'query':      query or f"SELECT * FROM {table_name}"
        }

    def _get_hash(self, table_name: str) -> str | None:
        """Executa a query e retorna hash do resultado."""
        cfg = self._tables[table_name]
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(cfg['query'])
            rows = cursor.fetchall()
            cursor.close()

            # Hash do resultado serializado
            content = json.dumps([list(r) for r in rows], default=str)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            print(f'[Watcher] Erro ao verificar {table_name}: {e}')
            return None

    def _loop(self):
        """Loop principal — roda em thread separada."""
        while self._running:
            now = time.time()

            for table_name, cfg in self._tables.items():
                # Verifica se está na hora de checar essa tabela
                if now - cfg['last_check'] < cfg['interval']:
                    continue

                cfg['last_check'] = now
                current_hash = self._get_hash(table_name)

                if current_hash is None:
                    continue

                # Primeira verificação — apenas armazena o hash
                if cfg['last_hash'] is None:
                    cfg['last_hash'] = current_hash
                    continue

                # Hash mudou — emite evento
                if current_hash != cfg['last_hash']:
                    cfg['last_hash'] = current_hash
                    print(f'[Watcher] Mudança detectada em {table_name}')
                    self.socketio.emit(
                        'db_notification',
                        {'action': 'external_change', 'table': table_name},
                        room=table_name.upper()
                    )

            time.sleep(1)  # Granularidade de 1s

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