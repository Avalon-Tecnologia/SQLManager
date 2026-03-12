''' [BEGIN CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
"""
WebSocket Manager para SQLManager
Gerencia conexões WebSocket e broadcast de eventos de banco de dados em tempo real.

Funcionalidades:
- Broadcast automático de INSERT/UPDATE/DELETE
- Rooms por tabela (clientes podem se inscrever em tabelas específicas)
- Dois modos de notificação:
  1. Simple: apenas notificação (action, table, recid)
  2. Full: notificação + dados completos do registro

Uso:
    # No servidor Flask
    ws_manager = WebSocketManager(app, socketio)
    
    # Broadcast automático
    ws_manager.broadcast_insert('ProductsTable', 123, data={...})
    ws_manager.broadcast_update('ProductsTable', 123, data={...})
    ws_manager.broadcast_delete('ProductsTable', 123)
"""

from typing import Any, Dict, Optional
import json

try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("[WARNING] flask-socketio não instalado. WebSocket desabilitado. Instale com: pip install flask-socketio")

class WebSocketManager:
    """Gerencia WebSocket para atualizações em tempo real do banco de dados"""
    
    def __init__(self, app=None, socketio: Optional[SocketIO] = None):
        """
        Inicializa o WebSocket Manager.
        
        Args:
            app: Flask app instance
            socketio: SocketIO instance (se None, cria automaticamente)
        """
        self.app = app
        self.enabled = SOCKETIO_AVAILABLE
        
        if self.enabled:
            if socketio is None and app is not None:
                # Cria SocketIO automaticamente
                self.socketio = SocketIO(app, cors_allowed_origins="*")
            else:
                self.socketio = socketio
            
            # Registra event handlers
            if self.socketio:
                self._register_events()
        else:
            self.socketio = None
    
    def _register_events(self):
        """Registra event handlers do SocketIO"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Cliente conectou ao WebSocket"""
            print('[WebSocket] Client connected')
            emit('connection_response', {
                'status': 'connected',
                'message': 'Connected to SQLManager WebSocket',
                'features': ['simple_notifications', 'full_data_sync']
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Cliente desconectou"""
            print('[WebSocket] Client disconnected')
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """
            Cliente se inscreve em uma tabela.
            Exemplo: socket.emit('subscribe', {table: 'ProductsTable'})
            """
            table_name = data.get('table', '').upper()
            if table_name:
                join_room(table_name)
                print(f'[WebSocket] Client subscribed to {table_name}')
                emit('subscribed', {
                    'table': table_name,
                    'message': f'Subscribed to {table_name} updates'
                })
            else:
                emit('error', {'message': 'Missing table name'})
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """
            Cliente cancela inscrição em uma tabela.
            Exemplo: socket.emit('unsubscribe', {table: 'ProductsTable'})
            """
            table_name = data.get('table', '').upper()
            if table_name:
                leave_room(table_name)
                print(f'[WebSocket] Client unsubscribed from {table_name}')
                emit('unsubscribed', {
                    'table': table_name,
                    'message': f'Unsubscribed from {table_name}'
                })
    
    def broadcast_insert(self, table_name: str, recid: int, data: Optional[Dict[str, Any]] = None):
        """
        Broadcast de INSERT para clientes inscritos.
        
        Args:
            table_name: Nome da tabela
            recid: ID do registro inserido
            data: Dados do registro (opcional, envia notificação completa se fornecido)
        """
        if not self.enabled or not self.socketio:
            return
        
        table_upper = table_name.upper()
        
        # Notificação simples (sempre enviada)
        simple_notification = {
            'action': 'insert',
            'table': table_name,
            'recid': recid
        }
        self.socketio.emit('db_notification', simple_notification, room=table_upper)
        
        # Notificação completa (se data fornecido)
        if data:
            full_notification = {
                'action': 'insert',
                'table': table_name,
                'recid': recid,
                'data': data
            }
            self.socketio.emit('db_data_sync', full_notification, room=table_upper)
        
        print(f'[WebSocket] Broadcasted INSERT for {table_name} (RECID: {recid})')
    
    def broadcast_update(self, table_name: str, recid: int, data: Optional[Dict[str, Any]] = None):
        """
        Broadcast de UPDATE para clientes inscritos.
        
        Args:
            table_name: Nome da tabela
            recid: ID do registro atualizado
            data: Dados atualizados (opcional)
        """
        if not self.enabled or not self.socketio:
            return
        
        table_upper = table_name.upper()
        
        # Notificação simples
        simple_notification = {
            'action': 'update',
            'table': table_name,
            'recid': recid
        }
        self.socketio.emit('db_notification', simple_notification, room=table_upper)
        
        # Notificação completa
        if data:
            full_notification = {
                'action': 'update',
                'table': table_name,
                'recid': recid,
                'data': data
            }
            self.socketio.emit('db_data_sync', full_notification, room=table_upper)
        
        print(f'[WebSocket] Broadcasted UPDATE for {table_name} (RECID: {recid})')
    
    def broadcast_delete(self, table_name: str, recid: int):
        """
        Broadcast de DELETE para clientes inscritos.
        
        Args:
            table_name: Nome da tabela
            recid: ID do registro deletado
        """
        if not self.enabled or not self.socketio:
            return
        
        table_upper = table_name.upper()
        
        # Notificação simples (DELETE não precisa de dados completos)
        notification = {
            'action': 'delete',
            'table': table_name,
            'recid': recid
        }
        self.socketio.emit('db_notification', notification, room=table_upper)
        
        print(f'[WebSocket] Broadcasted DELETE for {table_name} (RECID: {recid})')
    
    def broadcast_batch(self, table_name: str, action: str, count: int):
        """
        Broadcast de operação em lote (ex: update_recordset, delete_from).
        
        Args:
            table_name: Nome da tabela
            action: Tipo de ação ('update', 'delete')
            count: Número de registros afetados
        """
        if not self.enabled or not self.socketio:
            return
        
        table_upper = table_name.upper()
        
        notification = {
            'action': f'batch_{action}',
            'table': table_name,
            'affected_count': count
        }
        self.socketio.emit('db_notification', notification, room=table_upper)
        
        print(f'[WebSocket] Broadcasted BATCH_{action.upper()} for {table_name} ({count} records)')

''' [END CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
