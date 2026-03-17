''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
from ..CoreConfig  import CoreConfig
from ..connection  import database_connection as data
from ..controller  import ViewController, TableController,EDTController, BaseEnumController, NumberSequenceController

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


class Recid(EDTController):
    """
    Identificador numérico exclusivo.
    Args:
        value number: Identificador a ser validado
    """
    def __init__(self, value: EDTController.any_type = 0):
        super().__init__("onlyNumbers", DataType.Number, value)

__all__ = ["DataType", "Recid", "ViewController", "TableController", "EDTController", "BaseEnumController", "NumberSequenceController", "data", "CoreConfig"]

''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''