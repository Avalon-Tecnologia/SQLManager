''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''

from typing import Any, Optional, Union, Callable

class FieldCondition:
    '''
    Representa uma condição de campo com operador para construção de WHERE clauses
    Também suporta uso em if/while através de __bool__
    '''
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def __init__(self, field_name: str, operator: str, value: Any, table_alias: Optional[str] = None, left_value: Any = None, right_field_name: Optional[str] = None, right_table_alias: Optional[str] = None):
        self.field_name        = field_name
        self.operator          = operator
        self.value             = value
        self.table_alias       = table_alias
        self.left_value        = left_value  # Valor do campo (lado esquerdo da comparação)
        self.right_field_name  = right_field_name  # Nome do campo direito (para JOINs)
        self.right_table_alias = right_table_alias  # Alias da tabela direita (para JOINs)
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    
    def __and__(self, other: 'FieldCondition') -> 'BinaryExpression':
        return BinaryExpression(self, 'AND', other)
    
    def __or__(self, other: 'FieldCondition') -> 'BinaryExpression':
        return BinaryExpression(self, 'OR', other)
    
    def __bool__(self) -> bool:
        '''Permite usar em if/while - executa comparação Python real'''
        if self.left_value is None:
            return True  # Se não temos valor do campo, assume True
        
        left  = self.left_value
        right = self.value
        
        match self.operator:
            case '=':
                return left == right            
            case '==':
                return left == right            
            case '!=':
                return left != right
            case '<':
                return left < right
            case '<=':
                return left <= right        
            case '>':
                return left > right
            case '>=':
                return left >= right
            case 'IS':
                return left is right
            case 'IS NOT':
                return left is not right
            case 'IN':
                return left in right
            case 'NOT IN':
                return left not in right
            case 'LIKE':
                import re
                pattern = str(right).replace('%', '.*').replace('_', '.')
                return bool(re.match(pattern, str(left)))
            case 'NOT LIKE':
                import re
                pattern = str(right).replace('%', '.*').replace('_', '.')
                return not bool(re.match(pattern, str(left)))
            case _:
                return True  # Operador desconhecido, assume True para evitar falhas                    
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def to_sql(self) -> tuple:
        '''Converte a condição para SQL'''
        prefix = f"{self.table_alias}." if self.table_alias else ""
                
        if self.right_field_name is not None:
            right_prefix = f"{self.right_table_alias}." if self.right_table_alias else ""
            sql = f"{prefix}{self.field_name} {self.operator} {right_prefix}{self.right_field_name}"
            return (sql, [])  # Sem valores para binding
                
        sql = f"{prefix}{self.field_name} {self.operator} ?"
        return (sql, self.value)
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''

class BinaryExpression:
    '''Representa uma expressão binária entre condições'''
    def __init__(self, left: Union[FieldCondition, 'BinaryExpression'], 
                 operator: str, 
                 right: Union[FieldCondition, 'BinaryExpression']):
        self.left     = left
        self.operator = operator
        self.right    = right
    
    def __and__(self, other: Union[FieldCondition, 'BinaryExpression']) -> 'BinaryExpression':
        return BinaryExpression(self, 'AND', other)
    
    def __or__(self, other: Union[FieldCondition, 'BinaryExpression']) -> 'BinaryExpression':
        return BinaryExpression(self, 'OR', other)
    
    def to_sql(self) -> tuple:
        '''Converte a expressão para SQL recursivamente'''
        left_sql, left_val   = self.left.to_sql()
        right_sql, right_val = self.right.to_sql()
        
        left_values  = left_val if isinstance(left_val, list) else [left_val]
        right_values = right_val if isinstance(right_val, list) else [right_val]
        
        sql    = f"({left_sql} {self.operator} {right_sql})"
        values = left_values + right_values
        
        return (sql, values)
    
''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''