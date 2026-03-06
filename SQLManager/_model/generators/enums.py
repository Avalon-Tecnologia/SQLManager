

"""
Por meio deste arquivo adicionar todos os Enums (Base Enums) que são chaves do SQLManager, DataType e NoYes.
Esses Enums são usados para garantir a consistência dos dados para a controladora e suas informações.
"""

__all__ = [
    'Ensures',
]

Ensures = {
    "DataType": '''
from typing import Self
from SQLManager import BaseEnumController

class DataType(BaseEnumController.Enum):
    """
    Enumeração de tipos de dados (texto/texto), com label descritivo.
    """
    Null     : Self = ("NoneType",  "Tipo de dado Nulo")
    String   : Self = ("str",       "Tipo de dado String")
    Number   : Self = ("int",       "Tipo de dado Number")
    Float    : Self = ("float",     "Tipo de dado Float")
    Boolean  : Self = ("bool",      "Tipo de dado Boolean")
    Array    : Self = ("list",      "Tipo de dado Lista")
    Object   : Self = ("dict",      "Tipo de dado Dicionário")
    Tuple    : Self = ("tuple",     "Tipo de dado Tupla")
    Set      : Self = ("set",       "Tipo de dado Conjunto")
    Bytes    : Self = ("bytes",     "Tipo de dado Bytes")
    Function : Self = ("function",  "Tipo de dado Função")
    Class    : Self = ("type",      "Tipo de dado Classe")
    Date     : Self = ("date",      "Tipo de dado Data (YYYY-MM-DD)")
    DateTime : Self = ("datetime",  "Tipo de dado Data/Hora (YYYY-MM-DD HH:MM:SS)")
    Undefined: Self = ("undefined", "Tipo de dado Indefinido")
''',
    "NoYes": '''
from typing import Self
from SQLManager import BaseEnumController

class NoYes(BaseEnumController.Enum):
    """
    Enumeração de sim e não (int/texto), com label descritivo.
    """
    No  : Self = (0, "Não")
    Yes : Self = (1, "Sim")
''',
#[BEGIN CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {06/03/2026}
    "SequenceTypes": '''
from typing import Self
from SQLManager import BaseEnumController

class SequenceTypes(BaseEnumController.Enum):
    """
    Enumeração dos tipos de cada parte da sequencia.
    """
    UNDEFINED       : Self = (0, "Indefinido")
    CONSTANT        : Self = (1, "Constante")
    SEPARATOR       : Self = (2, "Separador")
    NUMERIC         : Self = (3, "Numeric")
'''
#[END CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {06/03/2026}
}
