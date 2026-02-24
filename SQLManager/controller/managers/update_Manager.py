''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''

from functools import wraps
from typing    import Optional, Union, Callable, TYPE_CHECKING

from ..BaseEnumController  import BaseEnumController
from ..EDTController       import EDTController

from ._conditions_Managers import FieldCondition, BinaryExpression

if TYPE_CHECKING:
    from ..TableController import TableController

class UpdateManager:
    """
    Gerencia operações UPDATE com validação automática
    """

    @staticmethod
    def validate_update(func: Callable) -> Callable:
        '''Decorator para validar operações de UPDATE'''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            validate = self.validate_fields()
            if not validate['valid']:
                raise Exception(validate['error'])
            
            if not hasattr(self, 'RECID') or self._get_field_instance('RECID').value is None:
                raise Exception("Atualização sem chave primaria, preencha o campo RECID")
            
            recid_instance = self._get_field_instance('RECID')
            if not self._check_exists(recid_instance == recid_instance.value):
                raise Exception(f"Registro com RECID {recid_instance.value} não existe na tabela {self.table_name}")
            
            return func(self, *args, **kwargs)
        return wrapper
    
    @validate_update
    def update(controller: 'TableController', _values) -> bool:
        """
        Atualiza um registro existente na tabela
        Returns:
            bool: True se atualizado com sucesso
        """
        recid_instance  = controller._get_field_instance('RECID')
        record          = list(filter(lambda r: r['RECID'] == recid_instance.value, controller.records))
        
        values      = []
        set_clauses = []
        
        for key in controller.__dict__:
            attr = controller._get_field_instance(key)

            if not (isinstance(attr, (EDTController, BaseEnumController, BaseEnumController.Enum))) or key == 'RECID':
                continue
            
            if record:
                old_val = record[0].get(key)
                new_val = _values[0].get(key)
                
                # print(f"Comparando campo {key}: antigo={old_val!r} novo={new_val!r}")
                if old_val == new_val:
                    continue

            set_clauses.append(f"{key} = ?")
            values.append(new_val)
        
        if not values:
            raise Exception("Nenhum campo foi alterado para atualizar.")
        
        query = f"UPDATE {controller.table_name} SET " + ", ".join(set_clauses) + " WHERE RECID = ?"
        values.append(controller._get_field_instance('RECID').value)
        
        try:
            with controller.db.transaction() as trs:
                trs.executeCommand(query, tuple(values))                        
            
            recid_instance = controller._get_field_instance('RECID')
            controller.select().where(recid_instance == recid_instance.value).limit(1).do_update(False).execute()

            updated_record = controller.records[0] if controller.records else None
            
            if updated_record:
                controller.set_current(updated_record)
            
            return True
        except Exception as error:            
            raise Exception(f"Erro ao atualizar registro: {error}")
    
    def update_recordset(controller: 'TableController', where: Optional[Union[FieldCondition, BinaryExpression]] = None, **fields) -> int:
        """
        Atualiza múltiplos registros em massa
        Args:
            where: Condição WHERE (usando operadores sobrecarregados)
            **fields: Campos a atualizar como kwargs
                Ex: item.update_recordset(where=item.PRICE < 100, ACTIVE=False, PRICE=50)
        Returns:
            int: Número de registros afetados
        """
        validate = controller.validate_fields()
        if not validate['valid']:
            raise Exception(validate['error'])
        
        if not fields:
            raise Exception("Nenhum campo para atualizar")
        
        table_columns = controller.get_table_columns()
        col_names     = [col[0] for col in table_columns]
        
        set_values = {}

        for field_key, field_val in fields.items():
            field_name = field_key.upper()
            if field_name not in col_names:
                raise Exception(f"Campo '{field_name}' não existe na tabela {controller.table_name}")
            set_values[field_name] = field_val
        
        set_clauses = [f"{field} = ?" for field in set_values.keys()]
        query       = f"UPDATE {controller.table_name} SET " + ", ".join(set_clauses)
        values      = list(set_values.values())
        
        if where:
            where_sql, where_values = where.to_sql()
            query += f" WHERE {where_sql}"
            values.extend(where_values if isinstance(where_values, list) else [where_values])
        
        try:
            with controller.db.transaction() as trs:
                cursor        = trs.executeCommand(query, tuple(values))
                affected_rows = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            return affected_rows
        except Exception as error:            
            raise Exception(f"Erro ao atualizar registros em massa: {error}")

''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''